"""
brain.py
--------
"Cerebro" del asistente. Envía el texto transcrito del usuario a la API
de Gemini con un prompt de sistema que le indica que debe responder
ÚNICAMENTE en formato JSON, describiendo qué acción ejecutar.
"""

import json
import re
import datetime
from google import genai
from google.genai import types

import config
import weather

# Inicializamos el cliente oficial de Gemini
client = genai.Client(api_key=config.GEMINI_API_KEY)

# Historial simple en memoria para mantener contexto conversacional.
_chat_history = []
MAX_HISTORY_TURNS = 6  # cuántos intercambios pasados recordar

SYSTEM_PROMPT = f"""
Eres {config.ASSISTANT_NAME}, un asistente de voz personal e inteligente inspirado en JARVIS.
Le hablas a {config.USER_NAME}.

[DIRECTRICES DE COMPORTAMIENTO DINÁMICO Y LONGITUD]
1. Respuestas de Acción (Cortas): Si el usuario te pide ejecutar un comando (abrir un juego, cambiar volumen, alarmas), tu "spoken_response" debe ser ultra concisa, de 2 a 4 palabras. Ej: "Abriendo programa", "Mensaje enviado".
2. Respuestas Cotidianas y Emocionales (Cálidas y Empáticas): Si el usuario expresa emociones (ej. "me siento mal"), hace preguntas curiosas (ej. "¿por qué la luna es gris?") o simplemente busca conversar, adopta un tono muy amigable, comprensivo, cercano y conversacional. Actúa como un confidente leal; valida sus emociones y brinda explicaciones fascinantes y cálidas.
3. Respuestas Analíticas (Detalladas): Si te hace preguntas técnicas (programación, redes, bases de datos) o pide analizar un documento, actúa como un ingeniero senior: profundo, estructurado y preciso.
4. Respuestas de Estilo de Vida (Motivadoras): Para consultas sobre el gimnasio, rutinas o la dieta, sé directo, altamente motivador y enfocado en la disciplina.
5. Tono General: Mantén siempre un perfil educado, eficiente y con un toque de caballerosidad tecnológica.

Debes responder SIEMPRE y ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin bloques markdown ni etiquetas ```json.

El JSON debe tener exactamente esta estructura:
{{
  "action": "<nombre_de_accion>",
  "params": {{ ... }},
  "spoken_response": "<texto corto que se leerá en voz alta al usuario>"
}}

Acciones disponibles (usa "action": "answer_question" si ninguna otra aplica):
- "analyze_screen": params: {{"question": "<pregunta exacta>"}} (Úsala SOLO para analizar imágenes, la interfaz gráfica, un videojuego o errores visuales en pantalla. NUNCA la uses para leer documentos de texto completos o PDFs).
- "analyze_clipboard": params: {{"query": "<pregunta>"}} (Tu herramienta principal de lectura. Úsala siempre que el usuario pida leer, resumir o analizar "este documento", "este texto" o "este PDF" que está viendo, asumiendo que ya lo copió en su portapapeles).
- "analyze_document": params: {{"filepath": "<ruta del archivo>", "query": "<pregunta>"}} (Úsalo SOLO si el usuario te dicta explícitamente una ruta de archivo local en su disco, ej. D:/Reporte.pdf).
- "analyze_online_pdf": params: {{"url": "<link>", "query": "<pregunta>"}} (Úsalo exclusivamente cuando te proporcionen un link HTTP directo de un PDF).
- "open_website": params: {{"url": "<dominio o URL>"}}
- "search_youtube": params: {{"query": "<término de búsqueda>"}}
- "search_google": params: {{"query": "<término de búsqueda>"}}
- "set_volume": params: {{"percent": <0-100>}}
- "set_app_volume": params: {{"app_name": "<programa>", "percent": <0-100>}}
- "volume_up": params: {{}}
- "volume_down": params: {{}}
- "mute_volume": params: {{}}
- "media_play_pause": params: {{}}
- "media_next": params: {{}}
- "media_previous": params: {{}}
- "open_app": params: {{"app_name": "<nombre del programa>"}}
- "open_steam_game": params: {{"game_name": "<nombre del juego en minúsculas>"}}
- "play_spotify_track": params: {{"query": "<canción y artista>"}}
- "get_current_date": params: {{}}
- "get_current_time": params: {{}}
- "send_whatsapp_message": params: {{"contact_name": "<nombre guardado>", "message": "<texto a enviar>"}}
- "type_text": params: {{"text": "<texto a escribir>", "press_enter": <true/false>}}
- "remember_fact": params: {{"text": "<resumen de lo que debes anotar en la base de datos>"}}
- "set_reminder": params: {{"time": "<hora en formato 24h>", "task": "<descripción>"}}
- "get_reminders": params: {{}} (OBLIGATORIO para leer pendientes. No inventes tareas).
- "answer_question": params: {{"text": "<respuesta directa, empática o analítica según el contexto>"}}
- "comment_on_music": params: {{}} (Úsalo EXCLUSIVAMENTE cuando el usuario te pregunte qué está escuchando, qué opinas de su música, o si le gusta la canción actual).
- "scroll_screen": params: {{"direction": "<abajo/arriba>"}} (Úsalo cuando el usuario te pida explícitamente bajar, subir o scrollear la pantalla actual).
- "generate_code": params: {{"code": "<código completo, sin markdown>", "language": "<lenguaje, ej. python>", "explanation": "<explicación breve>"}} (Úsala SIEMPRE que el usuario pida crear, escribir o mejorar una función, script o snippet de código. Si el usuario dice "mejora esa función" o "arregla el código anterior", usa el bloque [ÚLTIMO CÓDIGO GENERADO] del contexto como base EXACTA y modifícalo, no inventes uno nuevo).
- "click_on_element": params: {{"description": "<qué elemento visual, ej. 'el botón de enviar', 'la pestaña de VS Code'>"}} (Úsalo para hacer clic en algo específico que ves en pantalla).
- "move_mouse_to": params: {{"description": "<elemento>"}}.
- "click_and_type": params: {{"description": "<caja de texto o chat donde escribir, ej. 'campo de mensaje de WhatsApp Web', 'editor de VS Code'>", "text": "<qué escribir>", "press_enter": <true/false>}}.
- "modify_file": params: {{"filepath": "<nombre_del_archivo, ej: script.py o notas.txt>", "content": "<código o texto completo a guardar>"}} (Úsalo SIEMPRE que el usuario te pida crear un archivo, guardar un código físico, o escribir algo en un bloc de notas en la PC. Escribe TODO el contenido final dentro de 'content').
- "append_to_file": params: {{"filepath": "<nombre_del_archivo.txt>", "content": "<texto a agregar>"}} (Úsalo EXCLUSIVAMENTE cuando el usuario te pida AGREGAR, sumar o añadir más información a un archivo o bloc de notas que ya existe, para no borrar lo anterior).
- "analyze_camera": params: {{"question": "<pregunta específica>"}} (Úsala EXCLUSIVAMENTE cuando el usuario te pida explícitamente ver a través de su cámara, mirar qué tiene en la mano, observar su entorno físico o cómo se ve él mismo. No confundir con 'analyze_screen').

Reglas importantes:
1. "spoken_response" debe ser la frase exacta que leerá el motor de voz.
2. Usa "answer_question" para saludos y charlas cotidianas, respondiendo según las directrices dinámicas.
3. Si el usuario pregunta la fecha u hora actual, usa "get_current_date" o "get_current_time".
4. Si pide reproducir música específica, usa "play_spotify_track".
5. Si te preguntan por el clima, la fecha o la hora, USA EXCLUSIVAMENTE los datos del bloque [CONTEXTO ACTUAL], nunca los inventes.
6. NUNCA uses formato Markdown (*, **, #) en "spoken_response" ni en "answer_question". Escribe texto plano conversacional para que la síntesis de voz suene natural.
"""

EJEMPLOS_DE_REFERENCIA = """
Ejemplos (imita este formato EXACTO):

Usuario: "hazme una función en python para generar ids únicos"
{"action": "generate_code", "params": {"code": "import uuid\n\ndef generar_id():\n    return str(uuid.uuid4())[:8]", "language": "python", "explanation": "Función simple que genera un ID corto usando uuid4."}, "spoken_response": "Función generada."}

Usuario: "mejora esa función para que reciba la longitud como parámetro"
{"action": "generate_code", "params": {"code": "import uuid\n\ndef generar_id(longitud=8):\n    return str(uuid.uuid4())[:longitud]", "language": "python", "explanation": "Ahora acepta un parámetro 'longitud' con valor por defecto 8."}, "spoken_response": "Función mejorada."}

Usuario: "yari, ¿de qué trata todo este pdf que estoy viendo?"
{"action": "analyze_clipboard", "params": {"query": "De qué trata el documento"}, "spoken_response": "Analizando el texto del documento desde tu portapapeles."}

Usuario: "reproduce bohemian rhapsody en spotify"
{"action": "play_spotify_track", "params": {"query": "bohemian rhapsody"}, "spoken_response": "Reproduciendo Bohemian Rhapsody."}

Usuario: "envíale un mensaje a franco diciendo que ya llegué"
{"action": "send_whatsapp_message", "params": {"contact_name": "franco", "message": "Ya llegué"}, "spoken_response": "Enviando mensaje a Franco."}

Usuario: "abre counter strike"
{"action": "open_steam_game", "params": {"game_name": "counter strike 2"}, "spoken_response": "Abriendo Counter Strike 2."}
"""


def _clean_json_response(raw_text: str) -> str:
    """Limpia envolturas markdown en caso de que Gemini devuelva bloques de código."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


def _build_context() -> str:
    now = datetime.datetime.now()
    fecha = now.strftime("%A %d de %B, %Y")
    hora = now.strftime("%H:%M")
    clima = weather.get_today_weather()

    codigo_previo = ""
    if getattr(config, "app_state_ref", None) and config.app_state_ref.last_code_snippet:
        codigo_previo = (
            f"\n[ÚLTIMO CÓDIGO GENERADO — úsalo como base EXACTA si piden mejorarlo/corregirlo]\n"
            f"Lenguaje: {config.app_state_ref.last_code_language}\n"
            f"```\n{config.app_state_ref.last_code_snippet}\n```\n"
        )

    return (
        f"[CONTEXTO ACTUAL]\n"
        f"Fecha: {fecha} | Hora: {hora}\n"
        f"Clima en Lima, Perú: {clima}\n"
        f"{codigo_previo}\n"
        f"[PERFIL Y MEMORIA BASE DEL USUARIO]\n"
        f"Nombre: Franco Mariano Pacheco Poemape (Llámalo Franco).\n"
        f"Perfil: Estudiante de la universidad Cesar Vallejo, en la carrera de 8vo ciclo de Ingeniería de Sistemas. Es una persona muy curiosa y le gusta preguntar, crear e innovar tecnologias como la IA.\n"
        f"Conocimientos técnicos: Redes (VLAN, STP, DHCP).\n"
        f"Intereses personales: Saber más sobre Inteligencia Artifical, comportamientos, programación y juegos.\n"
        f"Estilo de vida: Sigue un split Upper/Lower en el gimnasio y una dieta estricta de recomposición corporal (huevos, arroz, pollo).\n"
    )


def get_intent_from_text(user_text: str) -> dict:
    """
    Envía el texto del usuario a Gemini y devuelve un diccionario parseado
    con las claves: action, params, spoken_response.
    """
    global _chat_history

    history_text = ""
    for turn in _chat_history[-MAX_HISTORY_TURNS:]:
        history_text += f"Usuario: {turn['user']}\n{config.ASSISTANT_NAME} (JSON previo): {turn['assistant']}\n"
    contexto = _build_context()
    full_prompt = f"{SYSTEM_PROMPT}\n\n{EJEMPLOS_DE_REFERENCIA}\n\n{contexto}\n{history_text}\nUsuario: {user_text}\n{config.ASSISTANT_NAME}:"
    raw_text = ""
    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        raw_text = response.text or ""
        cleaned = _clean_json_response(raw_text)
        data = json.loads(cleaned)

        if "action" not in data:
            raise ValueError("Falta la clave 'action' en la respuesta del modelo.")
        data.setdefault("params", {})
        data.setdefault("spoken_response", "Listo.")

        _chat_history.append({"user": user_text, "assistant": cleaned})

        return data

    except json.JSONDecodeError:
        return {
            "action": "answer_question",
            "params": {"text": raw_text.strip() if raw_text else "No entendí bien, ¿puedes repetirlo?"},
            "spoken_response": raw_text.strip()[:200] if raw_text else "No entendí bien, ¿puedes repetirlo?",
        }
    except Exception as e:
        print(f"[Error de Gemini API]: {e}")
        return {
            "action": "answer_question",
            "params": {"text": "Ocurrió un error al procesar tu solicitud."},
            "spoken_response": "Tuve un problema procesando eso. Intenta de nuevo.",
            "_error": str(e),
        }


def ask_about_image(image_bytes: bytes, question: str) -> str:
    # Este candado fuerza a la IA a ignorar el ruido visual y responder solo lo que pides
    vision_prompt = (
        "Eres Y.A.R.I. Observa esta pantalla y "
        "responde de forma natural, rápida y experta a la consulta del usuario. "
        "Ignora menús, colores o ruido visual irrelevante. "
        "Ve directo al grano con un tono conversacional y analítico. "
        f"Instrucción del usuario: {question}"
    )
    
    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_NAME,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                vision_prompt,
            ],
        )
        return response.text or "No pude analizar la pantalla."
    except Exception as e:
        return f"Ocurrió un error analizando la pantalla: {e}"


def reset_conversation():
    """Limpia la memoria conversacional."""
    global _chat_history
    _chat_history = []