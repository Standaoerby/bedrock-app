from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger
from datetime import datetime


class SettingsScreen(Screen):
    """Экран настроек приложения """
    
    # Theme properties
    current_theme = StringProperty("minecraft")
    current_variant = StringProperty("light")
    current_language = StringProperty("en")
    
    # ListProperty для значений селекторов (устанавливаются один раз)
    theme_list = ListProperty(["minecraft"])
    variant_list = ListProperty(["light", "dark"])
    language_list = ListProperty(["en", "ru"])
    
    # ДОБАВЛЕНО: Свойства для активности селекторов
    theme_selector_enabled = BooleanProperty(True)
    
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
        event_bus.subscribe("theme_changed", self._on_theme_changed_delayed)
        self._update_events = []
        self._initialized = False

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering SettingsScreen")
        try:
            self.load_all_settings()
            self.check_sensor_availability()
            self.start_updates()
            # Отложенная инициализация темы и привязок
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
            Clock.schedule_once(lambda dt: self.refresh_text(), 0.1)
            Clock.schedule_once(lambda dt: self._setup_select_buttons(), 0.2)
            self._initialized = True
        except Exception as e:
            logger.error(f"Error in SettingsScreen.on_pre_enter: {e}")

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        try:
            self.stop_updates()
        except Exception as e:
            logger.error(f"Error in SettingsScreen.on_pre_leave: {e}")

    def _setup_select_buttons(self):
        """Настройка кнопок выбора"""
        try:
            if not hasattr(self, 'ids'):
                return
                
            # Настройка кнопки темы
            if 'theme_button' in self.ids:
                theme_button = self.ids.theme_button
                theme_button.values = self.theme_list
                theme_button.selected_value = self.current_theme
                
                # ДОБАВЛЕНО: Деактивируем если доступна только одна тема
                theme_button.disabled = not self.theme_selector_enabled
                theme_button.opacity = 1.0 if self.theme_selector_enabled else 0.5
                
            # Настройка кнопки варианта темы
            if 'variant_button' in self.ids:
                variant_button = self.ids.variant_button
                variant_button.values = self.variant_list
                variant_button.selected_value = self.current_variant
                
            # Настройка кнопки языка
            if 'language_button' in self.ids:
                language_button = self.ids.language_button
                language_button.values = self.language_list
                language_button.selected_value = self.current_language
                
            logger.debug("Select buttons configured")
                
        except Exception as e:
            logger.error(f"Error setting up select buttons: {e}")

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

    def _check_available_themes(self):
        """ДОБАВЛЕНО: Проверка количества доступных тем"""
        try:
            tm = self.get_theme_manager()
            
            # Пытаемся получить список тем из различных источников
            available_themes = []
            
            # Метод 1: Проверяем наличие метода в ThemeManager
            if tm and hasattr(tm, 'get_available_themes'):
                available_themes = tm.get_available_themes()
            
            # Метод 2: Проверяем папки тем
            if not available_themes:
                import os
                themes_dir = getattr(tm, 'themes_dir', 'themes') if tm else 'themes'
                if os.path.exists(themes_dir):
                    available_themes = [
                        name for name in os.listdir(themes_dir)
                        if os.path.isdir(os.path.join(themes_dir, name))
                    ]
            
            # Метод 3: Фиксированный список (fallback)
            if not available_themes:
                available_themes = ["minecraft"]
            
            self.theme_list = available_themes
            self.theme_selector_enabled = len(available_themes) > 1
            
            logger.info(f"Available themes: {available_themes}, selector enabled: {self.theme_selector_enabled}")
            
        except Exception as e:
            logger.error(f"Error checking available themes: {e}")
            self.theme_list = ["minecraft"]
            self.theme_selector_enabled = False

    def load_all_settings(self):
        """Загрузка всех настроек"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'user_config'):
                logger.error("UserConfig not available")
                return
                
            user_config = app.user_config
            
            # ДОБАВЛЕНО: Проверяем доступные темы
            self._check_available_themes()
            
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
            
            # Обновляем только TextInput поля
            Clock.schedule_once(lambda dt: self._update_input_fields(), 0.1)
            
            logger.info("Settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def _update_input_fields(self):
        """Обновление ТОЛЬКО текстовых полей ввода (НЕ селекторов)"""
        try:
            if not hasattr(self, 'ids'):
                return
                
            # Обновляем ТОЛЬКО текстовые поля - селекторы обновятся через setup
            if 'username_input' in self.ids:
                self.ids.username_input.text = self.username
            if 'birth_day_input' in self.ids:
                self.ids.birth_day_input.text = self.birth_day
            if 'birth_month_input' in self.ids:
                self.ids.birth_month_input.text = self.birth_month
            if 'birth_year_input' in self.ids:
                self.ids.birth_year_input.text = self.birth_year
                
        except Exception as e:
            logger.error(f"Error updating input fields: {e}")

    def check_sensor_availability(self):
        """Проверка доступности датчика освещения"""
        app = App.get_running_app()
        try:
            # Проверяем через AutoThemeService
            if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
                auto_status = app.auto_theme_service.get_status()
                self.light_sensor_available = auto_status.get('sensor_available', False)
                logger.info(f"Light sensor available (via AutoTheme): {self.light_sensor_available}")
            elif hasattr(app, 'sensor_service') and app.sensor_service:
                # Fallback к SensorService
                self.light_sensor_available = app.sensor_service.sensor_available
                logger.info(f"Light sensor available (via Sensor): {self.light_sensor_available}")
            else:
                self.light_sensor_available = False
                logger.info("Sensor services not available")
        except Exception as e:
            logger.error(f"Error checking sensor availability: {e}")
            self.light_sensor_available = False

    def toggle_auto_theme(self):
        """Переключение автоматической смены темы"""
        app = App.get_running_app()
        
        if not self.light_sensor_available:
            # Воспроизводим звук ошибки
            self._play_sound("error")
            logger.warning("Cannot toggle auto theme - sensor not available")
            return
        
        # Переключаем состояние
        self.auto_theme_enabled = not self.auto_theme_enabled
        
        # Воспроизводим звук
        sound_name = "confirm" if self.auto_theme_enabled else "click"
        self._play_sound(sound_name)
        
        # Интеграция с AutoThemeService
        if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
            try:
                if self.auto_theme_enabled:
                    # Калибруем датчик с текущими настройками
                    app.auto_theme_service.calibrate_sensor(int(self.light_sensor_threshold))
                    
                    # Делаем первичную проверку
                    app.auto_theme_service.force_check()
                    logger.info("Auto-theme enabled and calibrated")
                else:
                    logger.info("Auto-theme disabled")
            except Exception as e:
                logger.error(f"Error updating auto-theme service: {e}")
        
        # Обновляем UI
        Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
        
        logger.info(f"Auto theme toggled: {self.auto_theme_enabled}")

    def on_threshold_change(self, value):
        """Изменение порога датчика освещения"""
        try:
            new_threshold = max(1, min(int(value), 5))
            if new_threshold != self.light_sensor_threshold:
                self.light_sensor_threshold = new_threshold
                
                app = App.get_running_app()
                
                # Обновляем AutoThemeService
                if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
                    app.auto_theme_service.calibrate_sensor(new_threshold)
                    logger.info(f"Auto-theme threshold updated to {new_threshold}s")
                
                # Обновляем калибровку датчика в SensorService
                if hasattr(app, 'sensor_service') and app.sensor_service:
                    app.sensor_service.calibrate_light_sensor(new_threshold)
                
                logger.info(f"Light sensor threshold changed to: {new_threshold}")
                
        except Exception as e:
            logger.error(f"Error changing threshold: {e}")

    def update_sensor_status(self):
        """Обновление статуса датчика освещения"""
        app = App.get_running_app()
        try:
            # Получаем более детальный статус
            if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
                auto_status = app.auto_theme_service.get_status()
                
                self.light_sensor_available = auto_status.get('sensor_available', False)
                using_mock = auto_status.get('using_mock', True)
                light_level = auto_status.get('current_light', True)
                service_running = auto_status.get('service_running', False)
                
                # Формируем подробный статус
                if not self.light_sensor_available:
                    self.current_light_status = "Sensor Offline"
                elif not service_running:
                    self.current_light_status = "Service Stopped"
                else:
                    status_type = "Mock" if using_mock else "Real"
                    light_text = "☀️Light" if light_level else "🌙Dark"
                    auto_text = "Auto✅" if self.auto_theme_enabled else "Auto❌"
                    self.current_light_status = f"{light_text} ({status_type}, {auto_text})"
                
            elif hasattr(app, 'sensor_service') and app.sensor_service:
                # Fallback к SensorService
                readings = app.sensor_service.get_readings()
                light_level = readings.get('light_level', True)
                using_mock = getattr(app.sensor_service, 'using_mock_sensors', True)
                self.light_sensor_available = app.sensor_service.sensor_available
                
                if not self.light_sensor_available:
                    self.current_light_status = "Offline"
                else:
                    status = "Mock" if using_mock else "Real"
                    light_text = "☀️Light" if light_level else "🌙Dark"
                    self.current_light_status = f"{light_text} ({status})"
            else:
                self.current_light_status = "Services Offline"
                self.light_sensor_available = False
                
        except Exception as e:
            logger.error(f"Error updating sensor status: {e}")
            self.current_light_status = "Status Error"

    # МЕТОДЫ ОБРАБОТКИ СОБЫТИЙ UI - вызываются из SelectButton
    
    def on_theme_select(self, theme_name):
        """Выбор темы - вызывается из ThemeSelectButton"""
        # ДОБАВЛЕНО: Проверяем активность селектора темы
        if not self.theme_selector_enabled:
            logger.warning("Theme selector is disabled")
            self._play_sound("error")
            return
            
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
        """Выбор варианта темы (light/dark) - вызывается из ThemeSelectButton"""
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
        """Выбор языка - вызывается из LanguageSelectButton"""
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

    def _on_theme_changed_delayed(self, *args):
        """Асинхронная обработка смены темы"""
        # Отложенное обновление темы, чтобы не конфликтовать с селекторами
        Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)

    def on_username_change(self, instance, value):
        """Обработка изменения имени пользователя"""
        try:
            self.username = value.strip()
            logger.debug(f"Username changed to: {self.username}")
        except Exception as e:
            logger.error(f"Error in on_username_change: {e}")

    def on_birth_day_change(self, instance, value):
        """Обработка изменения дня рождения"""
        try:
            day = max(1, min(int(value) if value.isdigit() else 1, 31))
            self.birth_day = f"{day:02d}"
            instance.text = self.birth_day
        except Exception as e:
            logger.error(f"Error in on_birth_day_change: {e}")
            self.birth_day = "01"
            instance.text = self.birth_day

    def on_birth_month_change(self, instance, value):
        """Обработка изменения месяца рождения"""
        try:
            month = max(1, min(int(value) if value.isdigit() else 1, 12))
            self.birth_month = f"{month:02d}"
            instance.text = self.birth_month
        except Exception as e:
            logger.error(f"Error in on_birth_month_change: {e}")
            self.birth_month = "01"
            instance.text = self.birth_month

    def on_birth_year_change(self, instance, value):
        """Обработка изменения года рождения"""
        try:
            year = max(1900, min(int(value) if value.isdigit() else 2000, 2100))
            self.birth_year = f"{year:04d}"
            instance.text = self.birth_year
        except Exception as e:
            logger.error(f"Error in on_birth_year_change: {e}")
            self.birth_year = "2000"
            instance.text = self.birth_year

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
                    self.username = self.ids.username_input.text.strip()
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
        if not self._initialized:
            return
            
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return

        try:
            # Список виджетов для обновления темы (включая кнопки выбора)
            widgets_to_update = [
                "theme_label", "variant_label", "language_label", "username_label",
                "birthday_label", "auto_theme_label", "threshold_label", "sensor_status_label",
                "username_input", "birth_day_input", "birth_month_input", "birth_year_input",
                "auto_theme_button", "save_button",
                "theme_section_label", "language_section_label", "user_section_label", "auto_theme_section_label",
                "theme_button", "variant_button", "language_button"
            ]
            
            for widget_id in widgets_to_update:
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    
                    # Обновляем шрифт и цвет
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
                    
                    # ДОБАВЛЕНО: Обновляем состояние кнопки темы
                    if widget_id == "theme_button":
                        widget.disabled = not self.theme_selector_enabled
                        widget.opacity = 1.0 if self.theme_selector_enabled else 0.5

            # Обновляем состояние кнопки автотемы
            if hasattr(self, 'ids') and 'auto_theme_button' in self.ids:
                self.ids.auto_theme_button.text = "ON" if self.auto_theme_enabled else "OFF"
                if hasattr(self.ids.auto_theme_button, 'color'):
                    self.ids.auto_theme_button.color = tm.get_rgba("primary") if self.auto_theme_enabled else tm.get_rgba("text_secondary")
                    
        except Exception as e:
            logger.error(f"Error refreshing theme: {e}")

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        if not self._initialized:
            return
            
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
            
        try:
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
        except Exception as e:
            logger.error(f"Error refreshing text: {e}")