# pages/settings.py
# 🔥 ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ ФАЙЛ с устранением всех багов переключения тем

from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger
import os
import threading


class SettingsScreen(Screen):
    """🔥 ИСПРАВЛЕННЫЙ экран настроек приложения с правильным переключением тем"""
    
    # Theme properties
    current_theme = StringProperty("minecraft")
    current_variant = StringProperty("light")
    current_language = StringProperty("en")
    
    # ListProperty для значений селекторов (устанавливаются один раз)
    theme_list = ListProperty(["minecraft"])
    variant_list = ListProperty(["light", "dark"])
    language_list = ListProperty(["en", "ru"])
    
    # 🔥 ИСПРАВЛЕНО: Свойства для активности селекторов
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
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self._on_theme_changed_delayed)
        event_bus.subscribe("volume_changed", self._on_volume_changed)
        self._update_events = []
        self._initialized = False
        
        # 🔥 НОВОЕ: Защита от множественных обновлений
        self._theme_update_scheduled = False
    def _on_volume_changed(self, event_data):
        """🔥 НОВОЕ: Обработка изменения громкости от других источников"""
        try:
            if isinstance(event_data, dict) and 'volume' in event_data:
                new_volume = event_data['volume']
                if new_volume != self.current_volume:
                    self.current_volume = new_volume
                    logger.debug(f"Volume updated from event: {new_volume}%")
        except Exception as e:
            logger.error(f"Error handling volume change event: {e}")
    # ================================================
    # ЖИЗНЕННЫЙ ЦИКЛ ЭКРАНА
    # ================================================

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering SettingsScreen")
        try:
            self.load_all_settings()
            self.check_sensor_availability()
            self.check_volume_service()
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
        self.stop_updates()

    def start_updates(self):
        """Запуск периодических обновлений"""
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_sensor_status(), 5)
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        for event in self._update_events:
            if event:
                event.cancel()
        self._update_events = []

    # ================================================
    # ОСНОВНЫЕ МЕТОДЫ ПЕРЕКЛЮЧЕНИЯ ТЕМ
    # ================================================

    def on_theme_select(self, theme_name):
        """🔥 ИСПРАВЛЕННЫЙ выбор темы - БЕЗ дублирующих событий"""
        # Проверяем активность селектора темы
        if not self.theme_selector_enabled:
            logger.warning("Theme selector is disabled")
            self._play_sound("error")
            return
            
        if theme_name != self.current_theme:
            app = App.get_running_app()
            
            # Воспроизводим звук
            self._play_sound("click")
            
            # Обновляем локальное состояние
            self.current_theme = theme_name
            
            # 🔥 КРИТИЧНО: ТОЛЬКО загружаем тему - событие публикуется автоматически!
            if hasattr(app, 'theme_manager'):
                success = app.theme_manager.load(theme_name, self.current_variant)
                if success:
                    logger.info(f"✅ Theme changed to: {theme_name}")
                else:
                    logger.error(f"❌ Failed to load theme: {theme_name}")
            
            # 🔥 УБРАНО: event_bus.publish("theme_changed", ...)
            # Событие уже публикуется автоматически из load()!

    def on_variant_select(self, variant):
        """🔥 ИСПРАВЛЕННЫЙ выбор варианта темы - БЕЗ дублирующих событий"""
        if variant != self.current_variant:
            app = App.get_running_app()
            
            # Воспроизводим звук
            self._play_sound("click")
            
            # Обновляем локальное состояние
            self.current_variant = variant
            
            # 🔥 КРИТИЧНО: ТОЛЬКО загружаем тему - событие публикуется автоматически!
            if hasattr(app, 'theme_manager'):
                success = app.theme_manager.load(self.current_theme, variant)
                if success:
                    logger.info(f"✅ Theme variant changed to: {variant}")
                else:
                    logger.error(f"❌ Failed to load variant: {variant}")
            
            # 🔥 УБРАНО: event_bus.publish("theme_changed", ...)
            # Событие уже публикуется автоматически из load()!

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
        """🔥 ИСПРАВЛЕННАЯ асинхронная обработка смены темы"""
        # Защита от множественных обновлений
        if self._theme_update_scheduled:
            return
            
        self._theme_update_scheduled = True
        
        # Отложенное обновление темы, чтобы не конфликтовать с селекторами
        Clock.schedule_once(lambda dt: self._do_delayed_theme_update(), 0.1)

    def _do_delayed_theme_update(self):
        """🔥 НОВОЕ: Выполнение отложенного обновления темы"""
        try:
            self.refresh_theme()
        finally:
            self._theme_update_scheduled = False

    # ================================================
    # АВТОМАТИЧЕСКАЯ ТЕМА
    # ================================================

    def toggle_auto_theme(self):
        """🔥 ИСПРАВЛЕННОЕ переключение автоматической смены темы"""
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
                    logger.info("🌓 Auto-theme enabled and calibrated")
                else:
                    logger.info("🌓 Auto-theme disabled")
            except Exception as e:
                logger.error(f"Error updating auto-theme service: {e}")
        
        # Обновляем UI
        Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
        
        logger.info(f"Auto theme toggled: {self.auto_theme_enabled}")

    def on_threshold_change(self, value):
        """🔥 ИСПРАВЛЕННОЕ изменение порога датчика освещения БЕЗ дублирования логов"""
        try:
            new_threshold = max(1, min(int(value), 5))
            if new_threshold != self.light_sensor_threshold:
                self.light_sensor_threshold = new_threshold
                
                app = App.get_running_app()
                
                # Обновляем AutoThemeService
                if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
                    app.auto_theme_service.calibrate_sensor(new_threshold)
                
                # 🔥 ИСПРАВЛЕНО: НЕ дублируем логирование - AutoThemeService уже логирует
                
        except Exception as e:
            logger.error(f"Error changing threshold: {e}")

    # ================================================
    # ОБНОВЛЕНИЕ ТЕМЫ
    # ================================================

    def refresh_theme(self, *args):
        """🔥 ИСПРАВЛЕННОЕ консистентное обновление темы"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            logger.warning("ThemeManager not loaded in SettingsScreen.refresh_theme")
            return

        try:
            # Список всех виджетов для обновления
            widgets_to_update = [
                "theme_section_label", "language_section_label", "user_section_label",
                "auto_theme_section_label", "volume_section_label",
                "theme_button", "variant_button", "language_button",
                "auto_theme_button", "volume_up_button", "volume_down_button",
                "volume_value_label", "sensor_status_label", "save_button"
            ]
            
            for widget_id in widgets_to_update:
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    self._apply_theme_to_widget(widget, widget_id, tm)
            
            # Специальное обновление кнопки автотемы
            self._update_auto_theme_button(tm)
            
            # Обновляем селекторы темы
            self._update_theme_selectors()
            
            logger.debug("✅ Settings theme refreshed consistently")
            
        except Exception as e:
            logger.error(f"Error refreshing settings theme: {e}")

    def _apply_theme_to_widget(self, widget, widget_id, tm):
        """🔥 НОВОЕ: Применить тему к конкретному виджету"""
        try:
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
                elif widget_id == "sensor_status_label":
                    widget.color = tm.get_rgba("text_secondary")
                elif widget_id == "volume_value_label":
                    widget.color = tm.get_rgba("primary")
                elif widget_id in ["save_button", "volume_up_button", "volume_down_button"]:
                    widget.color = tm.get_rgba("primary")
                else:
                    widget.color = tm.get_rgba("text")
            
            # Обновляем фон кнопок
            if hasattr(widget, 'background_normal'):
                widget.background_normal = tm.get_image("button_bg")
                widget.background_down = tm.get_image("button_bg_active")
                
        except Exception as e:
            logger.error(f"Error applying theme to {widget_id}: {e}")

    def _update_auto_theme_button(self, tm):
        """🔥 НОВОЕ: Обновление кнопки автотемы"""
        try:
            if hasattr(self, 'ids') and 'auto_theme_button' in self.ids:
                button = self.ids.auto_theme_button
                
                # Обновляем текст
                button.text = "ON" if self.auto_theme_enabled else "OFF"
                
                # Обновляем цвет в зависимости от состояния
                if hasattr(button, 'color'):
                    if self.auto_theme_enabled:
                        button.color = tm.get_rgba("primary")
                    else:
                        button.color = tm.get_rgba("text_secondary")
                        
        except Exception as e:
            logger.error(f"Error updating auto theme button: {e}")

    def _update_theme_selectors(self):
        """🔥 НОВОЕ: Обновление селекторов темы"""
        try:
            # Обновляем значения селекторов
            if hasattr(self, 'ids'):
                if 'theme_button' in self.ids:
                    self.ids.theme_button.text = self.current_theme.title()
                    
                if 'variant_button' in self.ids:
                    self.ids.variant_button.text = self.current_variant.title()
                    
        except Exception as e:
            logger.error(f"Error updating theme selectors: {e}")

    # ================================================
    # УТИЛИТЫ
    # ================================================

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in SettingsScreen")
        return None

    def _play_sound(self, sound_name):
        """Воспроизведение звука"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.play_ui_sound(sound_name)
        except Exception as e:
            logger.debug(f"Error playing sound {sound_name}: {e}")

    def refresh_text(self, *args):
        """Обновление текстов интерфейса"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                # Обновляем переводимые элементы
                pass  # TODO: Добавить обновление текстов
        except Exception as e:
            logger.error(f"Error refreshing text: {e}")
    def volume_up(self):
        """🔥 НОВОЕ: Увеличение громкости через VolumeService"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service:
                # Вызываем метод VolumeService
                new_volume = app.volume_service.volume_up_manual()
                
                # Обновляем отображаемое значение
                self.current_volume = new_volume
                
                # Сохраняем в конфиг
                app.user_config.set('volume', new_volume)
                
                logger.info(f"Volume increased to {new_volume}%")
            else:
                logger.warning("Volume service not available")
                
        except Exception as e:
            logger.error(f"Error in volume_up: {e}")

    def volume_down(self):
        """🔥 НОВОЕ: Уменьшение громкости через VolumeService"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service:
                # Вызываем метод VolumeService
                new_volume = app.volume_service.volume_down_manual()
                
                # Обновляем отображаемое значение
                self.current_volume = new_volume
                
                # Сохраняем в конфиг
                app.user_config.set('volume', new_volume)
                
                logger.info(f"Volume decreased to {new_volume}%")
            else:
                logger.warning("Volume service not available")
                
        except Exception as e:
            logger.error(f"Error in volume_down: {e}")

    def set_volume_direct(self, volume):
        """🔥 НОВОЕ: Прямая установка громкости"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_service') and app.volume_service:
                # Ограничиваем значения
                volume = max(0, min(100, int(volume)))
                
                # Устанавливаем громкость
                if app.volume_service.set_volume(volume):
                    self.current_volume = volume
                    app.user_config.set('volume', volume)
                    logger.info(f"Volume set to {volume}%")
                else:
                    logger.warning("Failed to set volume")
            else:
                logger.warning("Volume service not available")
                
        except Exception as e:
            logger.error(f"Error in set_volume_direct: {e}")

    # ================================================
    # ЗАГРУЗКА И СОХРАНЕНИЕ НАСТРОЕК
    # ================================================

    def load_all_settings(self):
        """🔥 ИСПРАВЛЕННАЯ загрузка всех настроек"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'user_config'):
                # Загружаем настройки темы
                self.current_theme = app.user_config.get("theme", "minecraft")
                self.current_variant = app.user_config.get("variant", "light")
                self.current_language = app.user_config.get("language", "en")
                
                # Загружаем пользовательские настройки
                self.username = app.user_config.get("username", "")
                self.birth_day = app.user_config.get("birth_day", "01")
                self.birth_month = app.user_config.get("birth_month", "01")
                self.birth_year = app.user_config.get("birth_year", "2000")
                
                # Загружаем настройки автотемы
                self.auto_theme_enabled = app.user_config.get("auto_theme_enabled", False)
                self.light_sensor_threshold = app.user_config.get("light_sensor_threshold", 3)
                
                logger.info(f"✅ Settings loaded: theme={self.current_theme}, variant={self.current_variant}")
                
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def save_all_settings(self):
        """Сохранение всех настроек"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'user_config'):
                # Сохраняем настройки темы
                app.user_config.set("theme", self.current_theme)
                app.user_config.set("variant", self.current_variant)
                app.user_config.set("language", self.current_language)
                
                # Сохраняем пользовательские настройки
                app.user_config.set("username", self.username)
                app.user_config.set("birth_day", self.birth_day)
                app.user_config.set("birth_month", self.birth_month)
                app.user_config.set("birth_year", self.birth_year)
                
                # Сохраняем настройки автотемы
                app.user_config.set("auto_theme_enabled", self.auto_theme_enabled)
                app.user_config.set("light_sensor_threshold", self.light_sensor_threshold)
                
                logger.info("✅ All settings saved")
                
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    # ================================================
    # ПРОВЕРКА СЕРВИСОВ
    # ================================================

    def check_sensor_availability(self):
        """Проверка доступности датчика освещения"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'auto_theme_service') and app.auto_theme_service:
                status = app.auto_theme_service.get_status()
                self.light_sensor_available = status.get('sensor_available', False)
                
                # Обновляем статус
                if status.get('sensor_available'):
                    using_mock = status.get('using_mock', True)
                    light_level = status.get('current_light', True)
                    status_type = "Mock" if using_mock else "Real"
                    light_text = "☀️Light" if light_level else "🌙Dark"
                    auto_text = "Auto✅" if self.auto_theme_enabled else "Auto❌"
                    self.current_light_status = f"{light_text} ({status_type}, {auto_text})"
                else:
                    self.current_light_status = "Sensor Offline"
                    
            else:
                self.light_sensor_available = False
                self.current_light_status = "Service Offline"
                
        except Exception as e:
            logger.error(f"Error checking sensor availability: {e}")
            self.current_light_status = "Status Error"

    def check_volume_service(self):
        """🔥 ИСПРАВЛЕНО: Улучшенная проверка доступности VolumeService"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'volume_service') and app.volume_service:
                # Проверяем статус сервиса
                status = app.volume_service.get_status()
                
                # Сервис доступен
                self.volume_service_available = True
                
                # Получаем текущую громкость
                current_vol = app.volume_service.get_volume()
                self.current_volume = current_vol
                
                logger.info(f"✅ Volume service available, current volume: {current_vol}%")
                logger.debug(f"Volume service status: {status}")
                
            else:
                self.volume_service_available = False
                self.current_volume = 50  # Default value
                logger.warning("⚠️ Volume service not available")
                
        except Exception as e:
            logger.error(f"Error checking volume service: {e}")
            self.volume_service_available = False
            self.current_volume = 50

    def update_sensor_status(self):
        """Обновление статуса датчика освещения"""
        if self._initialized:
            self.check_sensor_availability()

    def _setup_select_buttons(self):
        """🔧 ИСПРАВЛЕННАЯ версия настройки кнопок выбора"""
        try:
            if not hasattr(self, 'ids'):
                logger.warning("Settings screen missing ids")
                return
                
            # 🔧 ИСПРАВЛЕНО: Обработка отсутствующих кнопок
            theme_button = self.ids.get('theme_select_button')
            variant_button = self.ids.get('variant_select_button') 
            language_button = self.ids.get('language_select_button')
            
            # Проверяем theme button
            if theme_button:
                if hasattr(theme_button, 'bind_selection_callback'):
                    theme_button.bind_selection_callback(self.on_theme_select)
                    logger.debug("✅ Theme button callback bound")
                elif hasattr(theme_button, 'bind'):
                    # Fallback для простых кнопок
                    theme_button.bind(on_release=lambda btn: self.on_theme_select(self.current_theme))
                    logger.debug("✅ Theme button fallback binding")
            else:
                logger.warning("⚠️ Theme select button not found")
                
            # Проверяем variant button
            if variant_button:
                if hasattr(variant_button, 'bind_selection_callback'):
                    variant_button.bind_selection_callback(self.on_variant_select)
                    logger.debug("✅ Variant button callback bound")
                elif hasattr(variant_button, 'bind'):
                    variant_button.bind(on_release=lambda btn: self.on_variant_select(self.current_variant))
                    logger.debug("✅ Variant button fallback binding")
                    
            # Проверяем language button
            if language_button:
                if hasattr(language_button, 'bind_selection_callback'):
                    language_button.bind_selection_callback(self.on_language_select)
                    logger.debug("✅ Language button callback bound")
                elif hasattr(language_button, 'bind'):
                    language_button.bind(on_release=lambda btn: self.on_language_select(self.current_language))
                    logger.debug("✅ Language button fallback binding")
                    
        except Exception as e:
            logger.error(f"❌ Error setting up select buttons: {e}")
    # ================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ ПОЛЬЗОВАТЕЛЯ
    # ================================================

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
            self.birth_year = str(year)
            instance.text = self.birth_year
        except Exception as e:
            logger.error(f"Error in on_birth_year_change: {e}")
            self.birth_year = "2000"
            instance.text = self.birth_year

    def on_save_button_press(self):
        """Обработчик кнопки сохранения"""
        try:
            self.save_all_settings()
            self._play_sound("confirm")
            logger.info("✅ Settings saved by user")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            self._play_sound("error")