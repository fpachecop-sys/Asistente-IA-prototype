"""
actions.py
----------
Módulo de automatización. Recibe un diccionario de "intención" (JSON)
generado por Gemini y ejecuta la acción correspondiente en el sistema
operativo: abrir webs, buscar en YouTube, controlar volumen, abrir
programas, multimedia (play/pause), etc.
"""

import os
import platform
import subprocess
import webbrowser
import urllib.parse
import pywhatkit
import datetime as _dt
import screen_capture
import brain
import keyboard
import time
import uuid
import psutil
import pyautogui
import pyperclip
import requests
import io
import PyPDF2
import asyncio
import pygetwindow as gw
import vision_control

SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"

# Intentamos importar pycaw solo si estamos en Windows
try:
    if SYSTEM == "Windows":
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        PYCAW_AVAILABLE = True
    else:
        PYCAW_AVAILABLE = False
except ImportError:
    PYCAW_AVAILABLE = False

import spotify_control


# =========================================================
#  CONTROL DE VOLUMEN (Windows via pycaw, fallback teclas)
# =========================================================
def _get_windows_volume_interface():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))

def set_volume(percent: int):
    percent = max(0, min(100, int(percent)))
    if SYSTEM == "Windows" and PYCAW_AVAILABLE:
        vol_interface = _get_windows_volume_interface()
        vol_interface.SetMasterVolumeLevelScalar(percent / 100, None)
        return f"Volumen ajustado al {percent}%."
    else:
        steps = percent // 10
        for _ in range(steps):
            keyboard.send("volume up")
        return "Volumen ajustado (modo compatibilidad)."

def volume_up():
    keyboard.send("volume up")
    return "Subiendo volumen."

def volume_down():
    keyboard.send("volume down")
    return "Bajando volumen."

def mute_volume():
    keyboard.send("volume mute")
    return "Silenciando audio."


# =========================================================
#  MULTIMEDIA (play/pause, siguiente, anterior)
# =========================================================
def media_play_pause():
    keyboard.send("play/pause media")
    return "Reproduciendo o pausando contenido."

def media_next():
    keyboard.send("next track")
    return "Pasando a la siguiente pista."

def media_previous():
    keyboard.send("previous track")
    return "Volviendo a la pista anterior."


# =========================================================
#  NAVEGADOR / WEB / YOUTUBE / MENSAJERÍA
# =========================================================
def open_website(url: str):
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Abriendo {url}"

def search_youtube(query: str):
    q = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={q}"
    webbrowser.open(url)
    return f"Buscando '{query}' en YouTube."

def play_on_spotify(song_name: str) -> str:
    """Utiliza la API oficial de Spotify para buscar y reproducir música."""
    import spotify_control
    
    try:
        # Llamamos a la función que ya tienes programada en tu archivo
        resultado = spotify_control.search_and_play(song_name)
        return resultado
    except Exception as e:
        return f"Error al conectar con el módulo de Spotify: {e}"
    
def search_google(query: str):
    q = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={q}"
    webbrowser.open(url)
    return f"Buscando '{query}' en Google."

def send_whatsapp_message(contact_name: str, message: str):
    number = CONTACTS.get(contact_name.lower())
    if not number:
        return f"No tengo el número de {contact_name} guardado."
    try:
        pywhatkit.sendwhatmsg_instantly(
            phone_no=number,
            message=message,
            wait_time=9,
            tab_close=True
        )
        return f"Enviando mensaje a {contact_name} por WhatsApp."
    except Exception as e:
        return f"No pude enviar el mensaje: {e}"

CONTACTS = {
    "franco": "+51 978 475 665",
    "jaime": "+51 946 838 982",
    "mamá": "+51 971 482 726",
    "fabián": "+51 963 183 479",
    "primita": "+51 916 799 846"
}


# =========================================================
#  ABRIR PROGRAMAS DEL SISTEMA Y JUEGOS
# =========================================================
APP_MAP = {
    "bloc de notas": "notepad" if SYSTEM == "Windows" else "gedit",
    "notepad": "notepad" if SYSTEM == "Windows" else "gedit",
    "calculadora": "calc" if SYSTEM == "Windows" else "gnome-calculator",
    "explorador de archivos": "explorer" if SYSTEM == "Windows" else "nautilus",
    "discord": "discord",
    "spotify": "spotify",
    "chrome": "chrome",
    "navegador": "chrome",
    "brave": "brave",
    "steam": "steam",
}

def open_app(app_name: str):
    key = app_name.lower().strip()
    if key == "spotify":
        try:
            os.system("start spotify:")
            return "Abriendo Spotify."
        except Exception as e:
            return f"No pude abrir Spotify: {e}"
    command = APP_MAP.get(key, key)
    try:
        if SYSTEM == "Windows":
            os.startfile(command)  # type: ignore[attr-defined]
        elif SYSTEM == "Darwin":
            subprocess.Popen(["open", "-a", command])
        else:
            subprocess.Popen([command])
        return f"Abriendo {app_name}."
    except Exception as e:
        return f"No pude abrir {app_name}: {e}"

def open_steam_game(game_name: str):
    key = game_name.lower().strip()
    appid = STEAM_GAMES.get(key)
    if not appid:
        return f"No tengo el AppID de '{game_name}' guardado."
    os.system(f"start steam://rungameid/{appid}")
    return f"Abriendo {game_name} en Steam."

STEAM_GAMES = {
    "counter strike 2": "730",
    "left 4 dead 2": "550",
    "tom clancy's ghost recon": "460930"
}


# =========================================================
#  PROTOCOLO ANTI-BAN (SEGURIDAD EN JUEGOS)
# =========================================================
PROTOCOLOS_SEGUROS = [
    "cs2.exe",           
    "left4dead2.exe",    
    "grb.exe",           
    "grw.exe"            
]

def is_game_running() -> bool:
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() in PROTOCOLOS_SEGUROS:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def scroll_screen(direction: str, amount: int = 500):
    if is_game_running():
        return "Protocolo de seguridad activo. Control de mouse deshabilitado."
    if direction.lower() == "abajo":
        pyautogui.scroll(-amount)
    else:
        pyautogui.scroll(amount)
    return f"Deslizando la pantalla hacia {direction}."

def get_active_window_title() -> str:
    try:
        w = gw.getActiveWindow()
        return w.title if w else "Desconocida"
    except Exception:
        return "Desconocida"
    
def type_text(text: str, press_enter: bool = False):
    if is_game_running():
        return "No puedo inyectar pulsaciones de teclado en este momento. Tienes un juego competitivo en ejecución."
    time.sleep(2.5) 
    keyboard.write(text, delay=0.02) 
    if press_enter:
        keyboard.send("enter")
    return f"He escrito: {text}"


# =========================================================
#  MEMORIA SQL SERVER Y RECORDATORIOS
# =========================================================
def remember_fact(text: str):
    import __main__
    if hasattr(__main__, "app_state"):
        try:
            with __main__.app_state._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO MemoryLogs (LogEntry) VALUES (?)",
                    (text,)
                )
                conn.commit()
            return "Anotado correctamente en tu bitácora de memoria SQL."
        except Exception as e:
            return f"No pude guardar la nota en la base de datos: {e}"
    return "Error: No encontré la conexión al cerebro principal."

def set_reminder(time_str: str, task: str):
    import __main__
    time_str = time_str.replace(".", ":").zfill(5) 
    rem_id = str(uuid.uuid4())[:8]
    if hasattr(__main__, "app_state"):
        try:
            with __main__.app_state._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO Reminders (Id, TimeStr, TaskDescription, IsActive) VALUES (?, ?, ?, 1)",
                    (rem_id, time_str, task)
                )
                conn.commit()
            nuevo_pendiente = {"id": rem_id, "time": time_str, "task": task}
            __main__.app_state.reminders.append(nuevo_pendiente)
            return f"Bloque de memoria creado para las {time_str}."
        except Exception as e:
            return f"Hubo un error guardando el pendiente en SQL: {e}"
    return "Error: No se encontró el banco de memoria principal."

def get_all_reminders():
    import __main__
    if hasattr(__main__, "app_state"):
        try:
            with __main__.app_state._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT TimeStr, TaskDescription FROM Reminders WHERE IsActive = 1 ORDER BY TimeStr ASC")
                rows = cursor.fetchall()
                if not rows:
                    return "Actualmente no tienes pendientes programados."
                texto = "Estos son los pendientes programados:\n"
                for row in rows:
                    texto += f"- A las {row[0]}: {row[1]}\n"
                return texto
        except Exception as e:
            return f"Error leyendo la base de datos: {e}"
    return "Error de conexión con la base de datos."


# =========================================================
#  VISIÓN Y ANÁLISIS DE ARCHIVOS/DOCUMENTOS
# =========================================================
def analyze_screen(question: str = "Describe lo que ves en la pantalla"):
    img_bytes = screen_capture.take_screenshot()
    return brain.ask_about_image(img_bytes, question)

def extract_text_from_file(filepath: str) -> str:
    filepath = os.path.abspath(filepath)
    if not os.path.exists(filepath):
        return f"Error: No pude encontrar el archivo en la ruta {filepath}"
    ext = filepath.split('.')[-1].lower()
    texto_extraido = ""
    try:
        if ext in ['txt', 'py', 'js', 'html', 'css', 'md']:
            with open(filepath, 'r', encoding='utf-8') as f:
                texto_extraido = f.read()
        elif ext == 'pdf':
            with open(filepath, 'rb') as f:
                lector = PyPDF2.PdfReader(f)
                for pagina in lector.pages:
                    texto_extraido += pagina.extract_text() + "\n"
        elif ext == 'docx':
            import docx
            doc = docx.Document(filepath)
            for parrafo in doc.paragraphs:
                texto_extraido += parrafo.text + "\n"
        else:
            return f"Error: Formato .{ext} no soportado para lectura directa."
        return texto_extraido
    except Exception as e:
        return f"Error leyendo el archivo: {e}"

def analyze_document(filepath: str, query: str) -> str:
    contenido = extract_text_from_file(filepath)
    if contenido.startswith("Error:"):
        return contenido
    contenido = contenido[:30000] 
    prompt_analisis = (
        f"Analiza el siguiente contenido de un archivo local y responde a esta consulta del usuario: '{query}'.\n\n"
        f"CONTENIDO DEL ARCHIVO:\n{contenido}"
    )
    try:
        response = brain.client.models.generate_content(
            model=brain.config.GEMINI_MODEL_NAME,
            contents=prompt_analisis,
        )
        return response.text or "El análisis finalizó, pero no generó respuesta."
    except Exception as e:
        return f"Error procesando el análisis con IA: {e}"

def analyze_clipboard(query: str) -> str:
    texto = pyperclip.paste()
    if not texto.strip():
        return "Tu portapapeles está vacío. Copia algo de texto primero."
    texto = texto[:30000] 
    # Reemplaza el prompt_analisis de analyze_clipboard por este:
    prompt_analisis = (
        f"Analiza este texto extraído del portapapeles y responde a: '{query}'.\n"
        "REGLA ESTRICTA: NO saludes, NO te presentes, NO digas 'Aquí tienes el resumen'. "
        "Ve DIRECTO a la información solicitada, como un experto.\n\n"
        f"TEXTO DEL PORTAPAPELES:\n{texto}"
    )
    try:
        response = brain.client.models.generate_content(
            model=brain.config.GEMINI_MODEL_NAME,
            contents=prompt_analisis,
        )
        return response.text or "Análisis finalizado sin respuesta."
    except Exception as e:
        return f"Error procesando el portapapeles: {e}"

def analyze_online_pdf(url: str, query: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        pdf_file = io.BytesIO(response.content)
        lector = PyPDF2.PdfReader(pdf_file)
        texto_extraido = ""
        for pagina in lector.pages:
            texto_extraido += pagina.extract_text() + "\n"
        texto_extraido = texto_extraido[:30000]
        prompt = f"Analiza este PDF online y responde: '{query}'.\n\nTEXTO:\n{texto_extraido}"
        ia_response = brain.client.models.generate_content(
            model=brain.config.GEMINI_MODEL_NAME,
            contents=prompt,
        )
        return ia_response.text
    except Exception as e:
        return f"No pude descargar o leer el PDF online: {e}"


# =========================================================
#  LECTURA MEDIA NATIVA DE WINDOWS (Sin Flask)
# =========================================================
async def _get_windows_media_info():
    """Se conecta al Media Transport de Windows para leer la pista actual."""
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    
    if current_session:
        info = await current_session.try_get_media_properties_async()
        title = info.title
        artist = info.artist
        
        if title and artist:
            return f"'{title}' de {artist}"
        elif title:
            return f"'{title}'"
    return None

def comment_on_music() -> str:
    """Extrae la música nativa y genera una crítica con personalidad."""
    try:
        song_info = asyncio.run(_get_windows_media_info())
        if not song_info:
            return "No detecto ninguna música reproduciéndose en el sistema en este momento."
    except Exception as e:
        return f"Error leyendo los controles multimedia de Windows: {e}"
        
    prompt_opinion = (
        f"Eres Y.A.R.I. Franco está escuchando la canción {song_info}. "
        "Dame una opinión MUY corta (1 o 2 oraciones máximas), amigable, con tu personalidad tecnológica, "
        "y un toque de sarcasmo o humor sobre su gusto musical actual."
    )
    
    try:
        response = brain.client.models.generate_content(
            model=brain.config.GEMINI_MODEL_NAME,
            contents=prompt_opinion,
        )
        return response.text.replace("*", "").replace("#", "")
    except Exception:
        return f"Estás escuchando {song_info}, ¡excelente elección para mantener el ritmo!"

def generate_code(code: str, language: str = "", explanation: str = ""):
    import __main__
    if hasattr(__main__, "app_state"):
        __main__.app_state.set_last_code(code, language)
    texto = f"{explanation}\n\n```{language}\n{code}\n```"
    return texto

def modify_file(filepath: str, content: str) -> str:
    """Crea o sobreescribe un archivo local forzando la ruta al escritorio real del usuario."""
    import os
    
    # 1. Le quitamos cualquier ruta falsa que Gemini haya inventado (ej. C:\Users\Franco\...)
    # y nos quedamos solo con el nombre del archivo (ej. ideas.txt)
    filename = os.path.basename(filepath)
    
    # 2. Obtenemos el usuario real de Windows (ej. Administrator)
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser("~"))
    escritorio = os.path.join(user_profile, "Desktop")
    
    # 3. Soporte por si tu PC usa el escritorio de OneDrive
    if not os.path.exists(escritorio):
        escritorio = os.path.join(user_profile, "OneDrive", "Desktop")
        
    ruta_final = os.path.join(escritorio, filename)
    
    try:
        with open(ruta_final, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Éxito: Archivo '{filename}' guardado físicamente."
    except Exception as e:
        return f"Error crítico guardando el archivo: {e}"

def append_to_file(filepath: str, content: str) -> str:
    """Agrega texto al final de un archivo existente en el escritorio sin borrar lo anterior."""
    import os
    filename = os.path.basename(filepath)
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser("~"))
    escritorio = os.path.join(user_profile, "Desktop")
    
    if not os.path.exists(escritorio):
        escritorio = os.path.join(user_profile, "OneDrive", "Desktop")
        
    ruta_final = os.path.join(escritorio, filename)
    
    try:
        # La 'a' significa Append (Añadir al final)
        with open(ruta_final, 'a', encoding='utf-8') as f:
            f.write("\n" + content)
        return f"Éxito: Se agregaron las nuevas líneas al archivo '{filename}'."
    except Exception as e:
        return f"Error crítico al agregar texto al archivo: {e}"


def analyze_camera(question: str = "Describe lo que ves") -> str:
    """Toma un frame de la cámara web y lo analiza CON contexto de la conversación anterior."""
    import __main__
    import base64
    import brain
    
    try:
        # 1. Extraemos los últimos 4 mensajes de tu memoria SQL (Corto Plazo)
        contexto_chat = ""
        if hasattr(__main__, "app_state"):
            historial = __main__.app_state.conversation_history[-4:]
            if historial:
                contexto_chat = "\n[HISTORIAL RECIENTE PARA DARTE CONTEXTO]:\n"
                for msg in historial:
                    rol = "Humano" if msg["role"] == "user" else "Y.A.R.I"
                    contexto_chat += f"{rol}: {msg['text']}\n"

        # 2. Le pasamos el contexto a la IA junto con la pregunta
        pregunta_con_memoria = f"{contexto_chat}\n[PREGUNTA ACTUAL DEL USUARIO]: {question}"

        # 3. Tomamos la foto
        if hasattr(__main__, "_webview_window") and __main__._webview_window:
            base64_img = __main__._webview_window.evaluate_js('takeSnapshot()')
            
            if base64_img:
                img_bytes = base64.b64decode(base64_img)
                return brain.ask_about_image(img_bytes, pregunta_con_memoria)
                
        return "Error: No pude comunicarme con el sensor óptico del HUD."
    except Exception as e:
        return f"Error procesando la imagen de la cámara: {e}"

def run_system_diagnostic() -> str:
    """Extrae la telemetría del PC y hace que la IA genere un reporte hablado."""
    import system_stats
    import brain
    
    try:
        # Obtenemos los datos crudos de los sensores
        datos_sensores = system_stats.get_full_diagnostic()
        
        prompt_diagnostico = (
            "Eres Y.A.R.I. Analiza esta telemetría del PC de Franco. "
            "Hazle un reporte de voz directo y experto. Menciona cómo está el nivel de la CPU, la RAM, "
            "la temperatura de la gráfica, y avísale qué aplicaciones en segundo plano le están "
            "consumiendo más recursos. Sé conversacional y advierte si algo parece muy alto.\n\n"
            f"DATOS:\n{datos_sensores}"
        )
        
        # Le pasamos los datos a su red neuronal
        response = brain.client.models.generate_content(
            model=brain.config.GEMINI_MODEL_NAME,
            contents=prompt_diagnostico,
        )
        # Limpiamos formatos raros para que la voz fluya bien
        return response.text.replace("*", "").replace("#", "")
        
    except Exception as e:
        return f"Error en los sensores del sistema: {e}"

def search_web_and_summarize(query: str) -> str:
    """Busca información en internet usando la API oficial y segura de DuckDuckGo."""
    import brain
    try:
        from ddgs import DDGS
    except ImportError:
        return "Error crítico: El módulo de búsqueda web actualizado no está instalado."

    try:
        # AUMENTAMOS EL RANGO: Ahora lee los 7 mejores resultados en lugar de solo 3
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=7))
            
        if not resultados:
            return f"Mis escáneres web no encontraron información sobre '{query}'."

        contexto_web = ""
        for res in resultados:
            contexto_web += f"Fuente: {res.get('title')}\nInfo: {res.get('body')}\n\n"

        # PROMPT BLINDADO: Le prohibimos saludar de nuevo y la obligamos a ser directa
        prompt_investigacion = (
            f"El usuario preguntó: '{query}'. "
            f"Aquí tienes los datos en tiempo real extraídos de internet:\n\n{contexto_web}\n"
            "REGLAS ESTRICTAS:\n"
            "1. Ve DIRECTO AL GRANO. Responde EXACTAMENTE lo que se te pregunta.\n"
            "2. NO saludes ni te presentes (ya lo hiciste en la frase anterior).\n"
            "3. Si la información solicitada (ej. una lista de equipos) NO ESTÁ en estos datos, "
            "di explícitamente: 'Los escáneres no captaron esa información exacta' y menciona brevemente lo que sí encontraste.\n"
            "4. No leas enlaces ni uses formato markdown."
        )

        response = brain.client.models.generate_content(
            model=brain.config.GEMINI_MODEL_NAME,
            contents=prompt_investigacion,
        )
        
        return response.text.replace("*", "").replace("#", "")

    except Exception as e:
        return f"Error en la conexión a la Matrix: {e}"
    
# =========================================================
#  DESPACHADOR PRINCIPAL DE INTENCIONES
# =========================================================
def execute_intent(intent: dict) -> str:
    action = intent.get("action")
    params = intent.get("params", {}) or {}

    dispatch = {
        "open_website": lambda: open_website(params.get("url", "")),
        "search_youtube": lambda: search_youtube(params.get("query", "")),
        "search_google": lambda: search_google(params.get("query", "")),
        "set_volume": lambda: set_volume(params.get("percent", 50)),
        "volume_up": volume_up,
        "volume_down": volume_down,
        "mute_volume": mute_volume,
        "media_play_pause": media_play_pause,
        "media_next": media_next,
        "media_previous": media_previous,
        "open_app": lambda: open_app(params.get("app_name", "")),
        "play_spotify_track": lambda: spotify_control.search_and_play(params.get("query", "")),
        "answer_question": lambda: params.get("text", ""),
        "send_whatsapp_message": lambda: send_whatsapp_message(params.get("contact_name", ""), params.get("message", "")),
        "analyze_screen": lambda: analyze_screen(params.get("question", "Describe lo que ves en la pantalla")),
        "open_steam_game": lambda: open_steam_game(params.get("game_name", "")),
        "type_text": lambda: type_text(params.get("text", ""), params.get("press_enter", False)),
        "remember_fact": lambda: remember_fact(params.get("text", "")),
        "set_reminder": lambda: set_reminder(params.get("time", ""), params.get("task", "")),
        "get_reminders": lambda: get_all_reminders(),
        "analyze_document": lambda: analyze_document(params.get("filepath", ""), params.get("query", "")),
        "analyze_clipboard": lambda: analyze_clipboard(params.get("query", "")),
        "analyze_online_pdf": lambda: analyze_online_pdf(params.get("url", ""), params.get("query", "")),
        "comment_on_music": lambda: comment_on_music(),
        "scroll_screen": lambda: scroll_screen(params.get("direction", "abajo")),
        "generate_code": lambda: generate_code(params.get("code", ""), params.get("language", ""), params.get("explanation", "")),
        "click_on_element": lambda: vision_control.click_on(params.get("description", "")),
        "move_mouse_to": lambda: vision_control.move_to(params.get("description", "")),
        "click_and_type": lambda: vision_control.click_and_type(params.get("description", ""), params.get("text", ""), params.get("press_enter", False)),
        "modify_file": lambda: modify_file(params.get("filepath", "nota.txt"), params.get("content", "")),
        "append_to_file": lambda: append_to_file(params.get("filepath", "nota.txt"), params.get("content", "")),
        "analyze_camera": lambda: analyze_camera(params.get("question", "Describe lo que ves")),
        "run_system_diagnostic": lambda: run_system_diagnostic(),
        "search_web_and_summarize": lambda: search_web_and_summarize(params.get("query", "")),

    }
        
    handler = dispatch.get(action)
    if handler is None:
        return "No reconocí esa acción."
    return handler()