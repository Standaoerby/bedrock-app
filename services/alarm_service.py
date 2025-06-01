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
            "ringtones": "robot.mp3",
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
                    self.alarm_data = json.load(f)
            else:
                self.alarm_data = {"alarm": self.default_alarm}
                self.save_config()
        except Exception as e:
            logger.error(f"Error loading alarm config: {e}")
            self.alarm_data = {"alarm": self.default_alarm}
    
    def save_config(self):
        if self._is_stopped:
            return False
            
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.alarm_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving alarm config: {e}")
            return False
    
    def get_alarm(self):
        if self._is_stopped:
            return None
        return self.alarm_data.get("alarm", self.default_alarm)
    
    def set_alarm(self, alarm_settings):
        if self._is_stopped:
            return False
            
        self.alarm_data["alarm"] = alarm_settings
        self.save_config()
        return True
    
    def test_alarm(self):
        if self._is_stopped:
            return False
            
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if app and hasattr(app, 'alarm_clock') and app.alarm_clock:
                alarm = self.get_alarm()
                ringtone = alarm.get("ringtone", "robot.mp3")
                fadein = alarm.get("fadein", False)
                
                app.alarm_clock.trigger_alarm(ringtone, fadein)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error testing alarm: {e}")
            return False
    
    def stop(self):
        if self._is_stopped:
            return
        
        self._is_stopped = True
        
        try:
            self._is_stopped = False
            self.save_config()
            self._is_stopped = True
        except Exception as e:
            logger.error(f"Error during final save: {e}")
    
    def is_stopped(self):
        return self._is_stopped