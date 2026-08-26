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


def wake_word_loop():
    import speech_recognition as sr
    global _is_busy_processing
    
    recognizer = voice._recognizer
    # Ajustamos la sensibilidad al ruido de tu cuarto
    with sr.Microphone() as source:
        print("Calibrando ruido de fondo...")
        recognizer.adjust_for_ambient_noise(source, duration=1.5)
        print("✅ Y.A.R.I. en línea. Di 'Yari' o 'Jarvis' para dar una orden.")
        
        while True:
            try:
                # Se queda esperando en bajo consumo hasta que hables
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=15)
                
                if _is_busy_processing:
                    continue # Ignorar si la IA ya está hablando/pensando
                    
                app_state.set_orb_state("listening")
                texto = voice.transcribe_audio_data(audio)
                
                if not texto:
                    app_state.set_orb_state("idle")
                    continue
                    
                texto_lower = texto.lower()
                print(f"[Escuchado en ambiente]: {texto}")
                
                # Activar solo si oye su nombre
                if "yari" in texto_lower or "jarvis" in texto_lower:
                    _is_busy_processing = True
                    # Limpiamos el nombre para enviar solo la orden a Gemini
                    comando = texto_lower.replace("yari", "").replace("jarvis", "").strip()
                    
                    if comando:
                        _process_user_text(comando)
                    else:
                        # Si solo dijiste su nombre y nada más
                        voice.speak("¿En qué te ayudo?")
                        app_state.set_orb_state("idle")
                        _is_busy_processing = False
                else:
                    app_state.set_orb_state("idle")

            except sr.WaitTimeoutError:
                app_state.set_orb_state("idle")
            except Exception as e:
                app_state.set_orb_state("idle")
                pass

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

    # Hilo 2: Motor Auditivo Constante (Wake-Word)
    threading.Thread(target=wake_word_loop, daemon=True).start()

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
    """Revisa el reloj cada 20 segundos y habla si hay un pendiente, actualizando SQL."""
    import time
    import datetime
    
    while True:
        now_str = datetime.datetime.now().strftime("%H:%M")
        
        for r in app_state.reminders[:]:
            if r["time"] == now_str:
                mensaje = f"Interrumpo tus sistemas para recordarte un pendiente: {r['task']}."
                app_state.set_orb_state("speaking")
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