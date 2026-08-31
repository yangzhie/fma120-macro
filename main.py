#!/usr/bin/env python3
from __future__ import annotations

import argparse
import struct
import time
from dataclasses import dataclass
from pathlib import Path

import serial
from serial.tools import list_ports

# Route number - distinguishes unique routes to avoid overlap
# Application checks the route id, then stop index
ROUTE_ID = 86

# Encryption key for all stops
# Device will not be able to decrypt the audio without this
SHARED_BROADCAST_CODE = "AURA86DEMO2026"

# Front of every payload (2 bytes)
# Makes the payload unique - parser checks this first
MAGIC = b"AU"

# Versioning of current protocol
PROTOCOL_VERSION = 1

# TODO: Unused features
DIRECTION_OUTBOUND = 0
LANGUAGE_ENGLISH = 1

# Dedicated/hard-coded stops dictionary for the proof-of-concept
STOPS = {
    1: Stop(
        index=1,
        name="Stop 1",
        folder="Stop 1",
        audio_stem="audio1"
    ),
    2: Stop(
        index=2,
        name="Stop 2",
        folder="Stop 2",
        audio_stem="audio2"
    ),
    3: Stop(
        index=3,
        name="Stop 3",
        folder="Stop 3",
        audio_stem="audio3"
    ),
    4: Stop(
        index=4,
        name="Stop 4",
        folder="Stop 4",
        audio_stem="audio4"
    )
}

def build_payload(
    stop: Stop
) -> bytes:
    """
    Builds the custom 9 bytes.

    Layout:
    AU(MAGIC)-PROTOCOL_VERSION-ROUTE_ID-INDEX-DIRECTION-LANGUAGE-AUDIO_ID
    """

    return (
        MAGIC
        + bytes([
            PROTOCOL_VERSION
        ])
        + struct.pack(
            "<H",
            ROUTE_ID
        )
        + bytes([
            stop.index,
            stop.direction,
            stop.language,
            stop.index
        ])
    )


# ============================================================
# BF METADATA ENCODING
# ============================================================

def build_bf_hex(
    stop: Stop,
    company_id: int
) -> str:
    """
    Build the BF manufacturer-specific advertising data.

    Layout:

    Length
      |
    0xFF
      |
    Company ID
      |
    AU
      |
    Protocol Version
      |
    Route ID
      |
    Stop ID
      |
    Direction
      |
    Language
      |
    Audio ID
    """

    # First build our custom project metadata.
    project_payload = (
        build_project_payload(stop)
    )

    # 0xFF identifies manufacturer-specific advertising data.
    # The Company ID is stored in little-endian format.
    after_length = (
        bytes([0xFF])
        + struct.pack(
            "<H",
            company_id
        )
        + project_payload
    )

    # The first byte describes how many bytes follow it.
    full_payload = (
        bytes([
            len(after_length)
        ])
        + after_length
    )

    # FMA120 BF configuration uses hexadecimal text.
    return (
        full_payload
        .hex()
        .upper()
    )


# ============================================================
# BF METADATA DECODING
# ============================================================

def decode_bf_hex(
    bf_hex: str
) -> dict:
    """
    Decode BF hexadecimal data back into
    Route 86 project information.

    This performs the opposite operation
    to build_bf_hex().
    """

    # Convert hexadecimal text back into raw bytes.
    raw = bytes.fromhex(
        bf_hex
    )

    # The first byte should equal the number
    # of bytes that follow it.
    if raw[0] != len(raw) - 1:
        raise ValueError(
            "BF length mismatch"
        )

    # 0xFF means manufacturer-specific data.
    if raw[1] != 0xFF:
        raise ValueError(
            "Not manufacturer-specific data"
        )

    # Extract the Bluetooth Company ID.
    company_id = int.from_bytes(
        raw[2:4],
        "little"
    )

    # Everything after the Company ID is
    # our custom project payload.
    payload = raw[4:]

    # Check whether this data belongs to our project.
    if payload[:2] != MAGIC:
        raise ValueError(
            "Wrong project magic"
        )

    # Extract each field from the project payload.
    return {
        "company_id":
            company_id,

        "version":
            payload[2],

        "route_id":
            int.from_bytes(
                payload[3:5],
                "little"
            ),

        "stop_index":
            payload[5],

        "direction":
            payload[6],

        "language":
            payload[7],

        "audio_id":
            payload[8]
    }


# ============================================================
# NEXT-STOP LOGIC
# ============================================================

def expected_next_stop(
    completed_count: int
) -> Stop | None:
    """
    Determine which stop should be detected next.

    Examples:

    completed_count = 0 -> Stop 1
    completed_count = 1 -> Stop 2
    completed_count = 2 -> Stop 3
    completed_count = 3 -> Stop 4
    completed_count = 4 -> Journey complete
    """

    return STOPS.get(
        completed_count + 1
    )


# ============================================================
# EXPECTED STOP MATCHING
# ============================================================

def matches_expected_stop(
    bf_hex: str,
    expected: Stop
) -> bool:
    """
    Check whether the BF metadata received from
    a transmitter belongs to the expected stop.

    The detected transmitter must have:

    - Correct protocol version
    - Correct Route ID
    - Correct Stop ID
    - Correct direction
    - Correct language
    """

    # Decode the received BF data.
    data = decode_bf_hex(
        bf_hex
    )

    # Compare the decoded transmitter information
    # with the stop the passenger is expecting.
    return (
        data["version"]
        == PROTOCOL_VERSION

        and data["route_id"]
        == ROUTE_ID

        and data["stop_index"]
        == expected.index

        and data["direction"]
        == expected.direction

        and data["language"]
        == expected.language
    )


# ============================================================
# FMA120 SERIAL CONTROL
# ============================================================

class FMA120:
    """Control one physical FMA120 through its serial / COM port."""

    def __init__(self, port: str):
        """Open the FMA120 serial control connection."""
        self.ser = serial.Serial(
            port,
            921600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
            write_timeout=2
        )
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def close(self):
        """Close the serial connection."""
        self.ser.close()

    def command(self, body: str) -> list[str]:
        """Send a BC command and return the FMA120 response lines."""
        # Commands are sent as: BC:<command> followed by CRLF.
        packet = f"BC:{body}\r\n".encode("ascii")
        print(f"TX  BC:{body}")
        self.ser.write(packet)
        self.ser.flush()

        responses = []
        while True:
            raw = self.ser.readline()
            if not raw:
                break

            text = raw.decode("ascii", errors="replace").strip()
            if text:
                print(f"RX  {text}")
                responses.append(text)

        return responses

    def require_ok(self, body: str):
        """Send a command and require an OK response."""
        responses = self.command(body)
        if "OK" not in responses:
            raise RuntimeError(
                f"No OK for BC:{body}; got {responses}"
            )

    def provision(self, stop: Stop, company_id: int):
        """
        Configure this FMA120 as one Route 86 stop.

        BN = Broadcast Name
        BE = Broadcast Code
        BI = Broadcast ID
        BF = Route / stop metadata
        """
        # Generate the custom BF metadata for this stop.
        bf = build_bf_hex(stop, company_id)

        # 1. Set the human-readable Broadcast Name.
        self.require_ok(f"BN={stop.broadcast_name}")

        # 2. Set the shared Broadcast Code used by the PoC.
        self.require_ok(f"BE={SHARED_BROADCAST_CODE}")

        # 3. Set the unique Broadcast ID for this stop.
        self.require_ok(f"BI={stop.broadcast_id}")

        # 4. Set the custom BF metadata containing Route and Stop IDs.
        self.require_ok(f"BF={bf}")

        # Read values back to verify the configuration.
        print("Verification:")
        self.command("BN")
        self.command("BI")
        self.command("BF")


# ============================================================
# SERIAL PORT DISCOVERY
# ============================================================

def list_serial_ports():
    """List serial / COM ports so the FMA120 port can be identified."""
    for port in list_ports.comports():
        print(port.device, port.description)

# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def main():
    """
    Command-line entry point for the complete Auracast PoC.

    Available commands:
        list-ports
        list-audio
        show-spec
        provision
        play
        run-stop
    """

    parser = argparse.ArgumentParser(
        description=(
            "Route 86 Auracast FMA120 "
            "proof-of-concept controller"
        )
    )

    subparsers = parser.add_subparsers(
        dest="cmd",
        required=True
    )

    # --------------------------------------------------------
    # list-ports
    # --------------------------------------------------------
    subparsers.add_parser(
        "list-ports",
        help="List available serial / COM ports"
    )

    # --------------------------------------------------------
    # list-audio
    # --------------------------------------------------------
    subparsers.add_parser(
        "list-audio",
        help="List available audio output devices"
    )

    # --------------------------------------------------------
    # show-spec
    # --------------------------------------------------------
    show_spec = subparsers.add_parser(
        "show-spec",
        help="Show metadata for all Route 86 stops"
    )

    show_spec.add_argument(
        "--company-id",
        required=True,
        help="Bluetooth Company ID in hexadecimal"
    )

    # --------------------------------------------------------
    # provision
    # --------------------------------------------------------
    provision = subparsers.add_parser(
        "provision",
        help="Configure an FMA120 for a selected stop"
    )

    provision.add_argument(
        "--port",
        required=True,
        help="Serial / COM port of the FMA120"
    )

    provision.add_argument(
        "--stop",
        type=int,
        choices=range(1, 5),
        required=True,
        help="Stop number from 1 to 4"
    )

    provision.add_argument(
        "--company-id",
        required=True,
        help="Bluetooth Company ID in hexadecimal"
    )

    # --------------------------------------------------------
    # play
    # --------------------------------------------------------
    play = subparsers.add_parser(
        "play",
        help="Play the audio announcement for a selected stop"
    )

    play.add_argument(
        "--stop",
        type=int,
        choices=range(1, 5),
        required=True,
        help="Stop number from 1 to 4"
    )

    play.add_argument(
        "--audio-device",
        help="Audio output device, normally the FMA120 USB audio output"
    )

    play.add_argument(
        "--once",
        action="store_true",
        help="Play the announcement once instead of looping"
    )

    # --------------------------------------------------------
    # run-stop
    # --------------------------------------------------------
    run_stop = subparsers.add_parser(
        "run-stop",
        help="Provision the FMA120 and play the selected stop audio"
    )

    run_stop.add_argument(
        "--port",
        required=True,
        help="Serial / COM port of the FMA120"
    )

    run_stop.add_argument(
        "--stop",
        type=int,
        choices=range(1, 5),
        required=True,
        help="Stop number from 1 to 4"
    )

    run_stop.add_argument(
        "--company-id",
        required=True,
        help="Bluetooth Company ID in hexadecimal"
    )

    run_stop.add_argument(
        "--audio-device",
        help="Audio output device, normally the FMA120 USB audio output"
    )

    args = parser.parse_args()

    # ========================================================
    # COMMAND EXECUTION
    # ========================================================

    if args.cmd == "list-ports":
        list_serial_ports()

    elif args.cmd == "list-audio":
        list_audio_devices()

    elif args.cmd == "show-spec":
        company_id = parse_company_id(
            args.company_id
        )

        for stop in STOPS.values():
            bf = build_bf_hex(
                stop,
                company_id
            )

            print("\n==========================")
            print(f"Stop: {stop.index}")
            print(f"Name: {stop.name}")
            print(f"Broadcast Name: {stop.broadcast_name}")
            print(f"Broadcast Code: {SHARED_BROADCAST_CODE}")
            print(f"Broadcast ID: {stop.broadcast_id}")
            print(f"BF: {bf}")
            print(f"Decoded BF: {decode_bf_hex(bf)}")
            print(f"Audio File: {stop.audio_path}")

    elif args.cmd == "provision":
        stop = STOPS[args.stop]

        company_id = parse_company_id(
            args.company_id
        )

        device = FMA120(
            args.port
        )

        try:
            device.provision(
                stop,
                company_id
            )
        finally:
            device.close()

    elif args.cmd == "play":
        play_audio(
            STOPS[args.stop],
            args.audio_device,
            args.once
        )

    elif args.cmd == "run-stop":
        stop = STOPS[args.stop]

        company_id = parse_company_id(
            args.company_id
        )

        device = FMA120(
            args.port
        )

        try:
            device.provision(
                stop,
                company_id
            )
        finally:
            device.close()

        play_audio(
            stop,
            args.audio_device
        )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()