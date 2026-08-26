# vision_control.py
import pyautogui
import json
import re
import screen_capture
import brain

def _clean_json(text):
    text = text.strip()
    text = re.sub(r"^```json", "", text).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text

def locate_element(description: str) -> dict | None:
    """Le pide a Gemini que ubique un elemento en la pantalla actual y devuelve
    coordenadas relativas (0-100) convertidas a píxeles reales."""
    img_bytes = screen_capture.take_screenshot(save_to_memory=False)
    screen_w, screen_h = pyautogui.size()

    prompt = f"""
Analiza esta captura de pantalla. Ubica el elemento: "{description}".
Responde SOLO con JSON (sin markdown):
{{"found": true/false, "x_percent": <0-100 float, centro horizontal del elemento>, "y_percent": <0-100 float, centro vertical del elemento>}}
Si no lo encuentras, "found": false.
"""
    try:
        response = brain.client.models.generate_content(
            model=brain.config.GEMINI_MODEL_NAME,
            contents=[
                brain.types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                prompt,
            ],
        )
        data = json.loads(_clean_json(response.text))
        if not data.get("found"):
            return None
        x = int(screen_w * data["x_percent"] / 100)
        y = int(screen_h * data["y_percent"] / 100)
        return {"x": x, "y": y}
    except Exception as e:
        print(f"[Error localizando elemento]: {e}")
        return None


def click_on(description: str) -> str:
    coords = locate_element(description)
    if not coords:
        return f"No pude encontrar '{description}' en la pantalla."
    pyautogui.click(coords["x"], coords["y"])
    return f"Hice clic en '{description}'."


def move_to(description: str) -> str:
    coords = locate_element(description)
    if not coords:
        return f"No pude ubicar '{description}'."
    pyautogui.moveTo(coords["x"], coords["y"], duration=0.3)
    return f"Moví el cursor a '{description}'."


def click_and_type(description: str, text: str, press_enter: bool = False) -> str:
    """Hace clic en un campo (ej. 'la caja de texto del chat de Discord') y escribe ahí."""
    coords = locate_element(description)
    if not coords:
        return f"No encontré dónde escribir ('{description}')."
    pyautogui.click(coords["x"], coords["y"])
    import time; time.sleep(0.4)
    pyautogui.write(text, interval=0.02)
    if press_enter:
        pyautogui.press("enter")
    return f"Escribí en '{description}': {text}"