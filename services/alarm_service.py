# services/alarm_service.py
"""
ИСПРАВЛЕННЫЙ AlarmService - надежное управление настройками будильника с правильными путями
"""
import os
import json
import threading
from app.logger import app_logger as logger
from app.event_bus import event_bus


class AlarmService:
    def __init__(self):
        # ИСПРАВЛЕНО: Находим правильный путь к конфигурации
        self.config_file = self._find_config_path()
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
        config_dir = os.path.dirname(self.config_file)
        os.makedirs(config_dir, exist_ok=True)
        
        logger.info(f"AlarmService config path: {self.config_file}")
        
        # Загружаем настройки
        self._load_config()
        
        logger.info("AlarmService initialized")
    
    def _find_config_path(self):
        """НОВОЕ: Поиск правильного пути к файлу конфигурации"""
        
        # Пробуем разные возможные пути
        possible_paths = [
            # Относительно текущей директории
            "config/alarm.json",
            "./config/alarm.json",
            
            # Относительно директории скрипта
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "alarm.json"),
            
            # Абсолютные пути
            os.path.abspath("config/alarm.json"),
            os.path.abspath("./config/alarm.json"),
            
            # На случай если запускаемся из подпапки
            "../config/alarm.json",
        ]
        
        current_dir = os.getcwd()
        logger.debug(f"Current working directory: {current_dir}")
        
        # Проверяем каждый путь
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            logger.debug(f"Checking config path: {abs_path}")
            
            if os.path.exists(abs_path):
                logger.info(f"✅ Found config file: {abs_path}")
                return abs_path
            else:
                logger.debug(f"❌ Config not found: {abs_path}")
        
        # Если ничего не найдено, используем первый путь (будет создан)
        default_path = os.path.abspath("config/alarm.json")
        logger.info(f"📁 Config will be created at: {default_path}")
        return default_path
    
    def _load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            logger.debug(f"Attempting to load config from: {self.config_file}")
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                logger.debug(f"Raw config data: {data}")
                    
                if isinstance(data, dict) and "alarm" in data:
                    # Проверяем и дополняем недостающие поля
                    alarm = data["alarm"]
                    logger.debug(f"Loaded alarm config: {alarm}")
                    
                    for key, default_value in self.default_alarm.items():
                        if key not in alarm:
                            alarm[key] = default_value
                            logger.debug(f"Added missing key '{key}' with default: {default_value}")
                    
                    with self._lock:
                        self.alarm_data = data
                    
                    logger.info("✅ Alarm config loaded successfully")
                    logger.debug(f"Final alarm data: {self.alarm_data}")
                else:
                    logger.warning("Invalid config format, using defaults")
                    self._save_config()
            else:
                logger.info(f"No config file found at {self.config_file}, creating default")
                self._save_config()
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            import traceback
            logger.error(f"Config load traceback: {traceback.format_exc()}")
            
            # При ошибке используем дефолтные настройки
            with self._lock:
                self.alarm_data = {"alarm": self.default_alarm.copy()}
            self._save_config()
    
    def _save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            with self._lock:
                data = self.alarm_data.copy()
            
            logger.debug(f"Saving config to: {self.config_file}")
            logger.debug(f"Config data: {data}")
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Config saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            import traceback
            logger.error(f"Config save traceback: {traceback.format_exc()}")
    
    def get_alarm(self):
        """Получение текущих настроек будильника"""
        with self._lock:
            alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
            logger.debug(f"get_alarm() returning: {alarm}")
            return alarm.copy()
    
    def update_alarm(self, **kwargs):
        """Обновление настроек будильника"""
        try:
            logger.debug(f"update_alarm called with: {kwargs}")
            
            with self._lock:
                current_alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
                
                # Обновляем только переданные параметры
                for key, value in kwargs.items():
                    if key in self.default_alarm:
                        old_value = current_alarm.get(key)
                        current_alarm[key] = value
                        logger.debug(f"Updated {key}: {old_value} -> {value}")
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
            import traceback
            logger.error(f"Update alarm traceback: {traceback.format_exc()}")
            return False
    
    def set_alarm(self, alarm_dict):
        """Полная замена настроек будильника"""
        try:
            logger.debug(f"set_alarm called with: {alarm_dict}")
            
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
            import traceback
            logger.error(f"Set alarm traceback: {traceback.format_exc()}")
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
            
            logger.debug(f"Publishing alarm change events: {event_data}")
            
            # Отправляем событие
            event_bus.publish("alarm_changed", event_data)
            
            # Для совместимости отправляем старое событие
            event_bus.publish("alarm_settings_changed", alarm)
            
            logger.debug("Alarm change events sent")
            
        except Exception as e:
            logger.error(f"Error notifying alarm change: {e}")
            import traceback
            logger.error(f"Notify alarm change traceback: {traceback.format_exc()}")
    
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
    
    def diagnose(self):
        """НОВОЕ: Диагностика состояния AlarmService"""
        logger.info("🔧 === ALARM SERVICE DIAGNOSTIC ===")
        
        logger.info(f"[config_file      ] {self.config_file}")
        logger.info(f"[config_exists    ] {os.path.exists(self.config_file)}")
        logger.info(f"[working_directory] {os.getcwd()}")
        
        if os.path.exists(self.config_file):
            try:
                size = os.path.getsize(self.config_file)
                logger.info(f"[config_size      ] {size} bytes")
                
                with open(self.config_file, 'r') as f:
                    content = f.read()
                logger.info(f"[config_content   ] {len(content)} chars")
                
            except Exception as e:
                logger.info(f"[config_error     ] {e}")
        
        # Показываем текущие данные
        with self._lock:
            alarm = self.alarm_data.get("alarm", {})
        
        logger.info(f"[current_time     ] {alarm.get('time', 'MISSING')}")
        logger.info(f"[current_enabled  ] {alarm.get('enabled', 'MISSING')}")
        logger.info(f"[current_repeat   ] {alarm.get('repeat', 'MISSING')}")
        logger.info(f"[current_ringtone ] {alarm.get('ringtone', 'MISSING')}")
        
        logger.info("🔧 === END DIAGNOSTIC ===")
        
        return {
            "config_file": self.config_file,
            "config_exists": os.path.exists(self.config_file),
            "current_alarm": alarm
        }