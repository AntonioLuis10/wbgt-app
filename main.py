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

# ESTA ES LA RUTA NUEVA QUE RECIBE LAS COORDENADAS DESDE TU LISTA DESPLEGABLE
@app.get("/api/weather")
async def get_weather(lat: float, lon: float, loc: str):
    async with httpx.AsyncClient() as client:
        # URL corregida para minutely_15 (pidiendo 1 día para no saturar)
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation&minutely_15=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation&wind_speed_unit=ms&forecast_days=1&timezone=auto"
        weather_resp = await client.get(weather_url)
        weather_data = weather_resp.json()
        
        # Si la API devuelve un error (ej. falta una variable), lanzamos el 404
        if "error" in weather_data:
             raise HTTPException(status_code=404, detail="Error en Open-Meteo")

        return {
            "location": loc, 
            "current": {
                "ta": weather_data["current"]["temperature_2m"],
                "rh": weather_data["current"]["relative_humidity_2m"],
                "v": weather_data["current"]["wind_speed_10m"],
                "sr": weather_data["current"]["shortwave_radiation"]
            },
            # Enviamos la matriz minutely_15
            "minutely_15": weather_data["minutely_15"]
        }

# PYTHON ENTREGA LA WEB DIRECTAMENTE
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
