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

function setOrbState(state) {
  // Evitar que la interfaz se actualice si ya está en el estado correcto
  if (orbIndicator.dataset.state === state) return;
  orbIndicator.dataset.state = state;

  orbIndicator.className = "orb-dot " + (state === "idle" ? "" : state);
  orbLabel.textContent = STATE_LABELS[state] || "En reposo";

  // Apagar el láser de la cámara si la IA ya dejó de "pensar"
  if (state !== "thinking") {
    const scanline = document.querySelector('.camera-scanline');
    if (scanline) scanline.classList.remove('active');
  }
}

// NUEVO: Radar de sincronización en tiempo real con Python
setInterval(async () => {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.get_orb_state) {
    const state = await window.pywebview.api.get_orb_state();
    if (state) setOrbState(state);
  }
}, 250);

// ---------------------------------------------------------
// Envío de mensajes
// ---------------------------------------------------------
async function sendMessage(text) {
  if (!text || !text.trim()) return;

  chatInput.value = "";
  btnSend.disabled = true;
  setOrbState("thinking");

  try {
    await window.pywebview.api.send_text_message(text);
    setOrbState("speaking");
  } catch (err) {
    appendMessageToChat("assistant", "Fallo en la comunicación con el Core.");
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
  appendMessageToChat("assistant", "Log de comandos reiniciado.");
});

// Minimizar
document.getElementById("btn-minimize").addEventListener("click", () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.minimize_to_orb();
  }
});

// ---------------------------------------------------------
// Telemetría, Clima y Pendientes
// ---------------------------------------------------------
async function refreshDashboardData() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    // Pedimos los datos principales
    const data = await window.pywebview.api.get_dashboard_data();
    
    // 1. Hardware Stats
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
    } // <-- Aquí cerramos correctamente el bloque de Stats

    // 2. Clima
    if (data.weather) {
      const temp = data.weather.temp !== undefined ? `${data.weather.temp}°C` : "--°C";
      document.getElementById("weather-temp").textContent = temp;
      document.getElementById("weather-desc").textContent = data.weather.desc || "--";
      document.getElementById("weather-detail").textContent =
        `MÁX ${data.weather.tmax}° · MÍN ${data.weather.tmin}° · HUM ${data.weather.humidity}%`;
    }

  } catch (err) {
    console.error("Error al actualizar telemetría/clima:", err);
  }

  // 3. Pendientes (Envuelto en su propio try-catch para no romper el resto)
  try {
    const reminders = await window.pywebview.api.get_reminders();
    const container = document.getElementById("reminders-container");
    
    if (container) {
      container.innerHTML = ""; // Limpiar antes de actualizar
      
      if (!reminders || reminders.length === 0) {
        container.innerHTML = '<span class="stat-row-sub">No hay pendientes programados.</span>';
      } else {
        reminders.forEach(r => {
          const block = document.createElement("div");
          block.className = "quick-btn"; 
          block.innerHTML = `<strong class="neon-text" style="margin-right:8px;">${r.time}</strong> ${r.task}`;
          container.appendChild(block);
        });
      }
    }
  } catch (err) {
    console.error("Error cargando pendientes. Revisa que get_reminders exista en bridge.py", err);
  }
}

window.addEventListener("pywebviewready", async () => {
  // Cargar historial previo
  try {
    const history = await window.pywebview.api.get_history();
    if (history && history.length) {
      chatMessages.innerHTML = "";
      history.forEach((m) => appendMessageToChat(m.role, m.text));
    }
  } catch (err) {
    console.error("Error al sincronizar historial:", err);
  }

  // Iniciar telemetría
  refreshDashboardData();
  setInterval(refreshDashboardData, 10000);
});

// --- LÓGICA DE TEMAS DE COLOR ---
const themeButtons = document.querySelectorAll('.theme-btn');
const savedTheme = localStorage.getItem('yari_theme') || 'cyan';
document.body.setAttribute('data-theme', savedTheme);

themeButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const newTheme = btn.getAttribute('data-color');
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('yari_theme', newTheme);
  });
});

// --- LÓGICA DEL INYECTOR DE PERSONALIDAD ---
const btnInject = document.getElementById('btn-inject');
const skillInput = document.getElementById('skill-input');

async function injectSkill() {
  const rule = skillInput.value.trim();
  if (!rule) return;
  
  const command = `DIRECTRIZ DE SISTEMA DE ALTA PRIORIDAD. A partir de ahora debes cumplir esta regla de personalidad/habilidad: ${rule}. Confirma de manera muy breve diciendo "Protocolos de personalidad actualizados."`;
  
  skillInput.value = "";
  // NO dibujamos el mensaje de inyección aquí.
  setOrbState("thinking");

  try {
    await window.pywebview.api.send_text_message(command);
    setOrbState("speaking");
  } catch (err) {
    appendMessageToChat("assistant", "Error al inyectar protocolo.");
  } finally {
    setOrbState("idle");
  }
}

btnInject.addEventListener('click', injectSkill);
skillInput.addEventListener('keydown', (e) => {
  if (e.key === "Enter") injectSkill();
});

// --- LÓGICA DEL SENSOR ÓPTICO (WEBCAM) ---
async function initCamera() {
  const videoEl = document.getElementById('camera-feed');
  const wrapper = document.querySelector('.camera-wrapper');
  
  try {
    // Pedimos acceso a la cámara web (solo video, sin audio para evitar eco)
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    videoEl.srcObject = stream;
  } catch (error) {
    console.error("Error al acceder a la cámara:", error);
    // Si falla (ej. no tienes cámara conectada), muestra un mensaje estilo HUD
    wrapper.innerHTML = '<span class="stat-row-sub" style="color: #ffaa00;">SEÑAL DE VÍDEO PERDIDA. VERIFIQUE CONEXIÓN.</span>';
  }
}

// Inicializar la cámara apenas cargue la página
window.addEventListener('DOMContentLoaded', initCamera);
// Función para que Python pueda pedir una foto sin apagar la cámara web
// Función para que Python pueda pedir una foto sin apagar la cámara web
function takeSnapshot() {
  const video = document.getElementById('camera-feed');
  if (!video || !video.videoWidth) return null;
  
  // Encender el escáner visualmente
  const scanline = document.querySelector('.camera-scanline');
  if (scanline) {
    scanline.classList.add('active');
    
    // APAGADO AUTOMÁTICO: Quitamos el láser 2.5 segundos después de tomar la foto
    setTimeout(() => {
      scanline.classList.remove('active');
    }, 2500);
  }
  
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  
  // Retorna la foto comprimida al 50% de calidad
  return canvas.toDataURL('image/jpeg', 0.5).split(',')[1];
}

// Función para recibir mensajes en tiempo real desde Python
function appendMessageToChat(role, text) {
  const chatContainer = document.getElementById('chat-messages');
  if (!chatContainer) return;

  // Crear el contenedor del mensaje
  const msgDiv = document.createElement('div');
  msgDiv.className = role === 'user' ? 'msg msg-user' : 'msg msg-assistant';

  // Crear la burbuja de texto
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  // Crear la hora actual
  const timeSpan = document.createElement('span');
  timeSpan.className = 'msg-time';
  const now = new Date();
  timeSpan.textContent = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');

  // Ensamblar e inyectar
  msgDiv.appendChild(bubble);
  msgDiv.appendChild(timeSpan);
  chatContainer.appendChild(msgDiv);

  // Hacer auto-scroll hasta el fondo para ver el mensaje nuevo
  chatContainer.scrollTop = chatContainer.scrollHeight;
}
// Gatillo para enviar el volumen de voz a Python en tiempo real
const ttsVolume = document.getElementById('tts-volume-slider');
if (ttsVolume) {
  ttsVolume.addEventListener('input', (e) => {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.set_voice_volume) {
      window.pywebview.api.set_voice_volume(e.target.value);
    }
  });
}

