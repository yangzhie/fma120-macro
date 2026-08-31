from dataclasses import dataclass
from pathlib import Path

from main import DIRECTION_OUTBOUND, LANGUAGE_ENGLISH, ROUTE_ID

@dataclass(frozen=True)
class Stop:
    """
    Each stop's model and the transmitter config it maps to.
    Immutable - identity of stop must not be changed.
    """

    index: int
    name: str
    folder: str
    audio_stem: str
    direction: int = DIRECTION_OUTBOUND
    language: int = LANGUAGE_ENGLISH

    @property
    def audio_path(self) -> Path:
        """
        Path to the stop's announcement audio file.
        Supported formats: mp3 and mp4.
        """

        folder_path = Path(r"./audio") / self.folder

        # Loop through the audio folder to obtain audio file
        for extension in (".mp3", ".mp4"):
            # Obtain audio file
            audio_file = folder_path / f"{self.audio_stem}{extension}"

            # Check: if audio file exists
            if audio_file.exists():
                return audio_file

        # Return the expected MP3 path if no supported
        # audio file is currently found.
        return (folder_path / f"{self.audio_stem}.mp3")

    @property
    def broadcast_name(self) -> str:
        """
        Transmitter's UI-friendly broadcasted name.
        """

        name = f"AURA86-S{self.index}"
        return name

    # Standard Auracast broadcast ID
    # 3 bytes
    @property
    def broadcast_id(self) -> str: 
        """
        Auracast standard broadcast ID.
        3 bytes long.
        """

        return f"{ROUTE_ID:02X}00{self.index:02X}"
