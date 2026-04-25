import math
from array import array

import pygame


def init_click_sound():
    """Create a short synthesized click tone. Returns None if audio is unavailable."""
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256)

        sample_rate = 22050
        duration_s = 0.05
        freq_hz = 1400.0
        total = int(sample_rate * duration_s)
        pcm = array("h")
        for i in range(total):
            t = i / float(sample_rate)
            envelope = 1.0 - (i / float(total))
            sample = int(14000 * envelope * math.sin(2.0 * math.pi * freq_hz * t))
            pcm.append(sample)

        return pygame.mixer.Sound(buffer=pcm.tobytes())
    except Exception:
        return None


def play_click(click_sound):
    if click_sound is not None:
        try:
            click_sound.play()
        except Exception:
            pass
