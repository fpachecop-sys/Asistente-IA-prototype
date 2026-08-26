"""
config.py
---------
Configuración centralizada del asistente. Lee la API Key de Gemini desde
un archivo .env (recomendado) o desde variable de entorno del sistema.

NUNCA subas tu .env a un repositorio público (agrégalo a .gitignore).
"""

import os
from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env (si existe)
load_dotenv()

# ==========================
#   CLAVES / CREDENCIALES
# ==========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Spotify (Client Credentials: solo para BUSCAR canciones, no requiere
# login de usuario ni cuenta Premium). Sácalas gratis en:
# https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# ==========================
#   MODELO DE GEMINI
# ==========================
# gemini-3.6-flash es el modelo Flash vigente (rápido/económico) al momento
# de escribir esto. Google descontinúa modelos con frecuencia; si vuelve a
# dar error 404 "no longer available", el mensaje de error de la propia
# API suele indicar el modelo de reemplazo recomendado.
# Cambia esta línea para pasar de 20 a 500 usos al día:
GEMINI_MODEL_NAME = "gemini-3.1-flash-lite"

# ==========================
#   HOTKEY GLOBAL
# ==========================
# Combinación para activar el micrófono. Sintaxis de la librería `keyboard`.
HOTKEY_ACTIVATE = "k"

# Hotkey adicional para cerrar la app rápidamente
HOTKEY_QUIT = "ctrl+j"

# ==========================
#   VOZ (TTS)
# ==========================
# --- Edge TTS (voces neuronales, gratis, requiere internet) ---
# Es el motor de voz PRINCIPAL: suena mucho más natural que las voces
# nativas de Windows. No requiere API key, solo conexión a internet.
TTS_USE_EDGE = True

# Algunas voces en español disponibles (puedes cambiarla libremente):
#   "es-MX-JorgeNeural"    -> hombre, español México (recomendada, clara)
#   "es-MX-DaliaNeural"    -> mujer, español México
#   "es-ES-AlvaroNeural"   -> hombre, español España
#   "es-ES-ElviraNeural"   -> mujer, español España
#   "es-AR-TomasNeural"    -> hombre, español Argentina
# Ejecuta `edge-tts --list-voices | findstr es-` (Windows) para ver más.
TTS_EDGE_VOICE = "es-MX-DaliaNeural"

# Ajustes de velocidad y volumen en formato de porcentaje relativo
# que exige la librería edge-tts, ej: "+15%", "-10%", "+0%"
TTS_EDGE_RATE = "+12%"
TTS_EDGE_VOLUME = "+0%"

# --- pyttsx3 (fallback 100% offline si Edge TTS falla, ej. sin internet) ---
TTS_RATE = 185          # Velocidad de habla (palabras por minuto aprox.)
TTS_VOLUME = 1.0        # 0.0 a 1.0
TTS_VOICE_INDEX = None  # None = voz por defecto del sistema; usa 0,1,2... para elegir otra

# ==========================
#   RECONOCIMIENTO DE VOZ (STT)
# ==========================
STT_LANGUAGE = "es-ES"          # Cambia a "en-US" si prefieres inglés
STT_TIMEOUT = 5                 # Segundos máximos esperando que el usuario empiece a hablar
STT_PHRASE_TIME_LIMIT = 8       # Segundos máximos de grabación por frase
STT_ENERGY_THRESHOLD = 300      # Sensibilidad del micrófono (ajustar según ambiente/ruido)

# ==========================
#   INTERFAZ (UI)
# ==========================
UI_WIDTH = 260
UI_HEIGHT = 260
UI_ALWAYS_ON_TOP = True
UI_APPEARANCE_MODE = "dark"     # "dark" o "light"
UI_TRANSPARENT_COLOR = "#0d0d0d"  # Color usado como "transparente" (truco de Tkinter)

# Nombre que usará el asistente para referirse a sí mismo en el prompt del sistema
ASSISTANT_NAME = "JARVIS"

# Nombre del usuario (opcional, personaliza las respuestas)
USER_NAME = "Franco"