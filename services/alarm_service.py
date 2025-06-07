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
            "ringtone": "robot.mp3",  # ИСПРАВЛЕНО: было "ringtones"
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