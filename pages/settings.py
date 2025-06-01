from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger
from datetime import datetime


class SettingsScreen(Screen):
    """Экран настроек приложения"""
    
    # Theme properties
    current_theme = StringProperty("minecraft")
    current_variant = StringProperty("light")
    current_language = StringProperty("en")
    
    # User properties
    username = StringProperty("")
    birth_day = StringProperty("01")
    birth_month = StringProperty("01")
    birth_year = StringProperty("2000")
    
    # Auto theme properties
    auto_theme_enabled = BooleanProperty(False)
    light_sensor_available = BooleanProperty(False)
    light_sensor_threshold = NumericProperty(3)
    
    # Status properties
    current_light_status = StringProperty("Unknown")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
        self._update_events = []

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering SettingsScreen")
        self.load_all_settings()
        self.refresh_theme()
        self.refresh_text()
        self.check_sensor_availability()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in SettingsScreen")
        return None

    def start_updates(self):
        """Запуск периодических обновлений"""
        self._update_events = [
            # Обновляем статус датчика освещения каждые 5 секунд
            Clock.schedule_interval(lambda dt: self.update_sensor_status(), 5),
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        for event in self._update_events:
            event.cancel()
        self._update_events = []

    def _play_sound(self, sound_name):
        """Воспроизведение звука темы"""
        try:
            app = App.get_running_app()
            tm = self.get_theme_manager()
            if hasattr(app, "audio_service") and app.audio_service and tm:
                path = tm.get_sound(sound_name)
                if path:
                    app.audio_service.play(path)
        except Exception as e:
            logger.error(f"Error playing sound {sound_name}: {e}")

    def load_all_settings(self):
        """Загрузка всех настроек"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'user_config'):
                logger.error("UserConfig not available")
                return
                
            user_config = app.user_config
            
            # Загружаем основные настройки
            self.current_theme = user_config.get("theme", "minecraft")
            self.current_variant = user_config.get("variant", "light")
            self.current_language = user_config.get("language", "en")
            self.username = user_config.get("username", "")
            
            # Парсим дату рождения
            birthday = user_config.get("birthday", "2000-01-01")
            if birthday:
                try:
                    parts = birthday.split("-")
                    if len(parts) == 3:
                        self.birth_year = parts[0]
                        self.birth_month = parts[1]
                        self.birth_day = parts[2]
                except Exception as e:
                    logger.warning(f"Error parsing birthday: {e}")
                    self.birth_year = "2000"
                    self.birth_month = "01"
                    self.birth_day = "01"
            
            # Загружаем настройки автотемы
            self.auto_theme_enabled = user_config.get("auto_theme_enabled", False)
            self.light_sensor_threshold = user_config.get("light_sensor_threshold", 3)
            
            logger.info("Settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def check_sensor_availability(self):
        """Проверка доступности датчика освещения"""
        app = App.get_running_app()
        try:
            if hasattr(app, 'sensor_service') and app.sensor_service:
                self.light_sensor_available = app.sensor_service.sensor_available
                logger.info(f"Light sensor available: {self.light_sensor_available}")
            else:
                self.light_sensor_available = False
                logger.info("Sensor service not available")
        except Exception as e:
            logger.error(f"Error checking sensor availability: {e}")
            self.light_sensor_available = False

    def update_sensor_status(self):
        """Обновление статуса датчика освещения"""
        app = App.get_running_app()
        try:
            if hasattr(app, 'sensor_service') and app.sensor_service:
                readings = app.sensor_service.get_readings()
                light_level = readings.get('light_level', True)
                using_mock = getattr(app.sensor_service, 'using_mock_sensors', True)
                
                status = "Mock" if using_mock else "Real"
                light_text = "Light" if light_level else "Dark"
                self.current_light_status = f"{light_text} ({status})"
                
            else:
                self.current_light_status = "Offline"
                
        except Exception as e:
            logger.error(f"Error updating sensor status: {e}")
            self.current_light_status = "Error"

    def on_theme_select(self, theme_name):
        """Выбор темы"""
        if theme_name != self.current_theme:
            app = App.get_running_app()
            
            # Воспроизводим звук
            self._play_sound("click")
            
            self.current_theme = theme_name
            
            # Применяем тему
            if hasattr(app, 'theme_manager'):
                app.theme_manager.load(theme_name, self.current_variant)
                event_bus.publish("theme_changed", {"theme": theme_name, "variant": self.current_variant})
            
            logger.info(f"Theme changed to: {theme_name}")

    def on_variant_select(self, variant):
        """Выбор варианта темы (light/dark)"""
        if variant != self.current_variant:
            app = App.get_running_app()
            
            # Воспроизводим звук
            self._play_sound("click")
            
            self.current_variant = variant
            
            # Применяем вариант темы
            if hasattr(app, 'theme_manager'):
                app.theme_manager.load(self.current_theme, variant)
                event_bus.publish("theme_changed", {"theme": self.current_theme, "variant": variant})
            
            logger.info(f"Theme variant changed to: {variant}")

    def on_language_select(self, language):
        """Выбор языка"""
        if language != self.current_language:
            app = App.get_running_app()
            
            # Воспроизводим звук
            self._play_sound("click")
            
            self.current_language = language
            
            # Применяем язык
            if hasattr(app, 'localizer'):
                app.localizer.load(language)
                event_bus.publish("language_changed", {"language": language})
            
            logger.info(f"Language changed to: {language}")

    def toggle_auto_theme(self):
        """Переключение автоматической смены темы"""
        app = App.get_running_app()
        
        if not self.light_sensor_available:
            # Воспроизводим звук ошибки
            self._play_sound("error")
            logger.warning("Cannot toggle auto theme - sensor not available")
            return
        
        self.auto_theme_enabled = not self.auto_theme_enabled
        
        # Воспроизводим звук
        sound_name = "confirm" if self.auto_theme_enabled else "click"
        self._play_sound(sound_name)
        
        # Обновляем кнопку в интерфейсе
        if hasattr(self, 'ids') and 'auto_theme_button' in self.ids:
            self.ids.auto_theme_button.text = "ON" if self.auto_theme_enabled else "OFF"
        
        logger.info(f"Auto theme toggled: {self.auto_theme_enabled}")

    def on_threshold_change(self, value):
        """Изменение порога датчика освещения"""
        try:
            new_threshold = max(1, min(int(value), 5))
            if new_threshold != self.light_sensor_threshold:
                self.light_sensor_threshold = new_threshold
                
                app = App.get_running_app()
                # Обновляем калибровку датчика
                if hasattr(app, 'sensor_service') and app.sensor_service:
                    app.sensor_service.calibrate_light_sensor(new_threshold)
                
                logger.info(f"Light sensor threshold changed to: {new_threshold}")
                
        except Exception as e:
            logger.error(f"Error changing threshold: {e}")

    def test_theme_switch(self):
        """Тест переключения темы"""
        app = App.get_running_app()
        
        try:
            # Переключаем на противоположный вариант
            test_variant = "dark" if self.current_variant == "light" else "light"
            
            # Воспроизводим звук
            self._play_sound("confirm")
            
            # Применяем тест
            if hasattr(app, 'theme_manager'):
                app.theme_manager.load(self.current_theme, test_variant)
                event_bus.publish("theme_changed", {"theme": self.current_theme, "variant": test_variant})
            
            # Возвращаем обратно через 3 секунды
            Clock.schedule_once(lambda dt: self._restore_theme(), 3.0)
            
            logger.info(f"Theme test: switching to {test_variant} for 3 seconds")
            
        except Exception as e:
            logger.error(f"Error in theme test: {e}")
            # Воспроизводим звук ошибки
            self._play_sound("error")

    def _restore_theme(self):
        """Восстановление исходной темы после теста"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager'):
            app.theme_manager.load(self.current_theme, self.current_variant)
            event_bus.publish("theme_changed", {"theme": self.current_theme, "variant": self.current_variant})
        logger.info(f"Theme restored to: {self.current_theme}/{self.current_variant}")

    def save_all_settings(self):
        """Сохранение всех настроек"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'user_config'):
                self._play_sound("error")
                logger.error("UserConfig not available")
                return
                
            user_config = app.user_config
            
            # Собираем данные из полей ввода
            if hasattr(self, 'ids'):
                if 'username_input' in self.ids:
                    self.username = self.ids.username_input.text
                if 'birth_day_input' in self.ids:
                    self.birth_day = self.ids.birth_day_input.text
                if 'birth_month_input' in self.ids:
                    self.birth_month = self.ids.birth_month_input.text
                if 'birth_year_input' in self.ids:
                    self.birth_year = self.ids.birth_year_input.text
            
            # Формируем дату рождения
            try:
                day = max(1, min(int(self.birth_day), 31))
                month = max(1, min(int(self.birth_month), 12))  
                year = max(1900, min(int(self.birth_year), 2100))
                birthday = f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                birthday = "2000-01-01"
                logger.warning("Invalid birthdate, using default")
            
            # Сохраняем настройки
            user_config.set("theme", self.current_theme)
            user_config.set("variant", self.current_variant)
            user_config.set("language", self.current_language)
            user_config.set("username", self.username)
            user_config.set("birthday", birthday)
            user_config.set("auto_theme_enabled", self.auto_theme_enabled)
            user_config.set("light_sensor_threshold", int(self.light_sensor_threshold))
            
            # Воспроизводим звук успеха
            self._play_sound("confirm")
            
            logger.info("All settings saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            # Воспроизводим звук ошибки
            self._play_sound("error")

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return

        # Список виджетов для обновления темы
        widgets_to_update = [
            "theme_label", "variant_label", "language_label", "username_label",
            "birthday_label", "auto_theme_label", "threshold_label", "sensor_status_label",
            "theme_spinner", "variant_spinner", "language_spinner", 
            "username_input", "birth_day_input", "birth_month_input", "birth_year_input",
            "auto_theme_button", "save_button",
            "theme_section_label", "language_section_label", "user_section_label", "auto_theme_section_label"
        ]
        
        for widget_id in widgets_to_update:
            if hasattr(self, 'ids') and widget_id in self.ids:
                widget = self.ids[widget_id]
                
                # Обновляем шрифт
                if hasattr(widget, 'font_name'):
                    if "section" in widget_id:
                        widget.font_name = tm.get_font("title")
                    else:
                        widget.font_name = tm.get_font("main")
                    
                # Обновляем цвет текста
                if hasattr(widget, 'color'):
                    if "section" in widget_id:
                        widget.color = tm.get_rgba("primary")
                    elif "label" in widget_id:
                        if widget_id == "sensor_status_label":
                            widget.color = tm.get_rgba("text_secondary")
                        else:
                            widget.color = tm.get_rgba("text")
                    elif widget_id == "save_button":
                        widget.color = tm.get_rgba("primary")
                    else:
                        widget.color = tm.get_rgba("text")
                
                # Обновляем фон кнопок и полей
                if hasattr(widget, 'background_normal'):
                    widget.background_normal = tm.get_image("button_bg")
                    widget.background_down = tm.get_image("button_bg_active")

        # Обновляем состояние кнопки автотемы
        if hasattr(self, 'ids') and 'auto_theme_button' in self.ids:
            self.ids.auto_theme_button.text = "ON" if self.auto_theme_enabled else "OFF"
            if hasattr(self.ids.auto_theme_button, 'color'):
                self.ids.auto_theme_button.color = tm.get_rgba("primary") if self.auto_theme_enabled else tm.get_rgba("text_secondary")

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
            
        # Обновляем все локализованные тексты
        if hasattr(self, 'ids'):
            # Основные лейблы
            labels_map = {
                'theme_label': ('settings_theme', 'Theme'),
                'language_label': ('settings_language', 'Language'),
                'save_button': ('save', 'Save Settings')
            }
            
            for widget_id, (key, default) in labels_map.items():
                if widget_id in self.ids:
                    self.ids[widget_id].text = app.localizer.tr(key, default)