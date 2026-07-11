# app/main.py
from fastapi import FastAPI
from app.routers import sensor_router

app = FastAPI(title="FARO Sensor Service")
app.include_router(sensor_router.router, prefix="/api/sensors")