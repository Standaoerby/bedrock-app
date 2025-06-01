"""
Simplified Alarm service - только управление настройками
Логика проверки времени перенесена в AlarmClock
"""
import os
import json
from app.logger import app_logger as logger


class AlarmService:
    """Упрощённый сервис для управления настройками будильника"""
    
    def __init__(self):
        """Initialize alarm service"""
        self.config_file = os.path.join("config", "alarm.json")
        self._is_stopped = False
        
        # Create necessary directories
        os.makedirs("config", exist_ok=True)
        
        # Default alarm settings
        self.default_alarm = {
            "time": "07:30",
            "enabled": True,  # По умолчанию включен
            "repeat": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "ringtones": "robot.mp3",
            "fadein": False,
        }
        
        # Load configuration
        self.load_config()
        
        logger.info("AlarmService initialized (settings management only)")
    
    def load_config(self):
        """Load alarm configuration from file"""
        if self._is_stopped:
            return
            
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    self.alarm_data = json.load(f)
                logger.info(f"Loaded alarm configuration from {self.config_file}")
            else:
                # Use default settings if file doesn't exist
                self.alarm_data = {"alarm": self.default_alarm}
                self.save_config()
                logger.info("Created default alarm configuration")
        except Exception as e:
            logger.error(f"Error loading alarm configuration: {e}")
            self.alarm_data = {"alarm": self.default_alarm}
    
    def save_config(self):
        """Save alarm configuration to file"""
        if self._is_stopped:
            logger.debug("AlarmService stopped, skipping save")
            return False
            
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.alarm_data, f, indent=2)
            logger.info(f"Saved alarm configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving alarm configuration: {e}")
            return False
    
    def get_alarm(self):
        """Get the current alarm settings"""
        if self._is_stopped:
            return None
        return self.alarm_data.get("alarm", self.default_alarm)
    
    def set_alarm(self, alarm_settings):
        """Update the alarm settings"""
        if self._is_stopped:
            logger.debug("AlarmService stopped, skipping set_alarm")
            return False
            
        self.alarm_data["alarm"] = alarm_settings
        self.save_config()
        logger.info(f"Alarm settings updated: {alarm_settings}")
        return True
    
    def test_alarm(self):
        """Test the alarm by triggering it immediately"""
        if self._is_stopped:
            logger.debug("AlarmService stopped, skipping test")
            return False
            
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if app and hasattr(app, 'alarm_clock') and app.alarm_clock:
                alarm = self.get_alarm()
                ringtone = alarm.get("ringtone", "robot.mp3")
                fadein = alarm.get("fadein", False)
                
                logger.info("Testing alarm...")
                app.alarm_clock.trigger_alarm(ringtone, fadein)
                return True
            else:
                logger.error("App or alarm_clock not available for testing")
                return False
                
        except Exception as e:
            logger.error(f"Error testing alarm: {e}")
            return False
    
    def stop(self):
        """Stop method for safe shutdown"""
        if self._is_stopped:
            logger.debug("AlarmService already stopped")
            return
        
        logger.info("Stopping AlarmService...")
        
        # Отмечаем что сервис остановлен
        self._is_stopped = True
        
        # Попытка финального сохранения
        try:
            # Временно снимаем флаг для последнего сохранения
            self._is_stopped = False
            self.save_config()
            self._is_stopped = True
        except Exception as e:
            logger.error(f"Error during final save in AlarmService.stop(): {e}")
        
        logger.info("AlarmService stopped")
    
    def is_stopped(self):
        """Check if service is stopped"""
        return self._is_stopped