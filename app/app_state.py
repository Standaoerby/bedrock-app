import threading
from app.event_bus import event_bus

class AppState:
    """
    Глобальное состояние приложения Bedrock.
    Все ключевые параметры хранятся централизованно, доступ к ним потокобезопасен.
    При изменении важных параметров публикуется событие через EventBus.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self.theme = "minecraft"
        self.variant = "light"
        self.user = {
            "name": None,
            "dob": None,
            "language": "en"
        }
        self.volume = 70
        self.alarm = {}
        self.schedule = {}
        self.sensor_data = {}
        self.notifications = []
        self.media_files = []

    # Смена темы + публикация события
    def set_theme(self, theme, variant):
        with self._lock:
            if theme != self.theme or variant != self.variant:
                self.theme = theme
                self.variant = variant
                event_bus.publish("theme_changed", {
                    "theme": theme,
                    "variant": variant
                })

    # Смена языка + публикация события
    def set_language(self, lang):
        with self._lock:
            if self.user.get("language") != lang:
                self.user["language"] = lang
                event_bus.publish("language_changed", {"lang": lang})

    # Безопасная смена громкости + публикация события
    def set_volume(self, volume):
        with self._lock:
            volume = max(0, min(100, int(volume)))
            if self.volume != volume:
                self.volume = volume
                event_bus.publish("volume_changed", {"volume": volume})

    # Обновление будильника
    def set_alarm(self, alarm_data):
        with self._lock:
            self.alarm = alarm_data.copy()
            event_bus.publish("alarm_updated", {"alarm": self.alarm})

    # Обновление расписания
    def set_schedule(self, schedule_data):
        with self._lock:
            self.schedule = schedule_data.copy()
            event_bus.publish("schedule_updated", {"schedule": self.schedule})

    # Обновление данных сенсоров
    def set_sensor_data(self, sensor_data):
        with self._lock:
            self.sensor_data = sensor_data.copy()
            event_bus.publish("sensor_data_updated", {"sensor_data": self.sensor_data})

    # Обновление уведомлений
    def set_notifications(self, notifications):
        with self._lock:
            self.notifications = list(notifications)
            event_bus.publish("notifications_updated", {"notifications": self.notifications})

    # Обновление медиа-файлов
    def set_media_files(self, media_files):
        with self._lock:
            self.media_files = list(media_files)
            event_bus.publish("media_files_updated", {"media_files": self.media_files})

    # Получить копию текущего состояния (для передачи в другие компоненты)
    def snapshot(self):
        with self._lock:
            return {
                "theme": self.theme,
                "variant": self.variant,
                "user": self.user.copy(),
                "volume": self.volume,
                "alarm": self.alarm.copy(),
                "schedule": self.schedule.copy(),
                "sensor_data": self.sensor_data.copy(),
                "notifications": list(self.notifications),
                "media_files": list(self.media_files)
            }

# Глобальный singleton для использования везде по проекту
app_state = AppState()
