"""
ОПТИМИЗИРОВАННЫЙ AlarmService - единственный источник истины для управления будильником
ПОЛНАЯ ЗАМЕНА файла services/alarm_service.py
"""
import os
import json
import threading
import time
from app.logger import app_logger as logger
from app.event_bus import event_bus

# Пытаемся импортировать watchdog для file watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
    logger.info("✅ Watchdog available for file monitoring")
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("⚠️ Watchdog not available - install with 'pip install watchdog' for file monitoring")

class AlarmConfigHandler(FileSystemEventHandler):
    """Обработчик изменений файла конфигурации будильника"""
    def __init__(self, alarm_service):
        self.alarm_service = alarm_service
        self.last_modified = 0
        
    def on_modified(self, event):
        """Вызывается при изменении файла"""
        if event.is_directory:
            return
            
        if event.src_path.endswith('alarm.json'):
            current_time = time.time()
            # Debouncing - игнорируем частые изменения (меньше 1 секунды)
            if current_time - self.last_modified > 1.0:
                self.last_modified = current_time
                logger.debug("alarm.json modified externally, reloading...")
                self.alarm_service._reload_from_file()

class AlarmService:
    """
    ОПТИМИЗИРОВАННЫЙ сервис управления будильником
    
    Особенности:
    - Единственный источник истины для данных будильника
    - Автоматические события при изменениях
    - File watching для внешних изменений
    - Thread-safe операции
    - Умное кэширование
    - Полная обратная совместимость
    """
    
    def __init__(self):
        self.config_file = os.path.join("config", "alarm.json")
        self._is_stopped = False
        self._lock = threading.RLock()
        self._change_id = 0  # Для предотвращения циклических событий
        
        # Настройки по умолчанию
        self.default_alarm = {
            "time": "07:30",
            "enabled": True,
            "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "ringtone": "Bathtime In Clerkenwell.mp3",
            "fadein": False,
        }
        
        # Убеждаемся что директория существует
        os.makedirs("config", exist_ok=True)
        
        # Загружаем данные
        self._load_config()
        
        # Настраиваем file watching если доступен
        self._setup_file_watcher()
        
        logger.info("✅ Optimized AlarmService initialized")

    def _setup_file_watcher(self):
        """Настройка отслеживания изменений файла конфигурации"""
        if not WATCHDOG_AVAILABLE:
            logger.debug("File watching disabled - watchdog not available")
            self.file_observer = None
            return
            
        try:
            self.file_observer = Observer()
            self.file_handler = AlarmConfigHandler(self)
            self.file_observer.schedule(
                self.file_handler, 
                os.path.dirname(self.config_file), 
                recursive=False
            )
            self.file_observer.start()
            logger.debug("✅ File watcher for alarm.json started")
        except Exception as e:
            logger.warning(f"Cannot setup file watcher: {e}")
            self.file_observer = None

    def _load_config(self):
        """Загрузка конфигурации из файла"""
        with self._lock:
            try:
                if os.path.exists(self.config_file):
                    with open(self.config_file, "r") as f:
                        data = json.load(f)
                        self.alarm_data = data
                        
                        # Проверяем структуру данных
                        if "alarm" not in self.alarm_data:
                            logger.warning("No 'alarm' key in config, creating default")
                            self.alarm_data = {"alarm": self.default_alarm.copy()}
                            self._save_config_internal()
                else:
                    logger.info("Config file not found, creating default")
                    self.alarm_data = {"alarm": self.default_alarm.copy()}
                    self._save_config_internal()
                    
                logger.debug(f"Alarm config loaded: {self.alarm_data}")
                
            except Exception as e:
                logger.error(f"Error loading alarm config: {e}")
                self.alarm_data = {"alarm": self.default_alarm.copy()}

    def _save_config_internal(self):
        """Внутреннее сохранение конфигурации (без событий)"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.alarm_data, f, indent=2)
            logger.debug("Alarm config saved to file")
            return True
        except Exception as e:
            logger.error(f"Error saving alarm config: {e}")
            return False

    def _reload_from_file(self):
        """Перезагрузка конфигурации из файла при внешних изменениях"""
        with self._lock:
            old_alarm = self.alarm_data.get("alarm", {}).copy()
            self._load_config()
            new_alarm = self.alarm_data.get("alarm", {})
            
            # Отправляем событие только если данные действительно изменились
            if old_alarm != new_alarm:
                self._change_id += 1
                logger.info("Config reloaded from file, notifying subscribers")
                self._notify_change(new_alarm, source="file_watcher")

    def _notify_change(self, alarm_data, source="internal"):
        """Уведомление подписчиков об изменениях настроек будильника"""
        try:
            # Отправляем новое событие
            new_event_data = {
                "alarm": alarm_data.copy(),
                "source": source,
                "change_id": self._change_id,
                "timestamp": time.time()
            }
            
            # Отправляем старое событие для совместимости
            old_event_data = {
                "time": alarm_data.get("time", "07:30"),
                "enabled": alarm_data.get("enabled", False),
                "repeat": alarm_data.get("repeat", []),
                "ringtone": alarm_data.get("ringtone", ""),
                "fadein": alarm_data.get("fadein", False),
                "source": source
            }
            
            # Отправляем события асинхронно чтобы не блокировать
            from kivy.clock import Clock
            Clock.schedule_once(
                lambda dt: self._send_events(new_event_data, old_event_data), 
                0
            )
            logger.debug(f"Alarm change notification scheduled (source: {source})")
            
        except Exception as e:
            logger.error(f"Error notifying alarm change: {e}")

    def _send_events(self, new_event_data, old_event_data):
        """Отправка событий в main thread"""
        try:
            # Новое событие
            event_bus.publish("alarm_changed", new_event_data)
            # Старое событие для совместимости
            event_bus.publish("alarm_settings_changed", old_event_data)
            logger.debug("Both alarm events sent for compatibility")
        except Exception as e:
            logger.error(f"Error sending events: {e}")

    # ================================
    # ПУБЛИЧНЫЙ API ДЛЯ УПРАВЛЕНИЯ БУДИЛЬНИКОМ
    # ================================

    def get_alarm(self):
        """Получение текущих настроек будильника"""
        if self._is_stopped:
            logger.warning("AlarmService is stopped, returning default")
            return self.default_alarm.copy()
        
        with self._lock:
            alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
            return alarm.copy()  # Возвращаем копию для безопасности

    def update_alarm(self, **kwargs):
        """
        Обновление отдельных параметров будильника
        
        Args:
            **kwargs: Параметры для обновления (time, enabled, repeat, ringtone, fadein)
            
        Returns:
            bool: True если обновление прошло успешно
        """
        if self._is_stopped:
            logger.warning("AlarmService is stopped, cannot update alarm")
            return False
            
        with self._lock:
            try:
                current_alarm = self.alarm_data.get("alarm", {}).copy()
                updated = False
                
                # Обновляем только переданные параметры
                for key, value in kwargs.items():
                    if key in self.default_alarm:
                        if current_alarm.get(key) != value:
                            current_alarm[key] = value
                            updated = True
                            logger.debug(f"Alarm {key} updated: {value}")
                    else:
                        logger.warning(f"Unknown alarm parameter: {key}")
                
                if updated:
                    # Валидируем и сохраняем изменения
                    validated_alarm = self._validate_alarm_settings(current_alarm)
                    self.alarm_data["alarm"] = validated_alarm
                    success = self._save_config_internal()
                    
                    if success:
                        self._change_id += 1
                        logger.info(f"Alarm updated successfully: {kwargs}")
                        
                        # Уведомляем об изменениях
                        self._notify_change(validated_alarm, source="update_api")
                        return True
                    else:
                        logger.error("Failed to save alarm updates")
                        return False
                else:
                    logger.debug("No alarm changes detected")
                    return True
                    
            except Exception as e:
                logger.error(f"Error updating alarm: {e}")
                return False

    def set_alarm(self, alarm_settings):
        """
        Установка полного набора настроек будильника
        
        Args:
            alarm_settings (dict): Полный набор настроек будильника
            
        Returns:
            bool: True если настройки установлены успешно
        """
        if self._is_stopped:
            logger.warning("AlarmService is stopped, cannot set alarm")
            return False
            
        with self._lock:
            try:
                # Валидируем настройки
                validated_settings = self._validate_alarm_settings(alarm_settings)
                
                old_alarm = self.alarm_data.get("alarm", {}).copy()
                self.alarm_data["alarm"] = validated_settings
                
                success = self._save_config_internal()
                if success:
                    self._change_id += 1
                    logger.info(f"Alarm settings set: {validated_settings}")
                    self._notify_change(validated_settings, source="set_alarm")
                    return True
                else:
                    # Откатываем изменения при ошибке сохранения
                    self.alarm_data["alarm"] = old_alarm
                    logger.error("Failed to save alarm settings, rolled back")
                    return False
                    
            except Exception as e:
                logger.error(f"Error setting alarm: {e}")
                return False

    def toggle_enabled(self):
        """
        Переключение включения/выключения будильника
        
        Returns:
            bool: True если операция прошла успешно
        """
        current_alarm = self.get_alarm()
        new_enabled = not current_alarm.get("enabled", False)
        success = self.update_alarm(enabled=new_enabled)
        
        if success:
            logger.info(f"Alarm toggled: {'ON' if new_enabled else 'OFF'}")
        
        return success

    def _validate_alarm_settings(self, settings):
        """
        Валидация настроек будильника
        
        Args:
            settings (dict): Настройки для валидации
            
        Returns:
            dict: Валидированные настройки
        """
        validated = self.default_alarm.copy()
        
        for key, value in settings.items():
            if key in validated:
                # TODO: Добавить специфичную валидацию для каждого поля
                # Например, проверка формата времени, существования файла мелодии и т.д.
                validated[key] = value
            else:
                logger.warning(f"Ignoring unknown alarm setting: {key}")
                
        return validated

    # ================================
    # СОВМЕСТИМОСТЬ СО СТАРЫМ API
    # ================================

    def load_config(self):
        """СОВМЕСТИМОСТЬ: Старый метод загрузки конфигурации"""
        return self._load_config()

    def save_config(self):
        """СОВМЕСТИМОСТЬ: Старый метод сохранения конфигурации"""
        if self._is_stopped:
            logger.warning("AlarmService is stopped, cannot save config")
            return False
        return self._save_config_internal()

    def toggle(self):
        """СОВМЕСТИМОСТЬ: Метод для совместимости со старым API"""
        return self.toggle_enabled()

    def get_status_string(self):
        """Получение статуса будильника в виде строки"""
        if self._is_stopped:
            return "OFF"
            
        try:
            alarm = self.get_alarm()
            if alarm and alarm.get("enabled", False):
                return "ON"
            return "OFF"
        except Exception as e:
            logger.error(f"Error getting alarm status string: {e}")
            return "OFF"

    def get_time_string(self):
        """Получение времени будильника в виде строки"""
        if self._is_stopped:
            logger.warning("AlarmService is stopped, returning default time")
            return "07:30"
        
        try:
            alarm = self.get_alarm()
            if alarm:
                return alarm.get("time", "07:30")
            return "07:30"
        except Exception as e:
            logger.error(f"Error getting alarm time string: {e}")
            return "07:30"

    def get_next_alarm_info(self):
        """Get detailed info about next alarm"""
        if self._is_stopped:
            return {"time": "07:30", "status": "OFF", "next": None}
            
        try:
            alarm = self.get_alarm()
            if not alarm:
                return {"time": "07:30", "status": "OFF", "next": None}
                
            from datetime import datetime, timedelta
            
            # Calculate next alarm time
            if alarm.get("enabled", False):
                alarm_time = alarm.get("time", "07:30")
                days = alarm.get("repeat", [])
                
                # If no specific days, assume daily
                if not days:
                    return {
                        "time": alarm_time, 
                        "status": "ON", 
                        "next": "Tomorrow"
                    }
                    
                # Calculate next occurrence
                now = datetime.now()
                current_day = now.weekday()  # 0=Monday, 6=Sunday
                
                day_mapping = {
                    "mon": 0, "tue": 1, "wed": 2, "thu": 3, 
                    "fri": 4, "sat": 5, "sun": 6
                }
                
                alarm_days = [day_mapping.get(d.lower(), -1) for d in days if d.lower() in day_mapping]
                alarm_days = [d for d in alarm_days if d >= 0]
                
                if not alarm_days:
                    return {"time": alarm_time, "status": "ON", "next": "Daily"}
                
                # Find next alarm day
                next_day = None
                for day in sorted(alarm_days):
                    if day > current_day:
                        next_day = day
                        break
                        
                if next_day is None:
                    # Next week
                    next_day = min(alarm_days)
                    days_until = (7 - current_day) + next_day
                else:
                    days_until = next_day - current_day
                    
                if days_until == 0:
                    next_text = "Today"
                elif days_until == 1:
                    next_text = "Tomorrow"
                else:
                    next_text = f"In {days_until} days"
                    
                return {
                    "time": alarm_time,
                    "status": "ON", 
                    "next": next_text
                }
            else:
                return {
                    "time": alarm.get("time", "07:30"),
                    "status": "OFF",
                    "next": None
                }
                
        except Exception as e:
            logger.error(f"Error getting next alarm info: {e}")
            return {"time": "07:30", "status": "OFF", "next": None}

    def test_alarm(self):
        """Тестирование будильника"""
        if self._is_stopped:
            return False
            
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if app and hasattr(app, 'alarm_clock') and app.alarm_clock:
                alarm = self.get_alarm()
                ringtone = alarm.get("ringtone", "Bathtime In Clerkenwell.mp3")
                fadein = alarm.get("fadein", False)
                
                app.alarm_clock.trigger_alarm(ringtone, fadein)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error testing alarm: {e}")
            return False

    # ================================
    # УПРАВЛЕНИЕ ЖИЗНЕННЫМ ЦИКЛОМ
    # ================================

    def stop(self):
        """Остановка сервиса"""
        if self._is_stopped:
            return
            
        logger.info("Stopping AlarmService...")
        
        try:
            # Останавливаем file watcher
            if hasattr(self, 'file_observer') and self.file_observer:
                self.file_observer.stop()
                self.file_observer.join(timeout=1)
                logger.debug("File watcher stopped")
                
            # Финальное сохранение
            with self._lock:
                self._save_config_internal()
                
        except Exception as e:
            logger.error(f"Error during AlarmService stop: {e}")
        finally:
            self._is_stopped = True
            logger.info("AlarmService stopped")

    def is_stopped(self):
        """Проверка остановлен ли сервис"""
        return self._is_stopped

    # ================================
    # ДИАГНОСТИКА И ОТЛАДКА
    # ================================

    def get_debug_info(self):
        """Получение отладочной информации о состоянии сервиса"""
        with self._lock:
            return {
                "is_stopped": self._is_stopped,
                "config_file": self.config_file,
                "config_exists": os.path.exists(self.config_file),
                "file_watcher_active": hasattr(self, 'file_observer') and self.file_observer and self.file_observer.is_alive(),
                "watchdog_available": WATCHDOG_AVAILABLE,
                "change_id": self._change_id,
                "current_alarm": self.get_alarm()
            }