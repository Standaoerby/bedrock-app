# pages/settings.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ для SettingsScreen:
✅ Добавлен недостающий метод on_username_change
✅ Добавлены все недостающие методы для полей ввода
✅ Исправлена логика сохранения настроек  
✅ Улучшена обработка ошибок
"""

from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.app import App
from kivy.clock import Clock
from widgets.base_screen import BaseScreen
from app.logger import app_logger as logger
import os
import threading


class SettingsScreen(BaseScreen):
    """Экран настроек приложения с полным набором обработчиков"""
    
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
    
    # Volume control properties
    current_volume = NumericProperty(50)
    volume_service_available = BooleanProperty(False)
    
    # Status properties
    current_light_status = StringProperty("Unknown")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Инициализация состояния
        self.volume_service_available = False
        self.current_volume = 50
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

    # ======================================
    # Обработчики полей ввода
    # ======================================

    def on_username_change(self, widget, value):
        """ИСПРАВЛЕНО: Обработка изменения имени пользователя"""
        try:
            # Фильтруем и валидируем ввод
            cleaned_value = value.strip()[:20]  # Максимум 20 символов
            
            # Обновляем свойство
            self.username = cleaned_value
            
            # ИСПРАВЛЕНО: Используем правильный метод set() вместо []
            app = App.get_running_app()
            if hasattr(app, 'user_config'):
                app.user_config.set('username', cleaned_value)  # ✅ ПРАВИЛЬНО
                logger.debug(f"Username updated: '{cleaned_value}'")
            
        except Exception as e:
            logger.error(f"Error changing username: {e}")

    def on_birth_day_change(self, widget, value):
        """Обработка изменения дня рождения"""
        try:
            # Валидация дня (1-31)
            if value and value.isdigit():
                day = int(value)
                if 1 <= day <= 31:
                    self.birth_day = f"{day:02d}"
                else:
                    self.birth_day = "01"
                    widget.text = "01"
            else:
                self.birth_day = "01"
                widget.text = "01"
                
            # Автосохранение
            self._auto_save_birth_data()
            
        except Exception as e:
            logger.error(f"Error changing birth day: {e}")

    def on_birth_month_change(self, widget, value):
        """Обработка изменения месяца рождения"""
        try:
            # Валидация месяца (1-12)
            if value and value.isdigit():
                month = int(value)
                if 1 <= month <= 12:
                    self.birth_month = f"{month:02d}"
                else:
                    self.birth_month = "01"
                    widget.text = "01"
            else:
                self.birth_month = "01"
                widget.text = "01"
                
            # Автосохранение
            self._auto_save_birth_data()
            
        except Exception as e:
            logger.error(f"Error changing birth month: {e}")

    def on_birth_year_change(self, widget, value):
        """Обработка изменения года рождения"""
        try:
            # Валидация года (1900-2030)
            if value and value.isdigit():
                year = int(value)
                if 1900 <= year <= 2030:
                    self.birth_year = str(year)
                else:
                    self.birth_year = "2000"
                    widget.text = "2000"
            else:
                self.birth_year = "2000"
                widget.text = "2000"
                
            # Автосохранение
            self._auto_save_birth_data()
            
        except Exception as e:
            logger.error(f"Error changing birth year: {e}")

    def _auto_save_birth_data(self):
        """ИСПРАВЛЕНО: Автосохранение данных о дне рождения"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'user_config'):
                app.user_config.update({
                    "birth_day": int(self.birth_day),
                    "birth_month": int(self.birth_month),
                    "birth_year": int(self.birth_year)
                })
                logger.debug("Birth data auto-saved")
        except Exception as e:
            logger.error(f"Error auto-saving birth data: {e}")

    # ======================================
    # ОБРАБОТЧИКИ СЕЛЕКТОРОВ
    # ======================================

    def on_theme_select(self, selected_theme):
        """Обработка выбора темы"""
        try:
            if selected_theme != self.current_theme:
                self.current_theme = selected_theme
                self._apply_theme_change()
                logger.info(f"Theme changed to: {selected_theme}")
        except Exception as e:
            logger.error(f"Error selecting theme: {e}")

    def on_variant_select(self, selected_variant):
        """Обработка выбора варианта темы"""
        try:
            if selected_variant != self.current_variant:
                self.current_variant = selected_variant
                self._apply_theme_change()
                logger.info(f"Theme variant changed to: {selected_variant}")
        except Exception as e:
            logger.error(f"Error selecting variant: {e}")

    def on_language_select(self, selected_language):
        """Обработка выбора языка"""
        try:
            if selected_language != self.current_language:
                self.current_language = selected_language
                self._apply_language_change()
                logger.info(f"Language changed to: {selected_language}")
        except Exception as e:
            logger.error(f"Error selecting language: {e}")

    def _apply_theme_change(self):
        """Применение изменения темы"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'theme_manager') and app.theme_manager:
                # Загружаем новую тему
                success = app.theme_manager.load(self.current_theme, self.current_variant)
                if success:
                    # Сохраняем в конфигурацию
                    if hasattr(app, 'user_config'):
                        app.user_config.update({
                            'theme': self.current_theme,
                            'variant': self.current_variant
                        })
                        # user_config.save() вызывается автоматически в update()
                    logger.info(f"Applied theme: {self.current_theme}/{self.current_variant}")
                else:
                    logger.error("Failed to load new theme")
        except Exception as e:
            logger.error(f"Error applying theme change: {e}")

    def _apply_language_change(self):
        """Применение изменения языка"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                # Устанавливаем новый язык
                app.localizer.set_language(self.current_language)
                
                # Сохраняем в конфигурацию
                if hasattr(app, 'user_config'):
                    app.user_config['language'] = self.current_language
                    # user_config.save() вызывается автоматически при присвоении
                    
                logger.info(f"Applied language: {self.current_language}")
        except Exception as e:
            logger.error(f"Error applying language change: {e}")

    # ======================================
    # УПРАВЛЕНИЕ АВТОТЕМОЙ И ГРОМКОСТЬЮ
    # ======================================

    def toggle_auto_theme(self, enabled):
        """Переключение автотемы"""
        try:
            self.auto_theme_enabled = enabled
            
            app = App.get_running_app()
            if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
                # ИСПРАВЛЕНО: используем set_enabled вместо enable/disable
                app.auto_theme_service.set_enabled(enabled)
                    
            # Сохраняем в конфигурацию (ИСПРАВЛЕНО: используем set)
            if hasattr(app, 'user_config'):
                app.user_config.set('auto_theme', enabled)
                # user_config.set() автоматически сохраняет
                
            logger.info(f"Auto theme {'enabled' if enabled else 'disabled'}")
            
        except Exception as e:
            logger.error(f"Error toggling auto theme: {e}")

    def on_threshold_change(self, value):
        """Изменение порога света для автотемы"""
        try:
            self.light_sensor_threshold = value
            
            app = App.get_running_app()
            if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
                # ИСПРАВЛЕНО: используем calibrate_sensor вместо set_threshold
                app.auto_theme_service.calibrate_sensor(value)
                
            # Сохраняем в конфигурацию (ИСПРАВЛЕНО: используем set)
            if hasattr(app, 'user_config'):
                app.user_config.set('light_threshold', value)
                # user_config.set() автоматически сохраняет
                
            logger.debug(f"Light threshold changed to: {value}")
            
        except Exception as e:
            logger.error(f"Error changing threshold: {e}")

    def on_volume_change(self, value):
        """Изменение громкости"""
        try:
            self.current_volume = int(value)
            
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service:
                app.volume_service.set_volume(value / 100.0)  # Конвертируем в 0.0-1.0
                
            logger.debug(f"Volume changed to: {value}%")
            
        except Exception as e:
            logger.error(f"Error changing volume: {e}")

    # ======================================
    # ЗАГРУЗКА И СОХРАНЕНИЕ НАСТРОЕК
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
                self.birth_day = str(config.get("birth_day", "01")).zfill(2)
                self.birth_month = str(config.get("birth_month", "01")).zfill(2)
                self.birth_year = str(config.get("birth_year", "2000"))
                
                # Auto theme settings
                self.auto_theme_enabled = config.get("auto_theme", False)
                self.light_sensor_threshold = config.get("light_threshold", 3)
                
                logger.debug("Settings loaded from config")
            else:
                logger.warning("User config not available")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def save_all_settings(self):
        """ИСПРАВЛЕНО: Сохранение всех настроек через update()"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'user_config'):
                # ИСПРАВЛЕНО: Используем правильный метод update()
                app.user_config.update({
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
                
                logger.info("Settings saved successfully")
                
                # Показываем уведомление
                if hasattr(app, 'notification_service') and app.notification_service:
                    app.notification_service.add("Settings saved successfully", "system")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    # ======================================
    # ПРОВЕРКА СЕРВИСОВ
    # ======================================

    def check_sensor_availability(self):
        """Проверка доступности датчика освещенности"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'sensor_service') and app.sensor_service:
                # Проверяем наличие light sensor в sensor_service
                sensors = getattr(app.sensor_service, 'sensors', {})
                light_sensor = sensors.get('light')
                
                if light_sensor and hasattr(light_sensor, 'is_available'):
                    self.light_sensor_available = light_sensor.is_available()
                    if self.light_sensor_available:
                        # Получаем текущие показания
                        current_light = light_sensor.get_light_level()
                        self.current_light_status = f"Current: {current_light:.1f} lux"
                else:
                    self.light_sensor_available = False
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
        """Проверка доступности сервиса громкости"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service:
                self.volume_service_available = True
                # Получаем текущую громкость
                try:
                    current_vol = app.volume_service.get_volume()
                    self.current_volume = int(current_vol * 100)  # Конвертируем в 0-100
                except:
                    self.current_volume = 50  # Дефолтное значение
            else:
                self.volume_service_available = False
                self.current_volume = 50
                
            logger.debug(f"Volume service available: {self.volume_service_available}")
            
        except Exception as e:
            logger.error(f"Error checking volume service: {e}")
            self.volume_service_available = False

    # ======================================
    # ПЕРИОДИЧЕСКИЕ ОБНОВЛЕНИЯ
    # ======================================

    def start_settings_updates(self):
        """Запуск периодических обновлений"""
        try:
            if not self._settings_update_events:
                self._settings_update_events = [
                    Clock.schedule_interval(lambda dt: self.check_sensor_availability(), 5),
                    Clock.schedule_interval(lambda dt: self.check_volume_service(), 10),
                ]
                logger.debug("Settings updates started")
        except Exception as e:
            logger.error(f"Error starting settings updates: {e}")

    def stop_settings_updates(self):
        """Остановка периодических обновлений"""
        try:
            for event in self._settings_update_events:
                if event:
                    event.cancel()
            self._settings_update_events = []
            logger.debug("Settings updates stopped")
        except Exception as e:
            logger.error(f"Error stopping settings updates: {e}")

    # ======================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ======================================

    def _setup_select_buttons(self):
        """Настройка кнопок выбора"""
        try:
            if not hasattr(self, 'ids'):
                return
                
            # Здесь можно настроить селекторы тем/языков
            # если они реализованы как кастомные виджеты
            
        except Exception as e:
            logger.error(f"Error setting up select buttons: {e}")

    def _update_select_buttons_theme(self, theme_manager):
        """Обновление темы для кнопок выбора"""
        try:
            # Обновляем стили селекторов согласно теме
            pass
        except Exception as e:
            logger.error(f"Error updating select buttons theme: {e}")

    def _update_theme_preview(self, theme_manager):
        """Обновление превью темы"""
        try:
            # Обновляем preview элементы если есть
            pass
        except Exception as e:
            logger.error(f"Error updating theme preview: {e}")