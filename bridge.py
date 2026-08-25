# bridge.py
import weather
import brain
import actions

try:
    import system_stats
except ImportError:
    system_stats = None

class BridgeAPI:
    def __init__(self, app_state=None):
        self.app_state = app_state

    def send_text_message(self, text: str) -> dict:
        intent = brain.get_intent_from_text(text)
        action_result = actions.execute_intent(intent)
        return {
            "intent": intent,
            "action_result": action_result,
            "spoken_response": intent.get("spoken_response", "Comando ejecutado.")
        }

    def get_dashboard_data(self) -> dict:
        # Clima
        weather_data = weather.get_today_weather_dict()

        # Telemetría del Sistema
        if system_stats and hasattr(system_stats, "get_stats"):
            stats_data = system_stats.get_stats()
        else:
            # Fallback seguro con psutil si no existe system_stats
            import psutil
            ram = psutil.virtual_memory()
            stats_data = {
                "cpu": psutil.cpu_percent(interval=None),
                "ram_percent": ram.percent,
                "ram_used_gb": round(ram.used / (1024**3), 1),
                "ram_total_gb": round(ram.total / (1024**3), 1)
            }

        return {
            "stats": stats_data,
            "weather": weather_data
        }

    def minimize_to_orb(self):
        if self.app_state and hasattr(self.app_state, "orb_commands"):
            self.app_state.orb_commands.put("show")

    def get_history(self) -> list:
        # Devuelve el historial en memoria de brain si existe
        return brain._chat_history if hasattr(brain, "_chat_history") else []

    def get_reminders(self) -> list:
        return self.app_state.reminders if self.app_state else []