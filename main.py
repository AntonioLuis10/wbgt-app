from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class WeatherData(BaseModel):
    ta: float
    rh: float
    v: float
    sr: float

@app.post("/api/wbgt")
def calculate_wbgt(data: WeatherData):
    tw = (data.ta * math.atan(0.151977 * math.pow(data.rh + 8.313659, 0.5)) +
          math.atan(data.ta + data.rh) - math.atan(data.rh - 1.676331) +
          0.00391838 * math.pow(data.rh, 1.5) * math.atan(0.023101 * data.rh) - 4.686035)

    tnw = tw + (data.sr * 0.01) - (data.v * 0.1)
    tg = data.ta + (data.sr * 0.015) / (max(data.v, 0.1) ** 0.6)
    
    wbgt = 0.7 * tnw + 0.2 * tg + 0.1 * data.ta

    risk_level = "Riesgo Bajo (Operación Normal)"
    if wbgt >= 31.0:
        risk_level = "Riesgo Letal / Límite Acción Ligero"
    elif wbgt >= 28.0:
        risk_level = "Límite Acción (Trabajo Moderado)"
    elif wbgt >= 25.0:
        risk_level = "Precaución (Trabajo Pesado)"

    return {
        "wbgt": round(wbgt, 2),
        "risk": risk_level
    }

# ESTO ES LO NUEVO: Python entrega la web directamente
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()