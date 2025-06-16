# pages/settings.py
"""
ИСПРАВЛЕННАЯ страница настроек с использованием BaseScreen
Вся логика тем вынесена в базовый класс!
"""

from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.app import App
from kivy.clock import Clock
from widgets.base_screen import BaseScreen  # ИСПРАВЛЕНО: Используем BaseScreen
from app.logger import app_logger as logger
import os
import threading


class SettingsScreen(BaseScreen):  # ИСПРАВЛЕНО: Наследуемся от BaseScreen
    """Экран настроек приложения с использованием BaseScreen"""
    
    # Theme properties
    current_theme = StringProperty("minecraft")
    current_variant = StringProperty("light")
    current_language = StringProperty("en")
    
    # ListProperty для значений селекторов
    theme_list = ListProperty(["minecraft"])
    variant_list = ListProperty(["light", "dark"])
    language_list = ListProperty(["en", "ru"])
    
    # Свойства для активности селекторов
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
    
    # ИСПРАВЛЕНО: Volume control properties - инициализируем по умолчанию
    current_volume = NumericProperty(50)
    volume_service_available = BooleanProperty(False)
    
    # Status properties
    current_light_status = StringProperty("Unknown")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # BaseScreen управляет событиями темы автоматически!
        
        # ИСПРАВЛЕНО: Инициализация volume properties
        self.volume_service_available = False
        self.current_volume = 50
        
        # УБРАНО: Все подписки на события темы - BaseScreen делает это автоматически!
        # ТОЛЬКО специфичные для настроек события и состояние
        self._settings_update_events = []
        self._settings_initialized = False

    # ======================================
    # ПЕРЕОПРЕДЕЛЯЕМ МЕТОДЫ BaseScreen
    # ======================================

    def on_screen_initialized(self):
        """Инициализация после создания виджетов"""
        try:
            self.load_all_settings()
            self.check_sensor_availability()
            self.check_volume_service()
            self._setup_select_buttons()
            self._settings_initialized = True
            logger.debug("SettingsScreen initialized")
        except Exception as e:
            logger.error(f"Error initializing SettingsScreen: {e}")

    def on_screen_enter(self):
        """Логика входа на экран настроек"""
        self.start_settings_updates()
        logger.info("Entering SettingsScreen")

    def on_screen_leave(self):
        """Логика выхода с экрана настроек"""
        self.stop_settings_updates()

    def on_theme_refresh(self, theme_manager):
        """Специфичное обновление темы для страницы настроек"""
        try:
            # BaseScreen уже обновил все стандартные элементы!
            # Здесь только специфичная логика для настроек
            
            # Обновляем кнопки выбора
            self._update_select_buttons_theme(theme_manager)
            
            # Обновляем preview элементы если есть
            self._update_theme_preview(theme_manager)
            
            logger.debug("Settings theme refresh completed")
            
        except Exception as e:
            logger.error(f"Error in settings theme refresh: {e}")

    def on_text_refresh(self, localizer):
        """Обновление текстов для страницы настроек"""
        try:
            # Обновляем специфичные тексты настроек
            if hasattr(self, 'ids'):
                texts = {
                    'theme_section_label': localizer.tr("settings_theme_title", "Theme Settings"),
                    'language_section_label': localizer.tr("settings_language_title", "Language Settings"),
                    'user_section_label': localizer.tr("settings_user_title", "User Settings"),
                    'auto_theme_section_label': localizer.tr("settings_auto_theme_title", "Auto Theme"),
                    'volume_section_label': localizer.tr("settings_volume_title", "Volume Control"),
                    
                    'theme_label': localizer.tr("settings_theme", "Theme:"),
                    'variant_label': localizer.tr("settings_mode", "Mode:"),
                    'language_label': localizer.tr("settings_language", "Language:"),
                    'username_label': localizer.tr("settings_username", "Username:"),
                    'birthday_label': localizer.tr("settings_birthday", "Birthday:"),
                    'auto_theme_label': localizer.tr("settings_auto_theme", "Auto Theme:"),
                    'threshold_label': localizer.tr("settings_threshold", "Light Threshold:"),
                    'volume_label': localizer.tr("settings_volume", "Volume:"),
                    
                    'save_button': localizer.tr("settings_save", "Save Settings"),
                }
                
                for widget_id, text in texts.items():
                    if widget_id in self.ids:
                        self.ids[widget_id].text = text
            
            logger.debug("Settings text refresh completed")
            
        except Exception as e:
            logger.error(f"Error refreshing settings text: {e}")

    # ======================================
    # ЛОГИКА НАСТРОЕК (БЕЗ ТЕМИЗАЦИИ!)
    # ======================================

    def load_all_settings(self):
        """Загрузка всех настроек"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'user_config') and app.user_config:
                config = app.user_config
                
                # Theme settings
                self.current_theme = config.get("theme", "minecraft")
                self.current_variant = config.get("variant", "light")
                self.current_language = config.get("language", "en")
                
                # User settings
                self.username = config.get("username", "")
                self.birth_day = str(config.get("birth_day", "01"))
                self.birth_month = str(config.get("birth_month", "01"))
                self.birth_year = str(config.get("birth_year", "2000"))
                
                # Auto theme settings
                self.auto_theme_enabled = config.get("auto_theme", False)
                self.light_sensor_threshold = config.get("light_threshold", 3)
                
                logger.debug("Settings loaded from config")
            else:
                logger.warning("User config not available")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def check_sensor_availability(self):
        """Проверка доступности датчика освещенности"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'light_sensor_service') and app.light_sensor_service:
                self.light_sensor_available = app.light_sensor_service.is_available()
                if self.light_sensor_available:
                    current_reading = app.light_sensor_service.get_reading()
                    self.current_light_status = f"Current: {current_reading:.1f}"
                else:
                    self.current_light_status = "Sensor not available"
            else:
                self.light_sensor_available = False
                self.current_light_status = "Service not available"
                
            logger.debug(f"Light sensor available: {self.light_sensor_available}")
        except Exception as e:
            logger.error(f"Error checking sensor availability: {e}")
            self.light_sensor_available = False
            self.current_light_status = "Error checking sensor"

    def check_volume_service(self):
        """Проверка доступности сервиса управления громкостью"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'volume_service') and app.volume_service:
                status = app.volume_service.get_status()
                if status.get('running', False) and status.get('active_mixer'):
                    self.volume_service_available = True
                    self.current_volume = status.get('current_volume', 50)
                    logger.info(f"Volume service available - Current volume: {self.current_volume}%")
                else:
                    self.volume_service_available = False
                    logger.warning("Volume service not fully operational")
            else:
                self.volume_service_available = False
                logger.info("Volume service not available")
                
        except Exception as e:
            logger.error(f"Error checking volume service: {e}")
            self.volume_service_available = False
            self.current_volume = 50

    def start_settings_updates(self):
        """Запуск обновлений специфичных для настроек"""
        try:
            self.stop_settings_updates()  # Очищаем старые
            
            self._settings_update_events = [
                Clock.schedule_interval(self.update_light_status, 2.0),
                Clock.schedule_interval(self.update_volume_status, 1.0)
            ]
            logger.debug("Started settings updates")
        except Exception as e:
            logger.error(f"Error starting settings updates: {e}")

    def stop_settings_updates(self):
        """Остановка обновлений настроек"""
        try:
            for event in self._settings_update_events:
                event.cancel()
            self._settings_update_events.clear()
            logger.debug("Stopped settings updates")
        except Exception as e:
            logger.error(f"Error stopping settings updates: {e}")

    def update_light_status(self, dt=None):
        """Обновление статуса датчика освещенности"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'light_sensor_service') and app.light_sensor_service and self.light_sensor_available:
                current_reading = app.light_sensor_service.get_reading()
                self.current_light_status = f"Current: {current_reading:.1f}"
        except Exception as e:
            logger.debug(f"Error updating light status: {e}")

    def update_volume_status(self, dt=None):
        """Обновление статуса громкости"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service:
                new_volume = app.volume_service.get_volume()
                if new_volume != self.current_volume:
                    self.current_volume = new_volume
                    logger.debug(f"Volume updated: {self.current_volume}%")
                    
                    # Обновляем UI
                    if hasattr(self, 'ids') and 'volume_value_label' in self.ids:
                        self.ids.volume_value_label.text = f"{self.current_volume}%"
        except Exception as e:
            logger.error(f"Error updating volume status: {e}")

    # ======================================
    # ОБРАБОТЧИКИ СОБЫТИЙ НАСТРОЕК
    # ======================================

    def on_theme_select(self, theme_name):
        """Обработка выбора темы"""
        try:
            logger.info(f"Theme selected: {theme_name}")
            
            app = App.get_running_app()
            current_variant = getattr(app.theme_manager, 'variant', 'light')
            
            if hasattr(app, 'theme_manager'):
                success = app.theme_manager.load(theme_name.lower(), current_variant)
                if success:
                    self.current_theme = theme_name.lower()
                    if hasattr(app, 'user_config'):
                        app.user_config["theme"] = theme_name.lower()
                        if hasattr(app, 'save_user_config'):
                            app.save_user_config()
                    
                    # BaseScreen автоматически обновит тему!
                    logger.info(f"Theme changed to: {theme_name}")
                else:
                    logger.error(f"Failed to load theme: {theme_name}")
            
        except Exception as e:
            logger.error(f"Error selecting theme: {e}")

    def on_variant_select(self, variant_name):
        """Обработка выбора варианта темы"""
        try:
            logger.info(f"Variant selected: {variant_name}")
            
            app = App.get_running_app()
            current_theme = getattr(app.theme_manager, 'theme_name', 'classic')
            
            if hasattr(app, 'theme_manager'):
                success = app.theme_manager.load(current_theme, variant_name.lower())
                if success:
                    self.current_variant = variant_name.lower()
                    if hasattr(app, 'user_config'):
                        app.user_config["variant"] = variant_name.lower()
                        if hasattr(app, 'save_user_config'):
                            app.save_user_config()
                    
                    logger.info(f"Variant changed to: {variant_name}")
                else:
                    logger.error(f"Failed to load variant: {variant_name}")
            
        except Exception as e:
            logger.error(f"Error selecting variant: {e}")

    def on_language_select(self, language_name):
        """Обработка выбора языка"""
        try:
            lang_code = self._get_language_code(language_name)
            logger.info(f"Language selected: {language_name} ({lang_code})")
            
            app = App.get_running_app()
            if hasattr(app, 'localizer'):
                success = app.localizer.set_language(lang_code)
                if success:
                    self.current_language = lang_code
                    if hasattr(app, 'user_config'):
                        app.user_config["language"] = lang_code
                        if hasattr(app, 'save_user_config'):
                            app.save_user_config()
                    
                    # BaseScreen автоматически обновит тексты!
                    logger.info(f"Language changed to: {lang_code}")
                else:
                    logger.error(f"Failed to set language: {lang_code}")
            
        except Exception as e:
            logger.error(f"Error selecting language: {e}")

    def volume_up(self):
        """Увеличение громкости через UI"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service and self.volume_service_available:
                app.volume_service.volume_up_manual()
                Clock.schedule_once(lambda dt: self.update_volume_status(), 0.1)
                logger.info("Volume up triggered via UI")
            else:
                logger.warning("Volume service not available")
        except Exception as e:
            logger.error(f"Error in volume up: {e}")

    def volume_down(self):
        """Уменьшение громкости через UI"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service and self.volume_service_available:
                app.volume_service.volume_down_manual()
                Clock.schedule_once(lambda dt: self.update_volume_status(), 0.1)
                logger.info("Volume down triggered via UI")
            else:
                logger.warning("Volume service not available")
        except Exception as e:
            logger.error(f"Error in volume down: {e}")

    def save_settings(self):
        """Сохранение всех настроек"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'user_config'):
                config = app.user_config
                
                # Сохраняем все настройки
                config.update({
                    "theme": self.current_theme,
                    "variant": self.current_variant,
                    "language": self.current_language,
                    "username": self.username,
                    "birth_day": int(self.birth_day),
                    "birth_month": int(self.birth_month),
                    "birth_year": int(self.birth_year),
                    "auto_theme": self.auto_theme_enabled,
                    "light_threshold": self.light_sensor_threshold
                })
                
                if hasattr(app, 'save_user_config'):
                    app.save_user_config()
                
                logger.info("Settings saved successfully")
                
                # Показываем уведомление
                if hasattr(app, 'notification_service'):
                    app.notification_service.show_notification("Settings saved", "success")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    # ======================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ======================================

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

    def _update_select_buttons_theme(self, theme_manager):
        """Обновление темы кнопок выбора"""
        try:
            if not hasattr(self, 'ids'):
                return
            
            button_style = {
                'background_normal': theme_manager.get_image("button_bg"),
                'background_down': theme_manager.get_image("button_bg_active"),
                'color': theme_manager.get_rgba("text")
            }
            
            buttons = ['theme_button', 'variant_button', 'language_button']
            for button_id in buttons:
                if button_id in self.ids:
                    button = self.ids[button_id]
                    for prop, value in button_style.items():
                        if hasattr(button, prop) and value:
                            setattr(button, prop, value)
                            
        except Exception as e:
            logger.debug(f"Error updating select buttons theme: {e}")

    def _update_theme_preview(self, theme_manager):
        """Обновление предварительного просмотра темы"""
        try:
            if hasattr(self, 'ids'):
                preview_elements = {
                    'preview_primary': theme_manager.get_rgba("primary"),
                    'preview_background': theme_manager.get_rgba("background"),
                    'preview_accent': theme_manager.get_rgba("accent"),
                }
                
                for element_id, color in preview_elements.items():
                    if element_id in self.ids and hasattr(self.ids[element_id], 'color'):
                        self.ids[element_id].color = color
                        
        except Exception as e:
            logger.debug(f"Error updating theme preview: {e}")

    def _get_language_code(self, display_name):
        """Получение кода языка по отображаемому имени"""
        codes = {
            "Русский": "ru",
            "English": "en",
            "Russian": "ru"
        }
        return codes.get(display_name, "ru")