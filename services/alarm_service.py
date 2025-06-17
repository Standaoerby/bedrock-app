# services/alarm_service.py
"""
ИСПРАВЛЕННЫЙ AlarmService - унифицированные пути конфигурации и улучшенная надежность
"""
import os
import json
import threading
from app.logger import app_logger as logger
from app.event_bus import event_bus


class AlarmService:
    def __init__(self):
        # ИСПРАВЛЕНО: Унифицированный путь конфигурации
        self.config_file = self._get_unified_config_path()
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
    
    def _get_unified_config_path(self):
        """ИСПРАВЛЕНО: Унифицированный путь конфигурации для всех компонентов"""
        
        # Определяем корневую директорию проекта
        # Если мы в services/, то корень на уровень выше
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir.endswith('services'):
            project_root = os.path.dirname(current_dir)
        else:
            project_root = current_dir
        
        # Стандартный путь относительно корня проекта
        config_path = os.path.join(project_root, "config", "alarm.json")
        
        logger.debug(f"Unified config path: {config_path}")
        logger.debug(f"Project root: {project_root}")
        logger.debug(f"Current working dir: {os.getcwd()}")
        
        return config_path
    
    def _load_config(self):
        """ИСПРАВЛЕНО: Загрузка конфигурации с улучшенной обработкой ошибок"""
        try:
            # Проверяем существует ли файл
            if not os.path.exists(self.config_file):
                logger.info(f"Config file not found, creating default: {self.config_file}")
                self._save_config()  # Создаем файл с настройками по умолчанию
                return
            
            logger.debug(f"Loading config from: {self.config_file}")
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру
            if not isinstance(data, dict) or 'alarm' not in data:
                logger.warning(f"Invalid config structure, using defaults")
                self.alarm_data = {"alarm": self.default_alarm.copy()}
                self._save_config()  # Пересохраняем правильную структуру
                return
            
            # Дополняем отсутствующие поля значениями по умолчанию
            loaded_alarm = data['alarm']
            complete_alarm = self.default_alarm.copy()
            complete_alarm.update(loaded_alarm)
            
            with self._lock:
                self.alarm_data = {"alarm": complete_alarm}
            
            logger.info(f"Config loaded successfully: enabled={complete_alarm.get('enabled')}, time={complete_alarm.get('time')}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            logger.info("Creating new config with defaults")
            self.alarm_data = {"alarm": self.default_alarm.copy()}
            self._save_config()
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            import traceback
            logger.error(f"Config load traceback: {traceback.format_exc()}")
            
            # В случае любой ошибки используем настройки по умолчанию
            self.alarm_data = {"alarm": self.default_alarm.copy()}
    
    def _save_config(self):
        """ИСПРАВЛЕНО: Сохранение конфигурации с проверкой целостности"""
        try:
            with self._lock:
                data = self.alarm_data.copy()
            
            # Проверяем целостность данных перед сохранением
            if not isinstance(data, dict) or 'alarm' not in data:
                logger.error("Invalid data structure, cannot save")
                return
            
            alarm = data['alarm']
            if not isinstance(alarm, dict):
                logger.error("Invalid alarm structure, cannot save")
                return
            
            # Создаем директорию если нужно
            config_dir = os.path.dirname(self.config_file)
            os.makedirs(config_dir, exist_ok=True)
            
            logger.debug(f"Saving config to: {self.config_file}")
            logger.debug(f"Config data: {data}")
            
            # Создаем временный файл для атомарной записи
            temp_file = self.config_file + '.tmp'
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Атомарно перемещаем временный файл
            if os.path.exists(temp_file):
                if os.path.exists(self.config_file):
                    os.remove(self.config_file)
                os.rename(temp_file, self.config_file)
            
            logger.debug("Config saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            import traceback
            logger.error(f"Config save traceback: {traceback.format_exc()}")
            
            # Удаляем временный файл в случае ошибки
            temp_file = self.config_file + '.tmp'
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def get_alarm(self):
        """Получение текущих настроек будильника"""
        with self._lock:
            alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
            logger.debug(f"get_alarm() returning: {alarm}")
            return alarm.copy()
    
    def update_alarm(self, **kwargs):
        """ИСПРАВЛЕНО: Обновление настроек будильника с валидацией"""
        try:
            logger.debug(f"update_alarm called with: {kwargs}")
            
            with self._lock:
                current_alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
                
                # Обновляем только переданные и валидные параметры
                for key, value in kwargs.items():
                    if key in self.default_alarm:
                        # Дополнительная валидация для некоторых полей
                        if key == "time" and value:
                            if not self._validate_time_format(value):
                                logger.warning(f"Invalid time format: {value}, skipping")
                                continue
                        elif key == "enabled":
                            value = bool(value)  # Приводим к булеву типу
                        elif key == "repeat" and not isinstance(value, list):
                            logger.warning(f"Invalid repeat format: {value}, skipping")
                            continue
                        
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
        """ИСПРАВЛЕНО: Полная замена настроек будильника с валидацией"""
        try:
            logger.debug(f"set_alarm called with: {alarm_dict}")
            
            if not isinstance(alarm_dict, dict):
                logger.error(f"Invalid alarm_dict type: {type(alarm_dict)}")
                return False
            
            # Проверяем и дополняем настройки
            new_alarm = self.default_alarm.copy()
            
            for key, value in alarm_dict.items():
                if key in self.default_alarm:
                    # Валидация значений
                    if key == "time" and value:
                        if not self._validate_time_format(value):
                            logger.warning(f"Invalid time format: {value}, using default")
                            continue
                    elif key == "enabled":
                        value = bool(value)
                    elif key == "repeat" and not isinstance(value, list):
                        logger.warning(f"Invalid repeat format: {value}, using default")
                        continue
                    
                    new_alarm[key] = value
                else:
                    logger.warning(f"Unknown alarm parameter in set_alarm: {key}")
            
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
    
    def _validate_time_format(self, time_str):
        """НОВОЕ: Валидация формата времени"""
        try:
            if not isinstance(time_str, str):
                return False
            
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            
            hours, minutes = parts
            hour_int = int(hours)
            minute_int = int(minutes)
            
            return 0 <= hour_int <= 23 and 0 <= minute_int <= 59
            
        except (ValueError, TypeError):
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
        """ИСПРАВЛЕНО: Отправка события об изменении настроек"""
        try:
            alarm = self.get_alarm()
            
            # Формируем данные события
            event_data = {
                "enabled": alarm.get("enabled", False),
                "time": alarm.get("time", "07:30"),
                "repeat": alarm.get("repeat", []),
                "ringtone": alarm.get("ringtone", ""),
                "fadein": alarm.get("fadein", False),
                "source": "alarm_service"
            }
            
            logger.debug(f"Publishing alarm change events: {event_data}")
            
            # Отправляем событие
            event_bus.publish("alarm_changed", event_data)
            
            # Для совместимости отправляем старое событие
            event_bus.publish("alarm_settings_changed", alarm)
            
            logger.debug("Alarm change events sent successfully")
            
        except Exception as e:
            logger.error(f"Error notifying alarm change: {e}")
            import traceback
            logger.error(f"Notify alarm change traceback: {traceback.format_exc()}")
    
    # НОВОЕ: Методы для диагностики
    def diagnose(self):
        """Диагностика состояния AlarmService"""
        logger.info("🔧 === ALARM SERVICE DIAGNOSTIC ===")
        
        logger.info(f"[config_file       ] {self.config_file}")
        logger.info(f"[config_exists     ] {os.path.exists(self.config_file)}")
        
        if os.path.exists(self.config_file):
            try:
                stat = os.stat(self.config_file)
                logger.info(f"[config_size       ] {stat.st_size} bytes")
                logger.info(f"[config_modified   ] {stat.st_mtime}")
            except Exception as e:
                logger.info(f"[config_stat       ] Error: {e}")
        
        try:
            alarm = self.get_alarm()
            logger.info(f"[alarm_enabled     ] {alarm.get('enabled')}")
            logger.info(f"[alarm_time        ] {alarm.get('time')}")
            logger.info(f"[alarm_repeat      ] {alarm.get('repeat')}")
            logger.info(f"[alarm_ringtone    ] {alarm.get('ringtone')}")
            logger.info(f"[alarm_fadein      ] {alarm.get('fadein')}")
        except Exception as e:
            logger.info(f"[alarm_data        ] Error: {e}")
        
        logger.info("🔧 === END ALARM SERVICE DIAGNOSTIC ===")
    
    def get_config_path(self):
        """Получение пути к файлу конфигурации (для внешнего использования)"""
        return self.config_file
    
    def force_reload(self):
        """НОВОЕ: Принудительная перезагрузка конфигурации"""
        logger.info("Force reloading alarm configuration")
        self._load_config()
        self._notify_alarm_change()
        logger.info("Configuration reloaded successfully")