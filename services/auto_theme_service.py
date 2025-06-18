# services/auto_theme_service.py
# ФИНАЛЬНАЯ ВЕРСИЯ без ошибок методов

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
    Версия 2.0.2 - ФИНАЛЬНАЯ без ошибок методов
    """
    
    def __init__(self, sensor_service, theme_manager):
        self.sensor_service = sensor_service
        self.theme_manager = theme_manager
        self.enabled = False
        self.running = False
        self.threshold_seconds = 3
        self.calibration_time = 3
        self.check_thread = None
        
        # Состояние освещенности
        self.current_light_state = None
        self.state_start_time = None
        self.state_stable = False
        
        # Блокировка для thread safety
        self._lock = threading.RLock()
        
        logger.info("AutoThemeService v2.0.2 initialized - final version")
        
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
                logger.info(f"AutoTheme {'enabled' if enabled else 'disabled'}")
                
    def calibrate_sensor(self, threshold_seconds=3):
        """Калибровка датчика освещенности"""
        try:
            if not self.sensor_service:
                logger.error("Sensor service not available")
                return False
                
            logger.info(f"Calibrating light sensor for {threshold_seconds} seconds...")
            return self.sensor_service.calibrate_light_sensor(threshold_seconds)
            
        except Exception as e:
            logger.error(f"Error calibrating sensor: {e}")
            return False

    def force_check(self):
        """Принудительная проверка освещенности"""
        with self._lock:
            if not self.enabled:
                return
                
            self._check_light_and_switch()

    def get_status(self):
        """Получение статуса сервиса"""
        with self._lock:
            try:
                sensor_available = hasattr(self.sensor_service, 'get_light_level') if self.sensor_service else False
                return {
                    'enabled': self.enabled,
                    'running': self.running,
                    'sensor_available': sensor_available,
                    'current_light': self.current_light_state,
                    'threshold_seconds': self.threshold_seconds
                }
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return {'enabled': False, 'running': False, 'sensor_available': False}

    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.running:
            try:
                if self.enabled:
                    self._check_light_and_switch()
                time.sleep(1)  # Проверяем каждую секунду
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)  # Ждем дольше при ошибке

    def _check_light_and_switch(self):
        """Проверка освещенности и переключение темы"""
        try:
            is_bright = self.sensor_service.get_light_level()
            
            if self.current_light_state != is_bright:
                # Состояние изменилось
                self.current_light_state = is_bright
                self.state_start_time = time.time()
                self.state_stable = False
                return False
            
            # Состояние стабильно
            if not self.state_stable and self.state_start_time:
                elapsed = time.time() - self.state_start_time
                if elapsed >= self.threshold_seconds:
                    # Состояние стабильно достаточно долго
                    self.state_stable = True
                    variant = "light" if is_bright else "dark"
                    self._switch_theme(variant)
                    return True
                    
            self.state_stable = False
                
        except Exception as e:
            logger.error(f"Error checking light level: {e}")
            return False
            
        return False
            
    def _switch_theme(self, variant):
        """Thread-safe переключение темы через главный поток Kivy"""
        try:
            Clock.schedule_once(lambda dt: self._do_switch_theme_on_main_thread(variant), 0)
                
        except Exception as e:
            logger.error(f"Error scheduling theme switch: {e}")
            
    def _do_switch_theme_on_main_thread(self, variant):
        """ИСПРАВЛЕНО: Пересоздание экранов с правильными методами"""
        logger.info(f"🎨 Theme switch with screen recreation: {variant}")
        
        try:
            app = App.get_running_app()
            if not app or not hasattr(app, 'theme_manager') or not app.theme_manager:
                logger.error("❌ App or ThemeManager not available")
                return
            
            # Получаем информацию о текущем состоянии через правильные атрибуты
            current_theme = getattr(app.theme_manager, 'theme_name', 'minecraft')
            current_variant = getattr(app.theme_manager, 'variant', 'light')
            current_screen = "home"
            
            if not hasattr(app, 'root') or not app.root:
                logger.error("❌ App.root not available")
                return
            
            logger.debug(f"📋 App.root type: {type(app.root).__name__}")
            
            # Поиск ScreenManager
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
            
            # 1. ИСПРАВЛЕНО: Загружаем новую тему через единственный метод load()
            success = app.theme_manager.load(current_theme, variant)
                
            if not success:
                logger.error(f"❌ Failed to load theme")
                return
            
            logger.info(f"✅ Theme loaded: {current_theme}/{variant}")
            
            # 2. Сохраняем в конфиг
            if hasattr(app, 'user_config') and app.user_config:
                app.user_config.set('variant', variant)
            
            # 3. Пересоздаем экраны
            self._recreate_screens_simple(app, screen_manager, current_screen)
            
            # 4. Публикуем событие
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
        """Поиск ScreenManager"""
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
        
        logger.warning("❌ ScreenManager not found in any location")
        return None

    def _recreate_screens_simple(self, app, screen_manager, restore_screen="home"):
        """Пересоздание экранов + TopMenu"""
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
            
            # Создаем новые экраны
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
            
            # Принудительное обновление TopMenu
            top_menu = None
            if hasattr(app.root, 'ids') and 'topmenu' in app.root.ids:
                top_menu = app.root.ids.topmenu
            elif hasattr(app.root, 'ids') and 'top_menu' in app.root.ids:
                top_menu = app.root.ids.top_menu
            
            if top_menu:
                # Обновляем текущую страницу
                top_menu.current_page = restore_screen
                
                # Принудительно обновляем тему TopMenu (методы существуют!)
                if hasattr(top_menu, 'force_complete_refresh'):
                    top_menu.force_complete_refresh()
                    logger.debug("✅ TopMenu force refreshed")
                elif hasattr(top_menu, 'refresh_theme'):
                    top_menu.refresh_theme()
                    logger.debug("✅ TopMenu theme refreshed")
                
                logger.debug("✅ TopMenu fully updated")
            else:
                logger.warning("⚠️ TopMenu not found for update")
            
            # Обновляем overlay изображение (метод существует!)
            if hasattr(app.root, '_update_overlay'):
                app.root._update_overlay()
                logger.debug("✅ Overlay updated")
            
            logger.info(f"🎉 Screens + TopMenu recreated! Current: {restore_screen}")
            
        except Exception as e:
            logger.error(f"❌ Screen recreation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def debug_screen_manager(self):
        """Диагностика ScreenManager"""
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
            
            logger.info("🔧 ===========================================")
            
        except Exception as e:
            logger.error(f"Debug failed: {e}")

    def test_recreation(self):
        """Тестирование пересоздания экранов + TopMenu"""
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
            def load(self, theme, variant):  # ИСПРАВЛЕНО: только load()!
                return True
            theme_name = "minecraft"
            variant = "light"
        
        service = AutoThemeService(MockSensorService(), MockThemeManager())
        assert hasattr(service, 'calibrate_sensor'), "calibrate_sensor method missing"
        assert hasattr(service, 'force_check'), "force_check method missing"
        assert hasattr(service, 'set_enabled'), "set_enabled method missing"
        assert hasattr(service, 'get_status'), "get_status method missing"
        print("✅ AutoThemeService v2.0.2 module validation passed")
        return True
    except Exception as e:
        print(f"❌ AutoThemeService module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_auto_theme_service_module()