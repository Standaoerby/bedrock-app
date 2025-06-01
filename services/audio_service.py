import os
import time
from pygame import mixer
from app.logger import app_logger as logger


class AudioService:
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False  # Флаг для длинных аудио (рингтоны)
        self.last_play_time = 0
        
        # ДОБАВЛЕНО: флаг для предотвращения повторной остановки
        self._is_stopped = False
        
        # Инициализируем mixer сразу с конкретными параметрами
        try:
            mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            mixer.init()
            logger.info("AudioService initialized successfully")
        except Exception as e:
            logger.error(f"AudioService init error: {e}")

    def play(self, filepath, fadein=0):
        """Воспроизведение аудио файла"""
        if not filepath or not os.path.isfile(filepath):
            logger.warning(f"AudioService: файл не найден: {filepath}")
            return
            
        try:
            # Определяем тип аудио по пути
            is_ringtone = 'ringtones' in filepath
            is_theme_sound = any(sound_type in filepath for sound_type in 
                               ['click', 'confirm', 'error', 'notify', 'startup'])
            
            current_time = time.time()
            
            # Если играет длинный звук (рингтон) и мы хотим проиграть короткий звук - не прерываем
            if (self.is_playing and self.is_long_audio and is_theme_sound):
                logger.debug(f"Skipping theme sound {os.path.basename(filepath)} - ringtone is playing")
                return
            
            # Если играет короткий звук, но прошло мало времени - не прерываем
            if (self.is_playing and not self.is_long_audio and 
                (current_time - self.last_play_time) < 0.2):
                logger.debug(f"Skipping sound {os.path.basename(filepath)} - too soon after last sound")
                return
            
            # Останавливаем текущее воспроизведение только если нужно
            if self.is_playing:
                # Если играет рингтон и мы хотим новый рингтон - останавливаем
                # Если играет короткий звук и прошло достаточно времени - останавливаем
                if (self.is_long_audio and is_ringtone) or (not self.is_long_audio):
                    self.stop()
            
            # Запускаем новое воспроизведение
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
            
            audio_type = "ringtone" if is_ringtone else "theme sound"
            logger.debug(f"Playing {audio_type}: {os.path.basename(filepath)}")
            
        except Exception as e:
            logger.error(f"AudioService play error: {e}")
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def stop(self):
        """Остановка воспроизведения"""
        try:
            mixer.music.stop()
            if self.current_file:
                audio_type = "ringtone" if self.is_long_audio else "theme sound"
                logger.debug(f"Stopped {audio_type}: {os.path.basename(self.current_file)}")
        except Exception as e:
            logger.error(f"AudioService stop error: {e}")
        finally:
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def set_volume(self, value):
        """value: 0.0 .. 1.0"""
        try:
            mixer.music.set_volume(max(0.0, min(1.0, value)))
        except Exception as e:
            logger.error(f"AudioService set_volume error: {e}")

    def is_busy(self):
        """Проверка активного воспроизведения"""
        try:
            return mixer.music.get_busy()
        except Exception as e:
            logger.error(f"AudioService is_busy error: {e}")
            return False

audio_service = AudioService()