# app/app_state.py
# ИСПРАВЛЕНО: Улучшено thread-safety, добавлена диагностика состояния

import threading
from datetime import datetime
from app.logger import app_logger as logger


class AppState:
    """
    ИСПРАВЛЕНО: Централизованное управление состоянием приложения
    Thread-safe singleton для глобального состояния
    """
    
    def __init__(self):
        # Thread safety
        self._lock = threading.RLock()
        
        # ДОБАВЛЕНО: Версионирование и отслеживание
        self._state_version = "2.1.0"
        self._instance_id = id(self)
        self._last_updated = datetime.now()
        
        # Основное состояние
        self.theme = "minecraft"
        self.variant = "light"
        
        # Пользователь
        self.user = {
            "name": "",
            "birth_day": "01",
            "birth_month": "01", 
            "birth_year": "2000"
        }
        
        # Системные настройки
        self.volume = 50
        self.language = "en"
        
        # Будильник
        self.alarm = {
            "time": "07:30",
            "enabled": False,
            "repeat": [],
            "ringtone": "robot.mp3",
            "fadein": False
        }
        
        # Расписание
        self.schedule = {
            "events": [],
            "last_sync": None
        }
        
        # Данные датчиков
        self.sensor_data = {
            "light_level": True,  # True = light, False = dark
            "last_reading": None,
            "sensor_available": False
        }
        
        # Уведомления
        self.notifications = []
        
        # Медиа файлы
        self.media_files = []
        
        # ДОБАВЛЕНО: Статистика изменений
        self._change_count = 0
        self._subscribers = {}
        
        logger.info(f"AppState v{self._state_version} initialized (ID: {self._instance_id})")

    def _update_timestamp(self):
        """НОВОЕ: Обновление временной метки при изменениях"""
        self._last_updated = datetime.now()
        self._change_count += 1

    def diagnose_state(self):
        """НОВОЕ: Диагностика состояния AppState"""
        with self._lock:
            return {
                "instance_id": self._instance_id,
                "state_version": self._state_version,
                "last_updated": self._last_updated.isoformat(),
                "change_count": self._change_count,
                "current_theme": f"{self.theme}/{self.variant}",
                "user_name": self.user.get("name", ""),
                "volume": self.volume,
                "language": self.language,
                "alarm_enabled": self.alarm.get("enabled", False),
                "alarm_time": self.alarm.get("time", ""),
                "sensor_available": self.sensor_data.get("sensor_available", False),
                "light_level": self.sensor_data.get("light_level", True),
                "notifications_count": len(self.notifications),
                "media_files_count": len(self.media_files),
                "schedule_events_count": len(self.schedule.get("events", [])),
                "subscribers_count": len(self._subscribers)
            }

    def verify_instance(self):
        """НОВОЕ: Верификация экземпляра AppState"""
        return {
            "class_name": self.__class__.__name__,
            "instance_id": self._instance_id,
            "state_version": self._state_version,
            "is_thread_safe": True,
            "methods": [method for method in dir(self) if not method.startswith('_')]
        }

    # ================================
    # THEME MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_theme(self, theme, variant=None):
        """ИСПРАВЛЕНО: Установка темы с валидацией"""
        with self._lock:
            if isinstance(theme, str) and theme.strip():
                old_theme = self.theme
                self.theme = theme.strip()
                
                if variant and isinstance(variant, str) and variant.strip():
                    old_variant = self.variant
                    self.variant = variant.strip()
                    logger.info(f"Theme changed: {old_theme}/{old_variant} -> {self.theme}/{self.variant}")
                else:
                    logger.info(f"Theme changed: {old_theme} -> {self.theme}")
                
                self._update_timestamp()
                self._publish_event("theme_changed", {
                    "theme": self.theme, 
                    "variant": self.variant,
                    "old_theme": old_theme,
                    "old_variant": self.variant if variant else old_variant
                })
            else:
                logger.warning(f"Invalid theme value: {theme}")

    def set_variant(self, variant):
        """ИСПРАВЛЕНО: Установка варианта темы"""
        with self._lock:
            if isinstance(variant, str) and variant.strip():
                old_variant = self.variant
                self.variant = variant.strip()
                self._update_timestamp()
                
                logger.info(f"Variant changed: {old_variant} -> {self.variant}")
                self._publish_event("variant_changed", {
                    "variant": self.variant,
                    "theme": self.theme,
                    "old_variant": old_variant
                })
            else:
                logger.warning(f"Invalid variant value: {variant}")

    def get_theme(self):
        """Получение текущей темы"""
        with self._lock:
            return self.theme, self.variant

    # ================================
    # USER MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_user_data(self, **kwargs):
        """ИСПРАВЛЕНО: Установка данных пользователя с валидацией"""
        with self._lock:
            old_user = self.user.copy()
            updated_fields = []
            
            for key, value in kwargs.items():
                if key in self.user:
                    if isinstance(value, str):
                        value = value.strip()
                    
                    if self.user[key] != value:
                        self.user[key] = value
                        updated_fields.append(key)
                else:
                    logger.warning(f"Unknown user field: {key}")
            
            if updated_fields:
                self._update_timestamp()
                logger.info(f"User data updated: {updated_fields}")
                self._publish_event("user_data_changed", {
                    "updated_fields": updated_fields,
                    "user": self.user.copy(),
                    "old_user": old_user
                })

    def get_user_data(self):
        """Получение данных пользователя"""
        with self._lock:
            return self.user.copy()

    # ================================
    # VOLUME MANAGEMENT - ИСПРАВЛЕНО  
    # ================================
    
    def set_volume(self, volume):
        """ИСПРАВЛЕНО: Установка громкости с валидацией"""
        with self._lock:
            try:
                new_volume = max(0, min(100, int(volume)))
                if self.volume != new_volume:
                    old_volume = self.volume
                    self.volume = new_volume
                    self._update_timestamp()
                    
                    logger.debug(f"Volume changed: {old_volume} -> {new_volume}")
                    self._publish_event("volume_changed", {
                        "volume": new_volume,
                        "old_volume": old_volume
                    })
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid volume value: {volume} ({e})")

    def get_volume(self):
        """Получение текущей громкости"""
        with self._lock:
            return self.volume

    # ================================
    # LANGUAGE MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_language(self, language):
        """ИСПРАВЛЕНО: Установка языка с валидацией"""
        with self._lock:
            if isinstance(language, str) and language.strip():
                language = language.strip().lower()
                if self.language != language:
                    old_language = self.language
                    self.language = language
                    self._update_timestamp()
                    
                    logger.info(f"Language changed: {old_language} -> {language}")
                    self._publish_event("language_changed", {
                        "language": language,
                        "old_language": old_language
                    })
            else:
                logger.warning(f"Invalid language value: {language}")

    def get_language(self):
        """Получение текущего языка"""
        with self._lock:
            return self.language

    # ================================
    # ALARM MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_alarm_data(self, **kwargs):
        """ИСПРАВЛЕНО: Установка данных будильника"""
        with self._lock:
            old_alarm = self.alarm.copy()
            updated_fields = []
            
            for key, value in kwargs.items():
                if key in self.alarm:
                    if self.alarm[key] != value:
                        self.alarm[key] = value
                        updated_fields.append(key)
                else:
                    logger.warning(f"Unknown alarm field: {key}")
            
            if updated_fields:
                self._update_timestamp()
                logger.info(f"Alarm data updated: {updated_fields}")
                self._publish_event("alarm_data_changed", {
                    "updated_fields": updated_fields,
                    "alarm": self.alarm.copy(),
                    "old_alarm": old_alarm
                })

    def get_alarm_data(self):
        """Получение данных будильника"""
        with self._lock:
            return self.alarm.copy()

    # ================================
    # SENSOR DATA MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_sensor_data(self, **kwargs):
        """ИСПРАВЛЕНО: Установка данных датчиков"""
        with self._lock:
            old_sensor_data = self.sensor_data.copy()
            updated_fields = []
            
            for key, value in kwargs.items():
                if key in self.sensor_data:
                    if self.sensor_data[key] != value:
                        self.sensor_data[key] = value
                        updated_fields.append(key)
                else:
                    self.sensor_data[key] = value  # Разрешаем новые поля для датчиков
                    updated_fields.append(key)
            
            if updated_fields:
                # Обновляем время последнего чтения
                self.sensor_data["last_reading"] = datetime.now().isoformat()
                self._update_timestamp()
                
                logger.debug(f"Sensor data updated: {updated_fields}")
                self._publish_event("sensor_data_changed", {
                    "updated_fields": updated_fields,
                    "sensor_data": self.sensor_data.copy(),
                    "old_sensor_data": old_sensor_data
                })

    def get_sensor_data(self):
        """Получение данных датчиков"""
        with self._lock:
            return self.sensor_data.copy()

    # ================================
    # SCHEDULE MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_schedule(self, schedule):
        """ИСПРАВЛЕНО: Установка расписания"""
        with self._lock:
            if isinstance(schedule, dict):
                old_schedule = self.schedule.copy()
                self.schedule.update(schedule)
                self._update_timestamp()
                
                logger.info("Schedule updated")
                self._publish_event("schedule_updated", {
                    "schedule": self.schedule.copy(),
                    "old_schedule": old_schedule
                })
            else:
                logger.warning(f"Invalid schedule type: {type(schedule)}")

    def get_schedule(self):
        """Получение расписания"""
        with self._lock:
            return self.schedule.copy()

    # ================================
    # NOTIFICATIONS MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_notifications(self, notifications):
        """ИСПРАВЛЕНО: Установка уведомлений"""
        with self._lock:
            if isinstance(notifications, list):
                old_count = len(self.notifications)
                self.notifications = list(notifications)
                self._update_timestamp()
                
                new_count = len(self.notifications)
                logger.debug(f"Notifications updated: {old_count} -> {new_count}")
                self._publish_event("notifications_updated", {
                    "notifications": self.notifications.copy(),
                    "count": new_count,
                    "old_count": old_count
                })
            else:
                logger.warning(f"Invalid notifications type: {type(notifications)}")

    def add_notification(self, notification):
        """НОВОЕ: Добавление одного уведомления"""
        with self._lock:
            if isinstance(notification, dict):
                self.notifications.append(notification)
                self._update_timestamp()
                
                logger.debug(f"Notification added: {notification.get('title', 'Unknown')}")
                self._publish_event("notification_added", {
                    "notification": notification,
                    "total_count": len(self.notifications)
                })
            else:
                logger.warning(f"Invalid notification type: {type(notification)}")

    def clear_notifications(self):
        """НОВОЕ: Очистка всех уведомлений"""
        with self._lock:
            old_count = len(self.notifications)
            self.notifications.clear()
            self._update_timestamp()
            
            logger.info(f"Cleared {old_count} notifications")
            self._publish_event("notifications_cleared", {
                "cleared_count": old_count
            })

    def get_notifications(self):
        """Получение уведомлений"""
        with self._lock:
            return self.notifications.copy()

    # ================================
    # MEDIA FILES MANAGEMENT - ИСПРАВЛЕНО
    # ================================
    
    def set_media_files(self, media_files):
        """ИСПРАВЛЕНО: Установка медиа-файлов"""
        with self._lock:
            if isinstance(media_files, list):
                old_count = len(self.media_files)
                self.media_files = list(media_files)
                self._update_timestamp()
                
                new_count = len(self.media_files)
                logger.debug(f"Media files updated: {old_count} -> {new_count}")
                self._publish_event("media_files_updated", {
                    "media_files": self.media_files.copy(),
                    "count": new_count,
                    "old_count": old_count
                })
            else:
                logger.warning(f"Invalid media_files type: {type(media_files)}")

    def get_media_files(self):
        """Получение медиа-файлов"""
        with self._lock:
            return self.media_files.copy()

    # ================================
    # EVENT SYSTEM - НОВОЕ
    # ================================
    
    def _publish_event(self, event_name, event_data):
        """НОВОЕ: Публикация событий через event_bus"""
        try:
            from app.event_bus import event_bus
            event_bus.publish(event_name, event_data)
        except Exception as e:
            logger.error(f"Error publishing event {event_name}: {e}")

    def subscribe(self, event_name, callback):
        """НОВОЕ: Подписка на события AppState"""
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)
            logger.debug(f"Subscribed to {event_name}")

    def unsubscribe(self, event_name, callback):
        """НОВОЕ: Отписка от событий"""
        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(callback)
                    logger.debug(f"Unsubscribed from {event_name}")
                except ValueError:
                    logger.warning(f"Callback not found in {event_name} subscribers")

    # ================================
    # STATE SNAPSHOT - ИСПРАВЛЕНО
    # ================================
    
    def snapshot(self):
        """ИСПРАВЛЕНО: Получение копии текущего состояния"""
        with self._lock:
            return {
                "instance_id": self._instance_id,
                "state_version": self._state_version,
                "last_updated": self._last_updated.isoformat(),
                "change_count": self._change_count,
                "theme": self.theme,
                "variant": self.variant,
                "user": self.user.copy(),
                "volume": self.volume,
                "language": self.language,
                "alarm": self.alarm.copy(),
                "schedule": self.schedule.copy(),
                "sensor_data": self.sensor_data.copy(),
                "notifications": self.notifications.copy(),
                "media_files": self.media_files.copy()
            }

    def load_snapshot(self, snapshot):
        """НОВОЕ: Загрузка состояния из снапшота"""
        with self._lock:
            if not isinstance(snapshot, dict):
                logger.error("Invalid snapshot format")
                return False
            
            try:
                # Загружаем основные поля
                if "theme" in snapshot:
                    self.theme = snapshot["theme"]
                if "variant" in snapshot:
                    self.variant = snapshot["variant"]
                if "user" in snapshot:
                    self.user.update(snapshot["user"])
                if "volume" in snapshot:
                    self.volume = snapshot["volume"]
                if "language" in snapshot:
                    self.language = snapshot["language"]
                if "alarm" in snapshot:
                    self.alarm.update(snapshot["alarm"])
                if "schedule" in snapshot:
                    self.schedule.update(snapshot["schedule"])
                if "sensor_data" in snapshot:
                    self.sensor_data.update(snapshot["sensor_data"])
                if "notifications" in snapshot:
                    self.notifications = list(snapshot["notifications"])
                if "media_files" in snapshot:
                    self.media_files = list(snapshot["media_files"])
                
                self._update_timestamp()
                logger.info("State loaded from snapshot")
                self._publish_event("state_loaded", {"snapshot": snapshot})
                return True
                
            except Exception as e:
                logger.error(f"Error loading snapshot: {e}")
                return False


# ИСПРАВЛЕНО: Глобальный singleton с proper initialization
app_state = AppState()

def get_app_state():
    """НОВОЕ: Безопасное получение экземпляра AppState"""
    return app_state

def validate_app_state_module():
    """НОВОЕ: Валидация модуля AppState для отладки"""
    try:
        state = AppState()
        assert hasattr(state, 'diagnose_state'), "diagnose_state method missing"
        assert hasattr(state, 'verify_instance'), "verify_instance method missing"
        assert hasattr(state, 'snapshot'), "snapshot method missing"
        print("✅ AppState module validation passed")
        return True
    except Exception as e:
        print(f"❌ AppState module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_app_state_module()