#!/usr/bin/env python3
from __future__ import annotations

import argparse
import struct
import time
from dataclasses import dataclass
from pathlib import Path

import serial

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

def main():
    """
    Driver function, CLI entry point.

    Commands:
        list-ports
        list-audio
        show-spec
        provision
        play
        run-stop
    """

    # Parser-architecture
    parser = argparse.ArgumentParser(description="Route 86 Auracast FMA120 proof-of-concept controller")
    # Register each command
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # Find which port the FMA120 is on
    subparsers.add_parser("list-ports", help="List available serial ports")

    # Find the FMA120's audio device name
    subparsers.add_parser("list-audio", help="List available audio output devices")

    # Print all stops' config and BF hex
    show_spec = subparsers.add_parser("show-spec", help="Show metadata for all Route 86 stops")
    show_spec.add_argument("--company-id", required=True, help="Bluetooth Company ID in hexadecimal")

    # Write config to FMA120
    provision = subparsers.add_parser("provision", help="Configure an FMA120 for a selected stop")
    provision.add_argument("--port", required=True, help="Serial / COM port of the FMA120")
    provision.add_argument("--stop", type=int, choices=range(1, 5), required=True, help="Stop number from 1 to 4")
    provision.add_argument("--company-id", required=True, help="Bluetooth Company ID in hexadecimal")

    # Loop a stop's audio
    play = subparsers.add_parser("play", help="Play the audio announcement for a selected stop")
    play.add_argument("--stop", type=int, choices=range(1, 5), required=True, help="Stop number from 1 to 4")
    play.add_argument("--audio-device", help="Audio output device, normally the FMA120 USB audio output")
    play.add_argument("--once", action="store_true", help="Play the announcement once instead of looping")

    # Provision, then play
    run_stop = subparsers.add_parser("run-stop", help="Provision the FMA120 and play the selected stop audio")
    run_stop.add_argument("--port", required=True, help="Serial / COM port of the FMA120")
    run_stop.add_argument("--stop", type=int, choices=range(1, 5), required=True, help="Stop number from 1 to 4")
    run_stop.add_argument("--company-id", required=True, help="Bluetooth Company ID in hexadecimal")
    run_stop.add_argument("--audio-device", help="Audio output device, normally the FMA120 USB audio output")

    # Dispatching: each branch pulls what it needs out of args and calls the relevant function
    args = parser.parse_args()
    if args.cmd == "list-ports":
        list_serial_ports()
    elif args.cmd == "list-audio":
        list_audio_devices()
    elif args.cmd == "show-spec":
        company_id = parse_company_id(args.company_id)

        for stop in STOPS.values():
            bf = build_bf_hex(stop, company_id)

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
        company_id = parse_company_id(args.company_id)
        device = FMA120(args.port)
        try:
            device.provision(stop, company_id)
        finally:
            device.close()
    elif args.cmd == "play":
        play_audio(STOPS[args.stop], args.audio_device, args.once)
    elif args.cmd == "run-stop":
        stop = STOPS[args.stop]
        company_id = parse_company_id(args.company_id)
        device = FMA120(args.port)

        try:
            device.provision(stop, company_id)
        finally:
            device.close()

        play_audio(stop, args.audio_device)

if __name__ == "__main__":
    """
    Main dunder
    """

    main()