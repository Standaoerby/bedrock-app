import json
import os

class UserConfig:
    def __init__(self, config_path="config/user_config.json"):
        self.config_path = config_path
        self.data = {
            "username": "Пользователь",
            "birthday": "",
            "theme": "minecraft",
            "variant": "light",
            "alarm": {
                "enabled": False,
                "time": "07:00",
                "days": []
            },
            "notifications": {
                "volume": 1.0,
                "sound": ""
            },
            "language": "ru"
        }
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception as e:
                print(f"[UserConfig] Ошибка чтения {self.config_path}: {e}")

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[UserConfig] Ошибка сохранения {self.config_path}: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def get_alarm(self):
        return self.data.get("alarm", {})

    def set_alarm(self, alarm_data):
        self.data["alarm"] = alarm_data
        self.save()

# Экземпляр на всё приложение
user_config = UserConfig()
