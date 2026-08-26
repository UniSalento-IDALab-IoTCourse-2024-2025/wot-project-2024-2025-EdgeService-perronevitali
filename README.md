# FARO: EdgeService

## Descrizione del progetto
Il controllo della sicurezza negli ambienti industriali in cui vengono stoccate e movimentate sostanze pericolose rappresenta una delle sfide più delicate nella gestione degli impianti. Con l'aumento della complessità delle operazioni quotidiane, diventa fondamentale disporre di un supporto oggettivo che permetta di valutare in tempo reale se una determinata combinazione di attività concomitanti generi una condizione di rischio.

Per rispondere a questa esigenza è stato sviluppato **FARO** (Framework di Allerta e Rilevamento Operativo), un sistema che realizza un **Digital Twin** dell'area di stoccaggio: una rappresentazione virtuale costantemente sincronizzata con lo stato fisico dell'impianto. FARO integra tre componenti complementari: il monitoraggio ambientale tramite sensori collegati a un Raspberry Pi in ciascuna zona, il tracciamento della posizione e delle autorizzazioni del personale tramite beacon BLE rilevati dall'app mobile, e un modulo di pianificazione delle operazioni che, prima di autorizzare una nuova attività, ne valuta il rischio combinando una formula quantitativa consolidata in letteratura con un modello di Machine Learning. L'obiettivo comune di queste componenti è rispondere, in ogni istante, alla domanda: **è sicuro autorizzare questa operazione, in questa zona, adesso?**

---

## Architettura del sistema
FARO è organizzato secondo un'architettura a microservizi, in cui ciascun componente comunica con gli altri tramite API REST per le richieste sincrone e tramite RabbitMQ per gli eventi asincroni (AMQP tra microservizi, STOMP verso l'app mobile, MQTT per la diffusione degli allarmi d'area). Le principali componenti in cui si articola il sistema sono:

#### UserService
Microservizio Quarkus responsabile della gestione degli utenti (lavoratori e amministratori), dell'autenticazione JWT e della gestione delle code di messaggistica personale di ciascun utente.

#### OperationalService
Microservizio Quarkus responsabile della gestione delle aree, degli item, delle sostanze pericolose e della pianificazione delle task, oltre all'orchestrazione della doppia valutazione del rischio (formula + Machine Learning).

#### MLService
Servizio FastAPI che espone il modello di Machine Learning per la classificazione del rischio delle task e genera, tramite un LLM locale (Ollama), una spiegazione testuale del verdetto.

#### EdgeService *(repository corrente)*
Servizio FastAPI deployato sul Raspberry Pi presente in ogni area, responsabile dell'acquisizione delle misurazioni ambientali dal sensore DHT11 e della diffusione degli allarmi.

#### App mobile React Native
Applicazione sviluppata con React Native ed Expo che consente a lavoratori e amministratori di autenticarsi, tracciare automaticamente la propria posizione tramite beacon BLE, pianificare/evadere le task e ricevere notifiche in tempo reale.

#### RabbitMQ
Message broker che gestisce sia la messaggistica AMQP interna tra microservizi sia i protocolli STOMP e MQTT (tramite i relativi plugin) usati rispettivamente dall'app mobile per la coda personale e per la diffusione degli allarmi d'area con meccanismo di *retain*.

---

Di seguito viene fornita una descrizione dettagliata della componente implementata nella repository corrente.

## EdgeService

### Panoramica
*EdgeService* è il software **FastAPI** deployato su ciascun Raspberry Pi presente nelle aree dell'impianto. Le sue responsabilità sono: l'acquisizione periodica delle letture ambientali, la determinazione dello stato dell'area (normale/pericolo) e la diffusione degli allarmi al personale presente, oltre alla sincronizzazione delle soglie configurate dall'amministratore tramite *OperationalService*.

### Registrazione dell'area e configurazione
All'avvio, il servizio esegue un *handshake* con *OperationalService*: interroga l'endpoint `GET /api/areas/by-beacon` passando il proprio `beaconMAC` (configurato nel file `config.ini`) e, se trova una corrispondenza, memorizza localmente l'identificativo dell'area (`area_registration_service.py`). Se il backend non è raggiungibile al momento dell'avvio, il servizio ricade sull'ultimo `area_id` già memorizzato, garantendo il funzionamento anche in caso di malfunzionamenti del backend.

### Acquisizione delle letture e determinazione dello stato
Il sensore **DHT11** viene interrogato tramite la libreria Adafruit CircuitPython (`sensor_service.py`). Ogni lettura valida viene pubblicata sull'exchange `faro.sensors` di RabbitMQ, a cui *OperationalService* è sottoscritto per aggiornare lo storico e le misurazioni correnti dell'area.

La determinazione dello stato dell'area non si basa sulla singola lettura istantanea, bensì su una **finestra mobile** delle ultime N misurazioni: l'area assume uno stato di pericolo solo quando la media delle letture nella finestra supera la soglia di temperatura o di umidità configurata, e ne esce solo dopo un numero minimo di controlli consecutivi favorevoli. Questo meccanismo evita che singole letture anomale, dovute a rumore del sensore o a fluttuazioni momentanee, generino falsi allarmi o rientri prematuri dallo stato di pericolo.

### Diffusione degli allarmi d'area
Al cambio di stato della propria area, *EdgeService* pubblica un messaggio sul broker RabbitMQ utilizzando il protocollo **MQTT** anziché AMQP, sfruttando il plugin `rabbitmq_mqtt`: la pubblicazione avviene con il flag **retain** attivo sul topic dedicato all'area (`area/{areaId}/danger`), in modo che il broker conservi in memoria l'ultimo messaggio inviato su ciascun sotto-topic. Questo consente a un lavoratore che si sposta in una nuova area (e che quindi si sottoscrive dinamicamente al topic corrispondente dal proprio smartphone) di ricevere immediatamente lo stato corrente dell'area anche se il pericolo era stato segnalato prima del suo arrivo, senza dover attendere un nuovo evento o effettuare una richiesta sincrona al backend. Lo stesso meccanismo viene utilizzato per segnalare l'ingresso di personale non autorizzato in un'area (`area/{areaId}/unauthorized`).

Questa soluzione garantisce continuità di funzionamento anche in caso di malfunzionamento della rete o dei componenti centrali, con il limite che la consegna dell'allarme dipende comunque dalla raggiungibilità del broker RabbitMQ.

### API REST
| Metodo | Path | Descrizione |
|--------|------|-------------|
| GET | `/reading` | Lettura corrente del sensore (temperatura/umidità) |
| GET/PUT | endpoint su router soglie (`threshold_router`) | Lettura e aggiornamento delle soglie configurate per l'area, sincronizzate da *OperationalService* |

### Configurazione (`config.ini`)
Il servizio è configurato tramite un file `config.ini` locale (esempio in `config.ini.example`), suddiviso in sezioni:

| Sezione | Parametri principali |
|---------|----------------------|
| `[server]` | host, porta, debug |
| `[sensor]` | pin GPIO, intervallo di polling, soglie di default di temperatura/umidità |
| `[area]` | nome area, `beacon_mac`, `danger_index_threshold`, IP del Raspberry Pi, `area_id` (valorizzato dopo l'handshake) |
| `[external_api]` | URL base e timeout verso *OperationalService* |
| `[rabbitmq]` | host, porta, credenziali del broker |
| `[mqtt]` | host, porta, credenziali per la pubblicazione retained |
| `[logging]` | livello di log e percorso del file di log |

### Struttura del progetto
```
app/
├── config.py               # Caricamento della configurazione da config.ini
├── constants.py             # Exchange/routing key RabbitMQ, topic MQTT, sliding window
├── domain/
│   └── sensor_reading.py     # Modello di dominio della lettura sensore
├── dto/                      # DTO area, messaggi d'area, letture sensore, soglie
├── exceptions/
│   └── handler.py            # Gestione centralizzata delle eccezioni
├── main.py                    # Entry point FastAPI
├── routers/
│   ├── sensor_router.py         # Endpoint di lettura del sensore
│   └── threshold_router.py      # Endpoint di sincronizzazione soglie
└── services/
    ├── area_registration_service.py   # Handshake con OperationalService (beaconMAC → area_id)
    ├── external_api_service.py        # Client HTTP verso OperationalService
    ├── rabbitmq_service.py            # Pubblicazione AMQP (faro.sensors) e MQTT retained (faro.areas)
    └── sensor_service.py               # Lettura del sensore DHT11 e determinazione dello stato
```

### Tecnologie
- **FastAPI** come framework;
- **Adafruit Blinka** / **Adafruit CircuitPython DHT** per l'accesso ai pin GPIO e la lettura del sensore DHT11;
- **aio-pika** per la messaggistica AMQP verso RabbitMQ;
- **paho-mqtt** per la pubblicazione dei messaggi MQTT con flag *retain*;
- **httpx** per le chiamate REST sincrone verso *OperationalService*;
- **Raspberry Pi** + sensore **DHT11** + **beacon BLE** come hardware di riferimento per ciascuna area;