"""
voice.py
--------
Encapsula el reconocimiento de voz (Speech-to-Text vía Google Speech API,
gratuito a través de la librería `speech_recognition`) y la síntesis de
voz (Text-to-Speech vía `pyttsx3`, 100% local y sin costo).

Ambas operaciones son bloqueantes por naturaleza, así que SIEMPRE deben
llamarse desde un hilo (threading.Thread) para no congelar la interfaz
gráfica de Tkinter.
"""

import asyncio
import io
import os
import tempfile
import uuid
import wave

import pyaudio
import speech_recognition as sr
import pyttsx3
import edge_tts
import pygame

import config

# Inicializamos el mezclador de audio de pygame una sola vez (muy liviano,
# solo maneja reproducción, no hay procesamiento pesado).
pygame.mixer.init()

# ---------------------------------------------------------
# Reconocedor de voz (se reutiliza la misma instancia)
# ---------------------------------------------------------
_recognizer = sr.Recognizer()

# Configuración de grabación directa en memoria para Push-To-Talk
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


class PushToTalkRecorder:
    """
    Graba audio en memoria (RAM) mientras el usuario mantiene presionado
    el hotkey. No usa ningún reconocimiento continuo ni consume CPU
    mientras no se está grabando: el stream solo existe entre start() y
    stop_and_get_audio().
    """

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.recording = False

    def start(self):
        """Inicia la grabación en memoria en segundo plano."""
        self.frames = []
        self.recording = True
        try:
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
        except Exception as e:
            print(f"[Error micrófono]: {e}")
            self.recording = False

    def record_chunk(self):
        """Lee un bloque de audio si está grabando. Se llama repetidamente
        desde el hilo de grabación en main.py mientras la tecla está abajo."""
        if self.recording and self.stream:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.frames.append(data)
            except Exception:
                pass

    def stop_and_get_audio(self):
        """Detiene la grabación y convierte los bytes recolectados a
        un objeto sr.AudioData listo para transcribir."""
        self.recording = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass

        if not self.frames:
            return None

        # Convertimos los frames PCM crudos en un archivo WAV en RAM
        wav_buffer = io.BytesIO()
        wf = wave.open(wav_buffer, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(self.frames))
        wf.close()
        wav_buffer.seek(0)

        with sr.AudioFile(wav_buffer) as source:
            return _recognizer.record(source)


def transcribe_audio_data(audio_data) -> str:
    """Convierte el audio capturado (sr.AudioData) a texto usando la
    API gratuita de Google (a través de speech_recognition)."""
    if not audio_data:
        return ""
    try:
        return _recognizer.recognize_google(audio_data, language=config.STT_LANGUAGE)
    except Exception:
        return ""


# ---------------------------------------------------------
# Texto a voz (TTS) - Edge TTS (voces neuronales, requiere internet)
# con fallback automático a pyttsx3 (offline) si algo falla.
# ---------------------------------------------------------
async def _edge_tts_save(text: str, filepath: str):
    """Genera el audio con Edge TTS y lo guarda como MP3."""
    communicate = edge_tts.Communicate(
        text,
        voice=config.TTS_EDGE_VOICE,
        rate=config.TTS_EDGE_RATE,
        volume=config.TTS_EDGE_VOLUME,
    )
    await communicate.save(filepath)


def _speak_edge_tts(text: str) -> bool:
    """
    Sintetiza el texto con una voz neuronal de Microsoft Edge (gratis,
    sin API key, mucho más natural que las voces SAPI5 de Windows) y
    la reproduce con pygame. Devuelve True si tuvo éxito, False si falló
    (por ejemplo, sin internet), para poder hacer fallback a pyttsx3.
    """
    temp_path = os.path.join(tempfile.gettempdir(), f"jarvis_tts_{uuid.uuid4().hex}.mp3")
    try:
        asyncio.run(_edge_tts_save(text, temp_path))

        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        return True
    except Exception as e:
        print(f"[Edge TTS falló, usando fallback pyttsx3]: {e}")
        return False
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def _speak_pyttsx3(text: str):
    """Fallback 100% offline usando las voces nativas del sistema (SAPI5)."""
    engine = pyttsx3.init()
    engine.setProperty("rate", config.TTS_RATE)
    engine.setProperty("volume", config.TTS_VOLUME)

    if config.TTS_VOICE_INDEX is not None:
        voices = engine.getProperty("voices")
        if 0 <= config.TTS_VOICE_INDEX < len(voices):
            engine.setProperty("voice", voices[config.TTS_VOICE_INDEX].id)

    engine.say(text)
    engine.runAndWait()
    engine.stop()


def speak(text: str):
    """
    Reproduce el texto dado como voz. Intenta primero Edge TTS (voz
    neuronal natural en español); si falla por cualquier motivo (sin
    internet, servicio caído, etc.), cae automáticamente a pyttsx3.
    """
    if not text:
        return

    if config.TTS_USE_EDGE:
        success = _speak_edge_tts(text)
        if success:
            return

    _speak_pyttsx3(text)


def list_available_voices():
    """Utilidad de diagnóstico: imprime las voces instaladas en el sistema
    junto a su índice, para que puedas elegir TTS_VOICE_INDEX en config.py."""
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    for i, v in enumerate(voices):
        print(f"[{i}] {v.name} - {v.languages} - id={v.id}")
    engine.stop()


if __name__ == "__main__":
    # Ejecuta este archivo directamente para ver qué voces tienes disponibles:
    #   python voice.py
    list_available_voices()