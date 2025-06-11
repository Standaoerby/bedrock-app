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
        """Инициализация аудиосистемы для USB audio устройств"""
        try:
            # Ищем USB аудиоустройства (dongle, карты)
            usb_device = self._find_usb_audio_device()
            
            if usb_device:
                logger.info(f"Found USB audio device: {usb_device}")
                if self._init_pygame_with_device(usb_device):
                    return
            
            # Fallback на системное аудио по умолчанию
            logger.info("Using system default audio device")
            self._init_pygame_default()
                
        except Exception as e:
            logger.error(f"Audio initialization error: {e}")
            # Fallback к базовой инициализации
            self._init_pygame_default()

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
                    'behringer',    # Behringer USB interfaces
                    'focusrite',    # Focusrite interfaces
                    'scarlett',     # Scarlett series
                    'audio-technica', # Audio-Technica
                    'spdif',        # S/PDIF devices
                    'device'        # Generic USB Audio Device
                ]
                
                # Ищем USB устройства по именам карт
                for i, card in enumerate(cards):
                    card_lower = card.lower()
                    for usb_name in usb_audio_names:
                        if usb_name in card_lower:
                            logger.info(f"Found USB audio card: {card} (index {i})")
                            # GS3 работает с обычным hw, а не plughw
                            return f"hw:{i},0"
                            
            # Альтернативный метод через /proc/asound/cards
            try:
                with open('/proc/asound/cards', 'r') as f:
                    cards_info = f.read()
                    logger.debug(f"ALSA cards info:\n{cards_info}")
                    
                    lines = cards_info.strip().split('\n')
                    for line in lines:
                        line_lower = line.lower()
                        # Ищем USB устройства в описании
                        if any(name in line_lower for name in ['usb', 'headset', 'device', 'gs3']):
                            # Извлекаем номер карты (первое число в строке)
                            parts = line.split()
                            if parts:
                                card_num = parts[0].rstrip(':')
                                if card_num.isdigit():
                                    logger.info(f"Found USB audio device in card {card_num}: {line.strip()}")
                                    return f"hw:{card_num},0"
                            
            except Exception as e:
                logger.warning(f"Could not read /proc/asound/cards: {e}")
                
        except Exception as e:
            logger.error(f"Error finding USB audio device: {e}")
            
        return None

    def _init_pygame_with_device(self, device):
        """Инициализация pygame с конкретным аудиоустройством"""
        try:
            # Настраиваем переменные окружения для SDL
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            os.environ['AUDIODEV'] = device
            
            # GS3 отлично работает на 48kHz (показал тест aplay)
            mixer.pre_init(
                frequency=48000,    # GS3 поддерживает 48kHz
                size=-16,           # 16-bit signed
                channels=2,         # Стерео
                buffer=1024         # Стандартный буфер для USB
            )
            
            mixer.init()
            
            # Тест воспроизведения
            if self._test_audio_output():
                logger.info(f"AudioService initialized with GS3 USB device: {device}")
                self.audio_device = device
                return True
            else:
                logger.warning("GS3 USB device test failed, falling back to default")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing pygame with GS3 USB audio: {e}")
            return False

    def _init_pygame_default(self):
        """Базовая инициализация pygame mixer для системного аудио по умолчанию"""
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
            logger.info("AudioService initialized with system default audio")
            self.audio_device = "system_default"
        except Exception as e:
            logger.error(f"Default audio initialization error: {e}")

    def _test_audio_output(self):
        """Тест аудиовыхода"""
        try:
            # Проверяем, что mixer инициализирован корректно
            init_result = mixer.get_init()
            if init_result is None:
                return False
                
            # Логируем параметры инициализации
            freq, format_info, channels = init_result
            logger.debug(f"Audio initialized: {freq}Hz, format={format_info}, channels={channels}")
            return True
            
        except Exception as e:
            logger.error(f"Audio test failed: {e}")
            return False

    def set_volume(self, value):
        """Установка громкости только через pygame"""
        try:
            volume = max(0.0, min(1.0, value))
            mixer.music.set_volume(volume)
            logger.debug(f"Set pygame volume to {volume} on device {self.audio_device}")
            
            # Pygame управляет только своей громкостью
            # Системная громкость управляется через VolumeService
                    
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
                # Системная громкость управляется VolumeService
                mixer.music.set_volume(1.0)
                
                logger.debug(f"🎵 Playing audio: {os.path.basename(filepath)} on {self.audio_device}")
                
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
            "device_type": "usb" if "hw:" in str(self.audio_device) else "system_default",
            "alsa_available": ALSA_AVAILABLE,
            "mixer_initialized": mixer.get_init() is not None
        }
        
        if ALSA_AVAILABLE:
            try:
                info["alsa_cards"] = alsaaudio.cards()
            except:
                info["alsa_cards"] = []
                
        # Добавляем информацию о текущих настройках pygame
        try:
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
            pygame_busy = mixer.music.get_busy()
            pygame_init = mixer.get_init()
            
            logger.info(f"🔧 === AUDIOSERVICE DIAGNOSIS (USB MODE) ===")
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
                "pygame_init": pygame_init,
                "audio_device": self.audio_device
            }
        except Exception as e:
            logger.error(f"Error in diagnose_state: {e}")
            return {"error": str(e)}

    def reinitialize_audio(self):
        """Переинициализация аудиосистемы"""
        logger.info("Reinitializing audio system for USB audio...")
        try:
            mixer.quit()
            time.sleep(0.1)  # Небольшая задержка для USB устройств
        except:
            pass
            
        self._init_audio()

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
        
        # Закрываем mixer
        try:
            mixer.quit()
        except:
            pass
            
        # Переинициализируем с новым устройством
        try:
            if device_identifier == "system_default":
                self._init_pygame_default()
            else:
                self._init_pygame_with_device(device_identifier)
            
            logger.info(f"Successfully switched to audio device: {self.audio_device}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching audio device: {e}")
            # Fallback к системному аудио
            self._init_pygame_default()
            return False


# Создаем глобальный экземпляр
audio_service = AudioService()