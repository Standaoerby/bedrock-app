#!/usr/bin/env python3

import threading
import time
from app.logger import app_logger as logger
from app.event_bus import event_bus
from kivy.app import App
from kivy.clock import Clock  # 🚨 КРИТИЧЕСКИ ВАЖНО: Импорт Clock для thread-safe операций


class AutoThemeService:
    """
    Сервис автоматического переключения темы на основе освещенности
    Версия 1.3.0 - ИСПРАВЛЕНО: Все критические ошибки и улучшена консистентность
    """
    
    def __init__(self, sensor_service, theme_manager):
        self.sensor_service = sensor_service
        self.theme_manager = theme_manager
        self.enabled = False
        self.running = False
        self.threshold_seconds = 3  # Время удержания для переключения
        self.calibration_time = 3   # Время калибровки
        self.check_thread = None
        
        # Состояние освещенности
        self.current_light_state = None  # True = светло, False = темно
        self.state_start_time = None
        self.state_stable = False
        
        # Блокировка для thread safety
        self._lock = threading.RLock()
        
        logger.info("AutoThemeService initialized")
        
    def start(self):
        """Запуск сервиса"""
        if self.running:
            return
            
        self.running = True
        self.check_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.check_thread.start()
        logger.info("AutoThemeService started")
        
    def stop(self):
        """Остановка сервиса"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=1)
        logger.info("AutoThemeService stopped")
        
    def set_enabled(self, enabled):
        """🚨 ИСПРАВЛЕНО: Включение/выключение автоматической смены темы БЕЗ повторной калибровки"""
        with self._lock:
            old_enabled = self.enabled
            self.enabled = enabled
            
            # Логируем только изменения состояния
            if old_enabled != enabled:
                logger.info(f"Auto-theme {'enabled' if enabled else 'disabled'}")
            
            # НЕ калибруем повторно - калибровка должна быть сделана заранее через calibrate_sensor()
            
    def is_enabled(self):
        """Проверка включен ли сервис"""
        with self._lock:
            return self.enabled
            
    def calibrate(self):
        """Калибровка датчика освещенности"""
        if self.enabled:
            self._calibrate_sensor()

    def calibrate_sensor(self, threshold_seconds=None):
        """🚨 ИСПРАВЛЕНО: Публичный метод калибровки БЕЗ дублирования логов"""
        with self._lock:
            if threshold_seconds is not None:
                self.threshold_seconds = max(1, min(threshold_seconds, 10))  # Ограничиваем диапазон 1-10 секунд
                self.calibration_time = self.threshold_seconds
            
            # Выполняем калибровку (логирование внутри _calibrate_sensor)
            self._calibrate_sensor()
            
    def _calibrate_sensor(self):
        """🚨 ИСПРАВЛЕНО: Внутренняя калибровка БЕЗ дублирования логов"""
        try:
            if hasattr(self.sensor_service, 'calibrate_light_sensor'):
                # 🚨 ИСПРАВЛЕНО: Передаем параметр threshold_seconds и НЕ логируем результат
                confidence = self.sensor_service.calibrate_light_sensor(self.threshold_seconds)
                
                # Сброс состояния после калибровки
                self.current_light_state = None
                self.state_start_time = None
                self.state_stable = False
                
                # 🚨 ИСПРАВЛЕНО: Одно компактное сообщение вместо трёх
                logger.info(f"Auto-theme calibrated: {self.threshold_seconds}s threshold, confidence: {confidence:.2f}")
            else:
                logger.warning("Sensor service doesn't support light calibration")
                
        except Exception as e:
            logger.error(f"Error calibrating light sensor: {e}")
            
    def force_check(self):
        """🚨 ИСПРАВЛЕНО: Принудительная проверка освещенности БЕЗ избыточного логирования"""
        with self._lock:
            if not self.enabled:
                return
                
            # Выполняем проверку без дополнительного логирования
            self._check_light_level()
            
    def check_and_update_theme(self):
        """Проверка и обновление темы - публичный метод для вызова из UI"""
        with self._lock:
            if not self.enabled:
                return False
                
            return self._check_light_level()

    def get_status(self):
        """🚨 ДОБАВЛЕНО: Получение статуса сервиса"""
        with self._lock:
            try:
                sensor_available = hasattr(self.sensor_service, 'get_light_level') if self.sensor_service else False
                current_light = self.sensor_service.get_light_level() if sensor_available else True
                using_mock = getattr(self.sensor_service, 'using_mock_sensors', True) if self.sensor_service else True
                
                return {
                    "enabled": self.enabled,
                    "running": self.running,
                    "sensor_available": sensor_available,
                    "service_running": self.running,
                    "current_light": current_light,
                    "using_mock": using_mock,
                    "threshold_seconds": self.threshold_seconds,
                    "current_state": self.current_light_state,
                    "state_stable": self.state_stable
                }
            except Exception as e:
                logger.error(f"Error getting AutoTheme status: {e}")
                return {
                    "enabled": self.enabled,
                    "running": self.running,
                    "sensor_available": False,
                    "error": str(e)
                }
            
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.running:
            try:
                if self.enabled:
                    self._check_light_level()
                    
                # Проверяем каждые 0.5 секунды
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in auto-theme monitor loop: {e}")
                time.sleep(1)
                
    def _check_light_level(self):
        """🚨 ИСПРАВЛЕНО: Проверка уровня освещенности и переключение темы"""
        try:
            # 🚨 ИСПРАВЛЕНО: Используем правильный метод get_light_level() вместо is_light_detected()
            is_light = self.sensor_service.get_light_level()
            
            current_time = time.time()
            
            # 🚨 ИСПРАВЛЕНО: Инициализируем состояние при первом запуске
            if self.current_light_state is None:
                self.current_light_state = is_light
                logger.info(f"🔄 Auto-theme initialized: {'Light' if is_light else 'Dark'} mode detected")
                return False
            
            # Логика гистерезиса для предотвращения частых переключений
            if is_light != self.current_light_state:
                # Изменилось состояние освещенности
                if self.state_start_time is None:
                    # Начинаем отсчет времени
                    self.state_start_time = current_time
                    self.state_stable = False
                    logger.info(f"Light state changed to {'light' if is_light else 'dark'}, starting timer")
                    
                elif current_time - self.state_start_time >= self.threshold_seconds:
                    # Состояние стабильно в течение порогового времени
                    if not self.state_stable:
                        self.state_stable = True
                        self.current_light_state = is_light
                        
                        # Переключаем тему
                        new_variant = "light" if is_light else "dark"
                        self._switch_theme(new_variant)
                        
                        # 🚨 ИСПРАВЛЕНО: Правильное логирование БЕЗ обрыва строки
                        confidence = 1.00 if current_time - self.state_start_time >= self.threshold_seconds else 0.75
                        logger.info(f"🌓 Auto-theme: {'Dark→Light' if is_light else 'Light→Dark'} (confidence: {confidence:.2f}) → {new_variant} theme")
                        
                        return True
                        
            else:
                # Состояние не изменилось - сбрасываем таймер
                if self.state_start_time is not None:
                    logger.info("Light state returned to previous - resetting timer")
                self.state_start_time = None
                self.state_stable = False
                
            # Если изменений нет или они нестабильны
            if not self.state_stable:
                logger.info("🔍 No stable light change detected")
                
        except Exception as e:
            logger.error(f"Error checking light level: {e}")
            return False
            
        return False
            
    def _switch_theme(self, variant):
        """🚨 ИСПРАВЛЕНО: Thread-safe переключение темы через главный поток Kivy"""
        try:
            # Переносим ВСЕ операции с UI в главный поток через Clock.schedule_once
            Clock.schedule_once(lambda dt: self._do_switch_theme_on_main_thread(variant), 0)
                
        except Exception as e:
            logger.error(f"Error scheduling theme switch: {e}")
            
    def _do_switch_theme_on_main_thread(self, variant):
        """🚨 ОКОНЧАТЕЛЬНО ИСПРАВЛЕНО: Выполнение переключения темы с правильным вызовом методов"""
        logger.info(f"🎨 Starting theme switch to variant: {variant}")
        
        try:
            app = App.get_running_app()
            if not app:
                logger.error("❌ Cannot switch theme - App instance not available")
                return
                
            logger.info(f"✅ App instance found: {type(app).__name__}")
                
            if not hasattr(app, 'theme_manager') or not app.theme_manager:
                logger.error("❌ Cannot switch theme - ThemeManager not available")
                return
            
            logger.info(f"✅ ThemeManager found: {type(app.theme_manager).__name__}")
            
            # Получаем текущую тему
            current_theme = getattr(app.theme_manager, 'current_theme', None)
            if not current_theme:
                current_theme = getattr(app.theme_manager, 'theme_name', None)
            if not current_theme:
                logger.warning("⚠️ No current theme set, using default 'minecraft'")
                current_theme = "minecraft"
            
            logger.info(f"📋 Current theme: {current_theme}")
            
            # Проверяем, нужно ли переключать
            current_variant = getattr(app.theme_manager, 'current_variant', None)
            if not current_variant:
                current_variant = getattr(app.theme_manager, 'variant', None)
                
            logger.info(f"📋 Current variant: {current_variant} → New variant: {variant}")
                
            if current_variant == variant:
                logger.info(f"⏭️ Theme variant already set to {variant}, skipping")
                return  # Тема уже установлена
            
            # 🚨 ИСПРАВЛЕНО: Используем правильный метод load_theme с проверкой существования
            logger.info(f"🔄 Loading theme: {current_theme}/{variant}")
            
            if hasattr(app.theme_manager, 'load_theme'):
                success = app.theme_manager.load_theme(current_theme, variant)
                logger.info(f"📋 load_theme() result: {success}")
            elif hasattr(app.theme_manager, 'load'):
                success = app.theme_manager.load(current_theme, variant)
                logger.info(f"📋 load() result: {success}")
            else:
                logger.error("❌ ThemeManager has no load_theme or load method")
                return
                
            if not success:
                logger.error(f"❌ Failed to load theme {current_theme}/{variant}")
                return
            
            logger.info(f"✅ Theme loaded successfully: {current_theme}/{variant}")
            
            # Обновляем конфиг пользователя
            if hasattr(app, 'user_config') and app.user_config:
                try:
                    app.user_config.set('variant', variant)
                    logger.info(f"✅ Variant saved to config: {variant}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to save variant to config: {e}")
            
            # 🚨 ИСПРАВЛЕНО: Публикуем событие для обновления UI
            try:
                from app.event_bus import event_bus
                event_bus.publish("theme_changed", {
                    "theme": current_theme,
                    "variant": variant,
                    "source": "auto_theme_service"
                })
                logger.info(f"✅ theme_changed event published")
            except Exception as e:
                logger.warning(f"⚠️ Failed to publish theme_changed event: {e}")
            
            # 🚨 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Используем правильное имя метода!
            try:
                if hasattr(app.root, 'refresh_theme_everywhere'):
                    Clock.schedule_once(lambda dt: app.root.refresh_theme_everywhere(), 0.1)
                    logger.info(f"✅ Root widget refresh_theme_everywhere() scheduled")
                elif hasattr(app.root, 'refresh_theme'):
                    Clock.schedule_once(lambda dt: app.root.refresh_theme(), 0.1)
                    logger.info(f"✅ Root widget refresh_theme() scheduled")
                else:
                    logger.warning(f"⚠️ Root widget has no refresh_theme methods")
                    # Пытаемся обновить тему напрямую через все экраны
                    try:
                        if hasattr(app.root, 'screen_manager') and app.root.screen_manager:
                            for screen_name in app.root.screen_manager.screen_names:
                                screen = app.root.screen_manager.get_screen(screen_name)
                                if hasattr(screen, 'refresh_theme'):
                                    Clock.schedule_once(lambda dt, s=screen: s.refresh_theme(), 0.1)
                                    logger.info(f"✅ Screen {screen_name}.refresh_theme() scheduled")
                    except Exception as e2:
                        logger.warning(f"⚠️ Failed to refresh individual screens: {e2}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to refresh UI: {e}")
            
            logger.info(f"🎉 Theme successfully switched to {current_theme}/{variant}")
            
        except Exception as e:
            logger.error(f"❌ Error switching theme in main thread: {e}")
            import traceback
            logger.error(f"Theme switch traceback: {traceback.format_exc()}")

# ИСПРАВЛЕНО: НЕ создаем глобальный экземпляр
# Каждое приложение должно создать свой экземпляр через main.py

def validate_auto_theme_service_module():
    """Валидация модуля AutoThemeService для отладки"""
    try:
        # Создаем мок-объекты для тестирования
        class MockSensorService:
            def get_light_level(self):
                return True
            def calibrate_light_sensor(self, threshold=3):
                return 0.8
                
        class MockThemeManager:
            def load_theme(self, theme, variant):
                return True
            def load(self, theme, variant):
                return True
            current_theme = "minecraft"
            current_variant = "light"
        
        service = AutoThemeService(MockSensorService(), MockThemeManager())
        assert hasattr(service, 'calibrate_sensor'), "calibrate_sensor method missing"
        assert hasattr(service, 'check_and_update_theme'), "check_and_update_theme method missing"
        assert hasattr(service, 'get_status'), "get_status method missing"
        print("✅ AutoThemeService module validation passed")
        return True
    except Exception as e:
        print(f"❌ AutoThemeService module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_auto_theme_service_module()