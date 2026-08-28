# ui.py
"""
Núcleo flotante HUD (Bolita). Ahora con estética Sci-Fi,
anillos segmentados rotatorios y pulsaciones dinámicas.
"""
import customtkinter as ctk
import math
import queue

import config

# Colores actualizados para un estilo neón / cyber
STATE_COLORS = {
    "idle": ("#0a3a52", "#00e5ff"),       # Azul oscuro / Cian neón
    "listening": ("#004d33", "#00ffaa"),  # Verde oscuro / Verde neón
    "thinking": ("#4a0080", "#b520ff"),   # Púrpura oscuro / Magenta brillante
    "speaking": ("#00e5ff", "#ffffff"),   # Cian neón / Blanco puro
}
STATE_LABELS = {
    "idle": "EN REPOSO",
    "listening": "ESCUCHANDO...",
    "thinking": "PROCESANDO...",
    "speaking": "TRANSMITIENDO...",
}

class JarvisUI(ctk.CTk):
    def __init__(self, app_state, on_restore_dashboard=None, start_hidden=True):
        super().__init__()

        self.app_state = app_state
        self.on_restore_dashboard = on_restore_dashboard

        ctk.set_appearance_mode(config.UI_APPEARANCE_MODE)
        self.overrideredirect(True)
        self.attributes("-topmost", config.UI_ALWAYS_ON_TOP)
        self.configure(fg_color=config.UI_TRANSPARENT_COLOR)
        try:
            self.attributes("-transparentcolor", config.UI_TRANSPARENT_COLOR)
        except Exception:
            pass

        w, h = config.UI_WIDTH, config.UI_HEIGHT
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - w - 40
        y = screen_h - h - 100
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.canvas = ctk.CTkCanvas(
            self, width=w, height=h,
            bg=config.UI_TRANSPARENT_COLOR, highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Fuente monoespaciada para un look más técnico
        self.status_label = ctk.CTkLabel(
            self, text=STATE_LABELS["idle"],
            font=("Consolas", 11, "bold"),
            text_color="#00e5ff", fg_color=config.UI_TRANSPARENT_COLOR,
        )
        self.status_label.place(relx=0.5, rely=0.92, anchor="center")

        self.canvas.bind("<ButtonPress-1>", self._start_move)
        self.canvas.bind("<B1-Motion>", self._do_move)
        self.canvas.bind("<Double-Button-3>", lambda e: self._restore_dashboard())

        self._drag_data = {"x": 0, "y": 0}
        self.current_state = "idle"
        
        # Variables para controlar la rotación geométrica
        self._pulse_phase = 0.0
        self._rotation_angle = 0.0

        if start_hidden:
            self.withdraw()

        self._animate()
        self._poll_commands()

    def _start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_move(self, event):
        x = self.winfo_pointerx() - self._drag_data["x"]
        y = self.winfo_pointery() - self._drag_data["y"]
        self.geometry(f"+{x}+{y}")

    def _restore_dashboard(self):
        self.withdraw()
        if self.on_restore_dashboard:
            self.on_restore_dashboard()

    def set_state(self, state: str):
        if state not in STATE_COLORS:
            state = "idle"
        self.current_state = state
        self.status_label.configure(
            text=STATE_LABELS[state],
            text_color=STATE_COLORS[state][1]  # El texto cambia al color brillante del estado
        )

    def _poll_commands(self):
        try:
            while True:
                cmd = self.app_state.orb_commands.get_nowait()
                if cmd == "show":
                    self.deiconify()
                elif cmd == "hide":
                    self.withdraw()
                elif cmd.startswith("state:"):
                    self.set_state(cmd.split(":", 1)[1])
        except queue.Empty:
            pass
        self.after(50, self._poll_commands)

    def _animate(self):
        self.canvas.delete("all")
        w, h = config.UI_WIDTH, config.UI_HEIGHT
        cx, cy = w // 2, h // 2 - 15
        base_radius = 55

        color_inner, color_outer = STATE_COLORS[self.current_state]
        
        # 1. Motor Térmico (Velocidad adaptativa)
        speed = {"idle": 0.02, "listening": 0.12, "thinking": 0.18, "speaking": 0.25}[self.current_state]
        
        self._pulse_phase += speed
        self._rotation_angle = (self._rotation_angle + (speed * 45)) % 360
        
        pulse = math.sin(self._pulse_phase) * 4
        radius = base_radius + pulse

        # 2. Retícula de Apuntado (Crosshair estático)
        self.canvas.create_line(cx - radius - 35, cy, cx + radius + 35, cy, fill=color_inner, dash=(1, 6), width=1)
        self.canvas.create_line(cx, cy - radius - 35, cx, cy + radius + 35, fill=color_inner, dash=(1, 6), width=1)

        # 3. Anillo Perimetral y Nodos Satelitales
        outer_r = radius + 25
        self.canvas.create_oval(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r, outline=color_inner, width=1, dash=(1, 8))
        
        # Calculamos 4 satélites orbitando el anillo exterior
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle + self._rotation_angle * 0.8)
            nx = cx + math.cos(rad) * outer_r
            ny = cy + math.sin(rad) * outer_r
            self.canvas.create_oval(nx - 2, ny - 2, nx + 2, ny + 2, fill=color_outer, outline="")

        # 4. Anillo de Contención (Múltiples arcos finos en contra-rotación)
        cont_r = radius + 15
        for i in range(4):
            start = -self._rotation_angle * 1.2 + (i * 90)
            self.canvas.create_arc(cx - cont_r, cy - cont_r, cx + cont_r, cy + cont_r,
                                   start=start, extent=45, style="arc", outline=color_outer, width=1)

        # 5. Anillo de Datos Principal (Asimétrico)
        data_r = radius + 5
        self.canvas.create_arc(cx - data_r, cy - data_r, cx + data_r, cy + data_r,
                               start=self._rotation_angle * 1.5, extent=140, style="arc", outline=color_inner, width=2)
        self.canvas.create_arc(cx - data_r, cy - data_r, cx + data_r, cy + data_r,
                               start=self._rotation_angle * 1.5 + 200, extent=40, style="arc", outline=color_outer, width=3)

        # 6. Escáner de Frecuencia Interior (Giro ultra rápido con patrón de bits)
        scan_r = radius - 5
        self.canvas.create_arc(cx - scan_r, cy - scan_r, cx + scan_r, cy + scan_r,
                               start=-self._rotation_angle * 2.5, extent=280, style="arc", outline=color_inner, width=1, dash=(2, 3, 5, 3))

        # 7. Núcleo Cuántico (Respiración central)
        core_r = 13 + math.sin(self._pulse_phase * 3) * 3
        self.canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r, fill=color_outer, outline="")
        
        # 8. Anillo estabilizador pegado al núcleo
        self.canvas.create_oval(cx - core_r - 5, cy - core_r - 5, cx + core_r + 5, cy + core_r + 5, 
                                outline=color_inner, width=2, dash=(4, 4))

        # Mantener los 30 FPS fluidos
        self.after(33, self._animate)