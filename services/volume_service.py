"""
Volume Control Service for physical buttons
Handles GPIO button presses for volume up/down control
ИСПРАВЛЕНО: Автоопределение миксеров, fallback логика, улучшенная обработка ошибок
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

# ИСПРАВЛЕНО: Приоритетный список миксеров для поиска
MIXER_PRIORITIES = [
    'Master',
    'PCM', 
    'Speaker',
    'Headphone',
    'Digital',
    'Line Out',
    'Playback'
]

# GPIO imports with error handling
try:
    import lgpio
    LGPIO_AVAILABLE = True
except ImportError:
    LGPIO_AVAILABLE = False
    lgpio = None

try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True  
except ImportError:
    RPI_GPIO_AVAILABLE = False
    GPIO = None


class VolumeControlService:
    """Service for handling physical volume control buttons"""
    
    def __init__(self):
        """Initialize volume control service"""
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        
        # GPIO setup
        self.gpio_available = False
        self.gpio_lib = None
        self.gpio_handle = None
        
        # ИСПРАВЛЕНО: Миксер автоопределение
        self._available_mixers = []
        self._active_mixer = None
        self._mixer_card = 0
        
        # Volume state
        self._current_volume = 50  # Начальное значение по умолчанию
        self._volume_lock = Lock()
        
        # Button state tracking для дебаунсинга
        self._last_button_time = {VOLUME_UP_PIN: 0, VOLUME_DOWN_PIN: 0}
        self._last_button_state = {VOLUME_UP_PIN: True, VOLUME_DOWN_PIN: True}  # True = not pressed (pull-up)
        
        # Callback events
        self._volume_change_callback = None
        
        # ИСПРАВЛЕНО: Инициализируем миксеры при создании
        self._init_audio_mixers()
        
        logger.info(f"VolumeControlService initialized - Current volume: {self._current_volume}% (mixer: {self._active_mixer})")
    
    def _init_audio_mixers(self):
        """ИСПРАВЛЕНО: Инициализация и автоопределение доступных миксеров"""
        try:
            # Сначала находим доступные миксеры
            self._discover_mixers()
            
            # Выбираем лучший миксер из доступных
            self._select_best_mixer()
            
            # Получаем текущую громкость
            self._current_volume = self._get_system_volume()
            
            logger.info(f"Audio mixers initialized - Active: {self._active_mixer}, Available: {self._available_mixers}")
            
        except Exception as e:
            logger.error(f"Error initializing audio mixers: {e}")
            self._active_mixer = None

    def _discover_mixers(self):
        """ИСПРАВЛЕНО: Обнаружение доступных миксеров через amixer"""
        self._available_mixers = []
        
        try:
            # Получаем список всех доступных миксеров
            result = subprocess.run(
                ['amixer', 'scontrols'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                # Парсим вывод amixer scontrols
                for line in result.stdout.split('\n'):
                    if "Simple mixer control" in line:
                        # Извлекаем имя миксера между апострофами
                        match = re.search(r"'([^']+)'", line)
                        if match:
                            mixer_name = match.group(1)
                            self._available_mixers.append(mixer_name)
                
                logger.info(f"Discovered mixers: {self._available_mixers}")
            else:
                logger.warning(f"Failed to discover mixers: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout discovering mixers")
        except FileNotFoundError:
            logger.warning("amixer not available - cannot discover mixers")
        except Exception as e:
            logger.error(f"Error discovering mixers: {e}")

    def _select_best_mixer(self):
        """ИСПРАВЛЕНО: Выбор лучшего миксера из доступных"""
        self._active_mixer = None
        
        if not self._available_mixers:
            logger.warning("No mixers discovered")
            return
        
        # Ищем миксер по приоритету
        for priority_mixer in MIXER_PRIORITIES:
            for available_mixer in self._available_mixers:
                if priority_mixer.lower() in available_mixer.lower():
                    # Проверяем что этот миксер действительно работает
                    if self._test_mixer(available_mixer):
                        self._active_mixer = available_mixer
                        logger.info(f"Selected mixer: {self._active_mixer}")
                        return
        
        # Если ничего не подошло, пробуем первый доступный
        for mixer in self._available_mixers:
            if self._test_mixer(mixer):
                self._active_mixer = mixer
                logger.info(f"Selected fallback mixer: {self._active_mixer}")
                return
        
        logger.error("No working mixer found")

    def _test_mixer(self, mixer_name):
        """ИСПРАВЛЕНО: Тестирование работоспособности миксера"""
        try:
            result = subprocess.run(
                ['amixer', 'get', mixer_name], 
                capture_output=True, 
                text=True, 
                timeout=3
            )
            
            if result.returncode == 0:
                # Проверяем что в выводе есть процент громкости
                return '[' in result.stdout and '%' in result.stdout
            
            return False
            
        except Exception as e:
            logger.debug(f"Mixer {mixer_name} test failed: {e}")
            return False

    def start(self):
        """Start the volume control service"""
        if self.running:
            logger.warning("VolumeControlService already running")
            return False
            
        try:
            # Initialize GPIO
            self._init_gpio()
            
            if not self.gpio_available:
                logger.warning("GPIO not available - volume buttons will use mock mode")
            
            # ИСПРАВЛЕНО: Проверяем что у нас есть рабочий миксер
            if not self._active_mixer:
                logger.warning("No working audio mixer found - volume control may not work properly")
            
            # Start monitoring thread
            self.running = True
            self._stop_event.clear()
            self.thread = Thread(target=self._monitor_buttons, daemon=True)
            self.thread.start()
            
            logger.info("VolumeControlService started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting volume control service: {e}")
            return False
    
    def _init_gpio(self):
        """Initialize GPIO for volume buttons"""
        try:
            # Try lgpio first (preferred for Pi 5)
            if LGPIO_AVAILABLE:
                try:
                    self.gpio_handle = lgpio.gpiochip_open(0)
                    
                    # Set up both buttons with pull-up resistors
                    lgpio.gpio_claim_input(self.gpio_handle, VOLUME_UP_PIN, lgpio.SET_PULL_UP)
                    lgpio.gpio_claim_input(self.gpio_handle, VOLUME_DOWN_PIN, lgpio.SET_PULL_UP)
                    
                    self.gpio_lib = "lgpio"
                    self.gpio_available = True
                    logger.info(f"GPIO initialized with lgpio (pins {VOLUME_UP_PIN}, {VOLUME_DOWN_PIN})")
                    return
                    
                except Exception as e:
                    logger.warning(f"lgpio initialization failed: {e}")
                    if self.gpio_handle:
                        try:
                            lgpio.gpiochip_close(self.gpio_handle)
                        except:
                            pass
                        self.gpio_handle = None
            
            # Fallback to RPi.GPIO
            if RPI_GPIO_AVAILABLE:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(VOLUME_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.setup(VOLUME_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    
                    self.gpio_lib = "RPi.GPIO"
                    self.gpio_available = True
                    logger.info(f"GPIO initialized with RPi.GPIO (pins {VOLUME_UP_PIN}, {VOLUME_DOWN_PIN})")
                    return
                    
                except Exception as e:
                    logger.warning(f"RPi.GPIO initialization failed: {e}")
                    try:
                        GPIO.cleanup()
                    except:
                        pass
            
            # No GPIO available
            self.gpio_available = False
            logger.warning("No GPIO library available for volume buttons")
            
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
            self.gpio_available = False
    
    def _read_button(self, pin):
        """Read button state from GPIO"""
        try:
            if not self.gpio_available:
                return True  # Not pressed
                
            if self.gpio_lib == "lgpio":
                return bool(lgpio.gpio_read(self.gpio_handle, pin))
            elif self.gpio_lib == "RPi.GPIO":
                return bool(GPIO.input(pin))
            else:
                return True
                
        except Exception as e:
            logger.error(f"Error reading button {pin}: {e}")
            return True
    
    def _monitor_buttons(self):
        """Background thread to monitor button presses"""
        logger.info("Button monitoring started")
        
        while self.running and not self._stop_event.is_set():
            try:
                if self.gpio_available:
                    current_time = time.time()
                    
                    # Check volume up button
                    self._check_button(VOLUME_UP_PIN, current_time, self._volume_up)
                    
                    # Check volume down button  
                    self._check_button(VOLUME_DOWN_PIN, current_time, self._volume_down)
                
                # Small delay to avoid excessive CPU usage
                self._stop_event.wait(0.05)  # 50ms polling
                
            except Exception as e:
                logger.error(f"Error in button monitoring: {e}")
                self._stop_event.wait(0.1)  # Brief pause on error
        
        logger.info("Button monitoring stopped")
    
    def _check_button(self, pin, current_time, action_callback):
        """Check individual button state and handle press events"""
        try:
            current_state = self._read_button(pin)
            last_state = self._last_button_state.get(pin, True)
            last_time = self._last_button_time.get(pin, 0)
            
            # Button pressed (state goes from True to False due to pull-up)
            if last_state and not current_state:
                # Check debounce time
                if current_time - last_time > DEBOUNCE_TIME:
                    logger.debug(f"Button {pin} pressed")
                    action_callback()
                    self._last_button_time[pin] = current_time
            
            # Update state
            self._last_button_state[pin] = current_state
            
        except Exception as e:
            logger.error(f"Error checking button {pin}: {e}")
    
    def _volume_up(self):
        """Handle volume up button press"""
        try:
            with self._volume_lock:
                new_volume = min(self._current_volume + VOLUME_STEP, MAX_VOLUME)
                if new_volume != self._current_volume:
                    if self._set_system_volume(new_volume):
                        old_volume = self._current_volume
                        self._current_volume = new_volume
                        logger.info(f"Volume up: {old_volume}% → {self._current_volume}%")
                        
                        # Play feedback sound
                        self._play_feedback_sound("confirm")
                        
                        # Trigger callback
                        if self._volume_change_callback:
                            try:
                                self._volume_change_callback(self._current_volume, "up")
                            except Exception as cb_e:
                                logger.error(f"Error in volume change callback: {cb_e}")
                    else:
                        logger.error("Failed to set volume up")
                        self._play_feedback_sound("error")
                else:
                    logger.debug("Volume already at maximum")
                    self._play_feedback_sound("error")
                    
        except Exception as e:
            logger.error(f"Error in volume up: {e}")
    
    def _volume_down(self):
        """Handle volume down button press"""
        try:
            with self._volume_lock:
                new_volume = max(self._current_volume - VOLUME_STEP, MIN_VOLUME)
                if new_volume != self._current_volume:
                    if self._set_system_volume(new_volume):
                        old_volume = self._current_volume
                        self._current_volume = new_volume
                        logger.info(f"Volume down: {old_volume}% → {self._current_volume}%")
                        
                        # Play feedback sound
                        self._play_feedback_sound("click")
                        
                        # Trigger callback
                        if self._volume_change_callback:
                            try:
                                self._volume_change_callback(self._current_volume, "down")
                            except Exception as cb_e:
                                logger.error(f"Error in volume change callback: {cb_e}")
                    else:
                        logger.error("Failed to set volume down")
                        self._play_feedback_sound("error")
                else:
                    logger.debug("Volume already at minimum") 
                    self._play_feedback_sound("error")
                    
        except Exception as e:
            logger.error(f"Error in volume down: {e}")
    
    def _get_system_volume(self):
        """ИСПРАВЛЕНО: Получение громкости с использованием активного миксера"""
        try:
            if not self._active_mixer:
                logger.debug("No active mixer for getting volume")
                return self._current_volume  # Возвращаем кешированное значение
            
            # Use amixer to get volume
            result = subprocess.run(
                ['amixer', 'get', self._active_mixer], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse volume from output
                for line in result.stdout.split('\n'):
                    if '[' in line and '%' in line:
                        # Extract percentage
                        start = line.find('[') + 1
                        end = line.find('%')
                        if start > 0 and end > start:
                            volume_str = line[start:end]
                            volume = int(volume_str)
                            logger.debug(f"Got volume from {self._active_mixer}: {volume}%")
                            return volume
            
            logger.warning(f"Could not parse volume from {self._active_mixer} output")
            return self._current_volume  # Возвращаем кешированное значение
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout getting system volume")
            return self._current_volume
        except FileNotFoundError:
            logger.warning("amixer not available - using cached volume")
            return self._current_volume
        except Exception as e:
            logger.error(f"Error getting system volume: {e}")
            return self._current_volume
    
    def _set_system_volume(self, volume):
        """ИСПРАВЛЕНО: Установка громкости с использованием активного миксера"""
        try:
            if not self._active_mixer:
                logger.warning("No active mixer for setting volume")
                return False
            
            # Ensure volume is within bounds
            volume = max(MIN_VOLUME, min(volume, MAX_VOLUME))
            
            # Use amixer to set volume
            result = subprocess.run(
                ['amixer', 'set', self._active_mixer, f'{volume}%'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to set volume on {self._active_mixer}: {result.stderr}")
                return False
            
            logger.debug(f"Set volume on {self._active_mixer}: {volume}%")
                
            # ИСПРАВЛЕНО: Также пытаемся синхронизировать с audio service
            try:
                from kivy.app import App
                app = App.get_running_app()
                if hasattr(app, 'audio_service') and app.audio_service:
                    # AudioService expects 0-1 range
                    app.audio_service.set_volume(volume / 100.0)
                    logger.debug(f"Synced volume with AudioService: {volume/100.0}")
            except Exception as audio_e:
                logger.debug(f"Could not sync with audio service: {audio_e}")
                
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout setting system volume")
            return False
        except FileNotFoundError:
            logger.warning("amixer not available - cannot set system volume")
            return False
        except Exception as e:
            logger.error(f"Error setting system volume: {e}")
            return False
    
    def _play_feedback_sound(self, sound_name):
        """Play feedback sound for button press"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'audio_service') and hasattr(app, 'theme_manager'):
                if app.audio_service and app.theme_manager:
                    sound_file = app.theme_manager.get_sound(sound_name)
                    if sound_file:
                        app.audio_service.play(sound_file)
                        
        except Exception as e:
            logger.debug(f"Could not play feedback sound '{sound_name}': {e}")
    
    def stop(self):
        """Stop the volume control service"""
        if not self.running:
            return
            
        logger.info("Stopping VolumeControlService...")
        
        self.running = False
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        # Cleanup GPIO
        try:
            if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None
            elif self.gpio_lib == "RPi.GPIO":
                GPIO.cleanup([VOLUME_UP_PIN, VOLUME_DOWN_PIN])
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")
        
        logger.info("VolumeControlService stopped")
    
    def get_volume(self):
        """Get current volume level"""
        with self._volume_lock:
            # ИСПРАВЛЕНО: Периодически обновляем из системы для синхронизации
            try:
                system_volume = self._get_system_volume()
                if abs(system_volume - self._current_volume) > 2:  # Если разница больше 2%
                    logger.debug(f"Volume drift detected: cached={self._current_volume}%, system={system_volume}%")
                    self._current_volume = system_volume
            except Exception as e:
                logger.debug(f"Could not sync volume from system: {e}")
            
            return self._current_volume
    
    def set_volume(self, volume):
        """Set volume level programmatically"""
        try:
            with self._volume_lock:
                volume = max(MIN_VOLUME, min(volume, MAX_VOLUME))
                if self._set_system_volume(volume):
                    old_volume = self._current_volume
                    self._current_volume = volume
                    logger.info(f"Volume set programmatically: {old_volume}% → {volume}%")
                    
                    # Trigger callback
                    if self._volume_change_callback:
                        try:
                            self._volume_change_callback(volume, "set")
                        except Exception as cb_e:
                            logger.error(f"Error in volume change callback: {cb_e}")
                    
                    return True
                return False
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    def volume_up_manual(self):
        """Manual volume up (for testing or UI buttons)"""
        logger.info("Manual volume up triggered")
        self._volume_up()
    
    def volume_down_manual(self):
        """Manual volume down (for testing or UI buttons)"""
        logger.info("Manual volume down triggered")
        self._volume_down()
    
    def set_volume_change_callback(self, callback):
        """Set callback function for volume changes
        
        Args:
            callback: Function to call with (volume, action) parameters
                     action can be 'up', 'down', or 'set'
        """
        self._volume_change_callback = callback
        logger.info("Volume change callback set")
    
    def refresh_mixers(self):
        """ИСПРАВЛЕНО: Обновление списка доступных миксеров"""
        logger.info("Refreshing audio mixers...")
        try:
            self._init_audio_mixers()
            logger.info(f"Mixers refreshed - Active: {self._active_mixer}")
            return True
        except Exception as e:
            logger.error(f"Error refreshing mixers: {e}")
            return False
    
    def get_status(self):
        """Get service status for debugging"""
        return {
            'running': self.running,
            'gpio_available': self.gpio_available,
            'gpio_lib': self.gpio_lib,
            'current_volume': self._current_volume,
            'volume_step': VOLUME_STEP,
            'debounce_time': DEBOUNCE_TIME,
            'active_mixer': self._active_mixer,
            'available_mixers': self._available_mixers,
            'mixer_card': self._mixer_card,
            'button_pins': {
                'volume_up': VOLUME_UP_PIN,
                'volume_down': VOLUME_DOWN_PIN
            },
            'lgpio_available': LGPIO_AVAILABLE,
            'rpi_gpio_available': RPI_GPIO_AVAILABLE
        }