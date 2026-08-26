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
        
        # Si la tecla presionada no es la que configuraste (ej. 'k'), ignoramos
        if event.name.lower() != target_key:
            return

        # Cuando PRESIONAS la tecla hacia abajo
        if event.event_type == keyboard.KEY_DOWN:
            # 🛑 NUEVO: Interrumpir a la IA inmediatamente si estaba hablando
            voice.stop_audio()
            
            # Continuamos con la lógica normal de grabación
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
        print("Cerrando JARVIS...")
        if _webview_window:
            _webview_window.destroy()
        if _orb_app:
            _orb_app.after(0, _orb_app.destroy)

    keyboard.hook(on_key_event)
    keyboard.add_hotkey(config.HOTKEY_QUIT, on_quit)
    print(f"✅ JARVIS listo. Mantén presionada [{config.HOTKEY_ACTIVATE.upper()}] para hablar.")
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