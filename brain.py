"""
brain.py
--------
"Cerebro" del asistente. Envía el texto transcrito del usuario a la API
de Gemini con un prompt de sistema que le indica que debe responder
ÚNICAMENTE en formato JSON, describiendo qué acción ejecutar.

Esto nos permite unificar "responder preguntas" y "ejecutar comandos"
en un solo flujo: si Gemini decide que no hay ninguna acción de
automatización aplicable, devuelve action = "answer_question" con el
texto de la respuesta directa.
"""

import json
import re
import datetime
from google import genai
from google.genai import types

import config
import weather

# Inicializamos el cliente oficial de Gemini
client = genai.Client(api_key=config.GEMINI_API_KEY)

# Historial simple en memoria para mantener contexto conversacional.
_chat_history = []
MAX_HISTORY_TURNS = 6  # cuántos intercambios pasados recordar

SYSTEM_PROMPT = f"""
Eres {config.ASSISTANT_NAME}, un asistente de voz personal inspirado en JARVIS.
Le hablas a {config.USER_NAME}.
Tu personalidad es educada, amigable, eficiente y servicial. Cuando el usuario te
salude o platique contigo de forma casual, responde con naturalidad, calidez y un toque
de caballerosidad (por ejemplo: "Hola, ¿en qué te puedo ayudar hoy?",
"Todo excelente por aquí, ¿qué necesitas?").

Debes responder SIEMPRE y ÚNICAMENTE con un objeto JSON válido, sin texto adicional,
sin bloques markdown ni etiquetas ```json.

El JSON debe tener exactamente esta estructura:
{{
  "action": "<nombre_de_accion>",
  "params": {{ ... }},
  "spoken_response": "<texto corto que se leerá en voz alta al usuario>"
}}

Acciones disponibles (usa "action": "answer_question" si ninguna otra aplica):
- "open_website": params: {{"url": "<dominio o URL>"}}
- "search_youtube": params: {{"query": "<término de búsqueda>"}}
- "search_google": params: {{"query": "<término de búsqueda>"}}
- "set_volume": params: {{"percent": <0-100>}}
- "set_app_volume": params: {{"app_name": "<nombre del programa, ej: spotify, chrome>", "percent": <0-100>}}
- "volume_up": params: {{}}
- "volume_down": params: {{}}
- "mute_volume": params: {{}}
- "media_play_pause": params: {{}}
- "media_next": params: {{}}
- "media_previous": params: {{}}
- "open_app": params: {{"app_name": "<nombre del programa>"}}
- "play_spotify_track": params: {{"query": "<nombre de la canción y, si lo menciona, el artista, ej: 'Positions Ariana Grande'>"}}
- "get_current_date": params: {{}}
- "get_current_time": params: {{}}
- "answer_question": params: {{"text": "<respuesta concisa, cordial y directa>"}}
- "send_whatsapp_message": params: {{"contact_name": "<nombre guardado>", "message": "<texto a enviar>"}}

Reglas importantes:
1. "spoken_response" debe ser SIEMPRE una frase corta, fluida y hablada en voz alta
   (máximo 2 oraciones). Nunca lo dejes vacío.
2. Si el usuario te saluda ("hola", "buenos días") o pregunta cómo estás, usa "answer_question",
   responde amigablemente en "params.text" y pon un saludo cordial en "spoken_response".
3. Si el usuario pregunta la fecha u hora actual, usa "get_current_date" o "get_current_time".
4. Si pide ajustar el volumen de un programa específico (Spotify, juegos, navegador), usa "set_app_volume".
5. Si pide reproducir, poner, o escuchar una canción o artista específico, usa "play_spotify_track"
   (NO uses "open_app" para esto, ya que eso solo abre la app vacía sin reproducir nada).
6. No agregues texto ni explicaciones fuera de la estructura JSON.
7. Si te preguntan por el clima, la fecha o la hora, USA EXCLUSIVAMENTE los datos
   del bloque [CONTEXTO ACTUAL], nunca los inventes.
"""


def _clean_json_response(raw_text: str) -> str:
    """Limpia envolturas markdown en caso de que Gemini devuelva bloques de código."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


def _build_context() -> str:
    now = datetime.datetime.now()
    fecha = now.strftime("%A %d de %B, %Y")
    hora = now.strftime("%H:%M")
    clima = weather.get_today_weather()
    return (
        f"[CONTEXTO ACTUAL]\n"
        f"Fecha: {fecha} | Hora: {hora}\n"
        f"Clima en Lima, Perú: {clima}\n"
    )


def get_intent_from_text(user_text: str) -> dict:
    """
    Envía el texto del usuario a Gemini y devuelve un diccionario parseado
    con las claves: action, params, spoken_response.
    """
    global _chat_history

    history_text = ""
    for turn in _chat_history[-MAX_HISTORY_TURNS:]:
        history_text += f"Usuario: {turn['user']}\n{config.ASSISTANT_NAME} (JSON previo): {turn['assistant']}\n"
    contexto = _build_context()
    full_prompt = f"{SYSTEM_PROMPT}\n\n{contexto}\n{history_text}\nUsuario: {user_text}\n{config.ASSISTANT_NAME}:"
    raw_text = ""
    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        raw_text = response.text or ""
        cleaned = _clean_json_response(raw_text)
        data = json.loads(cleaned)

        if "action" not in data:
            raise ValueError("Falta la clave 'action' en la respuesta del modelo.")
        data.setdefault("params", {})
        data.setdefault("spoken_response", "Listo.")

        _chat_history.append({"user": user_text, "assistant": cleaned})

        return data

    except json.JSONDecodeError:
        return {
            "action": "answer_question",
            "params": {"text": raw_text.strip() if raw_text else "No entendí bien, ¿puedes repetirlo?"},
            "spoken_response": raw_text.strip()[:200] if raw_text else "No entendí bien, ¿puedes repetirlo?",
        }
    except Exception as e:
        print(f"[Error de Gemini API]: {e}")
        return {
            "action": "answer_question",
            "params": {"text": "Ocurrió un error al procesar tu solicitud."},
            "spoken_response": "Tuve un problema procesando eso. Intenta de nuevo.",
            "_error": str(e),
        }


def reset_conversation():
    """Limpia la memoria conversacional."""
    global _chat_history
    _chat_history = []