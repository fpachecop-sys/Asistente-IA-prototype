# weather.py
import requests

LIMA_LAT, LIMA_LON = -12.0464, -77.0428

WEATHER_CODES = {
    0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado",
    3: "nublado", 45: "con neblina", 48: "con neblina escarchada",
    51: "con llovizna ligera", 61: "con lluvia ligera", 63: "con lluvia moderada",
    65: "con lluvia fuerte", 80: "con chubascos", 95: "con tormenta",
}

def get_today_weather() -> str:
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LIMA_LAT,
                "longitude": LIMA_LON,
                "current": "temperature_2m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "America/Lima",
            },
            timeout=5,
        )
        data = r.json()
        temp_now = round(data["current"]["temperature_2m"])
        code = data["current"]["weather_code"]
        desc = WEATHER_CODES.get(code, "variable")
        tmax = round(data["daily"]["temperature_2m_max"][0])
        tmin = round(data["daily"]["temperature_2m_min"][0])
        return f"{temp_now}°C ahora, {desc}, con máxima de {tmax}°C y mínima de {tmin}°C"
    except Exception as e:
        return f"no disponible ({e})"