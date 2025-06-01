from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.app import App
from app.event_bus import event_bus
from app.logger import app_logger as logger
from datetime import datetime


class HomeScreen(Screen):
    """Главный экран с часами, датой, погодой и уведомлениями"""
    
    # Основные свойства для отображения
    clock_time = StringProperty("--:--")
    current_date = StringProperty("")
    current_alarm_time = StringProperty("--:--")
    alarm_status_text = StringProperty("OFF")
    
    # Погода
    weather_now_str = StringProperty("Loading...")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("→")
    
    # Уведомления - бегущая строка
    notification_text = StringProperty("Welcome to Bedrock 2.0!")
    notification_scroll_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # События для обновлений
        self._update_events = []
        
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme)
        event_bus.subscribe("language_changed", self.refresh_text)
        
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
            now = datetime.now()
            self.clock_time = now.strftime("%H:%M")
            
            # Локализованная дата
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                day_names = {
                    0: "day_monday", 1: "day_tuesday", 2: "day_wednesday", 
                    3: "day_thursday", 4: "day_friday", 5: "day_saturday", 6: "day_sunday"
                }
                month_names = {
                    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
                }
                
                day_key = day_names.get(now.weekday(), "day_monday")
                day_name = app.localizer.tr(day_key, now.strftime("%A"))
                month_name = month_names.get(now.month, now.strftime("%B"))
                
                self.current_date = f"{now.day} {month_name}, {day_name}"
            else:
                self.current_date = now.strftime("%d %B, %A")
                
        except Exception as e:
            logger.error(f"Error updating time: {e}")
            self.clock_time = "--:--"
            self.current_date = "Error"

    def update_weather(self, *args):
        """Обновление данных о погоде"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'weather_service') and app.weather_service:
                weather = app.weather_service.get_weather()
                
                # Текущая погода
                current = weather.get("current", {})
                if current:
                    temp_now = current.get('temperature', 0)
                    condition_now = current.get('condition', 'Unknown')
                    self.weather_now_str = f"{temp_now:.1f}°C {condition_now}"
                else:
                    self.weather_now_str = "No data"
                
                # Прогноз на 5 часов
                forecast_5h = weather.get("forecast_5h", {})
                if forecast_5h and forecast_5h.get('temperature') is not None:
                    temp_5h = forecast_5h.get('temperature', 0)
                    
                    if hasattr(app, 'localizer') and app.localizer:
                        in_5h_text = app.localizer.tr("in_5h", "in 5h")
                    else:
                        in_5h_text = "in 5h"
                    
                    self.weather_5h_str = f"{temp_5h:.1f}°C {in_5h_text}"
                    
                    # Тренд температуры
                    temp_diff = temp_5h - temp_now
                    if temp_diff > 1:
                        self.weather_trend_arrow = "↗"  # Растет
                    elif temp_diff < -1:
                        self.weather_trend_arrow = "↘"  # Падает
                    else:
                        self.weather_trend_arrow = "→"  # Стабильно
                else:
                    self.weather_5h_str = "No forecast"
                    self.weather_trend_arrow = "→"
            else:
                self.weather_now_str = "Service offline"
                self.weather_5h_str = "Service offline"
                self.weather_trend_arrow = "→"
                
        except Exception as e:
            logger.error(f"Error updating weather: {e}")
            self.weather_now_str = "Error"
            self.weather_5h_str = "Error"
            self.weather_trend_arrow = "→"

    def update_alarm_status(self, *args):
        """Обновление статуса будильника"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                if alarm and alarm.get("enabled", False):
                    self.current_alarm_time = alarm.get("time", "--:--")
                    if hasattr(app, 'localizer') and app.localizer:
                        self.alarm_status_text = app.localizer.tr("alarm_on", "ON")
                    else:
                        self.alarm_status_text = "ON"
                else:
                    self.current_alarm_time = "--:--"
                    if hasattr(app, 'localizer') and app.localizer:
                        self.alarm_status_text = app.localizer.tr("alarm_off", "OFF")
                    else:
                        self.alarm_status_text = "OFF"
            else:
                self.current_alarm_time = "--:--"
                self.alarm_status_text = "SERVICE OFFLINE"
                
        except Exception as e:
            logger.error(f"Error updating alarm status: {e}")
            self.current_alarm_time = "--:--"
            self.alarm_status_text = "ERROR"

    def update_notifications(self, *args):
        """Обновление уведомлений"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'notification_service') and app.notification_service:
                notifications = app.notification_service.list_unread()
                if notifications:
                    # Объединяем все уведомления в одну строку
                    texts = [n.get("text", "").strip() for n in notifications if n.get("text")]
                    if texts:
                        self.notification_text = "   •   ".join(texts)
                    else:
                        self.notification_text = "No new notifications"
                else:
                    if hasattr(app, 'user_config') and app.user_config:
                        username = app.user_config.get("username", "User")
                        if hasattr(app, 'localizer') and app.localizer:
                            welcome_text = app.localizer.tr("hello_user", "Hello, {username}!").format(username=username)
                            self.notification_text = welcome_text
                        else:
                            self.notification_text = f"Hello, {username}!"
                    else:
                        self.notification_text = "Welcome to Bedrock 2.0!"
            else:
                self.notification_text = "Notification service offline"
                
        except Exception as e:
            logger.error(f"Error updating notifications: {e}")
            self.notification_text = "Error loading notifications"

    def scroll_notification(self, *args):
        """Прокрутка уведомлений (бегущая строка)"""
        try:
            if not hasattr(self, 'ids') or 'notification_container' not in self.ids:
                return
                
            container = self.ids.notification_container
            if not hasattr(self, 'ids') or 'notification_text_label' not in self.ids:
                return
                
            label = self.ids.notification_text_label
            
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

    def toggle_alarm(self, *args):
        """Переключение состояния будильника"""
        try:
            app = App.get_running_app()
            
            # Воспроизводим звук
            tm = self.get_theme_manager()
            if hasattr(app, 'audio_service') and app.audio_service and tm:
                sound_file = tm.get_sound("click")
                if sound_file:
                    app.audio_service.play(sound_file)
            
            # Переключаем состояние будильника
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    new_enabled = not alarm.get("enabled", False)
                    alarm["enabled"] = new_enabled
                    app.alarm_service.set_alarm(alarm)
                    
                    # Немедленно обновляем отображение
                    self.update_alarm_status()
                    
                    logger.info(f"Alarm toggled: {'ON' if new_enabled else 'OFF'}")
                else:
                    logger.error("No alarm configuration found")
            else:
                logger.error("Alarm service not available")
                
        except Exception as e:
            logger.error(f"Error toggling alarm: {e}")

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            logger.warning("ThemeManager not loaded in HomeScreen.refresh_theme")
            return

        # Список виджетов для обновления темы
        widgets_to_update = [
            "date_label", "alarm_time_label", "alarm_toggle_btn", 
            "clock_label", "clock_shadow1", "clock_shadow2", "clock_shadow3",
            "weather_now_label", "weather_trend_label", "weather_5h_label",
            "notification_text_label"
        ]
        
        for widget_id in widgets_to_update:
            if hasattr(self, 'ids') and widget_id in self.ids:
                widget = self.ids[widget_id]
                
                # Обновляем шрифт
                if hasattr(widget, 'font_name'):
                    font_path = tm.get_font("main")
                    if font_path:
                        widget.font_name = font_path
                    
                # Обновляем цвет текста
                if hasattr(widget, 'color'):
                    if widget_id == "clock_label":
                        # Часы всегда белые
                        widget.color = [1, 1, 1, 1]
                    elif widget_id in ["clock_shadow1", "clock_shadow2", "clock_shadow3"]:
                        # Тени остаются черными с разной прозрачностью
                        pass
                    elif widget_id in ["alarm_time_label", "weather_now_label", "weather_trend_label"]:
                        widget.color = tm.get_rgba("primary")
                    elif widget_id in ["date_label", "weather_5h_label", "notification_text_label"]:
                        widget.color = tm.get_rgba("text")
                
                # Обновляем фон кнопок
                if hasattr(widget, 'background_normal'):
                    bg_normal = tm.get_image("button_bg")
                    bg_active = tm.get_image("button_bg_active")
                    if bg_normal:
                        widget.background_normal = bg_normal
                    if bg_active:
                        widget.background_down = bg_active

        logger.debug("HomeScreen theme refreshed")

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        # Обновляем дату, будильник и уведомления
        self.update_time()
        self.update_alarm_status() 
        self.update_notifications()