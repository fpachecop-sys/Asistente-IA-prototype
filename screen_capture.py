import mss
import io
import os
import datetime
from PIL import Image

def take_screenshot(save_to_memory=True) -> bytes:
    """Captura la pantalla, guarda un registro ligero y devuelve bytes para Gemini."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # monitor principal
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        
        # --- CAJITA DE MEMORIA ---
        if save_to_memory:
            os.makedirs("memory", exist_ok=True) # Crea la carpeta si no existe
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filepath = f"memory/vision_{timestamp}.jpg"
            # Guardamos localmente con quality=35 para que pese poquísimo (ej. 50kb)
            img.save(filepath, format="JPEG", quality=35) 
            
        # --- BUFFER PARA LA IA ---
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70) # Calidad normal para que Gemini vea bien
        return buffer.getvalue()