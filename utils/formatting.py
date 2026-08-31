import struct

from classes.stop import Stop
from main import MAGIC, PROTOCOL_VERSION, ROUTE_ID

def build_payload(stop: Stop) -> bytes:
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

def build_bf_hex(stop: Stop, company_id: int) -> str:
    """
    Takes the payload and wraps it in standard BLE advertising data

    Layout: Length-0xFF-Company ID-AU-Protocol Version-Route ID-Stop ID-Direction-Language-Audio ID
    """

    # 9-byte inner payload
    project_payload = (build_payload(stop))

    # Manufacturer-data envelope
    # Company ID is stored in little-endian format
    after_length = bytes([0xFF]) + struct.pack("<H", company_id) + project_payload

    # Prepend length + convert to bytes
    full_payload = bytes([len(after_length)]) + after_length

    # Hex encode
    encoded_hex = full_payload.hex().upper()

    return encoded_hex

def decode_bf_hex(bf_hex: str) -> dict:
    """
    Decode BF hexadecimal data back into bytes.
    Performs the opposite operation to build_bf_hex()
    """

    # Convert hex back into raw bytes
    raw_bytes = bytes.fromhex(bf_hex)

    # Check: length consistency
    if raw_bytes[0] != len(raw_bytes) - 1:
        raise ValueError("BF length mismatch")

    # Check: 0xFF means manufacturer-specific data
    if raw_bytes[1] != 0xFF:
        raise ValueError("Not manufacturer-specific data")

    # Extract the company ID
    company_id = int.from_bytes(raw_bytes[2:4], "little")

    # Everything after company ID is payload
    payload = raw_bytes[4:]

    # Check: payload is the project's
    if payload[:2] != MAGIC:
        raise ValueError("Wrong project magic")

    # Extract each field from payload
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
