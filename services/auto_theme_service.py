"""
AutoThemeService - автоматическое переключение темы по датчику освещенности
"""
import threading
import time
from app.logger import app_logger as logger
from app.event_bus import event_bus


class AutoThemeService:
    """Сервис автоматического переключения темы по датчику освещенности"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        self._last_check_time = 0
        self._check_interval = 2.0  # Проверяем каждые 2 секунды
        self._is_stopped = False
        
        logger.info("AutoThemeService initialized")
    
    def start(self):
        """Запуск сервиса автотемы"""
        if self.running:
            logger.warning("AutoThemeService already running")
            return
        
        logger.info("Starting AutoThemeService...")
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._auto_theme_loop, daemon=True)
        self.thread.start()
        logger.info("AutoThemeService started")
    
    def stop(self):
        """Остановка сервиса автотемы"""
        if self._is_stopped:
            return
            
        logger.info("Stopping AutoThemeService...")
        self.running = False
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        self._is_stopped = True
        logger.info("AutoThemeService stopped")
    
    def _auto_theme_loop(self):
        """Основной цикл проверки датчика освещенности"""
        while self.running and not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Проверяем не чаще чем раз в интервал
                if current_time - self._last_check_time < self._check_interval:
                    self._stop_event.wait(0.5)
                    continue
                
                self._last_check_time = current_time
                
                # Проверяем настройки автотемы
                if not self._is_auto_theme_enabled():
                    self._stop_event.wait(5.0)  # Проверяем реже если выключено
                    continue
                
                # Проверяем изменение освещенности
                if self._check_light_change():
                    self._handle_light_change()
                
                self._stop_event.wait(1.0)
                
            except Exception as e:
                logger.error(f"Error in auto-theme loop: {e}")
                self._stop_event.wait(5.0)
    
    def _is_auto_theme_enabled(self):
        """Проверка включена ли автотема"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'user_config') and app.user_config:
                return app.user_config.get("auto_theme_enabled", False)
            
            return False
        except Exception as e:
            logger.error(f"Error checking auto theme enabled: {e}")
            return False
    
    def _check_light_change(self):
        """Проверка изменения освещенности через SensorService"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'sensor_service') and app.sensor_service:
                # Проверяем доступность датчика
                if not app.sensor_service.sensor_available:
                    return False
                
                # Проверяем изменение освещенности
                return app.sensor_service.is_light_changed()
            
            return False
        except Exception as e:
            logger.error(f"Error checking light change: {e}")
            return False
    
    def _handle_light_change(self):
        """Обработка изменения освещенности с полным обновлением UI"""
        try:
            from kivy.app import App
            from kivy.clock import Clock
            app = App.get_running_app()
            
            if not hasattr(app, 'sensor_service') or not app.sensor_service:
                return
            
            # Получаем текущий уровень освещенности
            current_light = app.sensor_service.get_light_level()
            
            # Определяем нужную тему
            if current_light:
                # Светло - переключаем на светлую тему
                new_variant = "light"
                light_status = "Light"
            else:
                # Темно - переключаем на темную тему
                new_variant = "dark"
                light_status = "Dark"
            
            # Получаем текущую тему
            current_theme = "minecraft"  # По умолчанию
            current_variant = "light"   # По умолчанию
            
            if hasattr(app, 'user_config') and app.user_config:
                current_theme = app.user_config.get("theme", "minecraft")
                current_variant = app.user_config.get("variant", "light")
            
            # Переключаем только если вариант изменился
            if new_variant != current_variant:
                logger.info(f"🌓 Auto-switching theme: {light_status} detected → {new_variant} theme")
                
                # ЭТАП 1: Применяем новую тему в ThemeManager
                if hasattr(app, 'theme_manager') and app.theme_manager:
                    app.theme_manager.load(current_theme, new_variant)
                    logger.debug("✅ ThemeManager updated")
                
                # ЭТАП 2: Сохраняем в настройки
                if hasattr(app, 'user_config') and app.user_config:
                    app.user_config.set("variant", new_variant)
                    logger.debug("✅ User config updated")
                
                # ЭТАП 3: Принудительно обновляем UI через Kivy Clock
                def update_ui_phase_1(dt):
                    """Первая фаза обновления UI - корневой виджет и меню"""
                    try:
                        # Обновляем корневой виджет
                        if hasattr(app, 'root') and app.root:
                            if hasattr(app.root, 'refresh_theme_everywhere'):
                                app.root.refresh_theme_everywhere()
                                logger.debug("✅ Root widget theme updated")
                        
                        # Публикуем событие смены темы
                        event_bus.publish("theme_changed", {
                            "theme": current_theme, 
                            "variant": new_variant,
                            "auto_switched": True
                        })
                        logger.debug("✅ Theme changed event published")
                        
                    except Exception as e:
                        logger.error(f"Error in UI update phase 1: {e}")
                
                def update_ui_phase_2(dt):
                    """Вторая фаза обновления UI - активные экраны"""
                    try:
                        # Находим текущий активный экран и обновляем его
                        if hasattr(app, 'root') and app.root:
                            if hasattr(app.root, 'ids') and 'sm' in app.root.ids:
                                screen_manager = app.root.ids.sm
                                current_screen = screen_manager.current_screen
                                
                                if current_screen and hasattr(current_screen, 'refresh_theme'):
                                    current_screen.refresh_theme()
                                    logger.debug(f"✅ Current screen '{current_screen.name}' theme updated")
                        
                        logger.info(f"✅ Theme auto-switched to {new_variant} - UI updated")
                        
                    except Exception as e:
                        logger.error(f"Error in UI update phase 2: {e}")
                
                def play_confirmation_sound(dt):
                    """Третья фаза - воспроизведение звука подтверждения"""
                    try:
                        if hasattr(app, 'theme_manager') and hasattr(app, 'audio_service'):
                            sound_path = app.theme_manager.get_sound("confirm")
                            if sound_path and app.audio_service:
                                app.audio_service.play(sound_path)
                                logger.debug("✅ Confirmation sound played")
                    except Exception as e:
                        logger.error(f"Error playing confirmation sound: {e}")
                
                # РАСПИСЫВАЕМ ОБНОВЛЕНИЯ С ЗАДЕРЖКАМИ для корректной отработки
                Clock.schedule_once(update_ui_phase_1, 0.1)   # Через 100мс
                Clock.schedule_once(update_ui_phase_2, 0.3)   # Через 300мс  
                Clock.schedule_once(play_confirmation_sound, 0.5)  # Через 500мс
                
            else:
                logger.debug(f"🌓 Light level: {light_status}, theme already {current_variant}")
                
        except Exception as e:
            logger.error(f"Error handling light change: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def force_check(self):
        """Принудительная проверка освещенности с полным обновлением UI"""
        logger.info("🔍 Force checking light sensor for auto-theme...")
        try:
            if self._is_auto_theme_enabled():
                if self._check_light_change():
                    self._handle_light_change()
                    return True
                else:
                    logger.info("🔍 No light change detected")
                    # Даже если изменений нет, принудительно обновим UI для синхронизации
                    self._force_ui_refresh()
                    return False
            else:
                logger.info("🔍 Auto-theme is disabled")
                return False
        except Exception as e:
            logger.error(f"Error in force check: {e}")
            return False
    
    def _force_ui_refresh(self):
        """Принудительное обновление всего UI для синхронизации темы"""
        try:
            from kivy.app import App
            from kivy.clock import Clock
            app = App.get_running_app()
            
            def refresh_all_ui(dt):
                try:
                    # Обновляем корневой виджет
                    if hasattr(app, 'root') and app.root:
                        if hasattr(app.root, 'refresh_theme_everywhere'):
                            app.root.refresh_theme_everywhere()
                    
                    # Публикуем событие обновления темы
                    if hasattr(app, 'user_config') and app.user_config:
                        current_theme = app.user_config.get("theme", "minecraft")
                        current_variant = app.user_config.get("variant", "light")
                        
                        event_bus.publish("theme_changed", {
                            "theme": current_theme, 
                            "variant": current_variant,
                            "forced_refresh": True
                        })
                    
                    logger.debug("✅ Forced UI refresh completed")
                    
                except Exception as e:
                    logger.error(f"Error in forced UI refresh: {e}")
            
            # Планируем обновление через 100мс
            Clock.schedule_once(refresh_all_ui, 0.1)
            
        except Exception as e:
            logger.error(f"Error scheduling UI refresh: {e}")
    
    def manual_theme_switch(self, target_variant=None):
        """Ручное переключение темы с полным обновлением UI (для тестирования)"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if not hasattr(app, 'user_config') or not app.user_config:
                logger.error("User config not available")
                return False
            
            current_theme = app.user_config.get("theme", "minecraft")
            current_variant = app.user_config.get("variant", "light")
            
            # Определяем целевой вариант
            if target_variant is None:
                # Переключаем на противоположный
                target_variant = "dark" if current_variant == "light" else "light"
            
            logger.info(f"🔄 Manual theme switch: {current_variant} → {target_variant}")
            
            # Применяем новую тему
            if hasattr(app, 'theme_manager') and app.theme_manager:
                app.theme_manager.load(current_theme, target_variant)
            
            # Сохраняем в настройки
            app.user_config.set("variant", target_variant)
            
            # Используем тот же механизм обновления UI что и для автоматического переключения
            from kivy.clock import Clock
            
            def update_ui_manual(dt):
                try:
                    if hasattr(app, 'root') and app.root:
                        if hasattr(app.root, 'refresh_theme_everywhere'):
                            app.root.refresh_theme_everywhere()
                    
                    event_bus.publish("theme_changed", {
                        "theme": current_theme, 
                        "variant": target_variant,
                        "manual_switch": True
                    })
                    
                    logger.info(f"✅ Manual theme switch completed: {target_variant}")
                    
                except Exception as e:
                    logger.error(f"Error in manual UI update: {e}")
            
            Clock.schedule_once(update_ui_manual, 0.1)
            return True
            
        except Exception as e:
            logger.error(f"Error in manual theme switch: {e}")
            return False
    
    def get_status(self):
        """Получение статуса сервиса автотемы"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            status = {
                "service_running": self.running,
                "auto_theme_enabled": self._is_auto_theme_enabled(),
                "check_interval": self._check_interval,
                "last_check": self._last_check_time
            }
            
            # Добавляем статус датчика
            if hasattr(app, 'sensor_service') and app.sensor_service:
                sensor_status = app.sensor_service.get_light_sensor_status()
                status.update({
                    "sensor_available": sensor_status.get('gpio_available', False),
                    "using_mock": sensor_status.get('using_mock', True),
                    "current_light": sensor_status.get('current_level', True),
                    "raw_value": sensor_status.get('raw_value', 0)
                })
            else:
                status.update({
                    "sensor_available": False,
                    "using_mock": True,
                    "current_light": True,
                    "raw_value": 0
                })
            
            return status
        except Exception as e:
            logger.error(f"Error getting auto-theme status: {e}")
            return {"error": str(e)}
    
    def set_check_interval(self, interval_seconds):
        """Установка интервала проверки освещенности"""
        self._check_interval = max(1.0, min(10.0, interval_seconds))
        logger.info(f"Auto-theme check interval set to {self._check_interval:.1f}s")
    
    def calibrate_sensor(self, threshold_seconds=3):
        """Калибровка датчика освещенности"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'sensor_service') and app.sensor_service:
                app.sensor_service.calibrate_light_sensor(threshold_seconds)
                logger.info(f"Auto-theme sensor calibrated: {threshold_seconds}s threshold")
                return True
            else:
                logger.warning("Sensor service not available for calibration")
                return False
        except Exception as e:
            logger.error(f"Error calibrating sensor: {e}")
            return False