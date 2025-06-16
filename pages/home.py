# pages/home.py - ИСПРАВЛЕННАЯ версия с BaseScreen
"""
ИСПРАВЛЕНИЯ:
✅ Полная миграция на BaseScreen
✅ Убраны прямые подписки на события тем
✅ Убраны дублирующие методы
✅ Полное соответствие дизайну home.kv
✅ Правильные названия виджетов из KV
"""

from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.app import App
import time
import datetime
from app.event_bus import event_bus
from app.logger import app_logger as logger
from widgets.base_screen import BaseScreen


class HomeScreen(BaseScreen):
    """Главный экран с часами, датой, погодой и уведомлениями"""
    
    # Основные свойства для отображения (названия соответствуют home.kv)
    clock_time = StringProperty("--:--")
    current_date = StringProperty("")
    current_alarm_time = StringProperty("--:--")
    alarm_status_text = StringProperty("OFF")
    
    # Разделенная погода для правильного окрашивания
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
        super().__init__(**kwargs)  # BaseScreen автоматически подписывается на события
        
        # События для обновлений
        self._update_events = []
        
        # Переменные для оптимизации обновлений
        self._last_alarm_update = 0
        self._alarm_update_delay = 0.5  # Минимум 500ms между обновлениями
        self._cached_alarm_data = None
        
        # Подписка на специфичные события приложения
        event_bus.subscribe("alarm_settings_changed", self._on_alarm_settings_changed)
        
        logger.info("HomeScreen initialized with BaseScreen")

    def on_screen_initialized(self):
        """Переопределяем метод BaseScreen для специфичной инициализации"""
        try:
            # Выполняем первичную инициализацию данных
            self.update_all_data()
            logger.debug("HomeScreen initialization completed")
        except Exception as e:
            logger.error(f"Error in HomeScreen initialization: {e}")

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering HomeScreen")
        self.update_all_data()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

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
        """Полное обновление всех данных экрана"""
        self.update_time()
        self.update_weather()
        self.update_alarm_status()
        self.update_notifications()

    def update_time(self):
        """Обновление времени и даты"""
        try:
            now = datetime.datetime.now()
            self.clock_time = now.strftime("%H:%M")
            
            # Обновляем дату только если изменилась
            new_date = now.strftime("%A, %B %d")
            if self.current_date != new_date:
                self.current_date = new_date
                
        except Exception as e:
            logger.error(f"Error updating time: {e}")

    def update_weather(self):
        """Обновление погоды"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'weather_service') and app.weather_service:
                weather_data = app.weather_service.get_weather()
                if weather_data:
                    # Текущая погода
                    current = weather_data.get("current", {})
                    self.weather_now_temp = str(current.get("temperature", "--°C"))
                    self.weather_now_condition = str(current.get("condition", "Unknown"))
                    
                    # Прогноз на 5 часов
                    forecast = weather_data.get("forecast", {})
                    self.weather_5h_temp = str(forecast.get("temperature", "--°C")) 
                    self.weather_5h_condition = str(forecast.get("condition", "Unknown"))
                    
                    # Анализируем тренд температуры
                    try:
                        current_temp = float(current.get("temperature", "20").replace("°C", ""))
                        forecast_temp = float(forecast.get("temperature", "20").replace("°C", ""))
                        
                        self.current_temp_value = current_temp
                        self.forecast_temp_value = forecast_temp
                        
                        temp_diff = forecast_temp - current_temp
                        if temp_diff > 1:
                            self.temp_trend = 1
                            self.weather_trend_arrow = "↗"
                        elif temp_diff < -1:
                            self.temp_trend = -1  
                            self.weather_trend_arrow = "↘"
                        else:
                            self.temp_trend = 0
                            self.weather_trend_arrow = "→"
                            
                    except (ValueError, TypeError):
                        self.temp_trend = 0
                        self.weather_trend_arrow = "→"
                        
                    logger.debug("Weather data updated")
                    
        except Exception as e:
            logger.error(f"Error updating weather: {e}")

    def update_alarm_status(self, force_update=False):
        """Обновление статуса будильника с debouncing"""
        current_time = time.time()
        
        # Debouncing: предотвращаем частые обновления
        if not force_update and (current_time - self._last_alarm_update) < self._alarm_update_delay:
            return
            
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm_data = app.alarm_service.get_alarm()
                
                # Кэширование: обновляем только если данные изменились
                if alarm_data != self._cached_alarm_data or force_update:
                    self._cached_alarm_data = alarm_data.copy() if alarm_data else None
                    
                    if alarm_data:
                        self.current_alarm_time = alarm_data.get("time", "--:--")
                        self.alarm_status_text = "ON" if alarm_data.get("enabled", False) else "OFF"
                    else:
                        self.current_alarm_time = "--:--"
                        self.alarm_status_text = "OFF"
                    
                    self._last_alarm_update = current_time
                    logger.debug("Alarm status updated")
                    
        except Exception as e:
            logger.error(f"Error updating alarm status: {e}")

    def is_alarm_enabled(self):
        """Проверка включен ли будильник"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                return alarm.get("enabled", False) if alarm else False
        except Exception as e:
            logger.error(f"Error checking alarm status: {e}")
            return False

    def _on_alarm_settings_changed(self, event_data):
        """Обработка изменения настроек будильника"""
        try:
            logger.debug("Alarm settings changed, updating display")
            Clock.schedule_once(lambda dt: self.update_alarm_status(force_update=True), 0.1)
        except Exception as e:
            logger.error(f"Error handling alarm settings change: {e}")

    def update_notifications(self, *args):
        """Обновление уведомлений"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'notification_service') and app.notification_service:
                notifications = app.notification_service.list_unread()
                if notifications:
                    # Берём только последнее уведомление
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
            logger.debug(f"Minor error setting welcome notification: {e}")

    def scroll_notification(self, *args):
        """Прокрутка уведомлений"""
        try:
            if len(self.notification_text) > 50:  # Только если текст длинный
                scroll_speed = 15  # пикселей в секунду
                self.notification_scroll_x += scroll_speed * 0.1
                
                # Сброс прокрутки когда текст прокрутился полностью
                if self.notification_scroll_x > len(self.notification_text) * 8:
                    self.notification_scroll_x = -200  # Начинаем заново с левого края
        except Exception as e:
            logger.debug(f"Minor error scrolling notification: {e}")

    def toggle_alarm(self):
        """Переключение будильника"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'alarm_service') and app.alarm_service:
                app.alarm_service.toggle_enabled()
                
                # Проигрываем звук переключения
                if hasattr(app, 'audio_service') and app.audio_service:
                    sound_file = "sounds/click.mp3"
                    Clock.schedule_once(lambda dt: app.audio_service.play(sound_file), 0.1)
                    
                # Принудительно обновляем статус
                Clock.schedule_once(lambda dt: self.update_alarm_status(force_update=True), 0.1)
                logger.info("Alarm toggled")
                
        except Exception as e:
            logger.error(f"Error toggling alarm: {e}")

    # ========================================
    # ЦВЕТА ПОГОДЫ
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
    # ПЕРЕОПРЕДЕЛЕННЫЕ МЕТОДЫ BaseScreen
    # ========================================

    def on_theme_refresh(self, theme_manager):
        """
        Специфичное обновление темы для HomeScreen
        BaseScreen уже обновил все стандартные элементы
        """
        try:
            # Обновляем виджеты с особой логикой согласно home.kv
            special_widgets = {
                # Часы и тени (соответствие id из home.kv)
                "clock_label": {
                    'font_name': theme_manager.get_font("clock"),
                    'color': theme_manager.get_rgba("primary")
                },
                "clock_shadow1": {
                    'font_name': theme_manager.get_font("clock"),
                    'color': theme_manager.get_rgba("clock_shadow")
                },
                "clock_shadow2": {
                    'font_name': theme_manager.get_font("clock"),
                    'color': theme_manager.get_rgba("clock_shadow")
                },
                "clock_shadow3": {
                    'font_name': theme_manager.get_font("clock"),
                    'color': theme_manager.get_rgba("clock_shadow")
                },
                
                # Дата и будильник
                "date_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': theme_manager.get_rgba("text_secondary")
                },
                "alarm_time_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': theme_manager.get_rgba("text")
                },
                "alarm_toggle_btn": {
                    'color': theme_manager.get_rgba("text_accent") if self.is_alarm_enabled() else theme_manager.get_rgba("text_inactive")
                },
                
                # Погода (соответствие id из home.kv)
                "weather_now_temp_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': self.get_temperature_color(self.current_temp_value)
                },
                "weather_now_condition_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': theme_manager.get_rgba("text")
                },
                "weather_5h_temp_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': self.get_temperature_color(self.forecast_temp_value)
                },
                "weather_5h_condition_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': theme_manager.get_rgba("text")
                },
                "weather_5h_in_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': theme_manager.get_rgba("text_secondary")
                },
                "weather_trend_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': self.get_trend_arrow_color()
                },
                
                # Уведомления
                "notification_text_label": {
                    'font_name': theme_manager.get_font("main"),
                    'color': theme_manager.get_rgba("text")
                }
            }

            # Применяем специальные стили
            for widget_id, styles in special_widgets.items():
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    for prop, value in styles.items():
                        if hasattr(widget, prop) and value:
                            setattr(widget, prop, value)

            logger.debug("HomeScreen theme refresh completed")
            
        except Exception as e:
            logger.error(f"Error in HomeScreen theme refresh: {e}")

    def refresh_text(self):
        """Обновление локализованных текстов"""
        try:
            # Обновляем текст "in 5h"
            self.weather_5h_in_text = self._get_localized_text("in_5h", "in 5h")
            
            # Обновляем приветственное сообщение если оно активно
            if "Welcome" in self.notification_text or "Bedrock" in self.notification_text:
                self._set_welcome_notification()
                
            logger.debug("HomeScreen text refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing HomeScreen text: {e}")

    def force_alarm_status_refresh(self):
        """Принудительное обновление статуса будильника"""
        self._cached_alarm_data = None
        self._last_alarm_update = 0
        self.update_alarm_status()
        logger.info("Forced alarm status refresh")