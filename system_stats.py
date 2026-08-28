# system_stats.py
import psutil

def get_system_stats() -> dict:
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "disk_percent": psutil.disk_usage("/").percent,
    }

def get_full_diagnostic() -> str:
    import psutil
    try:
        import GPUtil
    except ImportError:
        GPUtil = None

    # 1. Escaneo de CPU y RAM
    cpu_percent = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_percent = ram.percent
    ram_used = round(ram.used / (1024**3), 2)
    ram_total = round(ram.total / (1024**3), 2)

    # 2. Búsqueda de aplicaciones devoradoras de RAM (Segundo plano)
    procesos = []
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            if p.info['memory_info']:
                procesos.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    # Ordenamos de mayor a menor consumo
    procesos = sorted(procesos, key=lambda p: p['memory_info'].rss, reverse=True)
    top_procesos = procesos[:3] # Tomamos el Top 3

    texto_procesos = ""
    for p in top_procesos:
        mem_mb = round(p['memory_info'].rss / (1024**2), 1)
        texto_procesos += f"- {p['name']}: {mem_mb} MB\n"

    # 3. Escaneo Térmico de GPU (NVIDIA)
    gpu_text = "GPU: No se detectaron sensores NVIDIA."
    if GPUtil:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            gpu_text = f"NVIDIA {gpu.name} | Temp: {gpu.temperature}°C | Uso: {round(gpu.load*100, 1)}%"

    # 4. Empaquetamos todo el reporte
    diagnostico = (
        f"=== REPORTE DE HARDWARE ===\n"
        f"CPU: Uso al {cpu_percent}%\n"
        f"RAM: {ram_percent}% de carga ({ram_used} GB usados de {ram_total} GB)\n"
        f"GRAFICA: {gpu_text}\n"
        f"\nTOP 3 PROCESOS MÁS PESADOS:\n{texto_procesos}"
    )
    return diagnostico

# Variables de estado (Anti-Spam de Alertas)
_alerta_ram_activa = False
_alerta_cpu_activa = False

def check_telemetry_alerts() -> list:
    """Monitorea el hardware y devuelve alertas solo si cruzan umbrales críticos."""
    global _alerta_ram_activa, _alerta_cpu_activa
    alertas = []
    
    # 1. Monitoreo de RAM (Umbral: 85%)
    ram_percent = psutil.virtual_memory().percent
    if ram_percent >= 85.0:
        if not _alerta_ram_activa:
            alertas.append(f"Atención. La memoria RAM ha superado el {ram_percent} por ciento. Sugiero cerrar procesos pesados.")
            _alerta_ram_activa = True
    else:
        # Si la RAM baja a niveles seguros, "reseteamos" la alerta
        if ram_percent < 75.0:
            _alerta_ram_activa = False

    # 2. Monitoreo de CPU (Umbral: 95%)
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent >= 95.0:
        if not _alerta_cpu_activa:
            alertas.append("Detecto un consumo crítico de procesador cercano al límite. Posible cuello de botella.")
            _alerta_cpu_activa = True
    else:
        if cpu_percent < 80.0:
            _alerta_cpu_activa = False
            
    return alertas