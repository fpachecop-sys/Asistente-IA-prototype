# ui.py
"""
Bolita flotante. Ahora vive en un hilo del mismo proceso y recibe
comandos por cola en vez de ser un proceso aparte, así el estado
(historial, hilo de grabación, etc.) nunca se duplica ni se pierde.
"""
import customtkinter as ctk
import math
import queue

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

        self.status_label = ctk.CTkLabel(
            self, text=STATE_LABELS["idle"],
            font=("Segoe UI", 12, "bold"),
            text_color="#dddddd", fg_color=config.UI_TRANSPARENT_COLOR,
        )
        self.status_label.place(relx=0.5, rely=0.92, anchor="center")

        self.canvas.bind("<ButtonPress-1>", self._start_move)
        self.canvas.bind("<B1-Motion>", self._do_move)
        # Doble click derecho: vuelve al dashboard (ya no cierra la app)
        self.canvas.bind("<Double-Button-3>", lambda e: self._restore_dashboard())

        self._drag_data = {"x": 0, "y": 0}
        self.current_state = "idle"
        self._pulse_phase = 0.0

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
        self.status_label.configure(text=STATE_LABELS[state])

    # -----------------------------------------------------
    #   Escucha comandos desde app_state.orb_commands
    #   (así el bridge de pywebview, que corre en otro hilo,
    #   nunca toca Tkinter directamente — solo mete comandos
    #   en la cola, que es segura entre hilos).
    # -----------------------------------------------------
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
        speed = {"idle": 0.04, "listening": 0.25, "thinking": 0.15, "speaking": 0.35}[self.current_state]
        self._pulse_phase += speed
        pulse = math.sin(self._pulse_phase) * 8
        radius = base_radius + pulse

        self.canvas.create_oval(
            cx - radius - 15, cy - radius - 15, cx + radius + 15, cy + radius + 15,
            outline=color_outer, width=2,
        )
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=color_inner, outline=color_outer, width=3,
        )
        core_r = radius * 0.35
        self.canvas.create_oval(
            cx - core_r, cy - core_r, cx + core_r, cy + core_r,
            fill=color_outer, outline="",
        )
        self.after(30, self._animate)