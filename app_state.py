import queue
import pyodbc

class AppState:
    def __init__(self):
        self.orb_commands = queue.Queue()
        
        # --- NUEVO: memoria de código separada del chat ---
        self.last_code_snippet = None
        self.last_code_language = None
        # ----------------------------------------------------

        self.conn_str = (
            r"DRIVER={ODBC Driver 17 for SQL Server};"
            r"SERVER=KernelOS-PC\SQLEXPRESS;" 
            r"DATABASE=YariDB;"
            r"Trusted_Connection=yes;"
        )
        
        self.conversation_history = self._load_history()
        self.reminders = self._load_reminders()

    # NUEVO método
    def set_last_code(self, code: str, language: str = ""):
        self.last_code_snippet = code
        self.last_code_language = language

    def _get_connection(self):
        """Crea y devuelve la conexión a SQL Server."""
        return pyodbc.connect(self.conn_str)

    def _load_history(self):
        """Extrae el historial de chat desde la base de datos."""
        history = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SenderRole, MessageText FROM ChatHistory ORDER BY CreatedAt ASC")
                for row in cursor.fetchall():
                    history.append({"role": row[0], "text": row[1]})
        except Exception as e:
            print(f"Error conectando a YariDB (Chat): {e}")
        return history

    def _load_reminders(self):
        """Extrae los pendientes activos desde SQL Server al arrancar."""
        loaded_reminders = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Solo traemos los pendientes que no han sonado todavía (IsActive = 1)
                cursor.execute("SELECT Id, TimeStr, TaskDescription FROM Reminders WHERE IsActive = 1 ORDER BY TimeStr ASC")
                for row in cursor.fetchall():
                    loaded_reminders.append({
                        "id": row[0],       # Id
                        "time": row[1],     # TimeStr
                        "task": row[2]      # TaskDescription
                    })
        except Exception as e:
            print(f"Error conectando a YariDB (Pendientes): {e}")
        return loaded_reminders

    def add_message(self, role: str, text: str):
        """Registra un mensaje en la memoria local y lo inserta en SQL Server."""
        self.conversation_history.append({"role": role, "text": text})
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO ChatHistory (SenderRole, MessageText) VALUES (?, ?)",
                    (role, text)
                )
                conn.commit()
        except Exception as e:
            print(f"Error guardando mensaje en BD: {e}")

    def set_orb_state(self, state: str):
        self.orb_commands.put(f"state:{state}")

    def show_orb(self):
        self.orb_commands.put("show")

    def hide_orb(self):
        self.orb_commands.put("hide")
