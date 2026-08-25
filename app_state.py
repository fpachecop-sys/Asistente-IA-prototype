import queue
import pyodbc

class AppState:
    def __init__(self):
        self.orb_commands = queue.Queue()
        self.reminders = []
        
        # ⚠️ IMPORTANTE: Cambia 'localhost' por el nombre de tu servidor en SSMS si es diferente
        self.conn_str = (
            r"DRIVER={ODBC Driver 17 for SQL Server};"
            r"SERVER=KernelOS-PC\SQLEXPRESS;" 
            r"DATABASE=YariDB;"
            r"Trusted_Connection=yes;"
        )
        
        # Cargamos la memoria persistente al iniciar
        self.conversation_history = self._load_history()

    def _get_connection(self):
        """Crea y devuelve la conexión a SQL Server."""
        return pyodbc.connect(self.conn_str)

    def _load_history(self):
        """Extrae el historial histórico desde la base de datos."""
        history = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Extraemos los mensajes ordenados cronológicamente
                cursor.execute("SELECT SenderRole, MessageText FROM ChatHistory ORDER BY CreatedAt ASC")
                for row in cursor.fetchall():
                    history.append({"role": row[0], "text": row[1]})
        except Exception as e:
            print(f"Error conectando a YariDB: {e}")
        return history

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