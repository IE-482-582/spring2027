/**
 * index.js — UB Racer client UI
 *
 * Connects to server.py via WebSocket at wss://THIS_HOST/ws.
 * Message protocol (JSON, "type" field):
 *
 *   Inbound (from server.py):
 *     system_status   — queue/car state, ~1 Hz
 *     session_start   — session details + car params
 *     session_end     — {carID, reason}
 *     confirm_required — {carID, carName, timeoutSec}
 *     host_notice     — {severity, text, carID}
 *     local_notice    — {severity, text}   (from controller.py)
 *     telemetry       — {carID, steering, throttle, compass, timestamp}
 *
 *   Outbound (to server.py):
 *     login        — {username}
 *     user_request — {action: "join"|"exit"|"confirm", carPreference?}
 *     drive        — {steering, throttle}
 *     local_notice — {severity, text}  (if students want to send from here)
 */

"use strict";

// ── State ────────────────────────────────────────────────────────────────────

let ws             = null;
let sessionActive  = false;
let sessionData    = null;   // last session_start payload
let username       = "";
let lastStatus     = null;   // last system_status message

// ── Keyboard drive state ─────────────────────────────────────────────────────

const keysDown  = new Set();
let driveTimer  = null;      // setInterval handle

// ── Countdown timers ─────────────────────────────────────────────────────────

let sessionCountdownTimer = null;
let confirmCountdownTimer = null;

// ── Element shortcuts ────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);

// ── Login view ────────────────────────────────────────────────────────────────

async function initLoginView() {
  // Pre-fill from server config if --username was supplied at CLI
  try {
    const resp = await fetch("/config");
    if (resp.ok) {
      const cfg = await resp.json();
      if (cfg.username) {
        $("username-input").value = cfg.username;
      }
    }
  } catch (_) { /* server may not be ready yet; ignore */ }
}

$("login-btn").addEventListener("click", doLogin);
$("username-input").addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });

function doLogin() {
  const uname = $("username-input").value.trim();
  if (!uname) {
    $("login-error").textContent = "Please enter a username.";
    return;
  }
  $("login-error").textContent = "";
  username = uname;
  $("username-display").textContent = username;
  $("login-view").style.display     = "none";
  $("main-view").style.display      = "block";
  connectWS();
}

// ── WebSocket connection ──────────────────────────────────────────────────────

function connectWS() {
  const url = `wss://${location.host}/ws`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    setHostDot(true);
    // Send login so server.py can register with host if --username wasn't supplied
    send({ type: "login", username });
    showNotice(6, "Connected to server.");
  };

  ws.onmessage = evt => {
    try {
      dispatch(JSON.parse(evt.data));
    } catch (e) {
      console.error("Bad message:", e);
    }
  };

  ws.onclose = () => {
    setHostDot(false);
    $("status-text").textContent = "Disconnected. Reconnecting…";
    // Reconnect after a short delay
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => { /* onclose will fire next; handled there */ };
}

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  }
}

// ── Message dispatch ──────────────────────────────────────────────────────────

function dispatch(msg) {
  switch (msg.type) {
    case "system_status":    onSystemStatus(msg);    break;
    case "session_start":    onSessionStart(msg);    break;
    case "session_end":      onSessionEnd(msg);      break;
    case "confirm_required": onConfirmRequired(msg); break;
    case "host_notice":      showNotice(msg.severity, msg.text, "host-notices-log");   break;
    case "local_notice":     showNotice(msg.severity, msg.text, "local-notices-log"); break;
    case "telemetry":        onTelemetry(msg);       break;
    default:
      console.log("Unknown message type:", msg.type);
  }
}

// ── System status ─────────────────────────────────────────────────────────────

function onSystemStatus(msg) {
  lastStatus = msg;
  setHostDot(true);
  updateStatusBar(msg);
  updateCarsTable(msg.cars);
  updateCarPreferenceSelect(msg.cars);
  updateQueueButtons(msg);
}

function setHostDot(connected) {
  const dot = $("host-dot");
  dot.classList.toggle("connected", connected);
}

function updateStatusBar(msg) {
  const s = msg.yourStatus;
  let text = "Idle";
  if (s === "queued") {
    const p = msg.globalQueuePosition;
    text = `In queue — position ${p}`;
  } else if (s === "confirm_pending") {
    text = "Waiting for your confirmation…";
  } else if (s === "driving") {
    text = `Driving ${msg.yourCarID}`;
  }
  $("status-text").textContent = text;
}

function updateCarsTable(cars) {
  const tbody = $("cars-tbody");
  tbody.innerHTML = "";
  for (const car of cars) {
    const tr = document.createElement("tr");
    const wait = car.estWaitSec != null ? `~${Math.round(car.estWaitSec)}s` : "—";
    const pos  = car.yourPosition === 0  ? "Driving"
               : car.yourPosition > 0    ? String(car.yourPosition)
               : "—";
    tr.innerHTML = `
      <td>${escHtml(car.name)}</td>
      <td class="avail-${car.availability}">${car.availability}</td>
      <td class="status-${car.status}">${car.status}</td>
      <td>${car.queueLength}</td>
      <td>${wait}</td>
      <td class="${car.yourPosition >= 0 ? "my-pos" : ""}">${pos}</td>
    `;
    tbody.appendChild(tr);
  }
}

let _carsKnown = [];
function updateCarPreferenceSelect(cars) {
  const sel = $("car-pref");
  // Only rebuild if car list changed
  const ids = cars.map(c => c.carID).join(",");
  if (ids === _carsKnown) return;
  _carsKnown = ids;
  const prev = sel.value;
  sel.innerHTML = `<option value="">Any car</option>`;
  for (const car of cars) {
    const opt = document.createElement("option");
    opt.value       = car.carID;
    opt.textContent = car.name;
    sel.appendChild(opt);
  }
  sel.value = prev; // restore selection if still valid
}

function updateQueueButtons(msg) {
  const inQueue = msg.yourStatus !== "idle";
  $("join-btn").disabled  = inQueue;
  $("leave-btn").disabled = !inQueue;
}

// ── Session ───────────────────────────────────────────────────────────────────

function onSessionStart(msg) {
  sessionActive = true;
  sessionData   = msg;

  $("session-panel").style.display    = "block";
  $("session-car-name").textContent   = `Session — ${msg.carID}`;

  const limits = `Throttle [${msg.throttleLimits.min}, ${msg.throttleLimits.max}]`
               + ` | Steering [${msg.steeringLimits.min}, ${msg.steeringLimits.max}]`;
  $("session-meta").textContent = limits;

  // Camera feed
  const cam = $("camera-feed");
  cam.src           = msg.mjpegURL;
  cam.style.display = "block";

  startSessionCountdown(msg.endTime);
  startDriveLoop();
  $("drive-hint").classList.add("active");
  showNotice(6, `Session started on ${msg.carID} (${msg.timeLimitSec}s)`);
}

function onSessionEnd(msg) {
  sessionActive = false;
  sessionData   = null;

  stopSessionCountdown();
  stopDriveLoop();

  $("session-panel").style.display = "none";
  $("camera-feed").src             = "";
  $("camera-feed").style.display   = "none";
  $("drive-hint").classList.remove("active");
  $("countdown").textContent       = "--:--";
  $("countdown").classList.remove("urgent");

  const reasons = {
    timeout:         "Session timed out",
    user_exit:       "You ended the session",
    admin_boot:      "Admin ended the session",
    car_disconnect:  "Car disconnected",
  };
  showNotice(5, reasons[msg.reason] ?? `Session ended (${msg.reason})`);
}

function startSessionCountdown(endTimeStr) {
  stopSessionCountdown();
  const el = $("countdown");
  sessionCountdownTimer = setInterval(() => {
    const secLeft = Math.max(0, (new Date(endTimeStr) - Date.now()) / 1000);
    const m = Math.floor(secLeft / 60);
    const s = Math.floor(secLeft % 60);
    el.textContent = `${m}:${String(s).padStart(2, "0")}`;
    el.classList.toggle("urgent", secLeft <= 15);
    if (secLeft <= 0) stopSessionCountdown();
  }, 500);
}

function stopSessionCountdown() {
  if (sessionCountdownTimer) {
    clearInterval(sessionCountdownTimer);
    sessionCountdownTimer = null;
  }
}

// ── Confirm dialog ────────────────────────────────────────────────────────────

function onConfirmRequired(msg) {
  $("confirm-car-name").textContent = `Car: ${escHtml(msg.carName)}`;
  $("confirm-overlay").style.display = "flex";

  let remaining = msg.timeoutSec ?? 60;
  $("confirm-timer").textContent = remaining;

  stopConfirmCountdown();
  confirmCountdownTimer = setInterval(() => {
    remaining--;
    $("confirm-timer").textContent = remaining;
    if (remaining <= 0) {
      stopConfirmCountdown();
      $("confirm-overlay").style.display = "none";
    }
  }, 1000);
}

function stopConfirmCountdown() {
  if (confirmCountdownTimer) {
    clearInterval(confirmCountdownTimer);
    confirmCountdownTimer = null;
  }
}

$("confirm-btn").addEventListener("click", () => {
  stopConfirmCountdown();
  $("confirm-overlay").style.display = "none";
  send({ type: "user_request", action: "confirm" });
});

// ── Telemetry display ─────────────────────────────────────────────────────────

function onTelemetry(msg) {
  $("tel-steering").textContent = msg.steering  != null ? msg.steering.toFixed(1)  : "—";
  $("tel-throttle").textContent = msg.throttle  != null ? msg.throttle.toFixed(1)  : "—";
  $("tel-compass").textContent  = msg.compass   != null ? msg.compass.toFixed(1)   : "—";
}

// ── Queue controls ────────────────────────────────────────────────────────────

$("join-btn").addEventListener("click", () => {
  const pref = $("car-pref").value || null;
  send({ type: "user_request", action: "join", carPreference: pref });
});

$("leave-btn").addEventListener("click", () => {
  send({ type: "user_request", action: "exit" });
});

// ── Keyboard drive ────────────────────────────────────────────────────────────
//
// Arrow keys control the car while a session is active.
// Students can replace or extend this with a gamepad, tilt, virtual joystick, etc.

document.addEventListener("keydown", e => {
  if (["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].includes(e.code)) {
    e.preventDefault(); // stop page scrolling
    keysDown.add(e.code);
  }
});
document.addEventListener("keyup", e => {
  keysDown.delete(e.code);
});

function getDriveValues() {
  const tLimits = sessionData?.throttleLimits ?? { min: -100, max: 100 };
  const sLimits = sessionData?.steeringLimits ?? { min: -90,  max: 90  };
  let steering = 0;
  let throttle = 0;
  if (keysDown.has("ArrowUp"))    throttle = tLimits.max;
  if (keysDown.has("ArrowDown"))  throttle = tLimits.min;
  if (keysDown.has("ArrowLeft"))  steering = sLimits.max;   // positive = turn left
  if (keysDown.has("ArrowRight")) steering = sLimits.min;
  return { steering, throttle };
}

function startDriveLoop() {
  if (driveTimer) return;
  driveTimer = setInterval(() => {
    if (!sessionActive) return;
    const { steering, throttle } = getDriveValues();
    send({ type: "drive", steering, throttle });
  }, 100); // 10 Hz
}

function stopDriveLoop() {
  if (driveTimer) {
    clearInterval(driveTimer);
    driveTimer = null;
  }
}

// ── Notices ───────────────────────────────────────────────────────────────────

function showNotice(severity, text, logId = "host-notices-log") {
  const log  = $(logId);
  const div  = document.createElement("div");
  const time = new Date().toLocaleTimeString();
  div.className   = `notice sev-${severity}`;
  div.textContent = `[${time}] ${text}`;
  log.prepend(div);
  // Keep at most 100 entries
  while (log.children.length > 100) log.removeChild(log.lastChild);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Boot ──────────────────────────────────────────────────────────────────────

initLoginView();
