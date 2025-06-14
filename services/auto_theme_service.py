# services/auto_theme_service.py
# 🔥 ИСПРАВЛЕНА КОНСИСТЕНТНОСТЬ: унифицированы вызовы методов

import time
import threading
from kivy.app import App
from kivy.clock import Clock
from app.logger import app_logger as logger
from app.event_bus import event_bus


class AutoThemeService:
    """
    🔥 ИСПРАВЛЕННЫЙ сервис автоматического переключения темы по датчику освещенности
    
    ИСПРАВЛЕНИЯ КОНСИСТЕНТНОСТИ:
    - Унифицированы вызовы theme_manager.load() везде
    - Добавлена проверка доступности theme_manager
    - Улучшена обработка ошибок
    """
    
    def __init__(self, sensor_service, threshold_seconds=3):
        self.sensor_service = sensor_service
        self.threshold_seconds = threshold_seconds
        self.calibration_time = threshold_seconds
        
        # Состояние сервиса
        self.enabled = False
        self.monitoring = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        
        # 🔥 ИСПРАВЛЕНО: Правильное отслеживание состояния
        self.current_light_state = None
        self.state_start_time = None
        self.state_stable = False
        
        logger.info(f"AutoThemeService initialized with {threshold_seconds}s threshold")

    # ================================================
    # УПРАВЛЕНИЕ СЕРВИСОМ
    # ================================================

    def start(self):
        """Запуск сервиса автоматического переключения тем"""
        with self._lock:
            if self.monitoring:
                logger.warning("AutoThemeService already running")
                return False
                
            try:
                self.enabled = True
                self.monitoring = True
                
                # Запускаем поток мониторинга
                self._monitor_thread = threading.Thread(
                    target=self._monitor_light_loop,
                    daemon=True,
                    name="AutoThemeMonitor"
                )
                self._monitor_thread.start()
                
                logger.info("🌓 AutoThemeService started")
                return True
                
            except Exception as e:
                logger.error(f"Error starting AutoThemeService: {e}")
                self.enabled = False
                self.monitoring = False
                return False

    def stop(self):
        """Остановка сервиса"""
        with self._lock:
            if not self.monitoring:
                return True
                
            try:
                self.enabled = False
                self.monitoring = False
                
                if self._monitor_thread and self._monitor_thread.is_alive():
                    # Ждём завершения потока
                    self._monitor_thread.join(timeout=2.0)
                    
                logger.info("🌓 AutoThemeService stopped")
                return True
                
            except Exception as e:
                logger.error(f"Error stopping AutoThemeService: {e}")
                return False

    def _monitor_light_loop(self):
        """🔥 ИСПРАВЛЕННЫЙ основной цикл мониторинга освещенности"""
        logger.info("Auto-theme monitoring started")
        
        while self.monitoring:
            try:
                if self.enabled and self.sensor_service:
                    self._check_light_level()
                time.sleep(1)  # Проверка каждую секунду
                
            except Exception as e:
                logger.error(f"Error in auto-theme monitor loop: {e}")
                time.sleep(1)

    # ================================================
    # ПРОВЕРКА ОСВЕЩЕННОСТИ
    # ================================================

    def _check_light_level(self):
        """🔥 ИСПРАВЛЕННАЯ проверка уровня освещенности и переключение темы"""
        try:
            # 🔥 ИСПРАВЛЕНО: Используем правильный метод get_light_level()
            is_light = self.sensor_service.get_light_level()
            current_time = time.time()
            
            # Логика гистерезиса для предотвращения частых переключений
            if is_light != self.current_light_state:
                # Изменилось состояние освещенности
                if self.state_start_time is None:
                    # Начинаем отсчет времени
                    self.state_start_time = current_time
                    self.state_stable = False
                    logger.debug(f"Light state changed to {'light' if is_light else 'dark'}, starting timer")
                    
                elif current_time - self.state_start_time >= self.threshold_seconds:
                    # Состояние стабильно в течение порогового времени
                    if not self.state_stable:
                        self.state_stable = True
                        self.current_light_state = is_light
                        
                        # 🔥 ИСПРАВЛЕНО: Переключаем тему через главный поток
                        new_variant = "light" if is_light else "dark"
                        Clock.schedule_once(
                            lambda dt: self._switch_theme_safely(new_variant), 0
                        )
                        
                        # 🔥 ИСПРАВЛЕНО: Компактное логирование
                        confidence = 1.00 if current_time - self.state_start_time >= self.threshold_seconds else 0.75
                        logger.info(f"🌓 Auto-theme: {'Dark→Light' if is_light else 'Light→Dark'} (confidence: {confidence:.2f})")
                        
                        return True
                        
            else:
                # Состояние не изменилось - сбрасываем таймер
                if self.state_start_time is not None:
                    logger.debug("Light state returned to previous - resetting timer")
                    self.state_start_time = None
                    self.state_stable = False
                
            # Если изменений нет или они нестабильны
            return False
                
        except Exception as e:
            logger.error(f"Error checking light level: {e}")
            return False

    def _switch_theme_safely(self, variant):
        """🔥 ИСПРАВЛЕНО: Безопасное переключение темы с консистентным API"""
        try:
            app = App.get_running_app()
            if not app:
                logger.error("Cannot access running app")
                return
                
            # 🔥 КОНСИСТЕНТНОСТЬ: Проверяем наличие theme_manager
            if not hasattr(app, 'theme_manager') or not app.theme_manager:
                logger.error("ThemeManager not available")
                return
                
            # Проверяем, нужно ли переключать
            current_variant = getattr(app.theme_manager, 'current_variant', None)
            if current_variant == variant:
                logger.debug(f"Theme already set to {variant}, skipping")
                return
                
            # Получаем текущую тему
            current_theme = getattr(app.theme_manager, 'current_theme', None)
            if not current_theme:
                logger.error("No current theme set")
                return
            
            # 🔥 КОНСИСТЕНТНОСТЬ: Используем load() как везде в проекте
            success = app.theme_manager.load(current_theme, variant)
            
            if success:
                # Обновляем конфиг пользователя
                if hasattr(app, 'user_config') and app.user_config:
                    app.user_config.set('variant', variant)
                
                logger.info(f"🌓 Auto-theme successfully switched to {variant}")
            else:
                logger.error(f"Failed to switch theme to {variant}")
            
            # 🔥 УБРАНО: event_bus.publish("theme_changed", ...)
            # Событие уже публикуется автоматически из load()!
            
        except Exception as e:
            logger.error(f"Error in safe theme switch: {e}")

    # ================================================
    # КАЛИБРОВКА И УПРАВЛЕНИЕ
    # ================================================

    def calibrate_sensor(self, threshold_seconds=None):
        """🔥 ИСПРАВЛЕНО: Публичный метод калибровки БЕЗ дублирования логов"""
        with self._lock:
            if threshold_seconds is not None:
                # Ограничиваем диапазон 1-10 секунд
                self.threshold_seconds = max(1, min(threshold_seconds, 10))
                self.calibration_time = self.threshold_seconds
            
            # Выполняем калибровку
            self._calibrate_sensor()
            
    def _calibrate_sensor(self):
        """🔥 ИСПРАВЛЕНО: Внутренняя калибровка БЕЗ дублирования логов"""
        try:
            if hasattr(self.sensor_service, 'calibrate_light_sensor'):
                # 🔥 ИСПРАВЛЕНО: Передаем параметр threshold_seconds
                confidence = self.sensor_service.calibrate_light_sensor(self.threshold_seconds)
                
                # Сброс состояния после калибровки
                self.current_light_state = None
                self.state_start_time = None
                self.state_stable = False
                
                # 🔥 ИСПРАВЛЕНО: Одно компактное сообщение вместо трёх
                logger.info(f"🌓 Auto-theme calibrated: {self.threshold_seconds}s threshold, confidence: {confidence}")
            else:
                logger.warning("Sensor service doesn't support light calibration")
                
        except Exception as e:
            logger.error(f"Error calibrating light sensor: {e}")

    def force_check(self):
        """🔥 ИСПРАВЛЕНО: Принудительная проверка освещенности"""
        with self._lock:
            if not self.enabled:
                logger.warning("AutoThemeService not enabled, cannot force check")
                return False
                
            try:
                # Сбрасываем состояние для немедленной проверки
                self.current_light_state = None
                self.state_start_time = None
                self.state_stable = False
                
                # Выполняем проверку через главный поток
                Clock.schedule_once(lambda dt: self._check_light_level(), 0)
                logger.info("🌓 Force light check triggered")
                return True
                
            except Exception as e:
                logger.error(f"Error in force check: {e}")
                return False

    # ================================================
    # СТАТУС И ДИАГНОСТИКА
    # ================================================

    def is_enabled(self):
        """Проверка включен ли сервис"""
        with self._lock:
            return self.enabled

    def is_running(self):
        """Проверка работает ли сервис"""
        with self._lock:
            return self.monitoring

    def get_status(self):
        """🔥 УЛУЧШЕНО: Получить подробный статус сервиса"""
        try:
            with self._lock:
                # Получаем статус датчика
                sensor_available = bool(self.sensor_service)
                using_mock = False
                current_light = True
                
                if self.sensor_service:
                    using_mock = getattr(self.sensor_service, 'using_mock_sensors', True)
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
                    "time_since_change": time.time() - self.state_start_time if self.state_start_time else None
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
        
        logger.info("🔍 AutoThemeService Diagnostics:")
        logger.info(f"  Service: {'🟢 Running' if status['service_running'] else '🔴 Stopped'}")
        logger.info(f"  Enabled: {'✅ Yes' if status['service_enabled'] else '❌ No'}")
        logger.info(f"  Sensor: {'🟢 Available' if status['sensor_available'] else '🔴 Offline'}")
        logger.info(f"  Mock: {'Yes' if status.get('using_mock') else 'No'}")
        logger.info(f"  Light: {'☀️ Light' if status.get('current_light') else '🌙 Dark'}")
        logger.info(f"  Threshold: {status.get('threshold_seconds')}s")
        
        # 🔥 НОВОЕ: Дополнительная диагностика theme_manager
        try:
            app = App.get_running_app()
            if app and hasattr(app, 'theme_manager'):
                tm_state = app.theme_manager.diagnose_state()
                logger.info(f"  ThemeManager: {'✅ Loaded' if tm_state['is_loaded'] else '❌ Not loaded'}")
                logger.info(f"  Current theme: {tm_state.get('current_theme', 'None')}/{tm_state.get('current_variant', 'None')}")
            else:
                logger.warning("  ThemeManager: ❌ Not available")
        except Exception as e:
            logger.error(f"  ThemeManager check failed: {e}")
        
        return status

    # ================================================
    # СОВМЕСТИМОСТЬ
    # ================================================

    def calibrate(self):
        """Совместимость: калибровка датчика освещенности"""
        if self.enabled:
            self._calibrate_sensor()