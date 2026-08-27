// ui_dashboard/app.js
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const btnSend = document.getElementById("btn-send");
const btnClear = document.getElementById("btn-clear");
const clockEl = document.getElementById("clock");
const dateEl = document.getElementById("date-display");
const orbIndicator = document.getElementById("orb-indicator");
const orbLabel = document.getElementById("orb-state-label");
const jarvisVisual = document.getElementById("jarvis-visual");
const eyeButton = document.getElementById("btn-jarvis-view");
const visualState = document.getElementById("visual-state");

const STATE_LABELS={idle:"En reposo",listening:"Escuchando...",thinking:"Procesando...",speaking:"Transmitiendo..."};
const VISUAL_LABELS={idle:"STANDBY",listening:"LISTENING",thinking:"PROCESSING",speaking:"TRANSMITTING"};

function updateDateTime(){const now=new Date();clockEl.textContent=now.toLocaleTimeString("es-PE",{hour12:false});const days=["DOM","LUN","MAR","MIÉ","JUE","VIE","SÁB"];dateEl.textContent=`${days[now.getDay()]} // ${String(now.getDate()).padStart(2,"0")}.${String(now.getMonth()+1).padStart(2,"0")}.${now.getFullYear()}`}
setInterval(updateDateTime,1000);updateDateTime();

function setOrbState(state){if(!STATE_LABELS[state])state="idle";if(orbIndicator.dataset.state===state)return;orbIndicator.dataset.state=state;orbIndicator.className="orb-dot "+(state==="idle"?"":state);orbLabel.textContent=STATE_LABELS[state];if(visualState)visualState.textContent=VISUAL_LABELS[state];if(state==="thinking"){const scanline=document.querySelector('.camera-scanline');if(scanline)scanline.classList.add('active')}else{const scanline=document.querySelector('.camera-scanline');if(scanline)scanline.classList.remove('active')}}
setInterval(async()=>{if(window.pywebview?.api?.get_orb_state){try{const state=await window.pywebview.api.get_orb_state();if(state)setOrbState(state)}catch(e){console.error(e)}}},250);

async function sendMessage(text){if(!text?.trim())return;chatInput.value="";btnSend.disabled=true;setOrbState("thinking");try{await window.pywebview.api.send_text_message(text);setOrbState("speaking")}catch(err){appendMessageToChat("assistant","Fallo en la comunicación con el Core.");console.error(err)}finally{setOrbState("idle");btnSend.disabled=false}}
btnSend.addEventListener("click",()=>sendMessage(chatInput.value));chatInput.addEventListener("keydown",e=>{if(e.key==="Enter")sendMessage(chatInput.value)});
btnClear.addEventListener("click",()=>{chatMessages.innerHTML="";appendMessageToChat("assistant","Log de comandos reiniciado.")});
document.getElementById("btn-minimize").addEventListener("click",()=>{if(window.pywebview?.api)window.pywebview.api.minimize_to_orb()});

// Panel visual de Y.A.R.I: el ojo abre/cierra el módulo sin tocar el chat.
eyeButton.addEventListener("click",()=>{const hidden=jarvisVisual.classList.toggle("hidden");jarvisVisual.setAttribute("aria-hidden",hidden);eyeButton.classList.toggle("active",!hidden)});

async function refreshDashboardData(){if(!window.pywebview?.api)return;try{const data=await window.pywebview.api.get_dashboard_data();if(data.stats){const cpu=data.stats.cpu??0,ram=data.stats.ram_percent??0;document.getElementById("cpu-value").textContent=`${cpu}%`;document.getElementById("cpu-bar").style.width=`${cpu}%`;document.getElementById("ram-value").textContent=`${ram}%`;document.getElementById("ram-bar").style.width=`${ram}%`;if(data.stats.ram_used_gb!==undefined)document.getElementById("ram-detail").textContent=`${data.stats.ram_used_gb} / ${data.stats.ram_total_gb} GB`}}catch(e){console.error("Telemetría:",e)}try{const reminders=await window.pywebview.api.get_reminders(),container=document.getElementById("reminders-container");if(container){container.innerHTML="";if(!reminders?.length)container.innerHTML='<span class="stat-row-sub">No hay pendientes programados.</span>';else reminders.forEach(r=>{const block=document.createElement("div");block.className="quick-btn";block.innerHTML=`<strong class="neon-text" style="margin-right:8px">${r.time}</strong>${r.task}`;container.appendChild(block)})}}catch(e){console.error("Pendientes:",e)}}
window.addEventListener("pywebviewready",async()=>{try{const history=await window.pywebview.api.get_history();if(history?.length){chatMessages.innerHTML="";history.forEach(m=>appendMessageToChat(m.role,m.text))}}catch(e){console.error("Historial:",e)}refreshDashboardData();setInterval(refreshDashboardData,10000)});

const themeButtons=document.querySelectorAll('.theme-btn'),savedTheme=localStorage.getItem('yari_theme')||'cyan';document.body.setAttribute('data-theme',savedTheme);themeButtons.forEach(btn=>btn.addEventListener('click',()=>{const theme=btn.dataset.color;document.body.setAttribute('data-theme',theme);localStorage.setItem('yari_theme',theme)}));

const btnInject=document.getElementById('btn-inject'),skillInput=document.getElementById('skill-input');async function injectSkill(){const rule=skillInput.value.trim();if(!rule)return;skillInput.value="";setOrbState("thinking");try{await window.pywebview.api.send_text_message(`DIRECTRIZ DE SISTEMA DE ALTA PRIORIDAD. A partir de ahora debes cumplir esta regla de personalidad/habilidad: ${rule}. Confirma de manera muy breve diciendo "Protocolos de personalidad actualizados."`)}catch(e){appendMessageToChat("assistant","Error al inyectar protocolo.")}finally{setOrbState("idle")}}btnInject.addEventListener('click',injectSkill);skillInput.addEventListener('keydown',e=>{if(e.key==='Enter')injectSkill()});

async function initCamera(){const video=document.getElementById('camera-feed'),wrapper=document.querySelector('.camera-wrapper');try{video.srcObject=await navigator.mediaDevices.getUserMedia({video:true,audio:false})}catch(e){console.error(e);wrapper.innerHTML='<span class="stat-row-sub" style="color:#ffaa00">SEÑAL DE VÍDEO PERDIDA.</span>'}}window.addEventListener('DOMContentLoaded',initCamera);
function takeSnapshot(){const video=document.getElementById('camera-feed');if(!video?.videoWidth)return null;const scan=document.querySelector('.camera-scanline');if(scan){scan.classList.add('active');setTimeout(()=>scan.classList.remove('active'),2500)}const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;canvas.getContext('2d').drawImage(video,0,0);return canvas.toDataURL('image/jpeg',.5).split(',')[1]}
function appendMessageToChat(role,text){if(!chatMessages)return;const msg=document.createElement('div');msg.className=role==='user'?'msg msg-user':'msg msg-assistant';const bubble=document.createElement('div');bubble.className='bubble';bubble.textContent=text;const time=document.createElement('span');time.className='msg-time';const now=new Date();time.textContent=`${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;msg.append(bubble,time);chatMessages.appendChild(msg);chatMessages.scrollTop=chatMessages.scrollHeight}

const ttsVolume=document.getElementById('tts-volume-slider');ttsVolume?.addEventListener('input',e=>{if(window.pywebview?.api?.set_voice_volume)window.pywebview.api.set_voice_volume(e.target.value)});
const btnMicSettings=document.getElementById('btn-mic-settings'),audioModal=document.getElementById('audio-modal'),closeAudioModal=document.getElementById('close-audio-modal'),btnTestMic=document.getElementById('btn-test-mic'),noiseGateSlider=document.getElementById('noise-gate-slider');
if(btnMicSettings&&audioModal){btnMicSettings.addEventListener('click',()=>audioModal.style.display='flex');closeAudioModal.addEventListener('click',()=>audioModal.style.display='none');btnTestMic.addEventListener('click',async()=>{btnTestMic.textContent='ESCUCHANDO...';if(window.pywebview?.api?.test_microphone)await window.pywebview.api.test_microphone();setTimeout(()=>btnTestMic.textContent='🔴 INICIAR PRUEBA',3500)})}
noiseGateSlider?.addEventListener('input',e=>{if(window.pywebview?.api?.set_noise_gate)window.pywebview.api.set_noise_gate(e.target.value)});
