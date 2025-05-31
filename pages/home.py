from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty
from kivy.clock import Clock
from app.event_bus import event_bus
from datetime import datetime

class HomeScreen(Screen):
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")
    notification_text = StringProperty("")
    current_date = StringProperty("")
    clock_time = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
        self._clock_event = None

    def on_pre_enter(self, *args):
        self.refresh_theme()
        self.refresh_text()
        self.update_all()
        if not self._clock_event:
            self._clock_event = Clock.schedule_interval(self.update_clock, 1)
        # Запуск других обновлений
        Clock.schedule_interval(lambda dt: self.update_alarm(), 60)   # Обновлять раз в минуту (раньше было 5 мин)
        Clock.schedule_interval(lambda dt: self.update_weather(), 900)
        Clock.schedule_interval(lambda dt: self.update_notification(), 30)
        Clock.schedule_interval(lambda dt: self.update_date(), 60)

    def update_all(self):
        self.update_date()
        self.update_alarm()
        self.update_weather()
        self.update_notification()
        self.update_clock()

    def update_clock(self, *args):
        now = datetime.now().strftime("%H:%M")
        self.clock_time = now

    def update_date(self, *args):
        now = datetime.now()
        # Здесь можно добавить локализацию даты!
        self.current_date = now.strftime("%d.%m.%Y, %A")  # для локализации дней и месяцев см. localizer

    def update_alarm(self, *args):
        app = App.get_running_app()
        alarm = app.alarm_service.get_alarm() if hasattr(app, "alarm_service") else None
        if alarm:
            self.current_alarm_time = alarm.get("time", "--:--")
            self.alarm_active = alarm.get("enabled", False)
        else:
            self.current_alarm_time = "--:--"
            self.alarm_active = False

    def toggle_alarm(self):
        app = App.get_running_app()
        alarm = app.alarm_service.get_alarm() if hasattr(app, "alarm_service") else None
        if alarm:
            alarm["enabled"] = not alarm.get("enabled", False)
            app.alarm_service.set_alarm(alarm)
            self.update_alarm()
            if alarm["enabled"]:
                app.audio_service.play(app.theme_manager.get_sound("success"))

    def update_weather(self, *args):
        app = App.get_running_app()
        weather = app.weather_service.get_weather() if hasattr(app, "weather_service") else {}
        now = weather.get("current", {})
        forecast_5h = weather.get("forecast_5h", {})
        if now:
            temp = now.get("temperature", "--")
            condition = now.get("condition", "")
            self.weather_now_str = f'{temp}°C {condition}'
        else:
            self.weather_now_str = ""
        if forecast_5h:
            temp_5h = forecast_5h.get("temperature", "--")
            self.weather_5h_str = f'{temp_5h}°C in 5h'
            try:
                temp_now = float(now.get("temperature", 0))
                temp_5h_val = float(forecast_5h.get("temperature", 0))
                if temp_5h_val > temp_now:
                    self.weather_trend_arrow = "↑"
                elif temp_5h_val < temp_now:
                    self.weather_trend_arrow = "↓"
                else:
                    self.weather_trend_arrow = "~"
            except Exception:
                self.weather_trend_arrow = ""
        else:
            self.weather_5h_str = ""
            self.weather_trend_arrow = ""

    def update_notification(self, *args):
        app = App.get_running_app()
        notification = app.notification_service.get_last_notification() if hasattr(app, "notification_service") else None
        if notification:
            self.notification_text = notification.get("text", "")
        else:
            self.notification_text = ""

    def refresh_theme(self, *args):
        app = App.get_running_app()
        tm = app.theme_manager

        # Цвета, шрифты для основных виджетов
        if "date_label" in self.ids:
            self.ids.date_label.color = tm.get_rgba("text")
            self.ids.date_label.font_name = tm.get_font("main")

        if "alarm_time_label" in self.ids:
            self.ids.alarm_time_label.color = tm.get_rgba("primary") if self.alarm_active else tm.get_rgba("text")
            self.ids.alarm_time_label.font_name = tm.get_font("main")

        if "alarm_toggle_btn" in self.ids:
            self.ids.alarm_toggle_btn.background_normal = tm.get_image("menu_button_bg")
            self.ids.alarm_toggle_btn.background_down = tm.get_image("menu_button_bg_active")
            self.ids.alarm_toggle_btn.color = tm.get_rgba("menu_button_text")
            self.ids.alarm_toggle_btn.font_name = tm.get_font("main")

        if "clock_label" in self.ids:
            self.ids.clock_label.color = tm.get_rgba("primary")
            self.ids.clock_label.font_name = tm.get_font("main")

        if "weather_now_label" in self.ids:
            self.ids.weather_now_label.color = tm.get_rgba("text")
            self.ids.weather_now_label.font_name = tm.get_font("main")

        if "notification_text_label" in self.ids:
            self.ids.notification_text_label.color = tm.get_rgba("text")
            self.ids.notification_text_label.font_name = tm.get_font("main")

    def refresh_text(self, *args):
        app = App.get_running_app()

        # Локализация даты — пример с днями недели/месяцами (можно ещё лучше, если будут ключи локали)
        import locale
        try:
            locale.setlocale(locale.LC_TIME, app.localizer.lang)
        except:
            pass

        if "date_label" in self.ids:
            # Можно более продвинутую локализацию: self.current_date = app.localizer.format_date(datetime.now())
            self.ids.date_label.text = datetime.now().strftime("%d %B, %A")

        if "alarm_toggle_btn" in self.ids:
            self.ids.alarm_toggle_btn.text = app.localizer.t("alarm_enabled") if self.alarm_active else app.localizer.t("cancel")

        if "weather_now_label" in self.ids:
            self.ids.weather_now_label.text = self.weather_now_str

        if "notification_text_label" in self.ids:
            self.ids.notification_text_label.text = self.notification_text

        if "clock_label" in self.ids:
            self.ids.clock_label.text = self.clock_time

