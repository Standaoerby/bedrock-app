import os
import time
from pygame import mixer
from app.logger import app_logger as logger


class AudioService:
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False
        self.last_play_time = 0
        self._is_stopped = False
        
        try:
            mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            mixer.init()
            logger.info("AudioService initialized")
        except Exception as e:
            logger.error(f"AudioService init error: {e}")

    def play(self, filepath, fadein=0):
        if not filepath or not os.path.isfile(filepath):
            return
            
        try:
            is_ringtone = 'ringtones' in filepath
            is_theme_sound = any(sound_type in filepath for sound_type in 
                               ['click', 'confirm', 'error', 'notify', 'startup'])
            
            current_time = time.time()
            
            # Не прерываем рингтон коротким звуком
            if (self.is_playing and self.is_long_audio and is_theme_sound):
                return
            
            # Не играем короткий звук слишком часто
            if (self.is_playing and not self.is_long_audio and 
                (current_time - self.last_play_time) < 0.2):
                return
            
            # Останавливаем текущее воспроизведение если нужно
            if self.is_playing:
                if (self.is_long_audio and is_ringtone) or (not self.is_long_audio):
                    self.stop()
            
            self.is_playing = True
            self.current_file = filepath
            self.is_long_audio = is_ringtone
            self.last_play_time = current_time
            
            mixer.music.load(filepath)
            if fadein > 0:
                mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
            else:
                mixer.music.play()
            mixer.music.set_volume(1.0)
            
        except Exception as e:
            logger.error(f"AudioService play error: {e}")
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def stop(self):
        try:
            mixer.music.stop()
        except Exception as e:
            logger.error(f"AudioService stop error: {e}")
        finally:
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def set_volume(self, value):
        try:
            mixer.music.set_volume(max(0.0, min(1.0, value)))
        except Exception as e:
            logger.error(f"AudioService set_volume error: {e}")

    def is_busy(self):
        try:
            return mixer.music.get_busy()
        except Exception as e:
            logger.error(f"AudioService is_busy error: {e}")
            return False

audio_service = AudioService()