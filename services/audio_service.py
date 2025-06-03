import os
import time
import logging
from pygame import mixer
from app.logger import app_logger as logger

# Попытка импорта ALSA для прямого управления
try:
    import alsaaudio
    ALSA_AVAILABLE = True
except ImportError:
    ALSA_AVAILABLE = False
    logger.warning("alsaaudio not available - using default pygame mixer")


class AudioService:
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False
        self.last_play_time = 0
        self._is_stopped = False
        self.audio_device = None
        
        # Инициализируем аудиосистему
        self._init_audio()
        
    def _init_audio(self):
        """Инициализация аудиосистемы с поддержкой Audio Bonnet"""
        try:
            # Сначала пытаемся найти Audio Bonnet
            bonnet_device = self._find_audio_bonnet()
            
            if bonnet_device:
                logger.info(f"Found Audio Bonnet: {bonnet_device}")
                self._init_pygame_with_device(bonnet_device)
            else:
                logger.warning("Audio Bonnet not found, using default audio")
                self._init_pygame_default()
                
        except Exception as e:
            logger.error(f"Audio initialization error: {e}")
            # Fallback к базовой инициализации
            self._init_pygame_default()

    def _find_audio_bonnet(self):
        """Поиск Audio Bonnet в системе"""
        try:
            if ALSA_AVAILABLE:
                # Ищем карты ALSA
                cards = alsaaudio.cards()
                logger.info(f"Available ALSA cards: {cards}")
                
                # Ищем Audio Bonnet по известным именам
                bonnet_names = [
                    'audioinjectorpi', 
                    'audioinjector-pi-soundcard',
                    'AudioInjector',
                    'wm8731',
                    'wm8960soundcard',
                    'wm8960-soundcard',
                    'wm8960'
                ]
                
                for i, card in enumerate(cards):
                    for bonnet_name in bonnet_names:
                        if bonnet_name.lower() in card.lower():
                            logger.info(f"Found Audio Bonnet card: {card} (index {i})")
                            return f"hw:{i},0"
                            
            # Альтернативный метод через /proc/asound/cards
            try:
                with open('/proc/asound/cards', 'r') as f:
                    cards_info = f.read()
                    logger.debug(f"ALSA cards info:\n{cards_info}")
                    
                    lines = cards_info.strip().split('\n')
                    for line in lines:
                        if any(name in line.lower() for name in ['audioinjector', 'wm8731', 'wm8960']):
                            # Извлекаем номер карты
                            card_num = line.split()[0]
                            return f"hw:{card_num},0"
                            
            except Exception as e:
                logger.warning(f"Could not read /proc/asound/cards: {e}")
                
        except Exception as e:
            logger.error(f"Error finding Audio Bonnet: {e}")
            
        return None

    def _init_pygame_with_device(self, device):
        """Инициализация pygame с конкретным аудиоустройством"""
        try:
            # Настраиваем переменную окружения для SDL
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            os.environ['AUDIODEV'] = device
            
            # Инициализируем pygame mixer с оптимальными настройками для Audio Bonnet
            mixer.pre_init(
                frequency=44100,    # CD качество
                size=-16,           # 16-bit signed
                channels=2,         # Стерео
                buffer=1024         # Буфер для низкой задержки
            )
            mixer.init()
            
            # Тест воспроизведения
            if self._test_audio_output():
                logger.info(f"AudioService initialized with Audio Bonnet device: {device}")
                self.audio_device = device
                return True
            else:
                logger.warning("Audio Bonnet test failed, falling back to default")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing pygame with Audio Bonnet: {e}")
            return False

    def _init_pygame_default(self):
        """Базовая инициализация pygame mixer"""
        try:
            mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            mixer.init()
            logger.info("AudioService initialized with default audio")
            self.audio_device = "default"
        except Exception as e:
            logger.error(f"Default audio initialization error: {e}")

    def _test_audio_output(self):
        """Тест аудиовыхода"""
        try:
            # Простой тест - проверяем, что mixer инициализирован
            return mixer.get_init() is not None
        except Exception as e:
            logger.error(f"Audio test failed: {e}")
            return False

    def set_volume(self, value):
        """ИСПРАВЛЕНО: Установка громкости только через pygame, без ALSA конфликтов"""
        try:
            volume = max(0.0, min(1.0, value))
            mixer.music.set_volume(volume)
            logger.debug(f"Set pygame volume to {volume}")
            
            # УБРАНО: Удаляем попытку управления ALSA громкостью из AudioService
            # Теперь VolumeService полностью отвечает за системную громкость
                    
        except Exception as e:
            logger.error(f"AudioService set_volume error: {e}")

    def play(self, filepath, fadein=0):
        """Воспроизведение файла"""
        if not filepath or not os.path.isfile(filepath):
            logger.warning(f"Audio file not found: {filepath}")
            return
            
        try:
            is_ringtone = 'ringtones' in filepath
            is_theme_sound = any(sound_type in filepath for sound_type in 
                            ['click', 'confirm', 'error', 'notify', 'startup'])
            
            current_time = time.time()
            
            # ИСПРАВЛЕНО: Ослабляем защиту от частого воспроизведения
            logger.debug(f"🎵 AudioService.play() called:")
            logger.debug(f"  filepath: {filepath}")
            logger.debug(f"  is_ringtone: {is_ringtone}")
            logger.debug(f"  is_theme_sound: {is_theme_sound}")
            logger.debug(f"  current state - is_playing: {self.is_playing}, current_file: {self.current_file}")
            
            # ИСПРАВЛЕНО: Более разумные проверки частоты
            if is_theme_sound:
                # Не прерываем рингтон коротким звуком
                if (self.is_playing and self.is_long_audio):
                    logger.debug("❌ Skipping theme sound - ringtone is playing")
                    return
                
                # ИСПРАВЛЕНО: Уменьшаем интервал между звуками темы до 0.1 секунды
                if (self.is_playing and not self.is_long_audio and 
                    (current_time - self.last_play_time) < 0.1):
                    logger.debug("❌ Skipping theme sound - too frequent")
                    return
            
            # Для рингтонов ВСЕГДА останавливаем текущее воспроизведение
            if is_ringtone:
                logger.info("🎵 Ringtone requested - stopping any current audio")
                if self.is_playing:
                    self.stop()
                    time.sleep(0.1)
            elif self.is_playing and is_theme_sound:
                # Для звуков темы - заменяем только короткие звуки
                if not self.is_long_audio:
                    self.stop()
            
            # Проверяем размер файла для рингтонов
            if is_ringtone:
                try:
                    file_size = os.path.getsize(filepath)
                    if file_size == 0:
                        logger.error(f"❌ Ringtone file is empty: {filepath}")
                        return
                    elif file_size > 50 * 1024 * 1024:  # > 50MB
                        logger.warning(f"⚠️ Large ringtone file: {file_size} bytes")
                except Exception as size_error:
                    logger.error(f"❌ Error checking ringtone file size: {size_error}")
                    return
            
            # Устанавливаем состояние
            self.is_playing = True
            self.current_file = filepath
            self.is_long_audio = is_ringtone
            self.last_play_time = current_time
            
            # Загружаем и воспроизводим файл
            try:
                mixer.music.load(filepath)
                
                if fadein > 0:
                    mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
                else:
                    mixer.music.play()
                mixer.music.set_volume(1.0)
                
                logger.debug(f"🎵 Playing audio: {os.path.basename(filepath)} on device: {self.audio_device}")
                
            except Exception as play_error:
                logger.error(f"❌ Error during playback: {play_error}")
                # Сбрасываем состояние при ошибке
                self.is_playing = False
                self.current_file = None
                self.is_long_audio = False
                return
            
        except Exception as e:
            logger.error(f"❌ AudioService play error: {e}")
            # Сбрасываем состояние при любой ошибке
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def stop(self):
        """Остановка воспроизведения"""
        logger.debug(f"🛑 AudioService.stop() called")
        
        try:
            if self.is_playing or mixer.music.get_busy():
                mixer.music.stop()
        except Exception as e:
            logger.error(f"❌ AudioService stop error: {e}")
        finally:
            # Всегда сбрасываем состояние
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def is_busy(self):
        """Проверка активности воспроизведения"""
        try:
            busy = mixer.music.get_busy()
            # Синхронизируем состояние с pygame
            if not busy and self.is_playing:
                logger.debug(f"🔍 Pygame not busy but is_playing=True - syncing state")
                self.is_playing = False
                self.current_file = None
                self.is_long_audio = False
            return busy
        except Exception as e:
            logger.error(f"❌ AudioService is_busy error: {e}")
            return False

    def get_device_info(self):
        """Получение информации об аудиоустройстве"""
        info = {
            "device": self.audio_device,
            "alsa_available": ALSA_AVAILABLE,
            "mixer_initialized": mixer.get_init() is not None
        }
        
        if ALSA_AVAILABLE:
            try:
                info["alsa_cards"] = alsaaudio.cards()
            except:
                info["alsa_cards"] = []
                
        return info

    def diagnose_state(self):
        """Диагностика состояния AudioService"""
        try:
            pygame_busy = mixer.music.get_busy()
            pygame_init = mixer.get_init()
            
            logger.info(f"🔧 === AUDIOSERVICE DIAGNOSIS ===")
            logger.info(f"is_playing: {self.is_playing}")
            logger.info(f"current_file: {self.current_file}")
            logger.info(f"is_long_audio: {self.is_long_audio}")
            logger.info(f"last_play_time: {self.last_play_time}")
            logger.info(f"audio_device: {self.audio_device}")
            logger.info(f"pygame mixer.get_busy(): {pygame_busy}")
            logger.info(f"pygame mixer.get_init(): {pygame_init}")
            
            return {
                "is_playing": self.is_playing,
                "current_file": self.current_file,
                "is_long_audio": self.is_long_audio,
                "pygame_busy": pygame_busy,
                "pygame_init": pygame_init
            }
        except Exception as e:
            logger.error(f"Error in diagnose_state: {e}")
            return {"error": str(e)}

    def reinitialize_audio(self):
        """Переинициализация аудиосистемы"""
        logger.info("Reinitializing audio system...")
        try:
            mixer.quit()
        except:
            pass
            
        self._init_audio()


# Создаем глобальный экземпляр
audio_service = AudioService()