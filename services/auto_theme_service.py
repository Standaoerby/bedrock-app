"""
AutoTheme Service - Автоматическое переключение темы по датчику освещенности
🔥 КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
- Исправлен constructor - принимает sensor_service и theme_manager (как в main.py)
- Принудительная активация физических сенсоров
- Правильные импорты и методы
- Совместимость с реальной структурой проекта
"""
import time
import threading
from threading import Thread
from app.logger import app_logger as logger
from app.event_bus import event_bus


class AutoThemeService:
    """🔥 ИСПРАВЛЕННЫЙ сервис автоматического переключения темы по датчику освещенности"""
    
    def __init__(self, sensor_service=None, theme_manager=None):
        """🔥 ИСПРАВЛЕН: Правильный constructor согласно main.py"""
        self.sensor_service = sensor_service
        self.theme_manager = theme_manager
        
        # Service state
        self.enabled = True
        self.monitoring = False
        self.threshold_seconds = 3
        
        # Light state tracking
        self.current_light_state = True
        self.state_stable = False
        self.state_start_time = None
        
        # Thread management
        self.thread = None
        self.running = False
        self._stop_event = threading.Event()
        
        # 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Форсируем проверку физических сенсоров
        if sensor_service:
            self._force_physical_sensor_check()
        
        logger.info("AutoThemeService initialized")
    
    def _force_physical_sensor_check(self):
        """🔥 НОВОЕ: Принудительная проверка физических сенсоров"""
        try:
            if not self.sensor_service:
                return
            
            # Проверяем состояние сенсоров
            using_mock = getattr(self.sensor_service, 'using_mock_sensors', True)
            gpio_available = getattr(self.sensor_service, 'gpio_available', False)
            sensor_available = getattr(self.sensor_service, 'sensor_available', False)
            
            logger.info(f"🔍 Sensor check: mock={using_mock}, gpio={gpio_available}, i2c={sensor_available}")
            
            if using_mock and not (gpio_available or sensor_available):
                logger.warning("❌ Auto-theme running with mock sensors only!")
                logger.info("🔧 Attempting to reinitialize physical sensors...")
                
                # Попытка повторной инициализации
                if hasattr(self.sensor_service, '_try_initialize_real_sensors'):
                    self.sensor_service._try_initialize_real_sensors()
                    
                    # Проверяем результат
                    updated_mock = getattr(self.sensor_service, 'using_mock_sensors', True)
                    updated_gpio = getattr(self.sensor_service, 'gpio_available', False)
                    updated_sensor = getattr(self.sensor_service, 'sensor_available', False)
                    
                    if not updated_mock or updated_gpio or updated_sensor:
                        logger.info("✅ Physical sensors successfully activated!")
                        # Обновляем наш статус
                        self.sensor_service.using_mock_sensors = False
                    else:
                        logger.warning("❌ Physical sensors still not available")
                        
                # 🔥 ДОПОЛНИТЕЛЬНАЯ ПОПЫТКА: Прямая попытка чтения GPIO
                if not (updated_gpio or updated_sensor):
                    logger.info("🔧 Attempting direct GPIO initialization...")
                    self._attempt_direct_gpio_init()
                        
        except Exception as e:
            logger.error(f"Error in force sensor check: {e}")
    
    def _attempt_direct_gpio_init(self):
        """🔥 НОВОЕ: Прямая попытка инициализации GPIO для света"""
        try:
            # Попытка с lgpio
            try:
                import lgpio
                gpio_handle = lgpio.gpiochip_open(0)
                lgpio.gpio_claim_input(gpio_handle, 18, lgpio.SET_PULL_UP)  # LDR_GPIO_PIN из sensor_service
                test_read = lgpio.gpio_read(gpio_handle, 18)
                
                # Если дошли сюда - GPIO работает
                if hasattr(self.sensor_service, 'gpio_handle'):
                    self.sensor_service.gpio_handle = gpio_handle
                    self.sensor_service.gpio_lib = "lgpio"
                    self.sensor_service.gpio_available = True
                    self.sensor_service.using_mock_sensors = False
                    
                logger.info(f"✅ Direct GPIO init successful with lgpio (test: {test_read})")
                return True
                
            except Exception as lgpio_e:
                logger.debug(f"Direct lgpio failed: {lgpio_e}")
            
            # Попытка с RPi.GPIO
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                test_read = GPIO.input(18)
                
                if hasattr(self.sensor_service, 'gpio_lib'):
                    self.sensor_service.gpio_lib = "RPi.GPIO"
                    self.sensor_service.gpio_available = True
                    self.sensor_service.using_mock_sensors = False
                    
                logger.info(f"✅ Direct GPIO init successful with RPi.GPIO (test: {test_read})")
                return True
                
            except Exception as rpi_e:
                logger.debug(f"Direct RPi.GPIO failed: {rpi_e}")
            
            logger.warning("❌ Direct GPIO initialization failed")
            return False
            
        except Exception as e:
            logger.error(f"Error in direct GPIO init: {e}")
            return False
    
    def start(self):
        """🔥 ИСПРАВЛЕН: Запуск с повторной проверкой сенсоров"""
        if self.monitoring:
            logger.warning("AutoThemeService already monitoring")
            return
        
        if not self.sensor_service:
            logger.error("Cannot start auto-theme: no sensor service")
            return
        
        # 🔥 НОВОЕ: Повторная проверка сенсоров перед запуском
        self._force_physical_sensor_check()
        
        # Проверяем доступность физических сенсоров
        gpio_available = getattr(self.sensor_service, 'gpio_available', False)
        sensor_available = getattr(self.sensor_service, 'sensor_available', False)
        using_mock = getattr(self.sensor_service, 'using_mock_sensors', True)
        
        if using_mock and not (gpio_available or sensor_available):
            logger.warning("❌ Starting auto-theme with mock sensors - limited functionality")
        else:
            logger.info("✅ Starting auto-theme with physical sensors")
        
        self.monitoring = True
        self.running = True
        self._stop_event.clear()
        
        # Запускаем поток мониторинга
        self.thread = Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        
        logger.info("🌓 AutoThemeService started")
    
    def _monitoring_loop(self):
        """🔥 УЛУЧШЕННЫЙ: Цикл мониторинга с лучшей обработкой ошибок"""
        logger.info("🌓 Auto-theme monitoring started")
        
        while self.running and not self._stop_event.is_set():
            try:
                self._check_light_and_update_theme()
                time.sleep(0.5)  # Проверяем каждые 0.5 секунд
                
            except Exception as e:
                logger.error(f"Error in auto-theme monitoring: {e}")
                time.sleep(2)  # Больше задержка при ошибке
        
        logger.info("🌓 Auto-theme monitoring stopped")
    
    def _check_light_and_update_theme(self):
        """🔥 ИСПРАВЛЕНО: Проверка света с fallback на mock"""
        try:
            if not self.sensor_service:
                return
            
            # Получаем текущий уровень света
            try:
                # Пытаемся получить реальные данные
                if hasattr(self.sensor_service, 'get_light_level'):
                    current_light = self.sensor_service.get_light_level()
                elif hasattr(self.sensor_service, '_read_light_sensor'):
                    raw_reading = self.sensor_service._read_light_sensor()
                    current_light = (raw_reading == 0) if raw_reading is not None else True
                else:
                    # Fallback на чтение из readings
                    readings = self.sensor_service.get_readings()
                    current_light = readings.get('light_level', True)
                
            except Exception as read_e:
                logger.debug(f"Error reading light sensor: {read_e}")
                # Fallback на mock логику
                current_hour = time.localtime().tm_hour
                current_light = 6 <= current_hour < 22
            
            # Обновляем состояние
            self._update_light_state(current_light)
            
        except Exception as e:
            logger.error(f"Error checking light: {e}")
    
    def _update_light_state(self, current_light):
        """Обновление состояния света и смена темы при необходимости"""
        current_time = time.time()
        
        # Если состояние изменилось
        if current_light != self.current_light_state:
            self.current_light_state = current_light
            self.state_start_time = current_time
            self.state_stable = False
            
            logger.debug(f"🌓 Light state changed: {'Light' if current_light else 'Dark'}")
        
        # Проверяем стабильность состояния
        elif self.state_start_time:
            time_in_state = current_time - self.state_start_time
            
            if time_in_state >= self.threshold_seconds and not self.state_stable:
                self.state_stable = True
                
                # Меняем тему
                new_variant = "light" if current_light else "dark"
                self._change_theme_variant(new_variant)
                
                logger.info(f"🌓 Auto-theme: {'Dark' if not current_light else 'Light'}→{'Light' if current_light else 'Dark'} (confidence: 1.00)")
    
    def _change_theme_variant(self, variant):
        """🔥 ИСПРАВЛЕНО: Смена варианта темы через theme_manager"""
        try:
            if not self.theme_manager:
                logger.warning("No theme_manager available for auto-theme")
                return
            
            current_theme = getattr(self.theme_manager, 'theme_name', 'minecraft')
            current_variant = getattr(self.theme_manager, 'variant', 'light')
            
            if variant != current_variant:
                # 🔥 ИСПРАВЛЕНО: Используем правильный метод theme_manager
                if hasattr(self.theme_manager, 'load'):
                    self.theme_manager.load(current_theme, variant)
                    logger.info(f"🎨 Auto-theme changed: {current_theme}/{current_variant} → {current_theme}/{variant}")
                
                # Также публикуем событие для UI обновлений
                try:
                    event_bus.publish("theme_changed", {
                        "theme": current_theme,
                        "variant": variant
                    })
                except Exception as event_e:
                    logger.debug(f"Event bus publish failed: {event_e}")
                
        except Exception as e:
            logger.error(f"Error changing theme variant: {e}")
    
    def calibrate_sensor(self, threshold_seconds):
        """Калибровка сенсора с новым порогом"""
        try:
            self.threshold_seconds = max(1, min(threshold_seconds, 30))
            logger.info(f"🔧 Auto-theme sensor calibrated: threshold={self.threshold_seconds}s")
            
            # Сбрасываем состояние для новой калибровки
            self.state_stable = False
            self.state_start_time = time.time()
            
        except Exception as e:
            logger.error(f"Error calibrating sensor: {e}")
    
    def force_check(self):
        """🔥 НОВОЕ: Принудительная проверка света (для initial check в main.py)"""
        try:
            logger.info("🔍 Force checking light sensor...")
            self._check_light_and_update_theme()
            logger.info("✅ Force check completed")
        except Exception as e:
            logger.error(f"Error in force check: {e}")
    
    def get_status(self):
        """🔥 УЛУЧШЕНО: Получение статуса с реальной информацией о сенсорах"""
        try:
            # Получаем статус датчика
            sensor_available = bool(self.sensor_service)
            using_mock = True
            current_light = True
            
            if self.sensor_service:
                using_mock = getattr(self.sensor_service, 'using_mock_sensors', True)
                gpio_available = getattr(self.sensor_service, 'gpio_available', False)
                i2c_available = getattr(self.sensor_service, 'sensor_available', False)
                
                # 🔥 ИСПРАВЛЕНО: Считаем mock только если нет физических сенсоров
                if gpio_available or i2c_available:
                    using_mock = False
                
                try:
                    current_light = self.sensor_service.get_light_level()
                except Exception as e:
                    logger.debug(f"Error getting light level for status: {e}")
            
            return {
                "service_running": self.monitoring,
                "service_enabled": self.enabled,
                "sensor_available": sensor_available,
                "using_mock": using_mock,
                "current_light": current_light,
                "threshold_seconds": self.threshold_seconds,
                "current_light_state": self.current_light_state,
                "state_stable": self.state_stable,
                "time_since_change": time.time() - self.state_start_time if self.state_start_time else None,
                # 🔥 НОВОЕ: Дополнительная диагностическая информация
                "gpio_available": getattr(self.sensor_service, 'gpio_available', False) if self.sensor_service else False,
                "i2c_available": getattr(self.sensor_service, 'sensor_available', False) if self.sensor_service else False,
                "gpio_lib": getattr(self.sensor_service, 'gpio_lib', None) if self.sensor_service else None,
                "theme_manager_available": bool(self.theme_manager)
            }
            
        except Exception as e:
            logger.error(f"Error getting auto-theme status: {e}")
            return {
                "service_running": False,
                "service_enabled": False,
                "sensor_available": False,
                "error": str(e)
            }
    
    def diagnose(self):
        """🔥 УЛУЧШЕНО: Диагностика для отладки"""
        status = self.get_status()
        
        logger.info("🔧 === AUTO-THEME SERVICE DIAGNOSIS ===")
        logger.info(f"Service running: {status.get('service_running', False)}")
        logger.info(f"Service enabled: {status.get('service_enabled', False)}")
        logger.info(f"Sensor available: {status.get('sensor_available', False)}")
        logger.info(f"Using mock sensors: {status.get('using_mock', True)}")
        logger.info(f"GPIO available: {status.get('gpio_available', False)}")
        logger.info(f"I2C available: {status.get('i2c_available', False)}")
        logger.info(f"GPIO library: {status.get('gpio_lib', 'None')}")
        logger.info(f"Theme manager available: {status.get('theme_manager_available', False)}")
        logger.info(f"Current light: {status.get('current_light', 'Unknown')}")
        logger.info(f"Threshold: {status.get('threshold_seconds', 0)}s")
        logger.info("🔧 === DIAGNOSIS COMPLETE ===")
        
        return status
    
    def stop(self):
        """Остановка сервиса"""
        if not self.monitoring:
            return
        
        logger.info("Stopping AutoThemeService...")
        self.monitoring = False
        self.running = False
        self._stop_event.set()
        
        # Ждем завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        logger.info("🌓 AutoThemeService stopped")