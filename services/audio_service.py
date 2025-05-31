import os
from pygame import mixer
from app.logger import app_logger as logger


class AudioService:
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        # Инициализируем mixer сразу с конкретными параметрами
        try:
            mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            mixer.init()
            # Принудительно "прогреваем" mixer пустым звуком
            print("[AudioService] Warming up mixer...")
        except Exception as e:
            print(f"[AudioService] Init error: {e}")

    def play(self, filepath, fadein=0):
        if not filepath or not os.path.isfile(filepath):
            print("AudioService: файл не найден:", filepath)
            return
            
        try:
            self.stop()
            self.is_playing = True
            self.current_file = filepath
            mixer.music.load(filepath)
            if fadein > 0:
                mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
            else:
                mixer.music.play()
            mixer.music.set_volume(1.0)
        except Exception as e:
            print(f"[AudioService] Play error: {e}")

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
