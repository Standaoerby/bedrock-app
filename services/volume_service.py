"""
Volume Control Service for USB Audio devices
ИСПРАВЛЕНО: Убрана циклическая зависимость, улучшена архитектура, безопасность GPIO
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
    """ИСПРАВЛЕНО: Service for handling physical volume control buttons with USB audio support"""
    
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
        self._last_button_state = {VOLUME_UP_PIN: 1, VOLUME_DOWN_PIN: 1}
        
        # Callback events
        self._volume_change_callback = None
        
        # ДОБАВЛЕНО: Версионирование и отслеживание экземпляров
        self._service_version = "2.1.0"
        self._instance_id = id(self)
        
        logger.info(f"VolumeControlService v{self._service_version} initializing (ID: {self._instance_id})")
        
        # Инициализируем систему
        self._init_usb_audio_system()
        self._init_gpio_system()
        
        
        logger.info(f"VolumeControlService initialization complete")
        if self.gpio_available:
            logger.info("🔘 GPIO available - auto-starting button monitoring")
            self.start()
        else:
            logger.info("🔘 GPIO not available - starting in software-only mode")
            self.running = True

    def _init_usb_audio_system(self):
        """ИСПРАВЛЕНО: Инициализация USB аудио системы с детальным логированием"""
        try:
            if not ALSA_AVAILABLE:
                logger.warning("ALSA not available - volume control disabled")
                return
                
            # Находим USB аудиокарты
            self._find_usb_audio_cards()
            
            # Находим доступные миксеры для USB карт
            self._find_available_mixers()
            
            # Выбираем лучший миксер
            self._select_best_mixer()
            
            # Читаем текущую громкость
            self._read_current_volume()
            
            logger.info(f"USB Audio system initialized. "
                       f"Active mixer: {self._active_mixer['name'] if self._active_mixer else 'None'}")
            
        except Exception as e:
            logger.error(f"Error initializing USB audio system: {e}")
            self._active_mixer = None

    def _find_usb_audio_cards(self):
        """Поиск USB аудиокарт в системе"""
        self._usb_cards = []
        
        if not ALSA_AVAILABLE:
            return
        
        try:
            cards = alsaaudio.cards()
            logger.info(f"Available ALSA cards: {cards}")
            
            for i, card_name in enumerate(cards):
                # Определяем USB карты по названию
                if any(usb_keyword in card_name.lower() 
                      for usb_keyword in ['usb', 'headset', 'webcam', 'gs3', 'dongle']):
                    
                    self._usb_cards.append({
                        'name': card_name,
                        'index': i
                    })
                    logger.info(f"Found USB audio card: {card_name} (index {i})")
            
            if not self._usb_cards:
                logger.info("No USB audio cards found, checking all cards")
                # Fallback: добавляем все карты кроме первой (обычно встроенная)
                for i, card_name in enumerate(cards[1:], 1):
                    self._usb_cards.append({
                        'name': card_name,
                        'index': i
                    })
                    
        except Exception as e:
            logger.error(f"Error finding USB audio cards: {e}")

    def _find_available_mixers(self):
        """Поиск доступных миксеров для USB карт"""
        self._available_mixers = []
        
        if not ALSA_AVAILABLE:
            return
        
        # Проверяем миксеры для каждой USB карты
        for card in self._usb_cards:
            card_index = card['index']
            card_name = card['name']
            
            try:
                # Получаем список миксеров для карты
                mixers = alsaaudio.mixers(cardindex=card_index)
                logger.debug(f"Card {card_name} mixers: {mixers}")
                
                for mixer_name in mixers:
                    try:
                        # Пытаемся создать mixer объект для проверки
                        mixer_obj = alsaaudio.Mixer(mixer_name, cardindex=card_index)
                        
                        # Проверяем что у миксера есть volume control
                        if hasattr(mixer_obj, 'getvolume'):
                            volumes = mixer_obj.getvolume()
                            if volumes:  # Есть channels с volume
                                self._available_mixers.append({
                                    'name': mixer_name,
                                    'card_index': card_index,
                                    'card_name': card_name,
                                    'channels': len(volumes)
                                })
                                logger.debug(f"Added mixer: {mixer_name} on {card_name}")
                        
                    except Exception as mixer_error:
                        logger.debug(f"Mixer {mixer_name} not suitable: {mixer_error}")
                        
            except Exception as card_error:
                logger.error(f"Error checking mixers for card {card_name}: {card_error}")

    def _select_best_mixer(self):
        """Выбор лучшего миксера на основе приоритетов"""
        self._active_mixer = None
        
        if not self._available_mixers:
            logger.warning("No suitable mixers found")
            return
        
        # Сортируем миксеры по приоритету
        for priority_name in USB_MIXER_PRIORITIES:
            for mixer in self._available_mixers:
                if mixer['name'] == priority_name:
                    self._active_mixer = mixer
                    self._mixer_card = mixer['card_index']
                    logger.info(f"Selected mixer: {mixer['name']} on card {mixer['card_name']}")
                    return
        
        # Если не найден приоритетный, берем первый доступный
        if self._available_mixers:
            self._active_mixer = self._available_mixers[0]
            self._mixer_card = self._active_mixer['card_index']
            logger.info(f"Using fallback mixer: {self._active_mixer['name']} on {self._active_mixer['card_name']}")

    def _read_current_volume(self):
        """Чтение текущей громкости с активного миксера"""
        if not self._active_mixer:
            self._current_volume = 50
            return
        
        try:
            mixer = alsaaudio.Mixer(
                self._active_mixer['name'], 
                cardindex=self._active_mixer['card_index']
            )
            volumes = mixer.getvolume()
            
            if volumes:
                # Берем среднее значение по каналам
                self._current_volume = sum(volumes) // len(volumes)
                logger.debug(f"Current volume: {self._current_volume}%")
            else:
                self._current_volume = 50
                
        except Exception as e:
            logger.error(f"Error reading volume: {e}")
            self._current_volume = 50

    def _init_gpio_system(self):
        """🔥 ИСПРАВЛЕННАЯ инициализация GPIO с дополнительной диагностикой"""
        self.gpio_available = False
        
        # Пытаемся инициализировать lgpio (приоритет для Pi 5)
        if LGPIO_AVAILABLE:
            try:
                self.gpio_handle = lgpio.gpiochip_open(0)
                if self.gpio_handle >= 0:
                    # Настраиваем пины как входы с подтяжкой вверх
                    lgpio.gpio_claim_input(self.gpio_handle, VOLUME_UP_PIN, lgpio.SET_PULL_UP)
                    lgpio.gpio_claim_input(self.gpio_handle, VOLUME_DOWN_PIN, lgpio.SET_PULL_UP)
                    
                    # 🔥 НОВОЕ: Тестовое чтение для проверки работоспособности
                    test_up = lgpio.gpio_read(self.gpio_handle, VOLUME_UP_PIN)
                    test_down = lgpio.gpio_read(self.gpio_handle, VOLUME_DOWN_PIN)
                    logger.info(f"🔍 GPIO test read - UP: {test_up}, DOWN: {test_down}")
                    
                    # 🔥 НОВОЕ: Инициализируем состояния реальными значениями
                    self._last_button_state[VOLUME_UP_PIN] = test_up
                    self._last_button_state[VOLUME_DOWN_PIN] = test_down
                    
                    self.gpio_lib = "lgpio"
                    self.gpio_available = True
                    logger.info("✅ GPIO initialized with lgpio")
                    return
                    
            except Exception as e:
                logger.warning(f"❌ lgpio initialization failed: {e}")
                if self.gpio_handle is not None and self.gpio_handle >= 0:
                    try:
                        lgpio.gpiochip_close(self.gpio_handle)
                    except:
                        pass
                    self.gpio_handle = None
        
        # Fallback на RPi.GPIO
        if RPI_GPIO_AVAILABLE:
            try:
                RPi_GPIO.setmode(RPi_GPIO.BCM)
                RPi_GPIO.setup(VOLUME_UP_PIN, RPi_GPIO.IN, pull_up_down=RPi_GPIO.PUD_UP)
                RPi_GPIO.setup(VOLUME_DOWN_PIN, RPi_GPIO.IN, pull_up_down=RPi_GPIO.PUD_UP)
                
                # 🔥 НОВОЕ: Тестовое чтение
                test_up = RPi_GPIO.input(VOLUME_UP_PIN)
                test_down = RPi_GPIO.input(VOLUME_DOWN_PIN)
                logger.info(f"🔍 GPIO test read - UP: {test_up}, DOWN: {test_down}")
                
                # Инициализируем состояния
                self._last_button_state[VOLUME_UP_PIN] = test_up
                self._last_button_state[VOLUME_DOWN_PIN] = test_down
                
                self.gpio_lib = "RPi.GPIO"
                self.gpio_available = True
                logger.info("✅ GPIO initialized with RPi.GPIO")
                return
                
            except Exception as e:
                logger.warning(f"❌ RPi.GPIO initialization failed: {e}")
        
        logger.warning("⚠️ GPIO not available - hardware buttons disabled")


    def start(self):
        """Запуск сервиса мониторинга кнопок"""
        if self.running:
            logger.warning("VolumeControlService already running")
            return
        
        if not self.gpio_available:
            logger.info("GPIO not available, volume service started in software-only mode")
            self.running = True
            return
        
        self.running = True
        self._stop_event.clear()
        
        # Запускаем поток мониторинга кнопок
        self.thread = Thread(target=self._monitor_buttons, daemon=True)
        self.thread.start()
        
        logger.info("VolumeControlService started with GPIO monitoring")

    def stop(self):
        """ИСПРАВЛЕНО: Безопасная остановка сервиса с cleanup GPIO"""
        if not self.running:
            return
        
        logger.info("Stopping VolumeControlService...")
        self.running = False
        self._stop_event.set()
        
        # Ждем завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Proper GPIO cleanup
        self._cleanup_gpio()
        
        logger.info("VolumeControlService stopped")

    def _cleanup_gpio(self):
        """НОВОЕ: Proper GPIO cleanup для предотвращения утечек ресурсов"""
        try:
            if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                # Освобождаем GPIO pins
                try:
                    lgpio.gpio_free(self.gpio_handle, VOLUME_UP_PIN)
                    lgpio.gpio_free(self.gpio_handle, VOLUME_DOWN_PIN)
                except Exception as e:
                    logger.debug(f"Error freeing GPIO pins: {e}")
                
                # Закрываем handle
                try:
                    lgpio.gpiochip_close(self.gpio_handle)
                except Exception as e:
                    logger.debug(f"Error closing GPIO handle: {e}")
                    
                self.gpio_handle = None
                
            elif self.gpio_lib == "RPi.GPIO":
                try:
                    RPi_GPIO.cleanup([VOLUME_UP_PIN, VOLUME_DOWN_PIN])
                except Exception as e:
                    logger.debug(f"Error cleaning up RPi.GPIO: {e}")
            
            self.gpio_available = False
            logger.debug("GPIO cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in GPIO cleanup: {e}")

    def _monitor_buttons(self):
        """🔥 УЛУЧШЕННЫЙ мониторинг кнопок с дополнительной диагностикой"""
        logger.info("🔘 Button monitoring started")
        
        # 🔥 НОВОЕ: Счетчик для периодической диагностики
        diagnostic_counter = 0
        
        while self.running and not self._stop_event.is_set():
            try:
                self._check_volume_buttons()
                
                # 🔥 НОВОЕ: Каждые 10 секунд выводим состояние кнопок (только в debug режиме)
                diagnostic_counter += 1
                if diagnostic_counter >= 200:  # 200 * 50ms = 10 секунд
                    try:
                        if self.gpio_lib == "lgpio":
                            up_current = lgpio.gpio_read(self.gpio_handle, VOLUME_UP_PIN)
                            down_current = lgpio.gpio_read(self.gpio_handle, VOLUME_DOWN_PIN)
                        elif self.gpio_lib == "RPi.GPIO":
                            up_current = RPi_GPIO.input(VOLUME_UP_PIN)
                            down_current = RPi_GPIO.input(VOLUME_DOWN_PIN)
                        else:
                            up_current = down_current = "N/A"
                        
                        logger.debug(f"🔘 Button states - UP: {up_current}, DOWN: {down_current}")
                        diagnostic_counter = 0
                    except Exception as diag_e:
                        logger.debug(f"Diagnostic read failed: {diag_e}")
                
                time.sleep(0.05)  # 50ms polling rate
                    
            except Exception as e:
                logger.error(f"❌ Error in button monitoring: {e}")
                time.sleep(0.1)
        
        logger.info("🔘 Button monitoring stopped")

    def _check_volume_buttons(self):
        """🔥 ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ проверка состояния кнопок с правильной логикой"""
        current_time = time.time()
        
        # Читаем текущее состояние пинов
        try:
            if self.gpio_lib == "lgpio":
                up_state = lgpio.gpio_read(self.gpio_handle, VOLUME_UP_PIN)
                down_state = lgpio.gpio_read(self.gpio_handle, VOLUME_DOWN_PIN)
            elif self.gpio_lib == "RPi.GPIO":
                up_state = RPi_GPIO.input(VOLUME_UP_PIN)
                down_state = RPi_GPIO.input(VOLUME_DOWN_PIN)
            else:
                return
        except Exception as e:
            logger.error(f"Error reading GPIO: {e}")
            return
        
        # 🔥 ИСПРАВЛЕНО: Проверяем переход состояния (edge detection)
        # При pull-up резисторах: не нажата=1, нажата=0
        # Реагируем только на переход от 1 к 0 (нажатие)
        
        # Volume Up - проверка нажатия
        if (up_state == 0 and 
            self._last_button_state[VOLUME_UP_PIN] == 1 and 
            current_time - self._last_button_time[VOLUME_UP_PIN] > DEBOUNCE_TIME):
            
            self._last_button_time[VOLUME_UP_PIN] = current_time
            self.volume_up_manual()
            logger.info("🔊 Volume up button pressed (GPIO)")
        
        # Volume Down - проверка нажатия  
        if (down_state == 0 and 
            self._last_button_state[VOLUME_DOWN_PIN] == 1 and
            current_time - self._last_button_time[VOLUME_DOWN_PIN] > DEBOUNCE_TIME):
            
            self._last_button_time[VOLUME_DOWN_PIN] = current_time
            self.volume_down_manual()
            logger.info("🔉 Volume down button pressed (GPIO)")
        
        # 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Обновляем предыдущие состояния ПОСЛЕ проверки
        self._last_button_state[VOLUME_UP_PIN] = up_state
        self._last_button_state[VOLUME_DOWN_PIN] = down_state



    def get_volume(self):
        """Получение текущей громкости"""
        with self._volume_lock:
            return self._current_volume

    def set_volume(self, volume):
        """ИСПРАВЛЕНО: Установка громкости с синхронизацией"""
        volume = max(MIN_VOLUME, min(MAX_VOLUME, int(volume)))
        
        if not self._active_mixer:
            logger.warning("No active mixer - cannot set volume")
            return False
        
        try:
            mixer = alsaaudio.Mixer(
                self._active_mixer['name'], 
                cardindex=self._active_mixer['card_index']
            )
            
            # Устанавливаем громкость на всех каналах
            mixer.setvolume(volume)
            
            with self._volume_lock:
                self._current_volume = volume
            
            # Уведомляем об изменении
            self._notify_volume_change(volume)
            
            logger.debug(f"Volume set to {volume}% on {self._active_mixer['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False

    def volume_up_manual(self):
        """Увеличение громкости (ручное или кнопка)"""
        current = self.get_volume()
        new_volume = min(MAX_VOLUME, current + VOLUME_STEP)
        
        if self.set_volume(new_volume):
            logger.info(f"Volume up: {current}% → {new_volume}%")
            return new_volume
        return current

    def volume_down_manual(self):
        """Уменьшение громкости (ручное или кнопка)"""
        current = self.get_volume()
        new_volume = max(MIN_VOLUME, current - VOLUME_STEP)
        
        if self.set_volume(new_volume):
            logger.info(f"Volume down: {current}% → {new_volume}%")
            return new_volume
        return current

    def _notify_volume_change(self, volume):
        """ИСПРАВЛЕНО: Уведомление об изменении громкости через event_bus"""
        try:
            # Используем event_bus вместо прямого импорта App
            from app.event_bus import event_bus
            event_bus.publish("volume_changed", {"volume": volume})
            
            # Callback если установлен
            if self._volume_change_callback:
                self._volume_change_callback(volume)
                
        except Exception as e:
            logger.error(f"Error notifying volume change: {e}")

    def set_volume_change_callback(self, callback):
        """Установка callback для изменения громкости"""
        self._volume_change_callback = callback

    def get_status(self):
        """Получение полного статуса сервиса"""
        return {
            'instance_id': self._instance_id,
            'service_version': self._service_version,
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
        
        logger.info(f"Service version: {status['service_version']}")
        logger.info(f"Instance ID: {status['instance_id']}")
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

    def verify_instance(self):
        """НОВОЕ: Верификация экземпляра VolumeControlService"""
        return {
            "class_name": self.__class__.__name__,
            "instance_id": self._instance_id,
            "service_version": self._service_version,
            "has_diagnose_audio_system": hasattr(self, 'diagnose_audio_system'),
            "has_get_status": hasattr(self, 'get_status'),
            "methods": [method for method in dir(self) if not method.startswith('_')]
        }


# ИСПРАВЛЕНО: НЕ создаем глобальный экземпляр
# Каждое приложение должно создать свой экземпляр через main.py

def validate_volume_service_module():
    """Валидация модуля VolumeControlService для отладки"""
    try:
        service = VolumeControlService()
        assert hasattr(service, 'get_status'), "get_status method missing"
        assert hasattr(service, 'set_volume'), "set_volume method missing"
        assert hasattr(service, 'diagnose_audio_system'), "diagnose_audio_system method missing"
        print("✅ VolumeControlService module validation passed")
        return True
    except Exception as e:
        print(f"❌ VolumeControlService module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_volume_service_module()