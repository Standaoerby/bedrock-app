import os
import json
import threading
import time
from app.logger import app_logger as logger

class UserConfig:
    """
    Управляет загрузкой и сохранением пользовательских настроек из config/user_config.json.
    Поддерживает дефолты, безопасную запись, автоматическое создание файла при необходимости.
    ИСПРАВЛЕНО: Добавлена защита от частого сохранения
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
        
        # НОВОЕ: Защита от частого сохранения
        self._save_delay = 0.5  # Задержка между сохранениями
        self._last_save_time = 0
        self._pending_save_event = None
        
        self.load()

    def load(self):
        """Загрузить конфиг. Если нет — создать с дефолтами."""
        with self._lock:
            try:
                if not os.path.isfile(self.config_path):
                    logger.warning(f"User config not found, creating default: {self.config_path}")
                    self._data = self.DEFAULTS.copy()
                    self._actual_save()  # Первое сохранение сразу
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
        """ИСПРАВЛЕНО: Сохранение с защитой от частых вызовов"""
        current_time = time.time()
        
        with self._lock:
            # Если недавно сохраняли, планируем отложенное сохранение
            if current_time - self._last_save_time < self._save_delay:
                if not self._pending_save_event:
                    try:
                        from kivy.clock import Clock
                        delay = self._save_delay - (current_time - self._last_save_time)
                        self._pending_save_event = Clock.schedule_once(self._delayed_save, delay)
                    except ImportError:
                        # Если Kivy недоступен, сохраняем сразу
                        self._actual_save()
                return
            
            self._actual_save()
    
    def _delayed_save(self, dt):
        """Отложенное сохранение"""
        with self._lock:
            self._pending_save_event = None
            self._actual_save()
    
    def _actual_save(self):
        """ИСПРАВЛЕНО: Реальное сохранение в файл с атомарностью"""
        try:
            # Атомарное сохранение через временный файл
            temp_path = f"{self.config_path}.tmp"
            
            # Создаем директорию если её нет
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            
            os.replace(temp_path, self.config_path)
            self._last_save_time = time.time()
            logger.info("User config saved.")
            
        except Exception as e:
            logger.error(f"Error saving user config: {e}")
            # Удаляем временный файл при ошибке
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, self.DEFAULTS.get(key, default))

    def set(self, key, value):
        with self._lock:
            old_value = self._data.get(key)
            if old_value != value:  # Сохраняем только если значение изменилось
                self._data[key] = value
                self.save()

    def update(self, new_data):
        with self._lock:
            changed = False
            for key, value in new_data.items():
                if self._data.get(key) != value:
                    self._data[key] = value
                    changed = True
            
            if changed:  # Сохраняем только если что-то изменилось
                self.save()

    def all(self):
        with self._lock:
            return self._data.copy()

# Глобальный singleton
user_config = UserConfig()