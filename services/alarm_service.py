"""
Alarm service - управление настройками будильника
"""
import os
import json
from app.logger import app_logger as logger


class AlarmService:
    def __init__(self):
        self.config_file = os.path.join("config", "alarm.json")
        self._is_stopped = False
        
        os.makedirs("config", exist_ok=True)
        
        self.default_alarm = {
            "time": "07:30",
            "enabled": True,
            "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "ringtone": "Bathtime In Clerkenwell.mp3",  # ИСПРАВЛЕНО: было "ringtones"
            "fadein": False,
        }
        
        self.load_config()
        logger.info("AlarmService initialized")
    
    def load_config(self):
        if self._is_stopped:
            return
            
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.alarm_data = data
                    # Проверяем структуру данных
                    if "alarm" not in self.alarm_data:
                        logger.warning("No 'alarm' key in config, creating default")
                        self.alarm_data = {"alarm": self.default_alarm}
                        self.save_config()
            else:
                self.alarm_data = {"alarm": self.default_alarm}
                self.save_config()
                
            logger.info(f"Alarm config loaded: {self.alarm_data}")
        except Exception as e:
            logger.error(f"Error loading alarm config: {e}")
            self.alarm_data = {"alarm": self.default_alarm}
    
    def save_config(self):
        if self._is_stopped:
            logger.warning("AlarmService is stopped, cannot save config")
            return False
            
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.alarm_data, f, indent=2)
            logger.info(f"Alarm config saved: {self.alarm_data}")
            return True
        except Exception as e:
            logger.error(f"Error saving alarm config: {e}")
            return False
    
    def get_alarm(self):
        if self._is_stopped:
            logger.warning("AlarmService is stopped, returning None")
            return None
        
        alarm = self.alarm_data.get("alarm", self.default_alarm.copy())
        logger.debug(f"Getting alarm: {alarm}")
        return alarm
    
    def set_alarm(self, alarm_settings):
        if self._is_stopped:
            logger.warning("AlarmService is stopped, cannot set alarm")
            return False
            
        try:
            logger.info(f"Setting alarm: {alarm_settings}")
            self.alarm_data["alarm"] = alarm_settings
            success = self.save_config()
            if success:
                logger.info("Alarm settings updated successfully")
            return success
        except Exception as e:
            logger.error(f"Error setting alarm: {e}")
            return False
    # Добавить этот метод в класс AlarmService в файле services/alarm_service.py
    # После метода set_alarm():

    def toggle(self):
        """Переключение состояния будильника (включен/выключен)"""
        if self._is_stopped:
            logger.warning("AlarmService is stopped, cannot toggle alarm")
            return False
            
        try:
            alarm = self.get_alarm()
            if alarm:
                # Переключаем состояние
                current_state = alarm.get("enabled", False)
                new_state = not current_state
                
                # Обновляем настройки
                alarm["enabled"] = new_state
                success = self.set_alarm(alarm)
                
                if success:
                    logger.info(f"Alarm toggled: {current_state} -> {new_state}")
                
                return success
            else:
                logger.error("Could not get alarm data for toggle")
                return False
                
        except Exception as e:
            logger.error(f"Error toggling alarm: {e}")
            return False
    
    def test_alarm(self):
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

    def get_time_string(self):
        """Get alarm time as formatted string"""
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

    def get_status_string(self):
        """Get alarm status as formatted string"""
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
                days = alarm.get("days", [])
                
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
                
                alarm_days = [day_mapping.get(d, -1) for d in days if d in day_mapping]
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
    
    def stop(self):
        if self._is_stopped:
            return
        
        logger.info("Stopping AlarmService...")
        
        try:
            # Сохраняем перед остановкой
            if not self._is_stopped:
                self.save_config()
        except Exception as e:
            logger.error(f"Error during final save: {e}")
        finally:
            self._is_stopped = True
            logger.info("AlarmService stopped")
    
    def is_stopped(self):
        return self._is_stopped