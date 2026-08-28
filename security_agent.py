import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import voice
import config

class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Ignoramos si se crea una carpeta, solo nos importan los archivos
        if event.is_directory:
            return
        
        filepath = event.src_path
        filename = os.path.basename(filepath)
        ext = filename.split('.')[-1].lower()
        
        # Vectores de ataque comunes
        peligrosas = ['exe', 'msi', 'bat', 'vbs', 'zip', 'rar', 'js']
        
        if ext in peligrosas:
            # Damos un pequeño retraso de 2 segundos para que el archivo termine de escribirse en el disco
            time.sleep(2)
            
            mensaje = f"Alerta de seguridad. He detectado la descarga de un archivo potencialmente ejecutable llamado {filename}. Sugiero precaución antes de abrirlo."
            
            # Cambiamos el estado visual del orbe si existe la referencia
            if getattr(config, "app_state_ref", None):
                config.app_state_ref.set_orb_state("speaking")
            
            voice.speak(mensaje)
            
            if getattr(config, "app_state_ref", None):
                config.app_state_ref.set_orb_state("idle")

def start_download_sentinel():
    """Inicia el observador pasivo en la carpeta de Descargas del usuario."""
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser("~"))
    descargas_path = os.path.join(user_profile, "Downloads")
    
    if not os.path.exists(descargas_path):
        return 
        
    event_handler = DownloadHandler()
    observer = Observer()
    # recursive=False indica que solo mire la carpeta principal, no las subcarpetas, ahorrando memoria
    observer.schedule(event_handler, descargas_path, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(5)
    except Exception as e:
        print(f"Error en el Centinela de Seguridad: {e}")
        observer.stop()
    observer.join()