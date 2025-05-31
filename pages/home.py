from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty
from kivy.clock import Clock
from datetime import datetime

class HomeScreen(Screen):
    current_date = StringProperty("")
    current_alarm_time = StringProperty("")
    alarm_active = BooleanProperty(False)
    clock_time = StringProperty("")
    weather_now_str = StringProperty("")
    weather_5h_str = StringProperty("")
    weather_trend_arrow = StringProperty("")
    weather_precip_str = StringProperty("")
    notification_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_interval(self.update_weather, 300)  # каждые 5 минут
        self.update_time()
        self.update_weather()

    def update_time(self, *args):
        now = datetime.now()
        app = self.get_app()
        # Локализация даты (если надо)
        self.current_date = now.strftime("%d %B, %A")
        self.clock_time = now.strftime("%H:%M:%S")

    def update_weather(self, *args):
        app = self.get_app()
        # Самый универсальный вызов — get_weather:
        if hasattr(app, "weather_service"):
            weather = app.weather_service.get_weather()
        else:
            weather = {}

        now = weather.get("current", {})
        forecast_5h = weather.get("forecast_5h", {})
        if now:
            temp = now.get("temperature", "--")
            condition = now.get("condition", "")
            precip = now.get("precipitation_probability", "")
            icon = self.get_weather_icon(condition)
            self.weather_now_str = f'{temp}°C {icon} {condition}'
            self.weather_precip_str = f'💧 {precip}%' if precip != "" else ""
        else:
            self.weather_now_str = ""
            self.weather_precip_str = ""
        if forecast_5h:
            temp_5h = forecast_5h.get("temperature", "--")
            in_5h_text = app.localizer.t("in_5h") if hasattr(app, "localizer") else "in 5h"
            self.weather_5h_str = f'{temp_5h}°C {in_5h_text}'
            try:
                temp_now = float(now.get("temperature", 0))
                temp_5h_val = float(forecast_5h.get("temperature", 0))
                if temp_5h_val > temp_now:
                    self.weather_trend_arrow = "↑"
                elif temp_5h_val < temp_now:
                    self.weather_trend_arrow = "↓"
                else:
                    self.weather_trend_arrow = "→"
            except Exception:
                self.weather_trend_arrow = ""
        else:
            self.weather_5h_str = ""
            self.weather_trend_arrow = ""

    def get_weather_icon(self, condition):
        mapping = {
            "Clear": "☀️",
            "Mostly Clear": "🌤️",
            "Partly Cloudy": "⛅",
            "Cloudy": "☁️",
            "Fog": "🌫️",
            "Rain": "🌧️",
            "Snow": "❄️",
            "Thunderstorm": "⛈️",
        }
        for key, val in mapping.items():
            if key.lower() in condition.lower():
                return val
        return "🌡️"

    def get_app(self):
        # Импорт тут, чтобы не было циклических импортов
        from kivy.app import App
        return App.get_running_app()
