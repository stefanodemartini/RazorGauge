# Copilot Instructions – RazorGauge

## Architecture Overview

This repository contains the line-diameter measurement system and its mechanical design. The
canonical firmware locations and board/version matrix are in `FIRMWARE.md`; hardware decisions
are in `STATO_PROGETTO.md`. Do not treat `Claude outputs/` or `_archivio_NON_USARE/` as active.

### 1. `master/master.ino` — active classic ESP32 firmware (0.4.25-RB2)
- Reads a **quadrature encoder** on GPIO 32/33 → length in cm using the configurable encoder calibration.
- Reads a **digital caliper** (DATA/CLOCK on GPIO 27/26) for diameter.
- Stores measured points in a **sorted linked list** (`DataPoint*`) keyed by `cm` position; duplicate cm values update the existing node.
- Does not apply EMA smoothing in firmware; the desktop app applies optional client-side smoothing.
- Compensated diameter: `compensated = displayValue − displayZeroValue − caliperZeroOffset`.
- Persists `caliperZeroOffset` in **EEPROM at address 0**.
- Serves the entire **web UI as a raw string literal** embedded directly in `master.ino` via `R"rawliteral(...)rawliteral"`.
- Exposes **HTTP on port 80** and **WebSocket on port 81** (`WebSocketsServer`).
- Connects to Wi-Fi via **WiFiManager** (AP SSID: `DiametroLinea_Setup`, password: `12345678`).
- Relays motor commands to the slave over **UART2** (TX=GPIO17, RX=GPIO16) at 115200 8N1.

### 2. `slave/slave.ino` — active classic ESP32 firmware (0.6.7)
- Controls a TB6600 stepper driver via **FastAccelStepper** (PUL=GPIO25, DIR=GPIO26, ENA=GPIO27).
- Receives ASCII commands over **UART2** (RX=GPIO16, TX=GPIO17) at 115200 8N1.
- Connects to the shared Wi-Fi via WiFiManager and exposes `/diag` for direct UART diagnostics.
- Maintains a `Mode` enum: `STOPPED | SCAN | FAST_S | FAST_O | GOTOPOS`.
- `GOTOPOS` uses a fast approach followed by a 400 Hz creep for precise stopping.
- Buttons: GPIO 32/33/34; GPIO 34 uses the board's external pull-up.

### 3. `app/` — WPF .NET Desktop App
- A Windows desktop alternative to the browser UI; the ESP32 backend is unchanged.
- `MainViewModel` manages scan/connection state; Design Mode and much of the UI behavior live in `Views/MainWindow.xaml.cs`.
- `BackendClient` connects to `ws://<host>:81/` using `ClientWebSocket`; it raises `RawMessageReceived` for every JSON frame.
- Settings are loaded from `appsettings.json` into `AppSettings` → `BackendSettings` + `ChartSettings`.
- The app uses ScottPlot WPF; dependencies are declared in `app/DiametroLineaDesktop.csproj`.

### 4. Shared library and CLI
- `FlyLinePhysics/` contains the shared physics calculations and `.flp` serialization.
- `FlyLinePhysics.Tests/` contains the library tests.
- `cli/` provides the `flyline` command-line designer and analysis tool. It currently references the WPF app, so it is Windows-targeted.

---

## UART Protocol

### Master → Slave (newline-terminated ASCII)
| Command | Meaning |
|---|---|
| `SCAN` | Start slow scan (`SCAN_HZ = 1500`) |
| `STOP` | Stop motor |
| `FAST_S` | Fast, same direction (`FAST_HZ = 12000`) |
| `FAST_O` | Fast, opposite direction |
| `STATUS?` | Request status |
| `GOTOPOS:<target_cm>:<max_hz>:<encoder_cm>:<F\|B>` | Move to target using the current encoder position |

### Slave → Master
`STATUS:<MODE>:<DIR>[:<remaining_steps>]`  
Examples: `STATUS:SCAN:FWD`, `STATUS:GOTOPOS:FWD:1500`, `STATUS:STOP:FWD`

---

## WebSocket JSON Events (Master → Browsers)
- `{"type":"motor","mode":"SCAN","dir":"FWD"}` — motor state update
- `{"type":"goto_status","active":true,"target":150.0,"current":42.0}` — GOTOPOS started
- `{"type":"goto_progress","remaining_cm":50,"current_cm":100,"target_cm":150}` — GOTOPOS in progress
- `{"type":"speed","speed":1.23}` — current speed in cm/s
- Measurement points are broadcast when `scanEnabled` is true and cm position changes

---

## CSV Format
The firmware `/export` endpoint and desktop CSV export use:
```
Lunghezza cm,Diametro mm
```
Import also supports legacy/multi-series headers such as `Dataset,Lunghezza cm,Diametro mm,Display mm`.

---

## Key Constants (must stay in sync between master and slave)
| Constant | Value | Location |
|---|---|---|
| Encoder PPR / wheel circumference | `600` / `200 mm` nominal | Both firmware sketches |
| `SCAN_HZ` (initial slave speed) | `1500` | `slave/slave.ino`; master closed-loop adjusts it |
| `FAST_HZ` / `MOTOR_FAST_HZ` | `12000` | Slave / master respectively |
| UART baud | `115200, 8N1` | Both |

---

## Build & Flash

### Arduino Firmware
- Use **Arduino IDE** or **PlatformIO**.
- Board targets: **classic ESP32** for both active master and slave. The `gauge_esp32s3/` folder is a bench variant only.
- Flash **slave first**, then master.
- Master libraries: `WiFi`, `WebServer`, `WebSocketsServer`, `EEPROM`, `WiFiManager`.
- Slave libraries: `FastAccelStepper`.

### WPF Desktop App
```sh
dotnet build app\app.sln
dotnet test FlyLinePhysics.Tests\FlyLinePhysics.Tests.csproj
dotnet build cli\FlyLineCli.csproj
```

---

## Conventions & Gotchas

- The encoder ISR is marked `IRAM_ATTR` (`updateEncoder`) — keep ISR code minimal and RAM-resident.
- `motorQueueTx` drops a `STATUS?` poll if a real command is already queued; do not bypass this gate.
- The web UI is embedded inline in `master.ino`; HTML/CSS/JS changes require re-flashing the master.
- When a new browser connects it gets only future WebSocket frames; full history must be fetched from `/export` first.
- Optimal scanning speed is **0.5–2.5 cm/s** (hardcoded in JS as `OPTIMAL_SPEED_MIN/MAX`).
- `caliperZeroOffset` survives resets because it is EEPROM-backed; `displayZeroValue` is RAM-only and resets on reboot.
- The desktop app's `appsettings.json` is the canonical place to change host/port; do not hard-code them in C#.
