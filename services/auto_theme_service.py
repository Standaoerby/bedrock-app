#!/usr/bin/env python3

import threading
import time
from app.logger import app_logger as logger
from app.event_bus import event_bus
from kivy.app import App
from kivy.clock import Clock


class AutoThemeService:
    """
    Сервис автоматического переключения темы на основе освещенности
    Версия 2.0.0 - ФИНАЛЬНАЯ ВЕРСИЯ с пересозданием экранов
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
        
        logger.info("AutoThemeService v2.0.0 initialized with screen recreation")
        
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
        """Включение/выключение автоматической смены темы"""
        with self._lock:
            old_enabled = self.enabled
            self.enabled = enabled
            
            if old_enabled != enabled:
                logger.info(f"Auto-theme {'enabled' if enabled else 'disabled'}")
            
    def is_enabled(self):
        """Проверка включен ли сервис"""
        with self._lock:
            return self.enabled
            
    def calibrate_sensor(self, threshold_seconds=None):
        """Калибровка датчика освещения"""
        with self._lock:
            if threshold_seconds is not None:
                self.threshold_seconds = max(1, min(threshold_seconds, 10))
                self.calibration_time = self.threshold_seconds
            
            self._calibrate_sensor()
            
    def _calibrate_sensor(self):
        """Внутренняя калибровка"""
        try:
            if hasattr(self.sensor_service, 'calibrate_light_sensor'):
                confidence = self.sensor_service.calibrate_light_sensor(self.threshold_seconds)
                
                # Сброс состояния после калибровки
                self.current_light_state = None
                self.state_start_time = None
                self.state_stable = False
                
                logger.info(f"Auto-theme calibrated: {self.threshold_seconds}s threshold, confidence: {confidence:.2f}")
            else:
                logger.warning("Sensor service doesn't support light calibration")
                
        except Exception as e:
            logger.error(f"Error calibrating light sensor: {e}")
            
    def force_check(self):
        """Принудительная проверка освещенности"""
        with self._lock:
            if not self.enabled:
                return
                
            self._check_light_level()
            
    def get_status(self):
        """Получение статуса сервиса"""
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
        """Проверка уровня освещенности и переключение темы"""
        try:
            is_light = self.sensor_service.get_light_level()
            current_time = time.time()
            
            # Инициализируем состояние при первом запуске
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
                        
                        confidence = 1.00 if current_time - self.state_start_time >= self.threshold_seconds else 0.75
                        logger.info(f"🌓 Auto-theme: {'Dark→Light' if is_light else 'Light→Dark'} (confidence: {confidence:.2f}) → {new_variant} theme")
                        
                        return True
                        
            else:
                # Состояние не изменилось - сбрасываем таймер
                if self.state_start_time is not None:
                    logger.info("Light state returned to previous - resetting timer")
                self.state_start_time = None
                self.state_stable = False
                
        except Exception as e:
            logger.error(f"Error checking light level: {e}")
            return False
            
        return False
            
    def _switch_theme(self, variant):
        """Thread-safe переключение темы через главный поток Kivy"""
        try:
            # Переносим ВСЕ операции с UI в главный поток через Clock.schedule_once
            Clock.schedule_once(lambda dt: self._do_switch_theme_on_main_thread(variant), 0)
                
        except Exception as e:
            logger.error(f"Error scheduling theme switch: {e}")
            
    def _do_switch_theme_on_main_thread(self, variant):
        """🚀 ФИНАЛЬНАЯ ВЕРСИЯ: Пересоздание экранов вместо обновления виджетов"""
        logger.info(f"🎨 Theme switch with screen recreation: {variant}")
        
        try:
            app = App.get_running_app()
            if not app or not hasattr(app, 'theme_manager') or not app.theme_manager:
                logger.error("❌ App or ThemeManager not available")
                return
            
            # Получаем информацию о текущем состоянии
            current_theme = getattr(app.theme_manager, 'current_theme', 'minecraft')
            current_variant = getattr(app.theme_manager, 'current_variant', 'light')
            current_screen = "home"  # дефолт
            
            # 🔧 ДИАГНОСТИКА: Проверяем доступ к root widget
            if not hasattr(app, 'root') or not app.root:
                logger.error("❌ App.root not available")
                return
            
            logger.debug(f"📋 App.root type: {type(app.root).__name__}")
            
            # 🔧 УЛУЧШЕННЫЙ ПОИСК ScreenManager
            screen_manager = self._find_screen_manager(app)
            if not screen_manager:
                logger.error("❌ ScreenManager not found anywhere!")
                return
            
            # Получаем текущий экран
            try:
                current_screen = screen_manager.current
                logger.info(f"📋 Current screen before switch: {current_screen}")
            except Exception as e:
                logger.warning(f"⚠️ Could not get current screen: {e}")
                current_screen = "home"
                
            if current_variant == variant:
                logger.info(f"⏭️ Theme already {variant}")
                return
            
            logger.info(f"🔄 Switching {current_theme}: {current_variant} → {variant} (screen: {current_screen})")
            
            # 1. Загружаем новую тему
            success = False
            if hasattr(app.theme_manager, 'load_theme'):
                success = app.theme_manager.load_theme(current_theme, variant)
            elif hasattr(app.theme_manager, 'load'):
                success = app.theme_manager.load(current_theme, variant)
                
            if not success:
                logger.error(f"❌ Failed to load theme")
                return
            
            logger.info(f"✅ Theme loaded: {current_theme}/{variant}")
            
            # 2. Сохраняем в конфиг
            if hasattr(app, 'user_config') and app.user_config:
                app.user_config.set('variant', variant)
            
            # 3. 🚀 ПЕРЕСОЗДАЕМ ЭКРАНЫ
            self._recreate_screens_simple(app, screen_manager, current_screen)
            
            # 4. Публикуем событие (для TopMenu и других подписчиков)
            from app.event_bus import event_bus
            event_bus.publish("theme_changed", {
                "theme": current_theme,
                "variant": variant,
                "source": "auto_theme_recreation"
            })
            
            logger.info(f"🎉 Theme recreation completed: {current_theme}/{variant}")
            
        except Exception as e:
            logger.error(f"❌ Error in theme recreation: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _find_screen_manager(self, app):
        """🔧 УЛУЧШЕННЫЙ поиск ScreenManager с диагностикой"""
        logger.debug("🔍 Searching for ScreenManager...")
        
        # Метод 1: app.root.screen_manager
        if hasattr(app.root, 'screen_manager') and app.root.screen_manager:
            logger.debug("✅ Found via app.root.screen_manager")
            return app.root.screen_manager
        
        # Метод 2: app.root.ids.sm  
        if hasattr(app.root, 'ids') and hasattr(app.root.ids, 'sm'):
            logger.debug("✅ Found via app.root.ids.sm")
            return app.root.ids.sm
        
        # Метод 3: app.root.ids['sm']
        if hasattr(app.root, 'ids') and 'sm' in app.root.ids:
            logger.debug("✅ Found via app.root.ids['sm']")
            return app.root.ids['sm']
        
        # Метод 4: Поиск по дереву виджетов
        if hasattr(app.root, 'walk'):
            for widget in app.root.walk():
                if widget.__class__.__name__ == 'ScreenManager':
                    logger.debug("✅ Found via widget tree walk")
                    return widget
        
        # 🔧 ДИАГНОСТИКА: Выводим что есть в app.root
        logger.debug(f"📋 app.root attributes: {[attr for attr in dir(app.root) if not attr.startswith('_')]}")
        
        if hasattr(app.root, 'ids'):
            logger.debug(f"📋 app.root.ids keys: {list(app.root.ids.keys()) if app.root.ids else 'No ids'}")
        
        logger.warning("❌ ScreenManager not found in any location")
        return None

    def _recreate_screens_simple(self, app, screen_manager, restore_screen="home"):
        """🚀 ПРОСТОЕ пересоздание экранов + TopMenu"""
        try:
            logger.info("🔄 Recreating screens and TopMenu...")
            
            # Импортируем классы экранов
            from pages.home import HomeScreen
            from pages.alarm import AlarmScreen  
            from pages.schedule import ScheduleScreen
            from pages.weather import WeatherScreen
            from pages.pigs import PigsScreen
            from pages.settings import SettingsScreen
            
            # Удаляем старые экраны
            screen_manager.clear_widgets()
            logger.debug("🗑️ Old screens cleared")
            
            # Создаем новые экраны (они автоматически используют актуальную тему)
            screens = [
                HomeScreen(name="home"),
                AlarmScreen(name="alarm"),
                ScheduleScreen(name="schedule"), 
                WeatherScreen(name="weather"),
                PigsScreen(name="pigs"),
                SettingsScreen(name="settings")
            ]
            
            # Добавляем новые экраны
            for screen in screens:
                screen_manager.add_widget(screen)
                logger.debug(f"✅ Created new {screen.name} screen")
            
            # Восстанавливаем текущий экран
            screen_manager.current = restore_screen
            app.root.current_page = restore_screen
            
            # 🔧 ПРИНУДИТЕЛЬНОЕ обновление TopMenu
            top_menu = None
            if hasattr(app.root, 'ids') and 'topmenu' in app.root.ids:
                top_menu = app.root.ids.topmenu
            elif hasattr(app.root, 'ids') and 'top_menu' in app.root.ids:
                top_menu = app.root.ids.top_menu
            
            if top_menu:
                # Обновляем текущую страницу
                top_menu.current_page = restore_screen
                
                # 🚀 ПРИНУДИТЕЛЬНО обновляем тему TopMenu
                if hasattr(top_menu, 'force_complete_refresh'):
                    top_menu.force_complete_refresh()
                    logger.debug("✅ TopMenu force refreshed")
                elif hasattr(top_menu, 'refresh_theme'):
                    top_menu.refresh_theme()
                    logger.debug("✅ TopMenu theme refreshed")
                
                logger.debug("✅ TopMenu fully updated")
            else:
                logger.warning("⚠️ TopMenu not found for update")
            
            # Обновляем overlay изображение
            if hasattr(app.root, '_update_overlay'):
                app.root._update_overlay()
                logger.debug("✅ Overlay updated")
            
            logger.info(f"🎉 Screens + TopMenu recreated! Current: {restore_screen}")
            
        except Exception as e:
            logger.error(f"❌ Screen recreation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _recreate_top_menu_simple(self, app, current_screen):
        """🚀 ПРОСТОЕ пересоздание TopMenu с актуальной темой"""
        try:
            logger.debug("🔄 Recreating TopMenu...")
            
            if not hasattr(app.root, 'ids') or 'topmenu' not in app.root.ids:
                logger.warning("⚠️ TopMenu not found in root.ids")
                return
            
            old_top_menu = app.root.ids.topmenu
            parent_container = old_top_menu.parent
            
            if not parent_container:
                logger.warning("⚠️ TopMenu parent not found")
                return
            
            # Запоминаем позицию в контейнере
            old_index = parent_container.children.index(old_top_menu)
            
            # Удаляем старый TopMenu
            parent_container.remove_widget(old_top_menu)
            logger.debug("🗑️ Old TopMenu removed")
            
            # Создаем новый TopMenu (автоматически получает актуальную тему!)
            from widgets.top_menu import TopMenu
            new_top_menu = TopMenu()
            new_top_menu.current_page = current_screen
            
            # Устанавливаем размеры из актуальной темы
            tm = app.theme_manager
            if tm:
                new_top_menu.size_hint_y = None
                new_top_menu.height = tm.get_param("menu_height") or 56
            
            # Добавляем в ту же позицию
            parent_container.add_widget(new_top_menu, index=old_index)
            
            # Обновляем ссылку в ids
            app.root.ids.topmenu = new_top_menu
            
            # Обновляем текст кнопок на актуальном языке
            if hasattr(new_top_menu, 'refresh_text'):
                new_top_menu.refresh_text()
            
            logger.info("🎉 TopMenu recreated with new theme!")
            
        except Exception as e:
            logger.error(f"❌ TopMenu recreation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def debug_screen_manager(self):
        """🔧 ОТЛАДКА: Диагностика ScreenManager"""
        try:
            app = App.get_running_app()
            if not app or not app.root:
                logger.info("❌ No app or root widget")
                return
            
            logger.info("🔧 === SCREEN MANAGER + TOPMENU DEBUG ===")
            logger.info(f"📋 app.root type: {type(app.root).__name__}")
            logger.info(f"📋 app.root.screen_manager: {getattr(app.root, 'screen_manager', 'NOT_FOUND')}")
            
            if hasattr(app.root, 'ids'):
                logger.info(f"📋 app.root.ids: {list(app.root.ids.keys())}")
                
                # ScreenManager info
                if 'sm' in app.root.ids:
                    sm = app.root.ids.sm
                    logger.info(f"📋 sm type: {type(sm).__name__}")
                    logger.info(f"📋 sm.screen_names: {list(sm.screen_names) if hasattr(sm, 'screen_names') else 'NO_SCREENS'}")
                    logger.info(f"📋 sm.current: {getattr(sm, 'current', 'NO_CURRENT')}")
                
                # TopMenu info
                if 'topmenu' in app.root.ids:
                    tm = app.root.ids.topmenu
                    logger.info(f"📋 topmenu type: {type(tm).__name__}")
                    logger.info(f"📋 topmenu.current_page: {getattr(tm, 'current_page', 'NO_CURRENT_PAGE')}")
                    logger.info(f"📋 topmenu.height: {getattr(tm, 'height', 'NO_HEIGHT')}")
                else:
                    logger.info(f"📋 topmenu: NOT_FOUND")
            
            # Поиск через walk
            screen_managers = []
            if hasattr(app.root, 'walk'):
                for widget in app.root.walk():
                    if 'ScreenManager' in widget.__class__.__name__:
                        screen_managers.append(widget)
            
            logger.info(f"📋 Found ScreenManagers via walk: {len(screen_managers)}")
            logger.info("🔧 ===========================================")
            
        except Exception as e:
            logger.error(f"Debug failed: {e}")

    def test_recreation(self):
        """🧪 ТЕСТ: Ручное тестирование пересоздания экранов + TopMenu"""
        try:
            app = App.get_running_app()
            logger.info("🧪 Testing screen + TopMenu recreation...")
            
            screen_manager = self._find_screen_manager(app)
            if screen_manager:
                current = getattr(screen_manager, 'current', 'home')
                self._recreate_screens_simple(app, screen_manager, current)
                logger.info("✅ Recreation test completed")
            else:
                logger.error("❌ Cannot test - ScreenManager not found")
                
        except Exception as e:
            logger.error(f"❌ Recreation test failed: {e}")


# Валидация модуля
def validate_auto_theme_service_module():
    """Валидация модуля AutoThemeService для отладки"""
    try:
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
        assert hasattr(service, '_find_screen_manager'), "_find_screen_manager method missing"
        assert hasattr(service, '_recreate_screens_simple'), "_recreate_screens_simple method missing"
        assert hasattr(service, '_recreate_top_menu_simple'), "_recreate_top_menu_simple method missing"
        assert hasattr(service, 'debug_screen_manager'), "debug_screen_manager method missing"
        print("✅ AutoThemeService v2.0.0 module validation passed")
        return True
    except Exception as e:
        print(f"❌ AutoThemeService module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_auto_theme_service_module()