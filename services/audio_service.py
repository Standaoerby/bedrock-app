# services/audio_service.py
import os
import time
import threading
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
        self._mixer_initialized = False  # ДОБАВЛЕНО: Флаг инициализации
        self._init_lock = threading.Lock()  # ДОБАВЛЕНО: Блокировка для thread-safety
        
        # Инициализируем аудиосистему с проверкой
        self._safe_init_audio()
        
    def _safe_init_audio(self):
        """ИСПРАВЛЕНО: Безопасная инициализация с блокировкой"""
        with self._init_lock:
            try:
                self._init_audio()
            except Exception as e:
                logger.error(f"Critical audio initialization error: {e}")
                # Устанавливаем минимальное состояние для предотвращения краха
                self._mixer_initialized = False
                self.audio_device = "error_state"
        
    def _init_audio(self):
        """Инициализация аудиосистемы для USB audio устройств"""
        try:
            # Сначала закрываем предыдущий mixer если есть
            self._safe_quit_mixer()
            
            # Ищем USB аудиоустройства (dongle, карты)
            usb_device = self._find_usb_audio_device()
            
            if usb_device:
                logger.info(f"Found USB audio device: {usb_device}")
                if self._init_pygame_with_device(usb_device):
                    self._mixer_initialized = True
                    return
            
            # Fallback на системное аудио по умолчанию
            logger.info("Using system default audio device")
            if self._init_pygame_default():
                self._mixer_initialized = True
            else:
                logger.error("Failed to initialize any audio device")
                self._mixer_initialized = False
                
        except Exception as e:
            logger.error(f"Audio initialization error: {e}")
            self._mixer_initialized = False

    def _safe_quit_mixer(self):
        """ДОБАВЛЕНО: Безопасное закрытие mixer"""
        try:
            if mixer.get_init() is not None:
                mixer.quit()
                time.sleep(0.1)  # Задержка для освобождения ресурсов
        except Exception as e:
            logger.debug(f"Error quitting mixer (non-critical): {e}")

    def _find_usb_audio_device(self):
        """Поиск USB аудиоустройств в системе"""
        try:
            if ALSA_AVAILABLE:
                # Получаем список ALSA карт
                cards = alsaaudio.cards()
                logger.info(f"Available ALSA cards: {cards}")
                
                # Ищем USB аудиоустройства по известным именам
                usb_audio_names = [
                    'gs3',          # Ваше конкретное устройство
                    'usb',          # Generic USB audio
                    'headset',      # USB headsets
                    'webcam',       # Webcam audio
                    'plantronics',  # Plantronics headsets
                    'logitech',     # Logitech devices
                    'creative',     # Creative USB cards
                    'behringer',    # Behringer interfaces
                    'focusrite',    # Focusrite interfaces
                    'audioengine',  # AudioEngine devices
                ]
                
                for i, card in enumerate(cards):
                    card_lower = card.lower()
                    if any(name in card_lower for name in usb_audio_names):
                        device = f"hw:{i},0"
                        logger.info(f"Found potential USB audio device: {card} -> {device}")
                        return device
                        
        except Exception as e:
            logger.error(f"Error finding USB audio devices: {e}")
        
        return None

    def _init_pygame_with_device(self, device):
        """ИСПРАВЛЕНО: Инициализация pygame с конкретным USB устройством"""
        try:
            # Настраиваем переменные окружения для SDL
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            os.environ['AUDIODEV'] = device
            
            # ИСПРАВЛЕНИЕ: Более консервативные настройки для совместимости
            mixer.pre_init(
                frequency=44100,    # Стандартная частота для лучшей совместимости
                size=-16,           # 16-bit signed
                channels=2,         # Стерео
                buffer=2048         # Увеличенный буфер для USB устройств
            )
            
            mixer.init()
            
            # Проверяем успешность инициализации
            if not self._test_audio_output():
                logger.warning("USB device test failed, falling back to default")
                return False
                
            logger.info(f"AudioService initialized with USB device: {device}")
            self.audio_device = device
            return True
                
        except Exception as e:
            logger.error(f"Error initializing pygame with USB audio: {e}")
            return False

    def _init_pygame_default(self):
        """ИСПРАВЛЕНО: Базовая инициализация pygame mixer для системного аудио"""
        try:
            # Очищаем переменные окружения
            os.environ.pop('SDL_AUDIODRIVER', None)
            os.environ.pop('AUDIODEV', None)
            
            # Инициализируем с настройками по умолчанию
            mixer.pre_init(
                frequency=44100,    # Стандартная частота
                size=-16,           # 16-bit signed
                channels=2,         # Стерео
                buffer=1024         # Стандартный буфер
            )
            
            mixer.init()
            
            # ИСПРАВЛЕНИЕ: Проверяем успешность инициализации
            if not self._test_audio_output():
                logger.error("Default audio device test failed")
                return False
                
            logger.info("AudioService initialized with system default audio")
            self.audio_device = "system_default"
            return True
            
        except Exception as e:
            logger.error(f"Default audio initialization error: {e}")
            return False

    def _test_audio_output(self):
        """ИСПРАВЛЕНО: Тест аудиовыхода с лучшей проверкой"""
        try:
            # Проверяем, что mixer инициализирован корректно
            init_result = mixer.get_init()
            if init_result is None:
                logger.error("Mixer not initialized - get_init() returned None")
                return False
                
            # Логируем параметры инициализации
            freq, format_info, channels = init_result
            logger.debug(f"Audio initialized: {freq}Hz, format={format_info}, channels={channels}")
            
            # ИСПРАВЛЕНИЕ: Дополнительная проверка доступности mixer.music
            try:
                # Проверяем что модуль music доступен
                mixer.music.get_busy()  # Простой вызов для проверки
                return True
            except Exception as music_error:
                logger.error(f"mixer.music not available: {music_error}")
                return False
            
        except Exception as e:
            logger.error(f"Audio test failed: {e}")
            return False

    def is_mixer_initialized(self):
        """ДОБАВЛЕНО: Проверка состояния mixer"""
        with self._init_lock:
            return self._mixer_initialized and mixer.get_init() is not None

    def set_volume(self, value):
        """ИСПРАВЛЕНО: Установка громкости с проверкой mixer"""
        if not self.is_mixer_initialized():
            logger.warning("Cannot set volume - mixer not initialized")
            return
            
        try:
            volume = max(0.0, min(1.0, value))
            mixer.music.set_volume(volume)
            logger.debug(f"Set pygame volume to {volume} on device {self.audio_device}")
                    
        except Exception as e:
            logger.error(f"AudioService set_volume error: {e}")

    def play(self, filepath, fadein=0):
        """ИСПРАВЛЕНО: Воспроизведение файла с проверкой mixer"""
        if not filepath or not os.path.isfile(filepath):
            logger.warning(f"Audio file not found: {filepath}")
            return
            
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверяем mixer перед использованием
        if not self.is_mixer_initialized():
            logger.error("❌ AudioService play error: mixer not initialized")
            # Пытаемся переинициализировать
            logger.info("Attempting to reinitialize audio system...")
            self._safe_init_audio()
            
            if not self.is_mixer_initialized():
                logger.error("❌ AudioService: Failed to reinitialize mixer")
                return
            
        try:
            with self._init_lock:  # Защищаем от concurrent access
                is_ringtone = 'ringtones' in filepath
                is_theme_sound = any(sound_type in filepath for sound_type in 
                                ['click', 'confirm', 'error', 'notify', 'startup'])
                
                current_time = time.time()
                
                # Защита от слишком частого воспроизведения
                if current_time - self.last_play_time < 0.1 and not is_ringtone:
                    logger.debug(f"Skipping audio play - too frequent")
                    return
                
                # Если уже играет длинный звук (рингтон), не прерываем
                if self.is_long_audio and mixer.music.get_busy():
                    if not is_ringtone:  # Новый звук не рингтон - не прерываем рингтон
                        logger.debug(f"Skipping audio play - ringtone is playing")
                        return
                
                # Останавливаем текущее воспроизведение
                if mixer.music.get_busy():
                    mixer.music.stop()
                    time.sleep(0.05)  # Короткая задержка для освобождения
                
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
                        
                    # Устанавливаем полную громкость для pygame
                    mixer.music.set_volume(1.0)
                    
                    logger.debug(f"🎵 Playing audio: {os.path.basename(filepath)} on {self.audio_device}")
                    
                except Exception as play_error:
                    logger.error(f"❌ Error during playback: {play_error}")
                    # Сбрасываем состояние при ошибке
                    self._reset_state()
                    return
            
        except Exception as e:
            logger.error(f"❌ AudioService play error: {e}")
            self._reset_state()
    def play_async(self, filepath, fadein=0):
        """Воспроизвести звук в отдельном потоке, чтобы не блокировать UI"""
        threading.Thread(
            target=self.play,
            args=(filepath,),
            kwargs={"fadein": fadein},
            daemon=True,
        ).start()

    def stop(self):
        """ИСПРАВЛЕНО: Остановка воспроизведения с проверкой mixer"""
        logger.debug(f"🛑 AudioService.stop() called")
        
        if not self.is_mixer_initialized():
            logger.debug("Mixer not initialized - clearing state only")
            self._reset_state()
            return
        
        try:
            with self._init_lock:
                if self.is_playing or mixer.music.get_busy():
                    mixer.music.stop()
                    time.sleep(0.05)  # Короткая задержка
        except Exception as e:
            logger.error(f"❌ AudioService stop error: {e}")
        finally:
            self._reset_state()

    def is_busy(self):
        """ИСПРАВЛЕНО: Проверка активности воспроизведения с проверкой mixer"""
        if not self.is_mixer_initialized():
            # Если mixer не инициализирован, сбрасываем состояние
            if self.is_playing:
                self._reset_state()
            return False
            
        try:
            busy = mixer.music.get_busy()
            # Синхронизируем состояние с pygame
            if not busy and self.is_playing:
                logger.debug(f"🔍 Pygame not busy but is_playing=True - syncing state")
                self._reset_state()
            return busy
        except Exception as e:
            logger.error(f"❌ AudioService is_busy error: {e}")
            self._reset_state()
            return False

    def _reset_state(self):
        """ДОБАВЛЕНО: Сброс внутреннего состояния"""
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False

    def get_device_info(self):
        """Получение информации об аудиоустройстве"""
        info = {
            "device": self.audio_device,
            "device_type": "usb" if "hw:" in str(self.audio_device) else "system_default",
            "alsa_available": ALSA_AVAILABLE,
            "mixer_initialized": self.is_mixer_initialized()
        }
        
        if ALSA_AVAILABLE:
            try:
                info["alsa_cards"] = alsaaudio.cards()
            except:
                info["alsa_cards"] = []
                
        # Добавляем информацию о текущих настройках pygame
        try:
            if self.is_mixer_initialized():
                init_result = mixer.get_init()
                if init_result:
                    freq, format_info, channels = init_result
                    info["pygame_settings"] = {
                        "frequency": freq,
                        "format": format_info,
                        "channels": channels
                    }
        except:
            info["pygame_settings"] = None
                
        return info

    def diagnose_state(self):
        """Диагностика состояния AudioService"""
        try:
            mixer_init = self.is_mixer_initialized()
            pygame_busy = mixer.music.get_busy() if mixer_init else False
            pygame_init = mixer.get_init() if mixer_init else None
            
            logger.info(f"🔧 === AUDIOSERVICE DIAGNOSIS ===")
            logger.info(f"mixer_initialized: {mixer_init}")
            logger.info(f"is_playing: {self.is_playing}")
            logger.info(f"current_file: {self.current_file}")
            logger.info(f"is_long_audio: {self.is_long_audio}")
            logger.info(f"last_play_time: {self.last_play_time}")
            logger.info(f"audio_device: {self.audio_device}")
            logger.info(f"pygame mixer.get_busy(): {pygame_busy}")
            logger.info(f"pygame mixer.get_init(): {pygame_init}")
            
            return {
                "mixer_initialized": mixer_init,
                "is_playing": self.is_playing,
                "current_file": self.current_file,
                "is_long_audio": self.is_long_audio,
                "pygame_busy": pygame_busy,
                "pygame_init": pygame_init,
                "audio_device": self.audio_device
            }
        except Exception as e:
            logger.error(f"Error in diagnose_state: {e}")
            return {"error": str(e)}

    def reinitialize_audio(self):
        """ИСПРАВЛЕНО: Переинициализация аудио системы"""
        logger.info("Reinitializing audio system...")
        
        # Останавливаем воспроизведение
        self.stop()
        
        # Переинициализируем
        self._safe_init_audio()
        
        # Возвращаем статус
        return self.is_mixer_initialized()

    def get_available_devices(self):
        """Получение списка доступных аудиоустройств"""
        devices = []
        
        if ALSA_AVAILABLE:
            try:
                cards = alsaaudio.cards()
                for i, card in enumerate(cards):
                    devices.append({
                        "name": card,
                        "device": f"hw:{i},0",
                        "index": i,
                        "type": "usb" if any(keyword in card.lower() 
                                           for keyword in ['usb', 'headset', 'device']) else "other"
                    })
            except Exception as e:
                logger.error(f"Error getting ALSA cards: {e}")
        
        # Добавляем системное устройство по умолчанию
        devices.append({
            "name": "System Default",
            "device": "system_default", 
            "index": -1,
            "type": "default"
        })
        
        return devices

    def switch_device(self, device_identifier):
        """Переключение на другое аудиоустройство"""
        logger.info(f"Switching audio device to: {device_identifier}")
        
        # Останавливаем текущее воспроизведение
        self.stop()
        
        # Переинициализируем с новым устройством
        with self._init_lock:
            self._safe_quit_mixer()
            
            try:
                if device_identifier == "system_default":
                    success = self._init_pygame_default()
                else:
                    success = self._init_pygame_with_device(device_identifier)
                
                self._mixer_initialized = success
                
                if success:
                    logger.info(f"Successfully switched to audio device: {self.audio_device}")
                else:
                    logger.error(f"Failed to switch to audio device: {device_identifier}")
                    # Fallback к системному аудио
                    if self._init_pygame_default():
                        self._mixer_initialized = True
                        logger.info("Fallback to system default audio successful")
                    
                return self._mixer_initialized
                    
            except Exception as e:
                logger.error(f"Error switching audio device: {e}")
                self._mixer_initialized = False
                return False


# Создаем глобальный экземпляр
audio_service = AudioService()