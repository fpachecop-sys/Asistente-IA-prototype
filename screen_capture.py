# screen_capture.py
import mss
import base64
import io
from PIL import Image

def take_screenshot() -> bytes:
    """Captura la pantalla principal y devuelve los bytes en JPEG."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # monitor principal
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        return buffer.getvalue()