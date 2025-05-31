from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty
from kivy.clock import Clock
from app.event_bus import event_bus
from datetime import datetime

class HomeScreen(Screen):
    # Данные для отображения
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("--°C")
    weather_5h_str = StringProperty("--°C")
    weather_trend_arrow = StringProperty("")
    notification_text = StringProperty("")
    current_date = StringProperty("")
    clock_time = StringProperty("--:--")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
        self._clock_event = None
        self._update_events = []

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        self.refresh_theme()
        self.refresh_text()
        self.update_all()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    def start_updates(self):
        """Запуск периодических обновлений"""
        if not self._clock_event:
            # Часы обновляются каждую секунду
            self._clock_event = Clock.schedule_interval(self.update_clock, 1)
            
        # Другие обновления
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_date(), 60),      # Дата раз в минуту
            Clock.schedule_interval(lambda dt: self.update_alarm(), 30),     # Будильник раз в 30 сек
            Clock.schedule_interval(lambda dt: self.update_weather(), 300),  # Погода раз в 5 минут
            Clock.schedule_interval(lambda dt: self.update_notification(), 15), # Уведомления раз в 15 сек
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None
            
        for event in self._update_events:
            event.cancel()
        self._update_events = []

    def update_all(self):
        """Полное обновление всех данных"""
        self.update_date()
        self.update_clock()
        self.update_alarm()
        self.update_weather()
        self.update_notification()

    def update_clock(self, *args):
        """Обновление времени"""
        now = datetime.now()
        self.clock_time = now.strftime("%H:%M")

    def update_date(self, *args):
        """Обновление даты"""
        now = datetime.now()
        # Русский формат даты
        weekdays = {
            0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 
            4: "Пт", 5: "Сб", 6: "Вс"
        }
        months = {
            1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
            7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"
        }
        
        weekday = weekdays[now.weekday()]
        month = months[now.month]
        self.current_date = f"{now.day} {month}, {weekday}"

    def update_alarm(self, *args):
        """Обновление информации о будильнике"""
        app = App.get_running_app()
        if hasattr(app, "alarm_service"):
            alarm = app.alarm_service.get_alarm()
            if alarm:
                self.current_alarm_time = alarm.get("time", "--:--")
                self.alarm_active = alarm.get("enabled", False)
            else:
                self.current_alarm_time = "--:--"
                self.alarm_active = False
        else:
            self.current_alarm_time = "--:--"
            self.alarm_active = False

    def toggle_alarm(self):
        """Переключение состояния будильника"""
        app = App.get_running_app()
        if hasattr(app, "alarm_service"):
            alarm = app.alarm_service.get_alarm()
            if alarm:
                # Переключаем состояние
                alarm["enabled"] = not alarm.get("enabled", False)
                app.alarm_service.set_alarm(alarm)
                
                # Обновляем отображение
                self.update_alarm()
                
                # Звук подтверждения
                if hasattr(app, "audio_service"):
                    sound = "confirm" if alarm["enabled"] else "click"
                    sound_file = app.theme_manager.get_sound(sound)
                    if sound_file:
                        app.audio_service.play(sound_file)

    def update_weather(self, *args):
        """Обновление информации о погоде"""
        app = App.get_running_app()
        if hasattr(app, "weather_service"):
            try:
                weather = app.weather_service.get_weather()
                
                # Текущая погода
                current = weather.get("current", {})
                if current:
                    temp = current.get("temperature", "--")
                    condition = current.get("condition", "")
                    # Сокращаем длинные названия условий
                    if len(condition) > 15:
                        condition = condition[:12] + "..."
                    self.weather_now_str = f"{temp}°C {condition}"
                else:
                    self.weather_now_str = "--°C"
                
                # Прогноз на 5 часов
                forecast_5h = weather.get("forecast_5h", {})
                if forecast_5h and forecast_5h.get("temperature") is not None:
                    temp_5h = forecast_5h.get("temperature", "--")
                    self.weather_5h_str = f"{temp_5h}°C"
                    
                    # Стрелка тренда температуры
                    try:
                        temp_now = float(current.get("temperature", 0))
                        temp_5h_val = float(temp_5h)
                        
                        if temp_5h_val > temp_now + 1:
                            self.weather_trend_arrow = "↗"
                        elif temp_5h_val < temp_now - 1:
                            self.weather_trend_arrow = "↘"
                        else:
                            self.weather_trend_arrow = "→"
                    except (ValueError, TypeError):
                        self.weather_trend_arrow = "→"
                else:
                    self.weather_5h_str = "--°C"
                    self.weather_trend_arrow = ""
                    
            except Exception as e:
                print(f"[HomeScreen] Ошибка обновления погоды: {e}")
                self.weather_now_str = "Ошибка погоды"
                self.weather_5h_str = "--°C"
                self.weather_trend_arrow = ""
        else:
            self.weather_now_str = "Нет сервиса погоды"
            self.weather_5h_str = "--°C"
            self.weather_trend_arrow = ""

    def update_notification(self, *args):
        """Обновление уведомлений"""
        app = App.get_running_app()
        if hasattr(app, "notification_service"):
            try:
                # Получаем последнее непрочитанное уведомление
                unread = app.notification_service.list_unread()
                if unread:
                    latest = unread[-1]  # Последнее
                    text = latest.get("text", "")
                    # Ограничиваем длину текста
                    if len(text) > 60:
                        text = text[:57] + "..."
                    self.notification_text = text
                else:
                    self.notification_text = ""
            except Exception as e:
                print(f"[HomeScreen] Ошибка обновления уведомлений: {e}")
                self.notification_text = ""
        else:
            self.notification_text = ""

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        app = App.get_running_app()
        if not hasattr(app, 'theme_manager'):
            return
            
        tm = app.theme_manager

        # Обновляем цвета и шрифты для всех элементов
        widgets_to_update = [
            "date_label", "alarm_time_label", "alarm_toggle_btn",
            "clock_label", "weather_now_label", "weather_5h_label", 
            "weather_trend_label", "notification_text_label"
        ]
        
        for widget_id in widgets_to_update:
            if widget_id in self.ids:
                widget = self.ids[widget_id]
                
                # Шрифт
                if hasattr(widget, 'font_name'):
                    widget.font_name = tm.get_font("main")
                    
                # Цвет текста
                if hasattr(widget, 'color'):
                    if widget_id == "clock_label":
                        widget.color = tm.get_rgba("primary")
                    elif widget_id == "alarm_time_label":
                        widget.color = tm.get_rgba("primary") if self.alarm_active else tm.get_rgba("text")
                    elif widget_id in ["weather_now_label", "weather_trend_label"]:
                        widget.color = tm.get_rgba("primary")
                    else:
                        widget.color = tm.get_rgba("text")
                
                # Фон кнопок
                if hasattr(widget, 'background_normal'):
                    widget.background_normal = tm.get_image("button_bg")
                    widget.background_down = tm.get_image("button_bg_active")

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
            
        # Обновляем дату в соответствии с языком
        self.update_date()
        
        # Можно добавить больше локализации по мере необходимости