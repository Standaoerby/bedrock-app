"""
Упрощенный сервис для работы с датчиками окружающей среды
Поддерживает как реальные датчики на Raspberry Pi, так и mock-данные для разработки

🔥 ИСПРАВЛЕНИЯ:
- Приоритет физических сенсоров перед mock
- Исправлен GPIO PIN (18 вместо 12)
- Добавлены отсутствующие импорты (math, threading)
- Унифицированная инициализация с volume_service
- Proper cleanup методы
"""
import time
import os
import random
import math
import threading
from threading import Thread
from datetime import datetime
from app.logger import app_logger as logger

# Constants (🔥 ИСПРАВЛЕНО: правильный PIN из логов)
ENS160_ADDRESS = 0x53
AHT21_ADDRESS = 0x38
LDR_GPIO_PIN = 18  # 🔥 ИСПРАВЛЕНО: из логов видно PIN 18, не 12

AIR_QUALITY_LEVELS = {
    1: "Excellent", 2: "Good", 3: "Moderate", 4: "Poor", 5: "Unhealthy"
}

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

# I2C sensor libraries
try:
    import board
    import busio
    import adafruit_ens160
    import adafruit_ahtx0
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False

class DummyENS160:
    """Simple mock for ENS160 sensor"""
    def __init__(self, i2c, address=ENS160_ADDRESS):
        self._eco2 = 800
        self._tvoc = 250
        self._aqi = 2
    
    @property
    def eCO2(self):
        self._eco2 += random.randint(-20, 20)
        return max(400, min(self._eco2, 1200))
    
    @property
    def TVOC(self):
        self._tvoc += random.randint(-10, 10)
        return max(50, min(self._tvoc, 400))
    
    @property
    def AQI(self):
        if random.random() < 0.1:
            self._aqi = random.randint(1, 3)
        return self._aqi

class DummyAHTx0:
    """Simple mock for AHT21 sensor"""
    def __init__(self, i2c, address=AHT21_ADDRESS):
        self._temperature = 22.5
        self._humidity = 45.0
        
    @property
    def temperature(self):
        # 🔥 ИСПРАВЛЕНО: добавлен math импорт
        base = 22.5 + 5 * math.sin(time.time() / 3600)
        self._temperature = base + random.uniform(-0.2, 0.2)
        return max(18.0, min(self._temperature, 28.0))
        
    @property
    def relative_humidity(self):
        # 🔥 ИСПРАВЛЕНО: добавлен math импорт
        base = 45 + 15 * math.sin(time.time() / 1800)
        self._humidity = base + random.uniform(-0.5, 0.5)
        return max(30.0, min(self._humidity, 70.0))

class DummyLDR:
    """Simple mock LDR with day/night simulation"""
    def __init__(self):
        self._manual_override = None
        self._last_change = time.time()
    
    def read_digital(self):
        """Read digital value: 0 = light, 1 = dark"""
        # Manual override for testing
        if self._manual_override is not None:
            return 0 if self._manual_override else 1
        
        # Day/night simulation: light 6:00-22:00
        current_hour = datetime.now().hour
        if 6 <= current_hour < 22:
            base_is_light = True
        else:
            base_is_light = False
        
        # Occasional random changes for testing
        if time.time() - self._last_change > random.randint(120, 300):
            if random.random() < 0.3:
                self._last_change = time.time()
                return 0 if not base_is_light else 1  # Flip for testing
        
        return 0 if base_is_light else 1

class SensorService:
    """🔥 ИСПРАВЛЕННЫЙ sensor service с приоритетом физических сенсоров"""
    
    def __init__(self):
        self.sensor_available = False
        self.gpio_available = False
        self.using_mock_sensors = True  # Начинаем с mock, переключаемся на real
        
        # Sensors
        self.ens = None
        self.aht = None
        self.ldr = None
        
        # GPIO (унифицированная инициализация с volume_service)
        self.gpio_lib = None
        self.gpio_handle = None
        
        # Threading
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        
        # Readings
        self._readings = {
            'temperature': 22.5,
            'humidity': 45.0,
            'co2': 800,
            'tvoc': 250,
            'air_quality': 'Good',
            'light_level': True,  # True = light, False = dark
            'light_raw': 1
        }
        
        # Light sensor state tracking
        self._last_light_state = None
        self._light_readings = []
        self._confidence_level = 0.7
        
        logger.info("SensorService initialized")
    
    def start(self):
        """🔥 ИСПРАВЛЕН: Приоритет физических сенсоров"""
        logger.info("Starting sensor service...")
        
        # 🔥 ПОРЯДОК ВАЖЕН: Сначала пытаемся физические сенсоры
        self._try_initialize_real_sensors()
        
        # Только если физические не работают - используем mock
        if not self.sensor_available and not self.gpio_available:
            logger.warning("🔄 Falling back to mock sensors")
            self._init_mock_sensors()
        
        # Start reading thread
        self.running = True
        self._stop_event.clear()
        self.thread = Thread(target=self._sensor_loop, daemon=True)
        self.thread.start()
        
        mode = "Physical" if not self.using_mock_sensors else "Mock"
        logger.info(f"✅ Sensor service started - Mode: {mode}")
        return True
    
    def _try_initialize_real_sensors(self):
        """🔥 НОВОЕ: Систематичная попытка инициализации физических сенсоров"""
        success = False
        
        # Попытка 1: I2C сенсоры
        logger.info("🔍 Attempting I2C sensor initialization...")
        if self._init_i2c_sensors():
            success = True
            logger.info("✅ I2C sensors initialized successfully")
        
        # Попытка 2: GPIO сенсоры (свет)
        logger.info("🔍 Attempting GPIO sensor initialization...")
        if self._init_gpio_sensors():
            success = True
            logger.info("✅ GPIO sensors initialized successfully")
        
        if success:
            self.using_mock_sensors = False
            logger.info("🎉 Physical sensors active!")
        else:
            logger.warning("❌ No physical sensors available")
    
    def _init_i2c_sensors(self):
        """🔥 ИСПРАВЛЕНО: Более надежная инициализация I2C"""
        if not I2C_AVAILABLE:
            logger.debug("I2C libraries not available")
            return False
            
        try:
            logger.debug("Testing I2C availability...")
            
            # Создаем I2C соединение
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Попытка инициализации ENS160
            try:
                self.ens = adafruit_ens160.ENS160(i2c, address=ENS160_ADDRESS)
                test_co2 = self.ens.eCO2
                logger.debug(f"ENS160 test reading: CO2={test_co2}")
            except Exception as e:
                logger.debug(f"ENS160 init failed: {e}")
                self.ens = None
            
            # Попытка инициализации AHT21
            try:
                self.aht = adafruit_ahtx0.AHTx0(i2c, address=AHT21_ADDRESS)
                test_temp = self.aht.temperature
                logger.debug(f"AHT21 test reading: temp={test_temp}")
            except Exception as e:
                logger.debug(f"AHT21 init failed: {e}")
                self.aht = None
            
            # Считаем успешным если хотя бы один сенсор работает
            if self.ens or self.aht:
                self.sensor_available = True
                logger.info("✅ I2C sensors initialized")
                return True
            else:
                logger.warning("❌ No I2C sensors available")
                return False
            
        except Exception as e:
            logger.warning(f"I2C initialization failed: {e}")
            return False
    
    def _init_gpio_sensors(self):
        """🔥 ИСПРАВЛЕНО: Унифицированная GPIO инициализация с volume_service"""
        try:
            # Используем те же библиотеки и подход что и volume_service
            
            # Попытка lgpio (Pi 5)
            if LGPIO_AVAILABLE:
                try:
                    if not hasattr(self, 'gpio_handle') or self.gpio_handle is None:
                        self.gpio_handle = lgpio.gpiochip_open(0)
                    
                    lgpio.gpio_claim_input(self.gpio_handle, LDR_GPIO_PIN, lgpio.SET_PULL_UP)
                    test_read = lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                    
                    self.gpio_lib = "lgpio"
                    self.gpio_available = True
                    logger.info(f"✅ GPIO light sensor initialized with lgpio (test: {test_read})")
                    return True
                    
                except Exception as e:
                    logger.debug(f"lgpio GPIO init failed: {e}")
                    if hasattr(self, 'gpio_handle') and self.gpio_handle:
                        try:
                            lgpio.gpiochip_close(self.gpio_handle)
                        except:
                            pass
                        self.gpio_handle = None
            
            # Fallback на RPi.GPIO
            if RPI_GPIO_AVAILABLE:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(LDR_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    test_read = GPIO.input(LDR_GPIO_PIN)
                    
                    self.gpio_lib = "RPi.GPIO"
                    self.gpio_available = True
                    logger.info(f"✅ GPIO light sensor initialized with RPi.GPIO (test: {test_read})")
                    return True
                    
                except Exception as e:
                    logger.debug(f"RPi.GPIO init failed: {e}")
                    try:
                        GPIO.cleanup()
                    except:
                        pass
            
            logger.warning("❌ GPIO light sensor initialization failed")
            return False
            
        except Exception as e:
            logger.error(f"GPIO sensor initialization error: {e}")
            return False
    
    def _init_mock_sensors(self):
        """Initialize mock sensors as fallback"""
        try:
            self.ens = DummyENS160(None)
            self.aht = DummyAHTx0(None)
            self.ldr = DummyLDR()
            
            self.sensor_available = True
            self.using_mock_sensors = True
            logger.info("Mock sensors initialized")
            
        except Exception as e:
            logger.error(f"Error initializing mock sensors: {e}")
    
    def _sensor_loop(self):
        """Main sensor reading loop"""
        while self.running and not self._stop_event.is_set():
            try:
                self._update_readings()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in sensor loop: {e}")
                time.sleep(5)
    
    def _update_readings(self):
        """Update all sensor readings"""
        try:
            # Update I2C sensors
            if self.ens:
                try:
                    self._readings['co2'] = self.ens.eCO2
                    self._readings['tvoc'] = self.ens.TVOC
                    aqi_num = self.ens.AQI
                    self._readings['air_quality'] = AIR_QUALITY_LEVELS.get(aqi_num, "Unknown")
                except Exception:
                    pass
            
            if self.aht:
                try:
                    self._readings['temperature'] = self.aht.temperature
                    self._readings['humidity'] = self.aht.relative_humidity
                except Exception:
                    pass
            
            # Update light sensor
            raw_value = self._read_light_sensor()
            self._readings['light_raw'] = raw_value
            
            # Convert to light level (0 = light, 1 = dark)
            light_level = (raw_value == 0) if raw_value is not None else True
            
            # Simple smoothing
            self._light_readings.append(light_level)
            if len(self._light_readings) > 4:
                self._light_readings.pop(0)
            
            # Calculate stable light level
            if len(self._light_readings) >= 3:
                light_count = sum(self._light_readings)
                self._readings['light_level'] = light_count >= len(self._light_readings) / 2
            
        except Exception as e:
            logger.error(f"Error updating readings: {e}")
    
    def _read_light_sensor(self):
        """Read raw light sensor value"""
        try:
            if self.gpio_available:
                if self.gpio_lib == "lgpio":
                    return lgpio.gpio_read(self.gpio_handle, LDR_GPIO_PIN)
                elif self.gpio_lib == "RPi.GPIO":
                    return GPIO.input(LDR_GPIO_PIN)
            elif self.ldr:
                return self.ldr.read_digital()
            
            return None
        except Exception as e:
            logger.error(f"Error reading light sensor: {e}")
            return None
    
    def get_readings(self):
        """Get current sensor readings"""
        return self._readings.copy()
    
    def get_light_level(self):
        """Get current light level for auto-theme"""
        return self._readings.get('light_level', True)
    
    def read_light_sensor(self):
        """Direct light sensor reading for calibration"""
        return self._read_light_sensor()
    
    def get_status(self):
        """🔥 НОВОЕ: Получение статуса сервиса"""
        return {
            "sensor_available": self.sensor_available,
            "gpio_available": self.gpio_available,
            "using_mock_sensors": self.using_mock_sensors,
            "gpio_lib": self.gpio_lib,
            "running": self.running,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "readings": self._readings
        }
    
    def stop(self):
        """🔥 ИСПРАВЛЕНО: Корректная остановка с cleanup"""
        if not self.running:
            return
        
        logger.info("Stopping sensor service...")
        self.running = False
        self._stop_event.set()
        
        # Ждем завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        # GPIO cleanup
        self._cleanup_gpio()
        
        logger.info("Sensor service stopped")
    
    def _cleanup_gpio(self):
        """🔥 НОВОЕ: Proper GPIO cleanup"""
        try:
            if self.gpio_lib == "lgpio" and self.gpio_handle is not None:
                try:
                    lgpio.gpio_free(self.gpio_handle, LDR_GPIO_PIN)
                    lgpio.gpiochip_close(self.gpio_handle)
                except Exception as e:
                    logger.debug(f"lgpio cleanup error: {e}")
                self.gpio_handle = None
                
            elif self.gpio_lib == "RPi.GPIO":
                try:
                    GPIO.cleanup([LDR_GPIO_PIN])
                except Exception as e:
                    logger.debug(f"RPi.GPIO cleanup error: {e}")
            
            self.gpio_available = False
            logger.debug("GPIO cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in GPIO cleanup: {e}")