"""
voice.py
--------
Encapsula el reconocimiento de voz (Speech-to-Text) y la síntesis de
voz de ultra-realismo usando ElevenLabs mediante API REST pura.
"""

import asyncio
import io
import os
import tempfile
import uuid
import wave
import requests

import pyaudio
import speech_recognition as sr
import pyttsx3
import pygame

import config

pygame.mixer.init()

# ---------------------------------------------------------
# Reconocedor de voz
# ---------------------------------------------------------
_recognizer = sr.Recognizer()

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
    if not audio_data:
        return ""
    try:
        return _recognizer.recognize_google(audio_data, language=config.STT_LANGUAGE)
    except Exception:
        return ""


def stop_audio():
    """Interrumpe la reproducción de voz instantáneamente."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


# ---------------------------------------------------------
# Texto a voz (TTS) - ElevenLabs API REST Directa
# ---------------------------------------------------------
def _speak_elevenlabs(text: str) -> bool:
    """Genera audio hiperrealista conectándose directo al servidor de ElevenLabs."""
    if not getattr(config, 'ELEVENLABS_API_KEY', None) or not getattr(config, 'ELEVENLABS_VOICE_ID', None):
        return False
        
    temp_path = os.path.join(tempfile.gettempdir(), f"yari_tts_{uuid.uuid4().hex}.mp3")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": config.ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code != 200:
            print(f"[Error ElevenLabs API]: {response.text}")
            return False
            
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        return True
    except Exception as e:
        print(f"[ElevenLabs falló, usando fallback pyttsx3]: {e}")
        return False
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def _speak_pyttsx3(text: str):
    """Fallback 100% offline."""
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
    if not text:
        return
    
    success = _speak_elevenlabs(text)
    
    if not success:
        _speak_pyttsx3(text)