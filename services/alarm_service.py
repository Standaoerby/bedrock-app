# services/alarm_service.py
"""
ФИНАЛЬНЫЙ AlarmService - простое управление настройками будильника
"""
import os
import json
import threading
from app.logger import app_logger as logger
from app.event_bus import event_bus


class AlarmService:
    def __init__(self):
        self.config_file = os.path.join("config", "alarm.json")
        self._lock = threading.RLock()
        
        # Настройки по умолчанию
        self.default_alarm = {
            "enabled": False,
            "time": "07:30",
            "repeat": [],
            "ringtone": "Bathtime In Clerkenwell.mp3",
            "fadein": False
        }
        
        self.alarm_data = {"alarm": self.default_alarm.copy()}
        
        # Создаем папку config если нет
        os.makedirs("config", exist_ok=True)
        
        # Загружаем настройки
        self._load_config()
        
        logger.info("AlarmService initialized")
    
    def _load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict) and "alarm" in data:
                    # Проверяем и дополняем недостающие поля
                    alarm = data["alarm"]
                    for key, default_value in self.default_alarm.items():
                        if key not in alarm:
                            alarm[key] = default_value
                    
                    with self._lock:
                        self.alarm_data = data
                    
                    logger.info("✅ Alarm config loaded")
                else:
                    logger.warning("Invalid config format, using defaults")
                    self._save_config()
            else:
                logger.info("No config file found, creating default")
                self._save_config()
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # При ошибке используем дефолтные настройки
            with self._lock:
                self.alarm_data = {"alarm": self.default_alarm.copy()}
            self._save_config()
    
    def _save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            with self._lock:
                data = self.alarm_data.copy()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Config saved")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get_alarm(self):
        """Получение текущих настроек будильника"""
        with self._lock:
            alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
            return alarm.copy()
    
    def update_alarm(self, **kwargs):
        """Обновление настроек будильника"""
        try:
            with self._lock:
                current_alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
                
                # Обновляем только переданные параметры
                for key, value in kwargs.items():
                    if key in self.default_alarm:
                        current_alarm[key] = value
                    else:
                        logger.warning(f"Unknown alarm parameter: {key}")
                
                self.alarm_data["alarm"] = current_alarm
            
            # Сохраняем и отправляем событие
            self._save_config()
            self._notify_alarm_change()
            
            logger.info(f"Alarm updated: {kwargs}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating alarm: {e}")
            return False
    
    def set_alarm(self, alarm_dict):
        """Полная замена настроек будильника"""
        try:
            # Проверяем и дополняем настройки
            new_alarm = self.default_alarm.copy()
            new_alarm.update(alarm_dict)
            
            with self._lock:
                self.alarm_data["alarm"] = new_alarm
            
            self._save_config()
            self._notify_alarm_change()
            
            logger.info(f"Alarm set: {new_alarm}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting alarm: {e}")
            return False
    
    def enable_alarm(self, enabled=True):
        """Включение/выключение будильника"""
        return self.update_alarm(enabled=enabled)
    
    def set_alarm_time(self, time_str):
        """Установка времени будильника (формат HH:MM)"""
        return self.update_alarm(time=time_str)
    
    def set_repeat_days(self, days):
        """Установка дней повтора (список: ["Mon", "Tue", ...])"""
        return self.update_alarm(repeat=days)
    
    def set_ringtone(self, ringtone):
        """Установка мелодии будильника"""
        return self.update_alarm(ringtone=ringtone)
    
    def _notify_alarm_change(self):
        """Отправка события об изменении настроек"""
        try:
            alarm = self.get_alarm()
            
            # Новое событие
            event_data = {
                "enabled": alarm.get("enabled", False),
                "time": alarm.get("time", "07:30"),
                "repeat": alarm.get("repeat", []),
                "ringtone": alarm.get("ringtone", ""),
                "fadein": alarm.get("fadein", False)
            }
            
            # Отправляем событие
            event_bus.publish("alarm_changed", event_data)
            
            # Для совместимости отправляем старое событие
            event_bus.publish("alarm_settings_changed", alarm)
            
            logger.debug("Alarm change events sent")
            
        except Exception as e:
            logger.error(f"Error notifying alarm change: {e}")
    
    def get_config_path(self):
        """Получение пути к файлу конфигурации"""
        return self.config_file
    
    def reset_to_defaults(self):
        """Сброс к настройкам по умолчанию"""
        try:
            with self._lock:
                self.alarm_data = {"alarm": self.default_alarm.copy()}
            
            self._save_config()
            self._notify_alarm_change()
            
            logger.info("Alarm reset to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting alarm: {e}")
            return False