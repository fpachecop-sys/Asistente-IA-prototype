"""
ui.py
-----
Interfaz gráfica ultra ligera: una ventana flotante, pequeña, sin bordes,
"always on top", con un orbe circular dibujado en un Canvas de Tkinter
(no usamos GIFs ni video, así el consumo de CPU/RAM es mínimo).

El orbe cambia de color y "pulsa" según el estado:
    - idle       -> gris/azul tenue, quieto
    - listening  -> celeste brillante, pulso rápido
    - thinking   -> morado, rotación/parpadeo
    - speaking   -> verde, pulso al ritmo de "habla" simulado

Toda la animación se hace con `after()` de Tkinter, que es muy barato
en CPU comparado con librerías gráficas pesadas.
"""

import customtkinter as ctk
import math

import config

STATE_COLORS = {
    "idle": ("#2b3a55", "#3d5175"),
    "listening": ("#00c8ff", "#33d9ff"),
    "thinking": ("#9b30ff", "#b565ff"),
    "speaking": ("#00ff9d", "#33ffb5"),
}

STATE_LABELS = {
    "idle": "En reposo",
    "listening": "Escuchando...",
    "thinking": "Pensando...",
    "speaking": "Hablando...",
}


class JarvisUI(ctk.CTk):
    def __init__(self, on_close_callback=None):
        super().__init__()

        self.on_close_callback = on_close_callback

        # ---- Configuración de ventana ----
        ctk.set_appearance_mode(config.UI_APPEARANCE_MODE)
        self.overrideredirect(True)  # sin bordes ni barra de título
        self.attributes("-topmost", config.UI_ALWAYS_ON_TOP)
        self.configure(fg_color=config.UI_TRANSPARENT_COLOR)

        # Intenta hacer transparente el color de fondo (funciona bien en Windows).
        # En Linux/Mac puede no tener efecto; la ventana simplemente se verá
        # como un panel oscuro sólido, lo cual sigue siendo liviano y elegante.
        try:
            self.attributes("-transparentcolor", config.UI_TRANSPARENT_COLOR)
        except Exception:
            pass

        w, h = config.UI_WIDTH, config.UI_HEIGHT
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        # Posiciona la ventana en la esquina inferior derecha por defecto
        x = screen_w - w - 40
        y = screen_h - h - 100
        self.geometry(f"{w}x{h}+{x}+{y}")

        # ---- Canvas para el orbe ----
        self.canvas = ctk.CTkCanvas(
            self,
            width=w,
            height=h,
            bg=config.UI_TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # ---- Etiqueta de estado ----
        self.status_label = ctk.CTkLabel(
            self,
            text=STATE_LABELS["idle"],
            font=("Segoe UI", 12, "bold"),
            text_color="#dddddd",
            fg_color=config.UI_TRANSPARENT_COLOR,
        )
        self.status_label.place(relx=0.5, rely=0.92, anchor="center")

        # ---- Permitir arrastrar la ventana con el mouse ----
        self.canvas.bind("<ButtonPress-1>", self._start_move)
        self.canvas.bind("<B1-Motion>", self._do_move)

        # Doble click derecho para cerrar la app manualmente
        self.canvas.bind("<Double-Button-3>", lambda e: self._close())

        self._drag_data = {"x": 0, "y": 0}

        # ---- Estado interno de la animación ----
        self.current_state = "idle"
        self._pulse_phase = 0.0
        self._animate()

    # -----------------------------------------------------
    #   Arrastrar ventana
    # -----------------------------------------------------
    def _start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_move(self, event):
        x = self.winfo_pointerx() - self._drag_data["x"]
        y = self.winfo_pointery() - self._drag_data["y"]
        self.geometry(f"+{x}+{y}")

    def _close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()

    # -----------------------------------------------------
    #   Cambiar estado visual (llamado desde main.py)
    # -----------------------------------------------------
    def set_state(self, state: str):
        """state: 'idle' | 'listening' | 'thinking' | 'speaking'"""
        if state not in STATE_COLORS:
            state = "idle"
        self.current_state = state
        self.status_label.configure(text=STATE_LABELS[state])

    # -----------------------------------------------------
    #   Bucle de animación (ligero: solo redibuja un círculo)
    # -----------------------------------------------------
    def _animate(self):
        self.canvas.delete("all")

        w, h = config.UI_WIDTH, config.UI_HEIGHT
        cx, cy = w // 2, h // 2 - 15
        base_radius = 55

        color_inner, color_outer = STATE_COLORS[self.current_state]

        # Velocidad de pulso distinta según el estado, para que se "sienta" diferente
        speed = {"idle": 0.04, "listening": 0.25, "thinking": 0.15, "speaking": 0.35}[self.current_state]
        self._pulse_phase += speed

        pulse = math.sin(self._pulse_phase) * 8  # oscila +/- 8px

        radius = base_radius + pulse

        # Aro exterior (glow simulado con óvalos concéntricos semi-transparentes vía color)
        self.canvas.create_oval(
            cx - radius - 15, cy - radius - 15, cx + radius + 15, cy + radius + 15,
            outline=color_outer, width=2,
        )
        # Círculo principal
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=color_inner, outline=color_outer, width=3,
        )
        # Núcleo brillante
        core_r = radius * 0.35
        self.canvas.create_oval(
            cx - core_r, cy - core_r, cx + core_r, cy + core_r,
            fill=color_outer, outline="",
        )

        # Volvemos a llamar esta función en ~30ms (~33 FPS), suficientemente
        # fluido para el ojo humano sin saturar la CPU.
        self.after(30, self._animate)
