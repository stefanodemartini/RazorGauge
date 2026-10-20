# RazorGauge

RazorGauge is a line-diameter measurement and fly-line design project. This repository contains
the firmware, Windows desktop application, shared physics library, CLI, and the hardware design
files.

## Repository map

| Path | Purpose |
|---|---|
| `master/` | Active ESP32 master firmware (0.4.25-RB2, caliper-based) |
| `slave/` | Active ESP32-classic motor controller firmware (0.6.7, Wi-Fi/RX2 diagnostics) |
| `master_razorgauge/` | Preliminary optical RazorGauge master (1.0.0-alpha) |
| `gauge_esp32/`, `gauge_esp32s3/`, `encoder_test/` | Bench and diagnostic firmware |
| `app/` | Windows WPF desktop application |
| `FlyLinePhysics/` | Shared line-physics and `.flp` serialization library |
| `FlyLinePhysics.Tests/` | Unit tests for the shared library |
| `cli/` | `flyline` command-line design and analysis tool |
| `cad/`, `integrazione_profiler/`, `piastra_alluminio/` | Mechanical CAD and integration design |
| `scheda/`, `scheda_smd/` | RazorBoard KiCad projects |
| `strumenti/` | Build, simulation, and verification scripts |

Generated outputs (such as mesh files, renders, PDFs, and build products) are generally excluded
from version control; the corresponding source files and scripts are kept in the repository.

## Where to start

- [FIRMWARE.md](./FIRMWARE.md): canonical sketches, active versions, boards, and firmware notes.
- [MANUALE.md](./MANUALE.md): application workflow and user-facing behavior.
- [STATO_PROGETTO.md](./STATO_PROGETTO.md): authoritative hardware decisions and current project status.
- [CONTEXT.md](./CONTEXT.md): software/repository context.
- [app/README.md](./app/README.md): desktop application overview.

## Build and test the .NET projects

From the repository root:

```powershell
dotnet build app\app.sln
dotnet test FlyLinePhysics.Tests\FlyLinePhysics.Tests.csproj
dotnet build cli\FlyLineCli.csproj
```

Run the desktop app with `dotnet run --project app\DiametroLineaDesktop.csproj`. The CLI project
is Windows-targeted because it currently references the WPF application for shared design and
export services.

## Arduino firmware

Build and flash each sketch for its matching board using Arduino IDE or `arduino-cli`. The active
motor slave targets the classic ESP32; do not select ESP32-S3 for `slave/slave.ino`. See
[FIRMWARE.md](./FIRMWARE.md) for the current board/version matrix and flash guidance.
