# app_state.py
"""
Estado compartido en memoria entre el dashboard y la bolita.
Como todo vive en el mismo proceso, el historial de conversación
con Gemini (brain._chat_history) y este estado nunca se pierden
al alternar entre las dos interfaces.
"""
import queue

class AppState:
    def __init__(self):
        self.conversation_history = []  # [{"role": "user"/"assistant", "text": "..."}]
        self.current_orb_state = "idle"  # idle | listening | thinking | speaking
        self.orb_commands = queue.Queue()  # comandos hacia la bolita: "show" | "hide" | "state:<x>"

    def add_message(self, role: str, text: str):
        self.conversation_history.append({"role": role, "text": text})

    def set_orb_state(self, state: str):
        self.current_orb_state = state
        self.orb_commands.put(f"state:{state}")

    def show_orb(self):
        self.orb_commands.put("show")

    def hide_orb(self):
        self.orb_commands.put("hide")