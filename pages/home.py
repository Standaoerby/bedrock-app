# pages/home.py - ПОЛНАЯ ОПТИМИЗИРОВАННАЯ ВЕРСИЯ (со всеми методами)
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.app import App
import time
import datetime
from app.event_bus import event_bus
from app.logger import app_logger as logger


class HomeScreen(Screen):
    """ОПТИМИЗИРОВАННЫЙ главный экран с часами, датой, погодой и уведомлениями"""
    
    # Основные свойства для отображения (названия соответствуют KV файлу)
    clock_time = StringProperty("--:--")
    current_date = StringProperty("")
    current_alarm_time = StringProperty("--:--")
    alarm_status_text = StringProperty("OFF")
    
    # ИСПРАВЛЕНО: Разделенная погода для правильного окрашивания
    # Текущая погода
    weather_now_temp = StringProperty("--°C")
    weather_now_condition = StringProperty("Loading...")
    
    # Прогноз на 5 часов
    weather_5h_temp = StringProperty("--°C")
    weather_5h_condition = StringProperty("Unknown")
    weather_5h_in_text = StringProperty("in 5h")
    
    # Стрелка тренда
    weather_trend_arrow = StringProperty("→")
    
    # Температуры для цветовой логики
    current_temp_value = NumericProperty(20)
    forecast_temp_value = NumericProperty(20)
    temp_trend = NumericProperty(0)  # -1, 0, 1 для падения, стабильно, рост
    
    # Уведомления - бегущая строка
    notification_text = StringProperty("Welcome to Bedrock 2.0!")
    notification_scroll_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # События для обновлений
        self._update_events = []
        
        # ОПТИМИЗАЦИЯ: Переменные для debouncing и кэширования
        self._last_alarm_update = 0
        self._alarm_update_delay = 0.5  # Минимум 500ms между обновлениями
        self._pending_theme_refresh = False
        self._cached_alarm_data = None
        self._alarm_data_changed = True
        
        # Переменные для оптимизации обновлений
        self._update_schedulers = {}
        self._last_full_update = 0
        self._full_update_interval = 30  # Полное обновление каждые 30 секунд
        
        # Инициализируем все свойства значениями по умолчанию
        self.clock_time = "--:--"
        self.current_date = ""
        self.current_alarm_time = "--:--"
        self.alarm_status_text = "OFF"
        
        # ИСПРАВЛЕНО: Инициализация разделенных полей погоды
        self.weather_now_temp = "--°C"
        self.weather_now_condition = "Loading..."
        self.weather_5h_temp = "--°C"
        self.weather_5h_condition = "Unknown"
        self.weather_5h_in_text = "in 5h"
        self.weather_trend_arrow = "→"
        
        self.current_temp_value = 20
        self.forecast_temp_value = 20
        self.temp_trend = 0
        self.notification_text = "Welcome to Bedrock 2.0!"
        self.notification_scroll_x = 0
        
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme)
        event_bus.subscribe("language_changed", self.refresh_text)
        # ИСПРАВЛЕНО: Подписка на события изменения настроек будильника
        event_bus.subscribe("alarm_settings_changed", self._on_alarm_settings_changed)
        
        logger.info("HomeScreen initialized with optimizations")

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering HomeScreen")
        self.refresh_theme()
        self.refresh_text()
        self.update_all_data()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in HomeScreen")
        return None

    def start_updates(self):
        """Запуск периодических обновлений"""
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_time(), 1),           # Время каждую секунду
            Clock.schedule_interval(lambda dt: self.update_weather(), 300),      # Погода каждые 5 минут
            Clock.schedule_interval(lambda dt: self.update_alarm_status(), 60),  # Будильник каждую минуту
            Clock.schedule_interval(lambda dt: self.update_notifications(), 30), # Уведомления каждые 30 сек
            Clock.schedule_interval(lambda dt: self.scroll_notification(), 0.1), # Прокрутка уведомлений
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        for event in self._update_events:
            if event:
                event.cancel()
        self._update_events = []

    def update_all_data(self):
        """Полное обновление всех данных"""
        self.update_time()
        self.update_weather()
        self.update_alarm_status()
        self.update_notifications()

    def update_time(self, *args):
        """Обновление времени и даты"""
        try:
            now = datetime.datetime.now()
            self.clock_time = now.strftime("%H:%M")
            
            # Обновляем дату только если она изменилась
            new_date = now.strftime("%A, %B %d")
            if self.current_date != new_date:
                self.current_date = new_date
                logger.debug(f"Date updated to: {new_date}")
                
        except Exception as e:
            logger.error(f"Error updating time: {e}")

# pages/home.py - ИСПРАВЛЕНИЯ для метода update_weather
# Заменяем существующий метод update_weather на этот:

    def update_weather(self, *args):
        """🔥 ИСПРАВЛЕННОЕ обновление погоды с проверкой готовности сервиса"""
        try:
            app = App.get_running_app()
            
            # 🔥 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Проверяем готовность weather_service
            if not hasattr(app, 'weather_service') or not app.weather_service:
                # Сервис еще не инициализирован - планируем повторную проверку
                self._set_weather_service_loading()
                Clock.schedule_once(lambda dt: self.update_weather(), 2.0)  # Проверяем через 2 сек
                logger.debug("Weather service not ready, scheduled retry in 2s")
                return
            
            # Сервис готов - получаем данные
            weather_data = app.weather_service.get_weather()
            
            if weather_data:
                # Текущая погода
                current = weather_data.get("current", {})
                self.weather_now_temp = f"{current.get('temperature', 20)}°"
                self.weather_now_condition = current.get('condition', 'Unknown')
                self.current_temp_value = current.get('temperature', 20)
                
                # Прогноз на 5 часов
                forecast = weather_data.get("forecast_5h", {})
                self.weather_5h_temp = f"{forecast.get('temperature', 18)}°"
                self.weather_5h_condition = forecast.get('condition', 'Unknown')
                self.forecast_temp_value = forecast.get('temperature', 18)
                
                # Тренд температуры
                self.temp_trend = self.forecast_temp_value - self.current_temp_value
                if self.temp_trend > 0:
                    self.weather_trend_arrow = "↗"
                elif self.temp_trend < 0:
                    self.weather_trend_arrow = "↘"
                else:
                    self.weather_trend_arrow = "→"
                
                # Время прогноза (локализованное)
                self.weather_5h_in_text = self._get_localized_text("in_5h", "in 5h")
                
                logger.debug(f"Weather updated: {self.weather_now_temp} -> {self.weather_5h_temp}")
            else:
                self._set_weather_no_data()
            
        except Exception as e:
            logger.error(f"Error updating weather: {e}")
            self._set_weather_service_offline()

    def _set_weather_service_loading(self):
        """🔥 НОВЫЙ МЕТОД: Устанавливает состояние "загрузка сервиса погоды" """
        self.weather_now_temp = "..."
        self.weather_now_condition = "Loading..."
        self.weather_5h_temp = "..."
        self.weather_5h_condition = "Starting..."
        self.weather_trend_arrow = "⏳"
        self.weather_5h_in_text = "Please wait"
        self.current_temp_value = 20
        self.forecast_temp_value = 20
        self.temp_trend = 0

    def _set_weather_no_data(self):
        """Устанавливает состояние "нет данных о погоде" """
        self.weather_now_temp = "--°"
        self.weather_now_condition = "No Data"
        self.weather_5h_temp = "--°"
        self.weather_5h_condition = "No Data"
        self.weather_trend_arrow = "?"
        self.weather_5h_in_text = self._get_localized_text("in_5h", "in 5h")
        self.current_temp_value = 20
        self.forecast_temp_value = 20
        self.temp_trend = 0

    def _set_weather_service_offline(self):
        """Устанавливает состояние "сервис погоды недоступен" """
        self.weather_now_temp = "Error"
        self.weather_now_condition = "Service Offline"
        self.weather_5h_temp = "Error"
        self.weather_5h_condition = "Service Offline"
        self.weather_trend_arrow = "✗"
        self.weather_5h_in_text = "Try again later"
        self.current_temp_value = 20
        self.forecast_temp_value = 20
        self.temp_trend = 0
    # ========================================
    # ОПТИМИЗИРОВАННЫЕ МЕТОДЫ БУДИЛЬНИКА
    # ========================================

    def update_alarm_status(self, *args):
        """ОПТИМИЗИРОВАННОЕ обновление статуса будильника БЕЗ лагов"""
        try:
            # DEBOUNCING - предотвращаем слишком частые обновления
            current_time = time.time()
            if current_time - self._last_alarm_update < self._alarm_update_delay:
                logger.debug("Alarm status update skipped due to debouncing")
                return
            
            self._last_alarm_update = current_time
            
            app = App.get_running_app()
            
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    # Обновляем время будильника
                    new_alarm_time = alarm.get("time", "07:30")
                    if self.current_alarm_time != new_alarm_time:
                        self.current_alarm_time = new_alarm_time
                        logger.debug(f"Alarm time updated to: {new_alarm_time}")
                    
                    # Обновляем статус
                    enabled = alarm.get("enabled", False)
                    if enabled:
                        new_status = self._get_localized_text("alarm_on", "ON")
                    else:
                        new_status = self._get_localized_text("alarm_off", "OFF")
                    
                    if self.alarm_status_text != new_status:
                        self.alarm_status_text = new_status
                        logger.debug(f"Alarm status updated to: {new_status}")
                        
                        # Планируем ОДНО обновление темы только для будильника
                        self._schedule_single_theme_refresh()
                else:
                    # Нет конфигурации будильника
                    self._set_alarm_defaults()
            else:
                # Сервис недоступен
                self._set_alarm_service_offline()
                
        except Exception as e:
            logger.error(f"Error updating alarm status: {e}")
            self._set_alarm_error_state()

    def _get_localized_text(self, key, default):
        """Получение локализованного текста с fallback"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                return app.localizer.tr(key, default)
            return default
        except Exception:
            return default

    def _set_alarm_defaults(self):
        """Установка значений по умолчанию"""
        if self.current_alarm_time != "07:30":
            self.current_alarm_time = "07:30"
        if self.alarm_status_text != "OFF":
            self.alarm_status_text = "OFF"
            self._schedule_single_theme_refresh()

    def _set_alarm_service_offline(self):
        """Установка статуса когда сервис недоступен"""
        if self.current_alarm_time != "07:30":
            self.current_alarm_time = "07:30"
        if self.alarm_status_text != "SERVICE OFFLINE":
            self.alarm_status_text = "SERVICE OFFLINE"
            self._schedule_single_theme_refresh()

    def _set_alarm_error_state(self):
        """Установка статуса при ошибке"""
        if self.current_alarm_time != "07:30":
            self.current_alarm_time = "07:30"
        if self.alarm_status_text != "ERROR":
            self.alarm_status_text = "ERROR"
            self._schedule_single_theme_refresh()

    def is_alarm_enabled(self):
        """Проверка включен ли будильник"""
        return self.alarm_status_text == "ON"

    def toggle_alarm(self, *args):
        """ОПТИМИЗИРОВАННОЕ переключение будильника"""
        try:
            app = App.get_running_app()
            
            # Воспроизводим звук клика
            self._play_toggle_sound()
            
            # Переключаем состояние будильника
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    current_enabled = alarm.get("enabled", False)
                    new_enabled = not current_enabled
                    
                    # Обновляем настройки
                    alarm["enabled"] = new_enabled
                    success = app.alarm_service.set_alarm(alarm)
                    
                    if success:
                        # ОПТИМИЗАЦИЯ: Принудительно обновляем отображение
                        self._alarm_data_changed = True
                        self.update_alarm_status()
                        
                        logger.info(f"Alarm toggled: {'ON' if new_enabled else 'OFF'}")
                    else:
                        logger.error("Failed to save alarm settings")
                else:
                    logger.error("No alarm configuration found")
            else:
                logger.error("Alarm service not available")
                
        except Exception as e:
            logger.error(f"Error toggling alarm: {e}")

    def _play_toggle_sound(self):
        """Воспроизведение звука переключения"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                tm = self.get_theme_manager()
                if tm:
                    sound_file = tm.get_sound("click")
                    if sound_file:
                        if hasattr(app.audio_service, 'play_async'):
                            app.audio_service.play_async(sound_file)
                        else:
                            app.audio_service.play(sound_file)
        except Exception as e:
            logger.error(f"Error playing toggle sound: {e}")

    def force_alarm_status_refresh(self):
        """Принудительное обновление статуса будильника"""
        self._alarm_data_changed = True
        self._cached_alarm_data = None
        self._last_alarm_update = 0
        self.update_alarm_status()
        logger.info("Forced alarm status refresh")

    # ========================================
    # УВЕДОМЛЕНИЯ
    # ========================================

    def update_notifications(self, *args):
        """ОПТИМИЗИРОВАННОЕ обновление уведомлений"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'notification_service') and app.notification_service:
                notifications = app.notification_service.list_unread()
                if notifications:
                    # Берём только последнее уведомление вместо объединения всех
                    last_notification = notifications[-1]
                    text = last_notification.get("text", "").strip()
                    if text and self.notification_text != text:
                        self.notification_text = text
                        self.notification_scroll_x = 0  # Сбрасываем прокрутку
                        logger.debug("Notification updated")
                else:
                    # Показываем приветствие если нет уведомлений
                    self._set_welcome_notification()
            else:
                self._set_welcome_notification()
                
        except Exception as e:
            logger.error(f"Error updating notifications: {e}")
            self._set_welcome_notification()

    def _set_welcome_notification(self):
        """Установка приветственного сообщения"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'user_config') and app.user_config:
                username = app.user_config.get("username", "User")
                welcome_text = self._get_localized_text("hello_user", "Hello, {username}!").format(username=username)
                if self.notification_text != welcome_text:
                    self.notification_text = welcome_text
                    self.notification_scroll_x = 0
            else:
                default_welcome = "Welcome to Bedrock 2.0!"
                if self.notification_text != default_welcome:
                    self.notification_text = default_welcome
                    self.notification_scroll_x = 0
        except Exception as e:
            logger.error(f"Error setting welcome notification: {e}")

    def scroll_notification(self, *args):
        """Прокрутка уведомлений (бегущая строка)"""
        try:
            if not hasattr(self, 'ids') or 'notification_container' not in self.ids:
                return
                
            container = self.ids.notification_container
            if not hasattr(self, 'ids') or 'notification_text_label' not in self.ids:
                return
                
            label = self.ids.notification_text_label
            
            # Проверяем, что label и container корректно инициализированы
            if not container.width or not label.texture_size:
                return
            
            # Если текст помещается в контейнер, не прокручиваем
            if label.texture_size[0] <= container.width:
                self.notification_scroll_x = 0
                return
            
            # Прокрутка справа налево
            scroll_speed = 1  # пикселей за кадр
            max_scroll = label.texture_size[0] + 50  # добавляем отступ
            
            self.notification_scroll_x -= scroll_speed
            if self.notification_scroll_x < -max_scroll:
                self.notification_scroll_x = container.width
                
        except Exception as e:
            logger.error(f"Error scrolling notification: {e}")

    # ========================================
    # ЦВЕТОВЫЕ МЕТОДЫ (ВАЖНО ДЛЯ ДИЗАЙНА!)
    # ========================================

    def get_temperature_color(self, temp_value):
        """Получить цвет для температуры в зависимости от значения"""
        if temp_value > 23:
            return [1, 0.6, 0, 1]  # Оранжевый для жаркой погоды
        elif temp_value < 18:
            return [0.2, 0.6, 1, 1]  # Синий для холодной погоды
        else:
            tm = self.get_theme_manager()
            return tm.get_rgba("primary") if tm else [1, 1, 1, 1]

    def get_trend_arrow_color(self):
        """Получить цвет стрелки тренда"""
        if self.temp_trend > 0:
            return [1, 0.6, 0, 1]  # Оранжевый для роста
        elif self.temp_trend < 0:
            return [0.2, 0.6, 1, 1]  # Синий для падения
        else:
            tm = self.get_theme_manager()
            return tm.get_rgba("text") if tm else [1, 1, 1, 1]

    # ========================================
    # ОПТИМИЗИРОВАННОЕ ОБНОВЛЕНИЕ ТЕМЫ
    # ========================================

    def _schedule_single_theme_refresh(self):
        """ОПТИМИЗАЦИЯ: Планирование ОДНОГО обновления темы"""
        if not self._pending_theme_refresh:
            self._pending_theme_refresh = True
            Clock.schedule_once(self._execute_theme_refresh, 0.1)

    def _execute_theme_refresh(self, dt):
        """Выполнение обновления темы"""
        try:
            self._pending_theme_refresh = False
            
            if self.should_do_full_update():
                # Полное обновление темы (редко)
                self.refresh_theme()
            else:
                # Частичное обновление только важных элементов (часто)
                self._refresh_alarm_colors()
                
        except Exception as e:
            logger.error(f"Error executing theme refresh: {e}")

    def should_do_full_update(self):
        """Проверка нужно ли делать полное обновление"""
        current_time = time.time()
        if current_time - self._last_full_update > self._full_update_interval:
            self._last_full_update = current_time
            return True
        return False

    def _refresh_alarm_colors(self):
        """ОПТИМИЗАЦИЯ: Обновление только цветов будильника"""
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                return
            
            # Обновляем цвета только элементов будильника
            alarm_widgets = [
                "alarm_time_label", 
                "alarm_toggle_btn"
            ]
            
            for widget_id in alarm_widgets:
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    
                    if widget_id == "alarm_toggle_btn":
                        # Специальная логика для кнопки toggle
                        if self.is_alarm_enabled():
                            widget.color = tm.get_rgba("text_accent")
                        else:
                            widget.color = tm.get_rgba("text_inactive")
                    else:
                        # Обычный текст
                        widget.color = tm.get_rgba("text")
            
            logger.debug("Alarm colors refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing alarm colors: {e}")

    def refresh_theme(self, *args):
        """ПОЛНОЕ обновление темы для всех элементов (как в оригинале)"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            logger.warning("ThemeManager not loaded in HomeScreen.refresh_theme")
            return

        try:
            # ИСПРАВЛЕНО: Обновленный список виджетов с разделенными элементами погоды
            widgets_to_update = [
                "date_label", "alarm_time_label", "alarm_toggle_btn", 
                "clock_label", "clock_shadow1", "clock_shadow2", "clock_shadow3",
                # Разделенные элементы погоды
                "weather_now_temp_label", "weather_now_condition_label",
                "weather_5h_temp_label", "weather_5h_condition_label", "weather_5h_in_label",
                "weather_trend_label",
                "notification_text_label"
            ]
            
            # Получаем путь к шрифту один раз
            font_path = tm.get_font("main")
            
            for widget_id in widgets_to_update:
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    
                    # Обновляем шрифт только если путь корректный
                    if hasattr(widget, 'font_name') and font_path:
                        try:
                            widget.font_name = font_path
                        except Exception as e:
                            logger.warning(f"Failed to set font for {widget_id}: {e}")
                        
                    # ИСПРАВЛЕНО: Правильная логика цветов
                    if hasattr(widget, 'color'):
                        if widget_id == "clock_label":
                            # Часы меняют цвет по теме
                            widget.color = tm.get_rgba("clock_main")
                        elif widget_id in ["clock_shadow1", "clock_shadow2", "clock_shadow3"]:
                            # Тени остаются черными с разной прозрачностью
                            pass
                        elif widget_id == "alarm_time_label":
                            # Цвет времени будильника зависит от статуса
                            if self.is_alarm_enabled():
                                widget.color = tm.get_rgba("primary")
                            else:
                                widget.color = tm.get_rgba("text_secondary")
                        elif widget_id == "alarm_toggle_btn":
                            # ИСПРАВЛЕНО: Цвет И ФОН кнопки будильника зависит от статуса
                            if self.is_alarm_enabled():
                                widget.color = tm.get_rgba("primary")
                            else:
                                widget.color = tm.get_rgba("text_secondary")
                            
                            # ИСПРАВЛЕНО: Добавляем фон кнопке
                            if hasattr(widget, 'background_normal'):
                                widget.background_normal = tm.get_image("button_bg")
                            if hasattr(widget, 'background_down'):
                                widget.background_down = tm.get_image("button_bg_active")
                        # ИСПРАВЛЕНО: Правильные цвета для элементов погоды
                        elif widget_id == "weather_now_temp_label":
                            # Температура сейчас - цвет по условию
                            widget.color = self.get_temperature_color(self.current_temp_value)
                        elif widget_id == "weather_5h_temp_label":
                            # Температура прогноза - цвет по условию
                            widget.color = self.get_temperature_color(self.forecast_temp_value)
                        elif widget_id == "weather_trend_label":
                            # Стрелка тренда - цвет по направлению
                            widget.color = self.get_trend_arrow_color()
                        elif widget_id in ["weather_now_condition_label", "weather_5h_condition_label", "weather_5h_in_label"]:
                            # Остальные элементы погоды - вторичный цвет
                            widget.color = tm.get_rgba("text_secondary")
                        elif widget_id == "notification_text_label":
                            # Уведомления - основной цвет текста
                            widget.color = tm.get_rgba("text")
                        else:
                            # Остальные элементы - основной цвет
                            widget.color = tm.get_rgba("text")
            
            logger.debug("Full theme refresh completed")
            
        except Exception as e:
            logger.error(f"Error in refresh_theme: {e}")

    def refresh_text(self, *args):
        """Обновление локализованных текстов"""
        try:
            # Принудительно обновляем уведомления с новым языком
            self._set_welcome_notification()
            
            # Обновляем статус будильника
            self.force_alarm_status_refresh()
            
            logger.debug("Text refresh completed")
            
        except Exception as e:
            logger.error(f"Error refreshing text: {e}")

    def _on_alarm_settings_changed(self, event_data):
        """ИСПРАВЛЕНО: Обработчик изменения настроек будильника из других страниц"""
        try:
            logger.info("Alarm settings changed event received, refreshing status")
            # Сбрасываем кэш и принудительно обновляем
            self._alarm_data_changed = True
            self._cached_alarm_data = None
            self._last_alarm_update = 0
            # Немедленное обновление статуса
            self.update_alarm_status()
        except Exception as e:
            logger.error(f"Error handling alarm settings change: {e}")

    # ========================================
    # УНИВЕРСАЛЬНЫЙ ПЛАНИРОВЩИК ОБНОВЛЕНИЙ
    # ========================================

    def schedule_update(self, update_name, callback, delay=0.1):
        """Универсальный планировщик обновлений с debouncing"""
        # Отменяем предыдущее обновление если оно есть
        if update_name in self._update_schedulers:
            self._update_schedulers[update_name].cancel()
        
        # Планируем новое
        self._update_schedulers[update_name] = Clock.schedule_once(
            lambda dt: self._execute_scheduled_update(update_name, callback), 
            delay
        )

    def _execute_scheduled_update(self, update_name, callback):
        """Выполнение запланированного обновления"""
        try:
            # Удаляем из планировщика
            if update_name in self._update_schedulers:
                del self._update_schedulers[update_name]
            
            # Выполняем callback
            callback()
            
        except Exception as e:
            logger.error(f"Error executing scheduled update '{update_name}': {e}")