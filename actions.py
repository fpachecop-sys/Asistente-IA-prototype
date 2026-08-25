"""
actions.py
----------
Módulo de automatización. Recibe un diccionario de "intención" (JSON)
generado por Gemini y ejecuta la acción correspondiente en el sistema
operativo: abrir webs, buscar en YouTube, controlar volumen, abrir
programas, multimedia (play/pause), etc.

Diseñado para ser multiplataforma en lo posible; algunas acciones
(volumen, teclas multimedia) están optimizadas para Windows mediante
`pycaw` / `keyboard`, con fallback silencioso en otros SO.
"""

import os
import platform
import subprocess
import webbrowser
import urllib.parse

SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"

# Intentamos importar pycaw solo si estamos en Windows (no falla en Linux/Mac)
try:
    if SYSTEM == "Windows":
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        PYCAW_AVAILABLE = True
    else:
        PYCAW_AVAILABLE = False
except ImportError:
    PYCAW_AVAILABLE = False

import keyboard
import spotify_control  # también sirve para simular teclas multimedia


# =========================================================
#   CONTROL DE VOLUMEN (Windows via pycaw, fallback teclas)
# =========================================================
def _get_windows_volume_interface():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def set_volume(percent: int):
    """Establece el volumen del sistema a un porcentaje (0-100)."""
    percent = max(0, min(100, int(percent)))
    if SYSTEM == "Windows" and PYCAW_AVAILABLE:
        vol_interface = _get_windows_volume_interface()
        # pycaw trabaja con escala logarítmica de -65.25 (mute) a 0.0 (máx)
        # Convertimos porcentaje lineal a el rango soportado por SetMasterVolumeLevelScalar (0.0 - 1.0)
        vol_interface.SetMasterVolumeLevelScalar(percent / 100, None)
        return f"Volumen ajustado al {percent}%."
    else:
        # Fallback simple: sube/baja usando teclas multimedia varias veces
        steps = percent // 10
        for _ in range(steps):
            keyboard.send("volume up")
        return "Volumen ajustado (modo compatibilidad)."


def volume_up():
    keyboard.send("volume up")
    return "Subiendo volumen."


def volume_down():
    keyboard.send("volume down")
    return "Bajando volumen."


def mute_volume():
    keyboard.send("volume mute")
    return "Silenciando audio."


# =========================================================
#   MULTIMEDIA (play/pause, siguiente, anterior)
# =========================================================
def media_play_pause():
    keyboard.send("play/pause media")
    return "Reproduciendo o pausando contenido."


def media_next():
    keyboard.send("next track")
    return "Pasando a la siguiente pista."


def media_previous():
    keyboard.send("previous track")
    return "Volviendo a la pista anterior."


# =========================================================
#   NAVEGADOR / WEB / YOUTUBE
# =========================================================
def open_website(url: str):
    """Abre una URL directa en el navegador predeterminado."""
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Abriendo {url}"


def search_youtube(query: str):
    """Busca un término específico en YouTube."""
    q = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={q}"
    webbrowser.open(url)
    return f"Buscando '{query}' en YouTube."


def search_google(query: str):
    """Realiza una búsqueda general en Google."""
    q = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={q}"
    webbrowser.open(url)
    return f"Buscando '{query}' en Google."


# =========================================================
#   ABRIR PROGRAMAS DEL SISTEMA
# =========================================================
# Mapa de "alias hablados" -> comando real del ejecutable.
# Personaliza esta lista según los programas instalados en tu PC.
APP_MAP = {
    "bloc de notas": "notepad" if SYSTEM == "Windows" else "gedit",
    "notepad": "notepad" if SYSTEM == "Windows" else "gedit",
    "calculadora": "calc" if SYSTEM == "Windows" else "gnome-calculator",
    "explorador de archivos": "explorer" if SYSTEM == "Windows" else "nautilus",
    "discord": "discord",
    "spotify": "spotify",
    "chrome": "chrome",
    "navegador": "chrome",
    "steam": "steam",
}


def open_app(app_name: str):
    """Intenta abrir un programa en el sistema."""
    key = app_name.lower().strip()

    # Caso especial: Spotify casi nunca está en el PATH de Windows.
    # Usamos su protocolo de URI, que Windows sabe resolver directamente
    # sin necesitar la ruta exacta del ejecutable.
    if key == "spotify":
        try:
            os.system("start spotify:")
            return "Abriendo Spotify."
        except Exception as e:
            return f"No pude abrir Spotify: {e}"

    command = APP_MAP.get(key, key)
    try:
        if SYSTEM == "Windows":
            os.startfile(command)  # type: ignore[attr-defined]
        elif SYSTEM == "Darwin":
            subprocess.Popen(["open", "-a", command])
        else:  # Linux
            subprocess.Popen([command])
        return f"Abriendo {app_name}."
    except Exception as e:
        return f"No pude abrir {app_name}: {e}"


# =========================================================
#   DESPACHADOR PRINCIPAL DE INTENCIONES
# =========================================================
def execute_intent(intent: dict) -> str:
    """
    Recibe un diccionario con la forma:
        {"action": "open_website", "params": {"url": "github.com"}}
    y ejecuta la función correspondiente. Devuelve un mensaje de
    confirmación en texto (para ser leído por el TTS si se desea).

    Si la acción es "answer_question", significa que Gemini decidió
    responder directamente con texto (no hay automatización que ejecutar);
    en ese caso el propio texto de la respuesta ya viene en intent["params"]["text"].
    """
    action = intent.get("action")
    params = intent.get("params", {}) or {}

    dispatch = {
        "open_website": lambda: open_website(params.get("url", "")),
        "search_youtube": lambda: search_youtube(params.get("query", "")),
        "search_google": lambda: search_google(params.get("query", "")),
        "set_volume": lambda: set_volume(params.get("percent", 50)),
        "volume_up": volume_up,
        "volume_down": volume_down,
        "mute_volume": mute_volume,
        "media_play_pause": media_play_pause,
        "media_next": media_next,
        "media_previous": media_previous,
        "open_app": lambda: open_app(params.get("app_name", "")),
        "play_spotify_track": lambda: spotify_control.search_and_play(params.get("query", "")),
        "answer_question": lambda: params.get("text", ""),
    }

    handler = dispatch.get(action)
    if handler is None:
        return "No reconocí esa acción."
    return handler()