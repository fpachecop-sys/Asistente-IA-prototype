"""
spotify_control.py
-------------------
Integración con Spotify SIN necesitar cuenta Premium.

Estrategia:
    1. Usamos la Spotify Web API (autenticación "Client Credentials",
       la más simple: solo Client ID + Secret, sin login de usuario)
       ÚNICAMENTE para BUSCAR la canción y obtener su ID exacto.
    2. Para REPRODUCIRLA, en vez de usar los endpoints de "playback"
       de la Web API (que sí requieren Premium), abrimos la canción
       mediante el protocolo de URI nativo de Spotify:
           spotify:track:<ID>
       Esto es equivalente a hacer doble clic en la canción dentro de
       tu propia app de escritorio, así que funciona igual con cuenta
       gratuita (puede incluir anuncios de vez en cuando, como es
       normal en el plan free, pero SÍ reproduce la canción pedida).

Requiere en tu .env:
    SPOTIFY_CLIENT_ID=...
    SPOTIFY_CLIENT_SECRET=...

(Client ID/Secret se sacan gratis en https://developer.spotify.com/dashboard,
no requieren que actives ningún login de usuario para este flujo).
"""

import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import subprocess
import time
import pyautogui
import config

_sp_client = None


def _get_client():
    """Crea (una sola vez) el cliente autenticado de Spotify."""
    global _sp_client
    if _sp_client is None:
        auth_manager = SpotifyClientCredentials(
            client_id=config.SPOTIFY_CLIENT_ID,
            client_secret=config.SPOTIFY_CLIENT_SECRET,
        )
        _sp_client = spotipy.Spotify(auth_manager=auth_manager)
    return _sp_client


def search_and_play(query: str) -> str:
    """
    Busca una canción (o "canción artista") en Spotify y la abre
    directamente en la app de escritorio para que empiece a sonar.

    Ejemplos de query: "Positions Ariana Grande", "Bohemian Rhapsody"
    """
    if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
        return ("No configuraste tus credenciales de Spotify todavía. "
                "Agrega SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en tu archivo .env.")

    try:
        sp = _get_client()
        results = sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])

        if not items:
            return f"No encontré ninguna canción para '{query}'."

        track = items[0]
        track_id = track["id"]
        track_name = track["name"]
        artist_name = track["artists"][0]["name"] if track["artists"] else ""

        # Abre la canción directamente en la app de escritorio de Spotify.
        # Si Spotify no estaba abierto, esto también lo abre automáticamente.
        # spotify_control.py (reemplaza el final de search_and_play)
        import subprocess
        import time
        import pyautogui
        cmd = f"Start-Process 'spotify:track:{track_id}'"
        subprocess.run(["powershell", "-command", cmd], shell=True)
        
        # Le damos 2 segundos a la PC para traer Spotify al frente
        time.sleep(2) 
        
        # Forzamos el "Doble Clic" o "Play" pulsando Enter
        pyautogui.press('enter')
        
        return f"Reproduciendo {track_name} de {artist_name} en Spotify."

    except Exception as e:
        return f"No pude buscar en Spotify: {e}"


def search_and_play_artist_top_track(artist_name: str) -> str:
    """
    Reproduce la canción más popular de un artista (útil cuando el
    usuario solo dice "pon música de X artista" sin canción específica).
    """
    return search_and_play(artist_name)