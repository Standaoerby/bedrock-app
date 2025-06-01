from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty, NumericProperty, BooleanProperty, ListProperty

from app.theme_manager import theme_manager
from app.localizer import localizer
from app.event_bus import event_bus
from app.app_state import app_state
from app.logger import app_logger as logger

class HomeScreen(BoxLayout):
    # Стандартные свойства для биндинга в KV
    clock_str = StringProperty("")
    date_str = StringProperty("")
    weather_temp = StringProperty("--")
    weather_condition = StringProperty("")
    alarm_status = StringProperty("")
    notifications_str = StringProperty("")
    background_image = StringProperty("")
    overlay_image = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 1. Первичная инициализация состояния
        self.update_clock()
        self.update_weather()
        self.update_alarm()
        self.update_notifications()
        self.apply_theme()
        # 2. Запуск таймера обновления часов
        Clock.schedule_interval(self.update_clock, 1)
        # 3. Подписки на события
        event_bus.subscribe("theme_changed", self.on_theme_changed)
        event_bus.subscribe("language_changed", self.on_language_changed)
        event_bus.subscribe("weather_updated", self.on_weather_update)
        event_bus.subscribe("alarm_updated", self.on_alarm_update)
        event_bus.subscribe("notifications_updated", self.on_notifications_update)

    # --- Время, дата ---
    def update_clock(self, *args):
        from datetime import datetime
        now = datetime.now()
        self.clock_str = now.strftime("%H:%M")
        # День недели и месяц локализуем
        day_key = f"weekday_{now.weekday()}"
        month_key = f"month_{now.month}"
        day_name = localizer.tr(day_key, now.strftime("%A"))
        month_name = localizer.tr(month_key, now.strftime("%B"))
        self.date_str = f"{now.day} {month_name}, {day_name}"

    def on_language_changed(self, *args):
        self.update_clock()
        self.update_alarm()
        self.update_notifications()
        self.update_weather()

    # --- Погода ---
    def update_weather(self, *args):
        weather = app_state.snapshot().get("sensor_data", {})
        self.weather_temp = str(weather.get("temperature", "--"))
        self.weather_condition = weather.get("condition", "")

    def on_weather_update(self, *args):
        self.update_weather()

    # --- Будильник ---
    def update_alarm(self, *args):
        alarm = app_state.snapshot().get("alarm", {})
        if alarm.get("enabled"):
            t = alarm.get("time", "")
            days = alarm.get("days", [])
            days_str = ", ".join([localizer.tr(f"weekday_{d}", str(d)) for d in days])
            self.alarm_status = f"{localizer.tr('alarm_on')} {t} {days_str}"
        else:
            self.alarm_status = localizer.tr("alarm_off")

    def on_alarm_update(self, *args):
        self.update_alarm()

    # --- Уведомления ---
    def update_notifications(self, *args):
        notifications = app_state.snapshot().get("notifications", [])
        # Только важные уведомления, если есть фильтрация (можно добавить)
        self.notifications_str = "   |   ".join([n.get("text", "") for n in notifications])

    def on_notifications_update(self, *args):
        self.update_notifications()

    # --- Тема ---
    def apply_theme(self, *args):
        self.background_image = theme_manager.get_image("background")
        self.overlay_image = theme_manager.get_overlay("home")

    def on_theme_changed(self, *args):
        self.apply_theme()

    def on_kv_post(self, *args):
        self.apply_theme()
