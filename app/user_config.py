import os
import json
import threading
from app.logger import app_logger as logger

class UserConfig:
    """
    Управляет загрузкой и сохранением пользовательских настроек из config/user_config.json.
    Поддерживает дефолты, безопасную запись, автоматическое создание файла при необходимости.
    """
    DEFAULTS = {
        "username": "User",
        "birthday": None,
        "theme": "minecraft",
        "variant": "light",
        "language": "en",
        "location": {"latitude": None, "longitude": None},
        "auto_theme_enabled": False,
        "light_sensor_threshold": 3
    }

    def __init__(self, config_path="config/user_config.json"):
        self.config_path = config_path
        self._lock = threading.RLock()
        self._data = {}
        self.load()

    def load(self):
        """Загрузить конфиг. Если нет — создать с дефолтами."""
        with self._lock:
            try:
                if not os.path.isfile(self.config_path):
                    logger.warning(f"User config not found, creating default: {self.config_path}")
                    self._data = self.DEFAULTS.copy()
                    self.save()
                else:
                    with open(self.config_path, encoding="utf-8") as f:
                        self._data = json.load(f)
                # Гарантируем наличие всех дефолтных ключей
                for k, v in self.DEFAULTS.items():
                    self._data.setdefault(k, v)
            except Exception as ex:
                logger.error(f"Failed to load user config: {ex}")
                self._data = self.DEFAULTS.copy()

    def save(self):
        """Сохранить конфиг (атомарно)."""
        with self._lock:
            try:
                # Пишем через временный файл для надёжности
                tmp_path = self.config_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self.config_path)
                logger.info("User config saved.")
            except Exception as ex:
                logger.error(f"Failed to save user config: {ex}")

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, self.DEFAULTS.get(key, default))

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
            self.save()

    def update(self, new_data):
        with self._lock:
            self._data.update(new_data)
            self.save()

    def all(self):
        with self._lock:
            return self._data.copy()

# Глобальный singleton
user_config = UserConfig()
