# main.py
"""
Punto de entrada único. Un solo proceso:
    - Hilo A (secundario): Tkinter -> la bolita (JarvisUI), oculta al inicio.
    - Hilo principal: pywebview -> el dashboard.
Ambos comparten `app_state` (historial, comandos) sin duplicar nada.
"""
import threading
import time
import webview
import keyboard
import system_stats
import weather
import config
import voice
import brain
import actions
import datetime
from ui import JarvisUI
from app_state import AppState

app_state = AppState()
_recorder = voice.PushToTalkRecorder()
_is_holding_key = False
_is_busy_processing = False
config.app_state_ref = app_state

_orb_app = None       # instancia de JarvisUI, se crea en el hilo Tkinter
_webview_window = None  # ventana del dashboard


# =========================================================
#   Puente Python <-> JS del dashboard
# =========================================================
class Bridge:
    def minimize_to_orb(self):
        """Llamado desde JS al hacer click en minimizar."""
        if _webview_window:
            _webview_window.hide()
        app_state.show_orb()

    def send_text_message(self, user_text: str):
        """Permite escribir por teclado desde el dashboard en vez de solo voz."""
        return _process_user_text(user_text)

    def get_history(self):
        return app_state.conversation_history

    def get_dashboard_data(self):
        return {
            "stats": system_stats.get_system_stats(),
            "weather": weather.get_today_weather_dict()
        }
    def get_reminders(self):
        return app_state.reminders
    
    def get_orb_state(self):
        # Le dice al panel web en qué estado se encuentra la IA
        return getattr(app_state, "current_state", "idle")

    def set_voice_volume(self, volume_str):
        """Recibe el porcentaje del HUD y ajusta el volumen de la IA."""
        try:
            import voice
            vol_int = int(volume_str)
            voice.change_tts_volume(vol_int)
        except Exception as e:
            print(f"Error cambiando volumen de voz: {e}")

    def test_microphone(self):
        """Graba 3 segundos y reproduce el audio para probar la calidad."""
        import threading
        
        def run_test():
            import pyaudio
            import wave
            import pygame
            import os
            import tempfile
            import uuid # <-- Añadimos uuid para crear nombres únicos
            
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            p = pyaudio.PyAudio()
            
            try:
                stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
                frames = []
                # Grabar por ~3 segundos
                for _ in range(0, int(RATE / CHUNK * 3)):
                    data = stream.read(CHUNK)
                    frames.append(data)
                stream.stop_stream()
                stream.close()
                p.terminate()
                
                # 1. PARCHE DE BLOQUEO: Nombre de archivo 100% único cada vez
                temp_wav = os.path.join(tempfile.gettempdir(), f"test_mic_{uuid.uuid4().hex}.wav")
                
                wf = wave.open(temp_wav, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                # 2. Reproducir
                pygame.mixer.music.load(temp_wav)
                pygame.mixer.music.play()
                
                # 3. Esperar a que el audio termine de sonar
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
                # 4. PARCHE DE LIMPIEZA: Liberar la pista del motor y borrar el archivo físico
                pygame.mixer.music.unload()
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"Error en prueba de mic: {e}")

        threading.Thread(target=run_test, daemon=True).start()
        return "Prueba iniciada"

def _restore_dashboard_from_orb():
    """Llamado desde ui.py (hilo Tkinter) cuando se hace doble-click en la bolita."""
    if _webview_window:
        _webview_window.show()


# =========================================================
#   Lógica compartida de procesamiento (voz o texto)
# =========================================================
# main.py

def _process_user_text(user_text: str) -> dict:
    app_state.add_message("user", user_text)
    app_state.set_orb_state("thinking")

    intent = brain.get_intent_from_text(user_text)
    action_result_text = actions.execute_intent(intent)
    
    action_name = intent.get("action")
    short_intro = intent.get("spoken_response", "").strip()
    
    acciones_de_lectura = [
        "analyze_screen", 
        "analyze_clipboard", 
        "analyze_document", 
        "analyze_online_pdf", 
        "comment_on_music", 
        "get_reminders",
        "modify_file",
        "append_to_file",
        "analyze_camera",
        "run_system_diagnostic",
        "search_web_and_summarize",
    ]
    
    # 🛑 CORRECCIÓN: Si es una pregunta normal, NO sumamos las frases
    if action_name == "answer_question":
        spoken_text = action_result_text
    elif action_name in acciones_de_lectura:
        spoken_text = f"{short_intro} {action_result_text}"
    else:
        spoken_text = short_intro or action_result_text

    # Limpiamos asteriscos y formato markdown
    spoken_text = spoken_text.replace("*", "").replace("#", "")

    app_state.add_message("assistant", spoken_text)
    app_state.set_orb_state("speaking")
    
    voice.speak(spoken_text)
    
    app_state.set_orb_state("idle")

    return {"spoken_response": spoken_text}


def _process_audio_thread():
    global _is_busy_processing
    _is_busy_processing = True
    try:
        app_state.set_orb_state("thinking")
        audio_data = _recorder.stop_and_get_audio()
        user_text = voice.transcribe_audio_data(audio_data)

        if not user_text:
            app_state.set_orb_state("idle")
            return

        print(f"[Usuario dijo]: {user_text}")
        _process_user_text(user_text)
    except Exception as e:
        print(f"[ERROR en procesamiento]: {e}")
    finally:
        app_state.set_orb_state("idle")
        _is_busy_processing = False


def _recording_loop():
    global _is_holding_key
    while _is_holding_key:
        _recorder.record_chunk()
        time.sleep(0.01)


def register_push_to_talk():
    global _is_holding_key, _is_busy_processing
    target_key = config.HOTKEY_ACTIVATE.lower()

    def on_key_event(event):
        global _is_holding_key, _is_busy_processing
        
        # 🛑 PARCHE ANTI-CRASH: Si el evento no tiene nombre, lo ignoramos
        if not event.name:
            return
            
        # Si la tecla presionada no es la configurada, ignoramos
        if event.name.lower() != target_key:
            return

        # Cuando PRESIONAS la tecla hacia abajo
        if event.event_type == keyboard.KEY_DOWN:
            voice.stop_audio() # Interrumpe si estaba hablando
            
            if not _is_holding_key and not _is_busy_processing:
                _is_holding_key = True
                app_state.set_orb_state("listening")
                _recorder.start()
                threading.Thread(target=_recording_loop, daemon=True).start()

        # Cuando SUELTAS la tecla
        elif event.event_type == keyboard.KEY_UP:
            if _is_holding_key:
                _is_holding_key = False
                threading.Thread(target=_process_audio_thread, daemon=True).start()

    def on_quit():
        print("Cerrando Y.A.R.I...")
        if _webview_window:
            _webview_window.destroy()
        if _orb_app:
            _orb_app.after(0, _orb_app.destroy)

    keyboard.hook(on_key_event)
    keyboard.add_hotkey(config.HOTKEY_QUIT, on_quit)
    print(f"✅ Y.A.R.I. lista. Mantén presionada [{config.HOTKEY_ACTIVATE.upper()}] para hablar.")
    keyboard.wait()

# =========================================================
#   Hilo de la bolita (Tkinter)
# =========================================================
def start_orb_thread():
    global _orb_app
    _orb_app = JarvisUI(app_state, on_restore_dashboard=_restore_dashboard_from_orb, start_hidden=True)
    _orb_app.mainloop()


def main():
    if not config.GEMINI_API_KEY:
        print("❌ ERROR: No se encontró GEMINI_API_KEY en el archivo .env")
        return

    global _webview_window

    # Hilo 1: la bolita (Tkinter), oculta hasta que se pida
    threading.Thread(target=start_orb_thread, daemon=True).start()

    # Hilo 2: hotkey global en segundo plano
    threading.Thread(target=register_push_to_talk, daemon=True).start()
    # Hilo 3: El vigilante del tiempo (Proactivo)
    threading.Thread(target=_proactive_reminder_loop, daemon=True).start()
    
    # Hilo principal: pywebview (dashboard)
    bridge = Bridge()
    DASHBOARD_HTML = "ui_dashboard/index.html"
    _webview_window = webview.create_window(
        "JARVIS", DASHBOARD_HTML, width=1200, height=800, js_api=bridge,
    )
    webview.start()

def _proactive_reminder_loop():
    """Revisa el reloj cada 20 segundos. Si hay un pendiente para AHORA o que YA PASÓ, lo avisa."""
    import time
    import datetime
    
    while True:
        now_str = datetime.datetime.now().strftime("%H:%M")
        
        for r in app_state.reminders[:]:
            # NUEVO: Comparamos si la hora programada es IGUAL o MENOR a la actual
            if r["time"] <= now_str:
                
                # Inteligencia extra: ¿Es un recordatorio exacto o uno atrasado?
                if r["time"] < now_str:
                    mensaje = f"Señor, mis sistemas estuvieron fuera de línea. Tienes un pendiente atrasado de las {r['time']}: {r['task']}."
                else:
                    mensaje = f"Interrumpo tus sistemas para recordarte un pendiente: {r['task']}."
                    
                app_state.set_orb_state("speaking")
                import voice # Aseguramos la importación
                voice.speak(mensaje)
                app_state.set_orb_state("idle")
                
                # Borramos de la interfaz visual
                app_state.reminders.remove(r)
                
                # Desactivamos el pendiente en SQL Server
                try:
                    with app_state._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE Reminders SET IsActive = 0 WHERE Id = ?", (r["id"],))
                        conn.commit()
                except Exception as e:
                    print(f"Error actualizando SQL: {e}")
                
        time.sleep(20)

if __name__ == "__main__":
    main()