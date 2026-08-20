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

# ESTA ES LA RUTA NUEVA PARA EL TIEMPO Y LA PREVISIÓN
@app.get("/api/weather")
async def get_weather(city: str):
    async with httpx.AsyncClient() as client:
        # 1. Buscar latitud y longitud
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=es&format=json"
        geo_resp = await client.get(geo_url)
        geo_data = geo_resp.json()
        
        if not geo_data.get("results"):
            raise HTTPException(status_code=404, detail="Ciudad no encontrada")
            
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        
        # 1. Extraemos todos los niveles de organización territorial
        city_name = geo_data["results"][0].get("name", city)
        provincia = geo_data["results"][0].get("admin2", "") # Provincia
        ccaa = geo_data["results"][0].get("admin1", "")      # Comunidad Autónoma o Estado
        pais = geo_data["results"][0].get("country", "")     # País
        
        # 2. Construimos la frase evitando que se repitan nombres (Ej: Madrid, Madrid)
        location_parts = []
        if city_name: location_parts.append(city_name)
        if provincia and provincia not in location_parts: location_parts.append(provincia)
        if ccaa and ccaa not in location_parts: location_parts.append(ccaa)
        if pais and pais not in location_parts: location_parts.append(pais)
        
        full_location = ", ".join(location_parts)
        
        # 3. Pedimos los datos del tiempo
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation&wind_speed_unit=ms&forecast_hours=24&timezone=auto"
        weather_resp = await client.get(weather_url)
        weather_data = weather_resp.json()
        
        return {
            "location": full_location, # <-- Envía la ubicación completa a la web
            "current": {
                "ta": weather_data["current"]["temperature_2m"],
                "rh": weather_data["current"]["relative_humidity_2m"],
                "v": weather_data["current"]["wind_speed_10m"],
                "sr": weather_data["current"]["shortwave_radiation"]
            },
            "hourly": weather_data["hourly"]
        }

# PYTHON ENTREGA LA WEB DIRECTAMENTE
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
