import serial

from classes.stop import Stop
from utils.formatting import build_bf_hex
from main import SHARED_BROADCAST_CODE

class FMA120:
    """
    Control one physical FMA120 through its serial port.
    """

    def __init__(self, port: str):
        """
        Opens the FMA120 connection.
        """

        # Open serial port and configure the line
        self.ser = serial.Serial(
            port,
            921600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
            write_timeout=2
        )

        # Clear anything left from prev. session
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def close(self):
        """
        Close the serial connection.
        """
        
        self.ser.close()

    def command(self, body: str) -> list[str]:
        """
        Wrap command in BAI framing.
        """

        # Commands are sent as: BC:<command> followed by CRLF
        packet = f"BC:{body}\r\n".encode("ascii")
        print(f"TX  BC:{body}")
        self.ser.write(packet)
        self.ser.flush()

        # Reads response lines until one comes back empty
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
        """
        Send command and require an OK response.
        """

        responses = self.command(body)
        if "OK" not in responses:
            raise RuntimeError(f"No OK for BC:{body}; got {responses}")

    def provision(self, stop: Stop, company_id: int):
        """
        Configure this FMA120 as one Route 86 stop.

        BN = Broadcast Name
        BE = Broadcast Code
        BI = Broadcast ID
        BF = Route / stop metadata
        """
        
        # Generate custom BF metadata for this stop
        bf = build_bf_hex(stop, company_id)

        # Set the transmitted Broadcast Name
        self.require_ok(f"BN={stop.broadcast_name}")

        # Set the shared Broadcast Code used by the PoC
        self.require_ok(f"BE={SHARED_BROADCAST_CODE}")

        # Set the unique Broadcast ID for this stop
        self.require_ok(f"BI={stop.broadcast_id}")

        # Set the custom BF metadata containing Route and Stop IDs
        self.require_ok(f"BF={bf}")

        # Read values back to verify
        print("Verification:")
        self.command("BN")
        self.command("BI")
        self.command("BF")