def list_audio_devices():
    """
    Audio output device discovery helper.
    Identifies the FMA120 transmitter.
    """

    import pygame

    from pygame._sdl2 import (
        audio as sdl2_audio
    )

    # Initialise pygame so audio devices can be queried
    pygame.init()

    # False = output devices
    devices = (
        sdl2_audio
        .get_audio_device_names(
            False
        )
    )

    # Loop all output devices
    for index, name in enumerate(devices):
        print(f"[{index}] {name}")

def play_audio(stop: Stop, audio_device: str | None, once: bool = False):
    """
    Play the audio file associated with a stop.
    Selected audio output should be FMA120 transmitter.

    Flow: audio file -> pygame -> FMA USB device -> FMA120 transmitter -> Auracast broadcast

    If once=False, announcement loops.
    If once=True, plays one time only.
    """

    import pygame

    # Obtain audio file for the stop
    audio_file = stop.audio_path

    # Stop if audio file does not exist
    if not audio_file.exists():
        raise FileNotFoundError(audio_file)

    # Reset existing mixer session before selecting new output
    pygame.mixer.quit()

    # Initialise output
    pygame.mixer.init(
        frequency=48000,
        size=-16,
        channels=2,
        buffer=1024,
        devicename=audio_device
    )

    # Load stop announcement
    pygame.mixer.music.load(str(audio_file))

    # Play once (0) or loop (-1)
    pygame.mixer.music.play(0 if once else -1)

    print(f"Playing {audio_file} -> {audio_device or 'default output'}")
    print("Terminate to stop")

    try:
        # Block until interrupted
        while (pygame.mixer.music.get_busy()):
            time.sleep(0.25)
    except KeyboardInterrupt:
        # Stop playback (terminate w/ Ctrl+C)
        pass
    finally:
        # Clean up mixer
        pygame.mixer.music.stop()
        pygame.mixer.quit()

