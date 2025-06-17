# services/audio_service.py
# ИСПРАВЛЕНО: Убран глобальный экземпляр, улучшена диагностика, исправлены ошибки

import os
import time
import threading
import inspect  # 🚨 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Добавлен отсутствующий импорт
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
    """
    ИСПРАВЛЕНО: Сервис для воспроизведения аудио с поддержкой USB устройств
    Включает диагностику, thread-safety и правильную обработку ошибок
    """
    
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False
        self.last_play_time = 0
        self._is_stopped = False
        self.audio_device = None
        self._mixer_initialized = False
        self._init_lock = threading.Lock()
        
        # ДОБАВЛЕНО: Версионирование и отслеживание экземпляров
        self._service_version = "2.1.0"
        self._instance_id = id(self)
        
        logger.info(f"AudioService v{self._service_version} initializing (ID: {self._instance_id})")
        
        # Инициализируем аудиосистему с проверкой
        self._safe_init_audio()
        
        logger.info(f"AudioService initialization complete. Mixer initialized: {self._mixer_initialized}")

    def _safe_init_audio(self):
        """Безопасная инициализация аудиосистемы"""
        with self._init_lock:
            try:
                self._safe_quit_mixer()
                
                # Пробуем найти USB аудиоустройство
                usb_device = self._find_usb_audio_device()
                
                if usb_device:
                    success = self._init_pygame_with_device(usb_device)
                    if success:
                        logger.info(f"AudioService initialized with USB device: {usb_device}")
                        self._mixer_initialized = True
                        return
                
                # Fallback к системному аудио
                success = self._init_pygame_default()
                if success:
                    logger.info("AudioService initialized with system default audio")
                    self._mixer_initialized = True
                else:
                    logger.error("Failed to initialize any audio system")
                    self._mixer_initialized = False
                    
            except Exception as e:
                logger.error(f"Error initializing audio system: {e}")
                self._mixer_initialized = False

    def _find_usb_audio_device(self):
        """Поиск USB аудиоустройства через ALSA"""
        if not ALSA_AVAILABLE:
            return None
            
        try:
            cards = alsaaudio.cards()
            logger.info(f"Available ALSA cards: {cards}")
            
            # Ищем USB аудиоустройства (исключаем HDMI)
            usb_cards = []
            for card in cards:
                if any(usb_indicator in card.lower() for usb_indicator in ['usb', 'gs3', 'dac', 'headphone']):
                    if 'hdmi' not in card.lower():
                        usb_cards.append(card)
                        logger.info(f"Found potential USB audio device: {card}")
            
            if usb_cards:
                # Пробуем найти конкретное устройство
                for i, card in enumerate(cards):
                    if card in usb_cards:
                        device_name = f"hw:{i},0"
                        logger.info(f"Found USB audio device: {device_name}")
                        return device_name
                        
        except Exception as e:
            logger.warning(f"Error finding USB audio device: {e}")
            
        return None

    def _init_pygame_with_device(self, device):
        """Инициализация pygame с конкретным устройством"""
        try:
            import os
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            os.environ['AUDIODEV'] = device
            
            mixer.pre_init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=1024
            )
            mixer.init()
            
            self.audio_device = device
            logger.info(f"Pygame mixer initialized with device: {device}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to initialize pygame with device {device}: {e}")
            return False

    def _init_pygame_default(self):
        """Инициализация pygame с системными настройками по умолчанию"""
        try:
            mixer.pre_init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=1024
            )
            mixer.init()
            
            self.audio_device = "system_default"
            logger.info("Pygame mixer initialized with system default")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pygame with default settings: {e}")
            return False

    def _safe_quit_mixer(self):
        """Безопасное завершение работы mixer"""
        try:
            if mixer.get_init():
                mixer.quit()
                time.sleep(0.1)  # Небольшая задержка для освобождения ресурсов
        except Exception as e:
            logger.debug(f"Error quitting mixer (expected during startup): {e}")

    def is_mixer_initialized(self):
        """Проверка инициализации mixer"""
        try:
            return self._mixer_initialized and mixer.get_init() is not None
        except Exception:
            self._mixer_initialized = False
            return False

    def diagnose_state(self):
        """Диагностика состояния AudioService"""
        try:
            mixer_init = self.is_mixer_initialized()
            pygame_busy = mixer.music.get_busy() if mixer_init else False
            pygame_init = mixer.get_init() if mixer_init else None
            
            # Только один лог INFO для общего статуса
            logger.info(f"🔧 === AUDIOSERVICE DIAGNOSIS v{self._service_version} ===")
            
            # Остальные детали в DEBUG
            logger.debug(f"instance_id: {self._instance_id}")
            logger.debug(f"service_version: {self._service_version}")
            logger.debug(f"mixer_initialized: {mixer_init}")
            logger.debug(f"is_playing: {self.is_playing}")
            logger.debug(f"current_file: {self.current_file}")
            logger.debug(f"is_long_audio: {self.is_long_audio}")
            logger.debug(f"last_play_time: {self.last_play_time}")
            logger.debug(f"audio_device: {self.audio_device}")
            logger.debug(f"pygame mixer.get_busy(): {pygame_busy}")
            logger.debug(f"pygame mixer.get_init(): {pygame_init}")
            
            return {
                "instance_id": self._instance_id,
                "service_version": self._service_version,
                "mixer_initialized": mixer_init,
                "is_playing": self.is_playing,
                "current_file": self.current_file,
                "is_long_audio": self.is_long_audio,
                "pygame_busy": pygame_busy,
                "pygame_init": pygame_init,
                "audio_device": self.audio_device,
                "alsa_available": ALSA_AVAILABLE
            }
        except Exception as e:
            logger.error(f"Error in diagnose_state: {e}")
            return {"error": str(e), "instance_id": self._instance_id}


    def verify_instance(self):
        """НОВОЕ: Верификация экземпляра AudioService"""
        return {
            "class_name": self.__class__.__name__,
            "instance_id": self._instance_id,
            "service_version": getattr(self, '_service_version', 'unknown'),
            "has_diagnose_state": hasattr(self, 'diagnose_state'),
            "has_play": hasattr(self, 'play'),
            "has_stop": hasattr(self, 'stop'),
            "methods": [method for method in dir(self) if not method.startswith('_')]
        }

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
                is_theme_sound = any(sound_type in filepath for sound_type in ['ui', 'click', 'error', 'success'])
                
                # Определяем тип аудио для правильной обработки
                file_size = os.path.getsize(filepath)
                self.is_long_audio = file_size > 1024 * 1024  # Больше 1MB считаем длинным
                
                logger.debug(f"Playing audio: {os.path.basename(filepath)}, "
                           f"fadein={fadein}, long_audio={self.is_long_audio}")
                
                # Останавливаем предыдущее воспроизведение
                if mixer.music.get_busy():
                    mixer.music.stop()
                    time.sleep(0.05)
                
                # Загружаем и воспроизводим файл
                mixer.music.load(filepath)
                
                # Применяем fadein если нужно
                if fadein > 0:
                    mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
                else:
                    mixer.music.play(loops=0)
                
                # Обновляем состояние
                self.is_playing = True
                self.current_file = filepath
                self.last_play_time = time.time()
                
                logger.info(f"✅ Started playing: {os.path.basename(filepath)}")
                
        except Exception as e:
            logger.error(f"❌ AudioService play error: {e}")
            self._reset_state()

    def play_async(self, filepath, fadein=0):
        """ИСПРАВЛЕНО: Асинхронное воспроизведение через поток"""
        threading.Thread(
            target=self.play,
            args=(filepath,),
            kwargs={"fadein": fadein},
            daemon=True,
        ).start()
        
    def play_loop(self, filepath, fadein=0):
        """НОВОЕ: Воспроизведение в цикле для будильников"""
        if not filepath or not os.path.isfile(filepath):
            logger.warning(f"Audio file not found: {filepath}")
            return
            
        if not self.is_mixer_initialized():
            logger.error("❌ AudioService play_loop error: mixer not initialized")
            self._safe_init_audio()
            
            if not self.is_mixer_initialized():
                logger.error("❌ AudioService: Failed to reinitialize mixer")
                return
            
        try:
            with self._init_lock:
                file_size = os.path.getsize(filepath)
                self.is_long_audio = file_size > 1024 * 1024
                
                logger.debug(f"Playing audio in loop: {os.path.basename(filepath)}, fadein={fadein}")
                
                # Останавливаем предыдущее воспроизведение
                if mixer.music.get_busy():
                    mixer.music.stop()
                    time.sleep(0.05)
                
                # Загружаем и воспроизводим в цикле
                mixer.music.load(filepath)
                
                # ИСПРАВЛЕНО: loops=-1 для бесконечного цикла
                if fadein > 0:
                    mixer.music.play(loops=-1, fade_ms=int(fadein * 1000))
                else:
                    mixer.music.play(loops=-1)
                
                # Обновляем состояние
                self.is_playing = True
                self.current_file = filepath
                self.last_play_time = time.time()
                
                logger.info(f"✅ Started playing in loop: {os.path.basename(filepath)}")
                
        except Exception as e:
            logger.error(f"❌ AudioService play_loop error: {e}")
            self._reset_state()

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
            "mixer_initialized": self.is_mixer_initialized(),
            "alsa_available": ALSA_AVAILABLE
        }
        
        if self.is_mixer_initialized():
            try:
                info.update({
                    "pygame_init": mixer.get_init(),
                    "pygame_busy": mixer.music.get_busy()
                })
            except Exception as e:
                info["pygame_error"] = str(e)
                
        return info

    def reinitialize_audio(self):
        """ДОБАВЛЕНО: Переинициализация аудиосистемы"""
        logger.info("Reinitializing audio system...")
        self._safe_init_audio()
        return self.is_mixer_initialized()

    def get_available_devices(self):
        """ДОБАВЛЕНО: Получение списка доступных аудиоустройств"""
        devices = []
        
        if ALSA_AVAILABLE:
            try:
                cards = alsaaudio.cards()
                for i, card in enumerate(cards):
                    devices.append({
                        "name": card,
                        "device": f"hw:{i},0",
                        "index": i,
                        "type": "alsa"
                    })
            except Exception as e:
                logger.warning(f"Error getting ALSA devices: {e}")
        
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


# ИСПРАВЛЕНО: НЕ создаем глобальный экземпляр
# Каждое приложение должно создать свой экземпляр AudioService через main.py

def validate_audio_service_module():
    """Валидация модуля AudioService для отладки"""
    try:
        service = AudioService()
        assert hasattr(service, 'diagnose_state'), "diagnose_state method missing"
        assert hasattr(service, 'play'), "play method missing"
        assert hasattr(service, 'stop'), "stop method missing"
        assert hasattr(service, 'verify_instance'), "verify_instance method missing"
        print("✅ AudioService module validation passed")
        return True
    except Exception as e:
        print(f"❌ AudioService module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_audio_service_module()