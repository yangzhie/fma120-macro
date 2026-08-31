# FMA120-macro

Provisions FlooGoo FMA120 transmitters as Route 86 tram stops and broadcasts their announcements over Auracast.

Part of the Auracast assistive listening proof of concept — a system that automatically connects Deaf and hard-of-hearing riders' hearing aids to the right broadcast at each stop of a journey. This repository covers the transmitter side. The companion Android app discovers these broadcasts and joins them.

---

## What this does

Each FMA120 becomes one tram stop. That takes two separate things:

**Configuration** is written to the dongle over USB serial and persists in its memory. Unplug the unit, take it to a stop, plug it in — it's still stop 1.

**Audio** does not persist. The FMA120 has no storage; it's a USB audio adapter that broadcasts whatever is actively playing through it. Something has to keep feeding it, continuously, for as long as the stop is live.

```
audio file → Python/pygame → USB audio → FMA120 → Auracast broadcast → rider's hearing aids
                                            ↑
                              serial config (name, code, ID, metadata)
```

---

## Requirements

- Python 3.10 or newer (uses `X | None` type syntax)
- FMA120 firmware **1.1.6.7 or newer** — the `BF` command doesn't exist below this
- A provisioned FMA120 connected over USB

```bash
pip install pyserial pygame
```

`pygame` is only needed for the audio commands. It's imported lazily so `provision` works without it.

---

## Quick start

```bash
# 1. Find the dongle's serial port
python auracast_python.py list-ports

# 2. Find the dongle's audio output name
python auracast_python.py list-audio

# 3. Check what will be written (no hardware needed)
python auracast_python.py show-spec --company-id FFFF

# 4. Configure a dongle and start broadcasting
python auracast_python.py run-stop \
    --port /dev/ttyACM0 \
    --stop 1 \
    --company-id FFFF \
    --audio-device "FlooGoo FMA120"
```

On Windows the port looks like `COM3` instead of `/dev/ttyACM0`.

---

## Commands

| Command | Hardware | Purpose |
|---|---|---|
| `list-ports` | dongle plugged in | Find which serial port the FMA120 is on |
| `list-audio` | none | Find the FMA120's audio device name |
| `show-spec` | **none** | Print every stop's configuration and BF hex |
| `provision` | dongle | Write configuration to one dongle |
| `play` | dongle | Loop a stop's announcement through it |
| `run-stop` | dongle | Provision, then play — the one you use at a stop |

`show-spec` is the useful one for anyone working on the Android app: it prints the exact bytes each transmitter will advertise, with no hardware required.

---

## Audio files

Expected layout:

```
AudioAuracast/
├── Stop 1/audio1.mp3
├── Stop 2/audio2.mp3
├── Stop 3/audio3.mp3
└── Stop 4/audio4.mp3
```

`.mp3`, `.mp4`, `.m4a` and `.wav` are all accepted; the first one found wins.

---

## What gets written to each dongle

Four BAI commands, sent over serial as `BC:<command>\r\n`:

| Command | Example | Meaning |
|---|---|---|
| `BN` | `AURA86-S1` | Broadcast name, shown in the phone's Auracast picker |
| `BE` | `AURA86DEMO2026` | Broadcast code — the encryption key |
| `BI` | `560001` | Standard Auracast Broadcast ID |
| `BF` | `0CFFFFFF415501560001000101` | Custom route/stop metadata |

All four stops share one broadcast code in this proof of concept.

---

## The BF metadata layout

`BF` carries the custom data the Android app matches on. It's standard BLE manufacturer-specific data wrapping a 9-byte project payload.

```
0C          length — 12 bytes follow
FF          AD type — manufacturer-specific data
FF FF       company ID, little-endian (0xFFFF = reserved for testing)
41 55       "AU" magic — identifies this project
01          protocol version
56 00       route ID (86), little-endian uint16
01          stop index
00          direction (0 = outbound)
01          language (1 = English)
01          audio ID
```

### Known-good values

Company ID `0xFFFF`:

| Stop | BF hex |
|---|---|
| 1 | `0CFFFFFF415501560001000101` |
| 2 | `0CFFFFFF415501560002000102` |
| 3 | `0CFFFFFF415501560003000103` |
| 4 | `0CFFFFFF415501560004000104` |

### Note for the Android app

`ScanRecord.getManufacturerSpecificData(0xFFFF)` strips the length byte, the `0xFF` type byte, and the company ID before returning anything. The app receives only the **9-byte payload starting at `41 55`**, not the full 13 bytes above.

`decode_bf_hex()` in this script is the reference implementation of the parser.

---

## Matching rules

A transmitter is the one the rider is waiting for when **all** of these agree:

- protocol version
- route ID
- stop index
- direction
- language

Stop index alone is not sufficient — stop 2 outbound and stop 2 inbound are different places with different announcements.

---

## Troubleshooting

**"Port busy"** — a previous run didn't close the port. Unplug and replug the dongle.

**`No OK for BC:BF=...`** — usually firmware older than 1.1.6.7. Check the version in FlooCast and update if needed. The firmware updater is only in the Windows build, and does not work inside a VM.

**Audio plays but nothing broadcasts** — `--audio-device` is probably wrong and audio is going to the laptop's speakers. Run `list-audio` and copy the name exactly.

**App sees the broadcast but hears nothing** — check `play_audio` is actually running. The dongle advertises its metadata whether or not audio is flowing.