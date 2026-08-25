# main.py
import threading
import sys
import time
import keyboard

import config
import voice
import brain
import actions
from ui import JarvisUI

_is_holding_key = False
_is_busy_processing = False
_recorder = voice.PushToTalkRecorder()

def _recording_loop():
    """Hilo secundario que captura fragmentos de micrófono mientras mantengas presionada la tecla."""
    global _is_holding_key, _recorder
    while _is_holding_key:
        _recorder.record_chunk()
        time.sleep(0.01)

def _process_audio_thread(app: JarvisUI):
    """Procesa el audio recopilado al soltar la tecla y llama a Gemini."""
    global _is_busy_processing, _recorder
    _is_busy_processing = True

    try:
        app.set_state("thinking")
        audio_data = _recorder.stop_and_get_audio()
        
        user_text = voice.transcribe_audio_data(audio_data)

        if not user_text:
            app.set_state("idle")
            _is_busy_processing = False
            return

        print(f"[Usuario dijo]: {user_text}")

        # Consulta a Gemini
        intent = brain.get_intent_from_text(user_text)
        print(f"[Intención Gemini]: {intent}")

        # Ejecución de la acción y respuesta por voz
        action_result_text = actions.execute_intent(intent)
        spoken_text = intent.get("spoken_response") or action_result_text

        app.set_state("speaking")
        voice.speak(spoken_text)

    except Exception as e:
        print(f"[ERROR en procesamiento]: {e}")
    finally:
        app.set_state("idle")
        _is_busy_processing = False

def register_push_to_talk(app: JarvisUI):
    """Eventos de teclado: Down (empezar a grabar) y Up (soltar y enviar)."""
    global _is_holding_key, _is_busy_processing, _recorder

    target_key = config.HOTKEY_ACTIVATE.lower()

    def on_key_event(event):
        global _is_holding_key, _is_busy_processing, _recorder

        if event.name.lower() != target_key:
            return

        # PRESIONAR LA TECLA (KEY DOWN)
        if event.event_type == keyboard.KEY_DOWN:
            if not _is_holding_key and not _is_busy_processing:
                _is_holding_key = True
                app.set_state("listening")  # El orbe empieza a brillar en celeste
                _recorder.start()
                # Inicia la captura continua mientras la tecla siga abajo
                threading.Thread(target=_recording_loop, daemon=True).start()

        # SOLTAR LA TECLA (KEY UP)
        elif event.event_type == keyboard.KEY_UP:
            if _is_holding_key:
                _is_holding_key = False  # Detiene la grabación
                # Inicia el procesamiento en segundo plano con el audio capturado
                threading.Thread(target=_process_audio_thread, args=(app,), daemon=True).start()

    def on_quit():
        print("Cerrando JARVIS...")
        app.after(0, app._close)

    keyboard.hook(on_key_event)
    keyboard.add_hotkey(config.HOTKEY_QUIT, on_quit)

    print(f"✅ JARVIS listo. Mantén presionada [{config.HOTKEY_ACTIVATE.upper()}] para hablar.")
    print(f"   Presiona [{config.HOTKEY_QUIT.upper()}] para salir.")

    keyboard.wait()

def main():
    if not config.GEMINI_API_KEY:
        print("❌ ERROR: No se encontró GEMINI_API_KEY en el archivo .env")
        sys.exit(1)

    app = JarvisUI(on_close_callback=lambda: keyboard.unhook_all())

    # Listener de teclado en segundo plano
    threading.Thread(target=register_push_to_talk, args=(app,), daemon=True).start()

    app.mainloop()

if __name__ == "__main__":
    main()