# UB Racer Client — Message Reference

This document lists all messages the client layer has access to, split between
**host-facing** messages (Socket.IO, managed by `server.py`) and **internal**
messages (WebSocket at `wss://CLIENT_IP:PORT/ws`, shared by `index.html` and
`controller.py` / `racerlib`).

---

## 1. Host ↔ server.py  (Socket.IO)

These messages are handled entirely by `server.py`.  Students do not send or
receive them directly; they arrive/depart as internal `/ws` messages instead.

### 1a. server.py → host

| Event | Payload | When |
|-------|---------|------|
| `user_register` | `{username: str, ip: str}` → ack `{status: str, message: str}` | Once, on browser login |
| `user_request` | `{action: "join"\|"exit"\|"confirm", carPreference?: carID}` | Queue management |
| `telemetry` | `{carID, timestamp, steering, throttle, compass}` | Each frame from car, forwarded up |

### 1b. host → server.py

| Event | Payload | Notes |
|-------|---------|-------|
| `session_start` | `{carID, carIP, wsPort, mjpegURL, sessionToken, timeLimitSec, steeringLimits: {min,max}, throttleLimits: {min,max}, cameraIntrinsics, startTime, endTime}` | Triggers car WS connection |
| `session_end` | `{carID, reason: "timeout"\|"user_exit"\|"admin_boot"\|"car_disconnect"}` | Triggers car WS teardown |
| `confirm_required` | `{carID, carName, timeoutSec: 60}` | Must confirm within timeout or move to back |
| `system_status` | `{cars: [...], globalQueuePosition, yourStatus, yourCarID}` | ~1 Hz + on any change |
| `host_notice` | `{severity: 0–7, text: str, carID: str\|null}` | Broadcast message from host operator |

---

## 2. Internal Client  (WebSocket `/ws`)

Both `index.html` (browser) and `controller.py` / `racerlib` connect here.
Controllers connect with `?role=controller`; browsers connect without a role.

### 2a. browser / controller → server.py

| `type` | Payload fields | Sender | server.py action |
|--------|---------------|--------|-----------------|
| `login` | `{username: str}` | browser only | Triggers `user_register` to host (once) |
| `drive` | `{steering: float, throttle: float}` | browser or controller | Forwarded to car WebSocket with session token |
| `user_request` | `{action: "join"\|"exit"\|"confirm", carPreference?: carID}` | browser or controller | Forwarded to host via Socket.IO |
| `local_notice` | `{severity: 0–7, text: str}` | controller only | Broadcast to browsers only (not echoed to controllers) |

### 2b. server.py → browser / controller

All of these are broadcast to **all** `/ws` clients (browsers + controllers)
unless noted.

| `type` | Payload fields | Source | Notes |
|--------|---------------|--------|-------|
| `session_start` | `{carID, carIP, wsPort, mjpegURL, sessionToken, timeLimitSec, steeringLimits, throttleLimits, cameraIntrinsics, startTime, endTime}` | host (forwarded) | |
| `session_end` | `{carID, reason}` | host (forwarded) | |
| `confirm_required` | `{carID, carName, timeoutSec}` | host (forwarded) | |
| `system_status` | `{cars, globalQueuePosition, yourStatus, yourCarID}` | host (forwarded) | |
| `host_notice` | `{severity, text, carID}` | host (forwarded) | |
| `telemetry` | `{carID, timestamp, steering, throttle, compass}` | car WS (forwarded) | |
| `local_notice` | `{severity, text}` | controller (forwarded) | **Browsers only** — not re-sent to controllers |

---

## 3. server.py ↔ Car  (plain WebSocket `ws://CAR_IP:WS_PORT`)

Handled entirely by `server.py`; students never touch this directly.

| Direction | Payload |
|-----------|---------|
| server.py → car | `{sessionToken: str, steering: float, throttle: float}` |
| car → server.py | `{carID, timestamp, steering, throttle, compass}` |

---

## 4. Dev-mode considerations

When running with `dev=True` in `racerlib` (and `--dev` flag to `server.py`),
no host connection is available.  Changes to the message layer:

### 4a. Resolved

- **`telemetry`** — not generated in dev mode; `on_telemetry` is never called.
- **`drive`** — `conn.drive(s, t)` sends a `local_notice` with the new
  **DEVDRIVE** severity (numeric value TBD, outside the current 0–7 range)
  and text `"drive: steering=X throttle=Y"` instead of forwarding to a car.
  Requires `index.html`/`index.js` to handle the new severity (deferred — see §4b).
- **`session_start` (student-triggered)** — student calls
  `conn.start_dev_session(camera_url, steering_limits, throttle_limits,
  time_limit_sec)` from `controller.py`; racerlib synthesises a `session_start`
  payload and calls `on_session_start` locally.

### 4b. Deferred — browser-side dev mode

The following require changes to `server.py` and `index.html`/`index.js` and
are intentionally out of scope for the current task:

1. **Browser form → dev session** — a form in `index.html` lets the user supply
   `camera_url`, `steering_limits`, `throttle_limits` directly in the browser.
   server.py receives a new inbound message (e.g., `dev_session_config`) and
   synthesises + broadcasts a `session_start`-shaped message so the browser
   renders the camera feed and session panel.  The exact message type and
   whether it reuses `session_start` or introduces `dev_session_start` is TBD.

2. **Browser notification of student-triggered dev session** — when the student
   calls `conn.start_dev_session(...)` from `controller.py`, the browser should
   also be notified so it can display the camera feed.  Design TBD (racerlib
   could send a message through `/ws` that server.py then broadcasts).

3. **DEVDRIVE severity rendering** — `index.js` needs a CSS class / display rule
   for the new DEVDRIVE severity in the notices div.
