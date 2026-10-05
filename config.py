"""Shared constants"""

# Route number: distinguishes unique routes to avoid overlap
ROUTE_ID = 86

# Encryption key, shared by all stops
SHARED_BROADCAST_CODE = "AURA86DEMO2026"

# Two bytes at the front of every payload
MAGIC = b"AU"

# Incremented on any change to the payload layout
PROTOCOL_VERSION = 1

# Unused, reserved
DIRECTION_OUTBOUND = 0
LANGUAGE_ENGLISH = 1