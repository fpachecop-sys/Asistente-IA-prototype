// ui_dashboard/app.js
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const btnSend = document.getElementById("btn-send");
const btnClear = document.getElementById("btn-clear");
const clockEl = document.getElementById("clock");
const dateEl = document.getElementById("date-display");
const orbIndicator = document.getElementById("orb-indicator");
const orbLabel = document.getElementById("orb-state-label");

const STATE_LABELS = {
  idle: "En reposo",
  listening: "Escuchando...",
  thinking: "Procesando...",
  speaking: "Transmitiendo...",
};

// ---------------------------------------------------------
// Reloj y Fecha (Estilo HUD)
// ---------------------------------------------------------
function updateDateTime() {
  const now = new Date();
  
  // Hora formato HH:MM:SS
  clockEl.textContent = now.toLocaleTimeString("es-PE", { hour12: false });

  // Fecha formato: DÍA // DD / MM / YYYY
  const days = ["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"];
  const dayName = days[now.getDay()];
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const yyyy = now.getFullYear();

  dateEl.textContent = `${dayName} // ${dd}.${mm}.${yyyy}`;
}
setInterval(updateDateTime, 1000);
updateDateTime();

// ---------------------------------------------------------
// Mensajes en el chat
// ---------------------------------------------------------
function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg ${role === "user" ? "msg-user" : "msg-assistant"}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  const time = document.createElement("span");
  time.className = "msg-time";
  time.textContent = new Date().toLocaleTimeString("es-PE", {
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  });

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setOrbState(state) {
  orbIndicator.className = "orb-dot " + (state === "idle" ? "" : state);
  orbLabel.textContent = STATE_LABELS[state] || "En reposo";
}

// ---------------------------------------------------------
// Envío de mensajes
// ---------------------------------------------------------
async function sendMessage(text) {
  if (!text || !text.trim()) return;

  appendMessage("user", text);
  chatInput.value = "";
  btnSend.disabled = true;
  setOrbState("thinking");

  try {
    const result = await window.pywebview.api.send_text_message(text);
    setOrbState("speaking");
    appendMessage("assistant", result.spoken_response);
  } catch (err) {
    appendMessage("assistant", "Fallo en la comunicación con el Core.");
    console.error(err);
  } finally {
    setOrbState("idle");
    btnSend.disabled = false;
  }
}

btnSend.addEventListener("click", () => sendMessage(chatInput.value));
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage(chatInput.value);
});

document.querySelectorAll(".quick-btn").forEach((btn) => {
  btn.addEventListener("click", () => sendMessage(btn.dataset.msg));
});

btnClear.addEventListener("click", () => {
  chatMessages.innerHTML = "";
  appendMessage("assistant", "Log de comandos reiniciado.");
});

// Minimizar
document.getElementById("btn-minimize").addEventListener("click", () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.minimize_to_orb();
  }
});

// ---------------------------------------------------------
// Telemetría y Clima
// ---------------------------------------------------------
async function refreshDashboardData() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    const data = await window.pywebview.api.get_dashboard_data();
    
    // Hardware Stats
    if (data.stats) {
      const cpu = data.stats.cpu ?? 0;
      const ramPercent = data.stats.ram_percent ?? 0;
      
      document.getElementById("cpu-value").textContent = `${cpu}%`;
      document.getElementById("cpu-bar").style.width = `${cpu}%`;

      document.getElementById("ram-value").textContent = `${ramPercent}%`;
      document.getElementById("ram-bar").style.width = `${ramPercent}%`;

      if (data.stats.ram_used_gb !== undefined) {
        document.getElementById("ram-detail").textContent =
          `${data.stats.ram_used_gb} / ${data.stats.ram_total_gb} GB`;
      }
    }

    // Clima
    if (data.weather) {
      const temp = data.weather.temp !== undefined ? `${data.weather.temp}°C` : "--°C";
      document.getElementById("weather-temp").textContent = temp;
      document.getElementById("weather-desc").textContent = data.weather.desc || "--";
      document.getElementById("weather-detail").textContent =
        `MÁX ${data.weather.tmax}° · MÍN ${data.weather.tmin}° · HUM ${data.weather.humidity}%`;
    }
  } catch (err) {
    console.error("Error al actualizar telemetría:", err);
  }
}

window.addEventListener("pywebviewready", async () => {
  // Cargar historial previo
  try {
    const history = await window.pywebview.api.get_history();
    if (history && history.length) {
      chatMessages.innerHTML = "";
      history.forEach((m) => appendMessage(m.role, m.text));
    }
  } catch (err) {
    console.error("Error al sincronizar historial:", err);
  }

  // Iniciar telemetría
  refreshDashboardData();
  setInterval(refreshDashboardData, 10000);
});