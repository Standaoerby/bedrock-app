"""
Volume Control Service for USB Audio devices
Handles GPIO button presses and system volume control for USB dongles/cards
ИСПРАВЛЕНО: Убрана циклическая зависимость, оптимизирован для USB audio
"""
import time
import subprocess
import threading
import re
from threading import Thread, Lock
from app.logger import app_logger as logger

# GPIO pins for volume buttons
VOLUME_UP_PIN = 23
VOLUME_DOWN_PIN = 24

# Volume control settings
MIN_VOLUME = 0
MAX_VOLUME = 100
VOLUME_STEP = 5
DEBOUNCE_TIME = 0.2  # seconds

# USB Audio миксеры (в порядке приоритета для GS3)
USB_MIXER_PRIORITIES = [
    'PCM',              # Основной для GS3 и других USB устройств
    'Master',           # Fallback для некоторых USB карт
    'Speaker',          # USB speakers
    'Headphone',        # USB headphones/headsets  
    'USB Audio',        # Generic USB Audio
    'Digital',          # USB Digital out
    'Line Out',         # USB audio interfaces
    'Playback',         # Alternative naming
    'Front'             # Multi-channel USB devices
]

# GPIO imports with error handling
try:
    import lgpio
    LGPIO_AVAILABLE = True
except ImportError:
    LGPIO_AVAILABLE = False
    lgpio = None

try:
    import RPi.GPIO as RPi_GPIO
    RPI_GPIO_AVAILABLE = True  
except ImportError:
    RPI_GPIO_AVAILABLE = False
    RPi_GPIO = None

# ALSA imports
try:
    import alsaaudio
    ALSA_AVAILABLE = True
except ImportError:
    ALSA_AVAILABLE = False
    alsaaudio = None


class VolumeControlService:
    """Service for handling physical volume control buttons with USB audio support"""
    
    def __init__(self):
        """Initialize volume control service"""
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        
        # GPIO setup
        self.gpio_available = False
        self.gpio_lib = None
        self.gpio_handle = None
        
        # USB Audio миксер автоопределение
        self._available_mixers = []
        self._active_mixer = None
        self._mixer_card = 0
        self._usb_cards = []  # Список USB аудиокарт
        
        # Volume state
        self._current_volume = 50
        self._volume_lock = Lock()
        
        # Button state tracking для дебаунсинга
        self._last_button_time = {VOLUME_UP_PIN: 0, VOLUME_DOWN_PIN: 0}
        self._last_button_state = {VOLUME_UP_PIN: True, VOLUME_DOWN_PIN: True}
        
        # Callback events
        self._volume_change_callback = None
        
        # Инициализируем USB аудио систему
        self._init_usb_audio_system()
        
        logger.info(f"VolumeControlService initialized - Current volume: {self._current_volume}% (USB mixer: {self._active_mixer})")
    
    def _init_usb_audio_system(self):
        """Инициализация и автоопределение USB аудио миксеров"""
        try:
            # Находим USB аудиокарты
            self._discover_usb_cards()
            
            # Находим доступные миксеры на USB картах
            self._discover_usb_mixers()
            
            # Выбираем лучший USB миксер
            self._select_best_usb_mixer()
            
            # Получаем текущую громкость
            self._current_volume = self._get_system_volume()
            
            logger.info(f"USB Audio system initialized - USB cards: {len(self._usb_cards)}, Active mixer: {self._active_mixer}")
            
        except Exception as e:
            logger.error(f"Error initializing USB audio system: {e}")
            # Fallback на системные миксеры
            self._fallback_to_system_mixers()
    
    def _discover_usb_cards(self):
        """Поиск USB аудиокарт в системе"""
        self._usb_cards = []
        
        if not ALSA_AVAILABLE:
            logger.warning("ALSA not available - cannot detect USB audio cards")
            return
            
        try:
            # Получаем все доступные ALSA карты
            all_cards = alsaaudio.cards()
            logger.debug(f"All ALSA cards: {all_cards}")
            
            # Ищем USB аудиокарты по именам
            usb_keywords = [
                'gs3',              # Ваше устройство
                'usb', 'headset', 'webcam', 'plantronics', 'logitech', 
                'creative', 'behringer', 'focusrite', 'scarlett', 
                'audio-technica', 'spdif', 'device', 'external'
            ]
            
            for i, card_name in enumerate(all_cards):
                card_lower = card_name.lower()
                
                # Проверяем, является ли карта USB устройством
                is_usb = any(keyword in card_lower for keyword in usb_keywords)
                
                if is_usb:
                    self._usb_cards.append({
                        'index': i,
                        'name': card_name,
                        'device': f'hw:{i}'
                    })
                    logger.info(f"Found USB audio card {i}: {card_name}")
            
            # Дополнительная проверка через /proc/asound/cards
            try:
                with open('/proc/asound/cards', 'r') as f:
                    cards_info = f.read()
                    
                lines = cards_info.strip().split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in usb_keywords):
                        # Извлекаем номер карты
                        parts = line.split()
                        if parts:
                            card_num_str = parts[0].rstrip(':')
                            if card_num_str.isdigit():
                                card_num = int(card_num_str)
                                
                                # Проверяем, не добавили ли уже эту карту
                                if not any(card['index'] == card_num for card in self._usb_cards):
                                    card_name = ' '.join(parts[2:]) if len(parts) > 2 else f"USB Card {card_num}"
                                    self._usb_cards.append({
                                        'index': card_num,
                                        'name': card_name,
                                        'device': f'hw:{card_num}'
                                    })
                                    logger.info(f"Found additional USB audio card {card_num}: {card_name}")
                                    
            except Exception as e:
                logger.debug(f"Could not read /proc/asound/cards: {e}")
                
            logger.info(f"Discovered {len(self._usb_cards)} USB audio card(s)")
            
        except Exception as e:
            logger.error(f"Error discovering USB cards: {e}")
    
    def _discover_usb_mixers(self):
        """Поиск доступных миксеров на USB аудиокартах"""
        self._available_mixers = []
        
        if not ALSA_AVAILABLE or not self._usb_cards:
            logger.warning("Cannot discover USB mixers - no ALSA or no USB cards found")
            return
            
        # Проверяем миксеры на каждой USB карте
        for usb_card in self._usb_cards:
            card_index = usb_card['index']
            card_name = usb_card['name']
            
            logger.debug(f"Checking mixers on USB card {card_index}: {card_name}")
            
            try:
                # Получаем список миксеров для этой карты
                mixers = alsaaudio.mixers(cardindex=card_index)
                
                for mixer_name in mixers:
                    try:
                        # Проверяем, что миксер работает
                        mixer = alsaaudio.Mixer(mixer_name, cardindex=card_index)
                        
                        # Проверяем наличие volume контроля
                        if hasattr(mixer, 'getvolume'):
                            volumes = mixer.getvolume()
                            if volumes:  # Если миксер возвращает громкость
                                self._available_mixers.append({
                                    'name': mixer_name,
                                    'card_index': card_index,
                                    'card_name': card_name,
                                    'device': f'hw:{card_index}',
                                    'current_volume': volumes[0] if volumes else 50
                                })
                                logger.debug(f"Found working mixer '{mixer_name}' on USB card {card_index}")
                        
                        mixer.close()
                        
                    except Exception as mixer_error:
                        logger.debug(f"Mixer '{mixer_name}' on card {card_index} not accessible: {mixer_error}")
                        
            except Exception as card_error:
                logger.debug(f"Cannot access mixers on USB card {card_index}: {card_error}")
        
        logger.info(f"Found {len(self._available_mixers)} working USB audio mixer(s)")
        for mixer in self._available_mixers:
            logger.debug(f"  - {mixer['name']} on {mixer['card_name']} (card {mixer['card_index']})")
    
    def _select_best_usb_mixer(self):
        """Выбор лучшего USB миксера из доступных"""
        if not self._available_mixers:
            logger.warning("No USB audio mixers found")
            return False
            
        # Ищем миксер с наивысшим приоритетом
        for priority_mixer in USB_MIXER_PRIORITIES:
            for mixer in self._available_mixers:
                if mixer['name'].lower() == priority_mixer.lower():
                    self._active_mixer = mixer
                    self._mixer_card = mixer['card_index']
                    logger.info(f"Selected USB mixer: '{mixer['name']}' on card {mixer['card_index']} ({mixer['card_name']})")
                    return True
        
        # Если приоритетный не найден, берём первый доступный
        if self._available_mixers:
            mixer = self._available_mixers[0]
            self._active_mixer = mixer
            self._mixer_card = mixer['card_index']
            logger.info(f"Using first available USB mixer: '{mixer['name']}' on card {mixer['card_index']}")
            return True
            
        return False
    
    def _fallback_to_system_mixers(self):
        """Fallback на системные миксеры если USB не найдены"""
        logger.info("Falling back to system audio mixers")
        
        if not ALSA_AVAILABLE:
            logger.error("ALSA not available - volume control disabled")
            return
            
        try:
            # Пробуем системные миксеры на карте 0
            mixers = alsaaudio.mixers(cardindex=0)
            
            for priority_mixer in ['Master', 'PCM', 'Speaker', 'Headphone']:
                if priority_mixer in mixers:
                    try:
                        mixer = alsaaudio.Mixer(priority_mixer, cardindex=0)
                        volumes = mixer.getvolume()
                        mixer.close()
                        
                        if volumes:
                            self._active_mixer = {
                                'name': priority_mixer,
                                'card_index': 0,
                                'card_name': 'System Default',
                                'device': 'hw:0',
                                'current_volume': volumes[0]
                            }
                            self._mixer_card = 0
                            logger.info(f"Using system mixer: '{priority_mixer}' on default card")
                            return
                            
                    except Exception as e:
                        logger.debug(f"System mixer '{priority_mixer}' not working: {e}")
                        
        except Exception as e:
            logger.error(f"Error accessing system mixers: {e}")
    
    def _get_system_volume(self):
        """Получение текущей системной громкости с USB аудио"""
        if not self._active_mixer or not ALSA_AVAILABLE:
            return 50  # Default fallback
            
        try:
            mixer = alsaaudio.Mixer(
                self._active_mixer['name'], 
                cardindex=self._active_mixer['card_index']
            )
            
            volumes = mixer.getvolume()
            mixer.close()
            
            if volumes:
                volume = volumes[0]  # Берём первый канал
                logger.debug(f"Current USB audio volume: {volume}%")
                return volume
            else:
                logger.warning("No volume data from USB mixer")
                return 50
                
        except Exception as e:
            logger.error(f"Error getting USB audio volume: {e}")
            return 50
    
    def _set_system_volume(self, volume):
        """Установка системной громкости для USB аудио"""
        if not self._active_mixer or not ALSA_AVAILABLE:
            logger.warning("Cannot set USB audio volume - no active mixer")
            return False
            
        try:
            volume = max(MIN_VOLUME, min(MAX_VOLUME, int(volume)))
            
            mixer = alsaaudio.Mixer(
                self._active_mixer['name'], 
                cardindex=self._active_mixer['card_index']
            )
            
            # Устанавливаем громкость на все каналы
            mixer.setvolume(volume)
            mixer.close()
            
            logger.debug(f"Set USB audio volume to {volume}% on mixer '{self._active_mixer['name']}'")
            return True
            
        except Exception as e:
            logger.error(f"Error setting USB audio volume: {e}")
            return False
    
    def start(self):
        """Запуск сервиса управления громкостью"""
        if self.running:
            logger.warning("VolumeControlService already running")
            return
            
        logger.info("Starting USB Volume Control Service...")
        
        # Инициализируем GPIO если доступен
        if self._init_gpio():
            logger.info("GPIO initialized for volume buttons")
        else:
            logger.info("GPIO not available - software volume control only")
            
        self.running = True
        self._stop_event.clear()
        
        # Запускаем поток мониторинга кнопок (если GPIO доступен)
        if self.gpio_available:
            self.thread = Thread(target=self._monitor_buttons, daemon=True)
            self.thread.start()
            logger.info("Volume button monitoring started")
        else:
            logger.info("Volume service started in software-only mode")
    
    def stop(self):
        """Остановка сервиса"""
        if not self.running:
            return
            
        logger.info("Stopping USB Volume Control Service...")
        
        self.running = False
        self._stop_event.set()
        
        # Ждём завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        # Очищаем GPIO
        self._cleanup_gpio()
        
        logger.info("Volume Control Service stopped")
    
    def _init_gpio(self):
        """Инициализация GPIO для кнопок громкости"""
        # Пробуем lgpio
        if LGPIO_AVAILABLE:
            try:
                self.gpio_handle = lgpio.gpiochip_open(0)
                
                # Настраиваем пины как входы с подтяжкой
                lgpio.gpio_claim_input(self.gpio_handle, VOLUME_UP_PIN, lgpio.SET_PULL_UP)
                lgpio.gpio_claim_input(self.gpio_handle, VOLUME_DOWN_PIN, lgpio.SET_PULL_UP)
                
                self.gpio_available = True
                self.gpio_lib = 'lgpio'
                logger.info(f"GPIO initialized with lgpio - pins {VOLUME_UP_PIN}/{VOLUME_DOWN_PIN}")
                return True
                
            except Exception as e:
                logger.error(f"lgpio initialization failed: {e}")
                if self.gpio_handle:
                    try:
                        lgpio.gpiochip_close(self.gpio_handle)
                    except:
                        pass
                    self.gpio_handle = None
        
        # Пробуем RPi.GPIO как fallback
        if RPI_GPIO_AVAILABLE:
            try:
                RPi_GPIO.setmode(RPi_GPIO.BCM)
                RPi_GPIO.setup(VOLUME_UP_PIN, RPi_GPIO.IN, pull_up_down=RPi_GPIO.PUD_UP)
                RPi_GPIO.setup(VOLUME_DOWN_PIN, RPi_GPIO.IN, pull_up_down=RPi_GPIO.PUD_UP)
                
                self.gpio_available = True
                self.gpio_lib = 'RPi.GPIO'
                logger.info(f"GPIO initialized with RPi.GPIO - pins {VOLUME_UP_PIN}/{VOLUME_DOWN_PIN}")
                return True
                
            except Exception as e:
                logger.error(f"RPi.GPIO initialization failed: {e}")
                try:
                    RPi_GPIO.cleanup()
                except:
                    pass
        
        logger.warning("No GPIO library available - volume buttons disabled")
        return False
    
    def _cleanup_gpio(self):
        """Очистка GPIO ресурсов"""
        if not self.gpio_available:
            return
            
        try:
            if self.gpio_lib == 'lgpio' and self.gpio_handle is not None:
                lgpio.gpio_free(self.gpio_handle, VOLUME_UP_PIN)
                lgpio.gpio_free(self.gpio_handle, VOLUME_DOWN_PIN)
                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None
                
            elif self.gpio_lib == 'RPi.GPIO':
                RPi_GPIO.cleanup()
                
            logger.debug("GPIO resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")
        finally:
            self.gpio_available = False
            self.gpio_lib = None
    
    def _monitor_buttons(self):
        """Мониторинг нажатий кнопок громкости"""
        logger.debug("Starting volume button monitoring...")
        
        while self.running and not self._stop_event.is_set():
            try:
                # Проверяем состояния кнопок
                self._check_button(VOLUME_UP_PIN, 'up')
                self._check_button(VOLUME_DOWN_PIN, 'down')
                
                time.sleep(0.05)  # 50ms polling
                
            except Exception as e:
                logger.error(f"Error in button monitoring: {e}")
                time.sleep(0.1)
                
        logger.debug("Volume button monitoring stopped")
    
    def _check_button(self, pin, action):
        """Проверка состояния кнопки с дебаунсингом"""
        try:
            # Читаем состояние пина
            if self.gpio_lib == 'lgpio':
                current_state = lgpio.gpio_read(self.gpio_handle, pin)
            else:  # RPi.GPIO
                current_state = RPi_GPIO.input(pin)
            
            # Кнопка нажата при LOW (из-за pull-up)
            button_pressed = (current_state == 0)
            last_state = not self._last_button_state[pin]  # Инвертируем для логики
            
            current_time = time.time()
            
            # Проверяем изменение состояния с дебаунсингом
            if (button_pressed and not last_state and 
                current_time - self._last_button_time[pin] > DEBOUNCE_TIME):
                
                self._last_button_time[pin] = current_time
                self._handle_volume_button(action)
            
            self._last_button_state[pin] = not button_pressed  # Сохраняем инвертированное
            
        except Exception as e:
            logger.error(f"Error checking button {pin}: {e}")
    
    def _handle_volume_button(self, action):
        """Обработка нажатия кнопки громкости"""
        try:
            with self._volume_lock:
                current_volume = self._get_system_volume()
                
                if action == 'up':
                    new_volume = min(MAX_VOLUME, current_volume + VOLUME_STEP)
                else:  # down
                    new_volume = max(MIN_VOLUME, current_volume - VOLUME_STEP)
                
                if new_volume != current_volume:
                    if self._set_system_volume(new_volume):
                        self._current_volume = new_volume
                        logger.info(f"USB Audio volume {action}: {new_volume}%")
                        
                        # Вызываем callback если установлен
                        if self._volume_change_callback:
                            try:
                                self._volume_change_callback(new_volume, action)
                            except Exception as callback_error:
                                logger.error(f"Volume change callback error: {callback_error}")
                
        except Exception as e:
            logger.error(f"Error handling volume button {action}: {e}")
    
    def set_volume(self, volume):
        """Программная установка громкости"""
        try:
            with self._volume_lock:
                if self._set_system_volume(volume):
                    self._current_volume = volume
                    logger.info(f"USB Audio volume set to: {volume}%")
                    
                    # Вызываем callback
                    if self._volume_change_callback:
                        try:
                            self._volume_change_callback(volume, 'set')
                        except Exception as callback_error:
                            logger.error(f"Volume change callback error: {callback_error}")
                    
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    def get_volume(self):
        """Получение текущей громкости"""
        try:
            with self._volume_lock:
                self._current_volume = self._get_system_volume()
                return self._current_volume
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return self._current_volume
    
    def set_volume_change_callback(self, callback):
        """Установка callback для изменения громкости"""
        self._volume_change_callback = callback
        logger.debug("Volume change callback set")
    
    def get_status(self):
        """Получение статуса сервиса"""
        return {
            'running': self.running,
            'gpio_available': self.gpio_available,
            'gpio_library': self.gpio_lib,
            'current_volume': self._current_volume,
            'active_mixer': self._active_mixer['name'] if self._active_mixer else None,
            'mixer_card': self._mixer_card,
            'usb_cards_count': len(self._usb_cards),
            'available_mixers_count': len(self._available_mixers),
            'button_pins': {
                'volume_up': VOLUME_UP_PIN,
                'volume_down': VOLUME_DOWN_PIN
            },
            'alsa_available': ALSA_AVAILABLE,
            'usb_cards': self._usb_cards,
            'available_mixers': self._available_mixers
        }
    
    def diagnose_audio_system(self):
        """Диагностика USB аудио системы"""
        logger.info("🔧 === USB AUDIO SYSTEM DIAGNOSIS ===")
        
        status = self.get_status()
        
        logger.info(f"ALSA available: {status['alsa_available']}")
        logger.info(f"USB cards found: {status['usb_cards_count']}")
        logger.info(f"Available mixers: {status['available_mixers_count']}")
        logger.info(f"Active mixer: {status['active_mixer']} on card {status['mixer_card']}")
        logger.info(f"Current volume: {status['current_volume']}%")
        logger.info(f"GPIO available: {status['gpio_available']} ({status['gpio_library']})")
        
        # Детальная информация о USB картах
        for i, card in enumerate(self._usb_cards):
            logger.info(f"USB Card {i}: {card['name']} (index {card['index']})")
            
        # Детальная информация о миксерах
        for i, mixer in enumerate(self._available_mixers):
            logger.info(f"Mixer {i}: {mixer['name']} on card {mixer['card_index']} ({mixer['card_name']})")
        
        return status
    
    def refresh_audio_devices(self):
        """Обновление списка USB аудиоустройств"""
        logger.info("Refreshing USB audio devices...")
        
        # Сохраняем текущие настройки
        old_mixer = self._active_mixer
        
        # Переинициализируем систему
        self._init_usb_audio_system()
        
        # Проверяем, изменился ли активный миксер
        if old_mixer and self._active_mixer:
            if (old_mixer['name'] != self._active_mixer['name'] or 
                old_mixer['card_index'] != self._active_mixer['card_index']):
                logger.info(f"Active USB mixer changed: {old_mixer['name']} -> {self._active_mixer['name']}")
        
        return self.get_status()


# Создаем глобальный экземпляр (НЕ автозапускаем)
volume_service = VolumeControlService()