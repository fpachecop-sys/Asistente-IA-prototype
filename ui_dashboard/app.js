// ui_dashboard/app.js
// Puente entre el dashboard y el backend Python (bridge de pywebview).

const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const btnSend = document.getElementById("btn-send");
const btnClear = document.getElementById("btn-clear");
const clockEl = document.getElementById("clock");
const orbIndicator = document.getElementById("orb-indicator");
const orbLabel = document.getElementById("orb-state-label");

const STATE_LABELS = {
  idle: "En reposo",
  listening: "Escuchando...",
  thinking: "Pensando...",
  speaking: "Hablando...",
};

// ---------------------------------------------------------
// Reloj
// ---------------------------------------------------------
function updateClock() {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString("es-PE", { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

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
    hour: "2-digit", minute: "2-digit",
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
// Enviar mensaje de texto al backend Python
// ---------------------------------------------------------
async function sendMessage(text) {
  if (!text.trim()) return;

  appendMessage("user", text);
  chatInput.value = "";
  btnSend.disabled = true;
  setOrbState("thinking");

  try {
    const result = await window.pywebview.api.send_text_message(text);
    setOrbState("speaking");
    appendMessage("assistant", result.spoken_response);
  } catch (err) {
    appendMessage("assistant", "Ocurrió un error al procesar tu mensaje.");
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

// Botones de acceso rápido
document.querySelectorAll(".quick-btn").forEach((btn) => {
  btn.addEventListener("click", () => sendMessage(btn.dataset.msg));
});

// Limpiar conversación (solo visual; el historial real vive en brain.py)
btnClear.addEventListener("click", () => {
  chatMessages.innerHTML = "";
  appendMessage("assistant", "Conversación limpiada.");
});

// ---------------------------------------------------------
// Minimizar a la bolita
// ---------------------------------------------------------
document.getElementById("btn-minimize").addEventListener("click", () => {
  window.pywebview.api.minimize_to_orb();
});

// ---------------------------------------------------------
// Cargar historial existente al abrir (por si vienes de la bolita)
// ---------------------------------------------------------
window.addEventListener("pywebviewready", async () => {
  try {
    const history = await window.pywebview.api.get_history();
    if (history && history.length) {
      chatMessages.innerHTML = "";
      history.forEach((m) => appendMessage(m.role, m.text));
    }
  } catch (err) {
    console.error("No se pudo cargar el historial:", err);
  }
});