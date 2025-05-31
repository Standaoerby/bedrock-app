import os
from pygame import mixer
from app.logger import app_logger as logger


class AudioService:
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        mixer.init()

    def play(self, filepath, fadein=0):
        if not os.path.isfile(filepath):
            print("AudioService: файл не найден:", filepath)
            return
        self.stop()
        self.is_playing = True
        self.current_file = filepath
        mixer.music.load(filepath)
        if fadein > 0:
            mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
        else:
            mixer.music.play()
        mixer.music.set_volume(1.0)

    def stop(self):
        mixer.music.stop()
        self.is_playing = False
        self.current_file = None

    def set_volume(self, value):
        """value: 0.0 .. 1.0"""
        mixer.music.set_volume(value)

    def is_busy(self):
        return mixer.music.get_busy()

audio_service = AudioService()
