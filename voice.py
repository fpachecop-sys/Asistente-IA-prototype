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
from faster_whisper import WhisperModel # <-- NUEVO IMPORT
import config

# Inicializamos el mezclador de audio de pygame una sola vez
pygame.mixer.init()

# ---------------------------------------------------------
# Reconocedor de voz
# ---------------------------------------------------------
_recognizer = sr.Recognizer()
_whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
print("Motor auditivo listo.")

# Configuración de grabación directa en memoria
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


class PushToTalkRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.recording = False

    def start(self):
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
        if self.recording and self.stream:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.frames.append(data)
            except Exception:
                pass

    def stop_and_get_audio(self):
        self.recording = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass

        if not self.frames:
            return None

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
    """Convierte el audio a texto y filtra alucinaciones de Whisper."""
    import os, tempfile, uuid
    if not audio_data:
        return ""
    
    try:
        wav_bytes = audio_data.get_wav_data()
        temp_wav = os.path.join(tempfile.gettempdir(), f"yari_listen_{uuid.uuid4().hex}.wav")
        with open(temp_wav, "wb") as f:
            f.write(wav_bytes)

        segments, info = _whisper_model.transcribe(temp_wav, beam_size=5, language="es")
        
        texto_completo = ""
        for segment in segments:
            texto_completo += segment.text + " "

        try:
            os.remove(temp_wav)
        except Exception:
            pass

        texto_limpio = texto_completo.strip()
        
        # --- FILTRO ANTI-FANTASMAS ---
        fantasmas = ["amara.org", "suscríbete", "subtítulos", "gracias", "youtube"]
        if any(fantasma in texto_limpio.lower() for fantasma in fantasmas) or len(texto_limpio) < 4:
            return "" # Ignorar silencios alucinados
            
        return texto_limpio
        
    except Exception as e:
        print(f"[Error Whisper]: {e}")
        return ""

def stop_audio():
    """Interrumpe la reproducción de voz instantáneamente."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


# ---------------------------------------------------------
# Texto a voz (TTS) - Edge TTS con fallback a pyttsx3
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
    """Genera audio con Microsoft Edge Neuronal (Gratis y fluido)."""
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
    """Fallback 100% offline usando las voces nativas del sistema."""
    engine = pyttsx3.init()
    engine.setProperty("rate", config.TTS_RATE)
    engine.setProperty("volume", config.TTS_VOLUME)

    if getattr(config, 'TTS_VOICE_INDEX', None) is not None:
        voices = engine.getProperty("voices")
        if 0 <= config.TTS_VOICE_INDEX < len(voices):
            engine.setProperty("voice", voices[config.TTS_VOICE_INDEX].id)

    engine.say(text)
    engine.runAndWait()
    engine.stop()


def speak(text: str):
    """Intenta usar Edge TTS, si falla usa el motor offline."""
    if not text:
        return

    if getattr(config, 'TTS_USE_EDGE', True):
        success = _speak_edge_tts(text)
        if success:
            return

    _speak_pyttsx3(text)


def list_available_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    for i, v in enumerate(voices):
        print(f"[{i}] {v.name} - {v.languages} - id={v.id}")
    engine.stop()


if __name__ == "__main__":
    list_available_voices()