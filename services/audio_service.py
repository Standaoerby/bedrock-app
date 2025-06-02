import os
import time  # ИСПРАВЛЕНИЕ: Добавляем глобальный import time
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
                    'wm8960soundcard',  # Добавляем WM8960
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
        """Установка громкости"""
        try:
            volume = max(0.0, min(1.0, value))
            mixer.music.set_volume(volume)
            
            # Дополнительно устанавливаем системную громкость если доступно ALSA
            if ALSA_AVAILABLE and self.audio_device and 'hw:' in self.audio_device:
                try:
                    card_index = int(self.audio_device.split(':')[1].split(',')[0])
                    mixer_control = alsaaudio.Mixer('Master', cardindex=card_index)
                    alsa_volume = int(volume * 100)
                    mixer_control.setvolume(alsa_volume)
                    logger.debug(f"Set ALSA volume to {alsa_volume}%")
                except Exception as e:
                    logger.warning(f"Could not set ALSA volume: {e}")
                    
        except Exception as e:
            logger.error(f"AudioService set_volume error: {e}")

    # ИСПРАВЛЕНИЕ для метода play() в services/audio_service.py
    # Заменить существующий метод на эту версию:

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
            
            # ИСПРАВЛЕНИЕ: Добавляем подробное логирование для диагностики
            logger.info(f"🎵 AudioService.play() called:")
            logger.info(f"  filepath: {filepath}")
            logger.info(f"  is_ringtone: {is_ringtone}")
            logger.info(f"  is_theme_sound: {is_theme_sound}")
            logger.info(f"  fadein: {fadein}")
            logger.info(f"  current state - is_playing: {self.is_playing}, current_file: {self.current_file}")
            logger.info(f"  current state - is_long_audio: {self.is_long_audio}")
            
            # ИСПРАВЛЕНИЕ: Проверки частоты применяются ТОЛЬКО к theme sounds
            if is_theme_sound:
                # Не прерываем рингтон коротким звуком
                if (self.is_playing and self.is_long_audio):
                    logger.info("❌ Skipping theme sound - ringtone is playing")
                    return
                
                # Не играем короткий звук слишком часто
                if (self.is_playing and not self.is_long_audio and 
                    (current_time - self.last_play_time) < 0.2):
                    logger.info("❌ Skipping theme sound - too frequent")
                    return
            
            # ИСПРАВЛЕНИЕ: Для рингтонов ВСЕГДА останавливаем текущее воспроизведение
            if is_ringtone:
                logger.info("🎵 Ringtone requested - stopping any current audio")
                if self.is_playing:
                    logger.info("🛑 Stopping current audio for ringtone...")
                    self.stop()
                    time.sleep(0.1)  # Даем время pygame mixer освободить ресурсы
            elif self.is_playing and is_theme_sound:
                # Для звуков темы - стандартная логика замещения
                if not self.is_long_audio:  # Заменяем только короткие звуки
                    logger.info("🔊 Stopping current theme sound for new theme sound")
                    self.stop()
            
            # ИСПРАВЛЕНИЕ: Проверяем размер файла для рингтонов
            if is_ringtone:
                try:
                    file_size = os.path.getsize(filepath)
                    logger.info(f"🎵 Ringtone file size: {file_size} bytes")
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
            
            logger.info(f"🎵 Loading audio file into pygame mixer...")
            
            # ИСПРАВЛЕНИЕ: Обрабатываем ошибки загрузки файла
            try:
                mixer.music.load(filepath)
                logger.info(f"✅ Audio file loaded successfully")
            except Exception as load_error:
                logger.error(f"❌ Error loading audio file: {load_error}")
                # Сбрасываем состояние при ошибке
                self.is_playing = False
                self.current_file = None
                self.is_long_audio = False
                return
            
            # ИСПРАВЛЕНИЕ: Обрабатываем ошибки воспроизведения
            try:
                if fadein > 0:
                    logger.info(f"🎵 Starting playback with {fadein}s fadein...")
                    mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
                else:
                    logger.info(f"🎵 Starting playback...")
                    mixer.music.play()
                mixer.music.set_volume(1.0)
                logger.info(f"✅ Playback started successfully")
            except Exception as play_error:
                logger.error(f"❌ Error starting playback: {play_error}")
                # Сбрасываем состояние при ошибке
                self.is_playing = False
                self.current_file = None
                self.is_long_audio = False
                return
            
            logger.info(f"🎵 Playing audio: {os.path.basename(filepath)} on device: {self.audio_device}")
            logger.info(f"🎵 Final state - is_playing: {self.is_playing}, current_file: {self.current_file}")
            
        except Exception as e:
            logger.error(f"❌ AudioService play error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Сбрасываем состояние при любой ошибке
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def stop(self):
        """Остановка воспроизведения"""
        logger.info(f"🛑 AudioService.stop() called")
        logger.info(f"  current state - is_playing: {self.is_playing}, current_file: {self.current_file}")
        
        try:
            if self.is_playing or mixer.music.get_busy():
                logger.info(f"🛑 Stopping pygame mixer...")
                mixer.music.stop()
                logger.info(f"✅ Pygame mixer stopped")
            else:
                logger.info(f"ℹ️ Nothing to stop")
        except Exception as e:
            logger.error(f"❌ AudioService stop error: {e}")
        finally:
            # Всегда сбрасываем состояние
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False
            logger.info(f"✅ AudioService state reset")

    def is_busy(self):
        """Проверка активности воспроизведения"""
        try:
            busy = mixer.music.get_busy()
            # ИСПРАВЛЕНИЕ: Синхронизируем состояние с pygame
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