from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import math
import httpx

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
    
    if wbgt > 28.9:
        risk_level = "Bandera Negra (Peligro Extremo)"
    elif wbgt >= 27.3:
        risk_level = "Bandera Roja (Riesgo Muy Alto)"
    elif wbgt >= 25.1:
        risk_level = "Bandera Naranja (Riesgo Alto)"
    elif wbgt >= 22.2:
        risk_level = "Bandera Amarilla (Riesgo Moderado)"
    else:
        risk_level = "Bandera Verde (Riesgo Bajo)"

    return {
        "wbgt": round(wbgt, 2),
        "risk": risk_level
    }

@app.get("/api/weather")
async def get_weather(lat: float, lon: float, loc: str):
    async with httpx.AsyncClient() as client:
        # CORRECCIÓN: Quitamos el bloque 'current' porque Open-Meteo no acepta Radiación Solar ahí.
        # Pedimos solo 'minutely_15' para extraer luego la hora actual.
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&minutely_15=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation&wind_speed_unit=ms&forecast_days=2&timezone=auto"
        
        weather_resp = await client.get(weather_url)
        weather_data = weather_resp.json()
        
        # Si Open-Meteo nos da error de sintaxis, lo atrapamos para verlo claro
        if "error" in weather_data:
            reason = weather_data.get("reason", "Error desconocido de Open-Meteo")
            raise HTTPException(status_code=400, detail=reason)
        
        return {
            "location": loc, 
            "minutely_15": weather_data.get("minutely_15", {})
        }

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })
