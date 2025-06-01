"""
AlarmClock - основной сервис для проверки времени будильника и его срабатывания
"""
import threading
import time
from datetime import datetime, timedelta
from app.logger import app_logger as logger


class AlarmClock:
    def __init__(self):
        self.running = False
        self.thread = None
        self.alarm_popup = None
        self._stop_event = threading.Event()
        self._snooze_until = None
        self._alarm_active = False
        self._last_trigger_time = None
        
        logger.info("AlarmClock initialized")
    
    def start(self):
        if self.running:
            return
        
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._check_alarm_loop, daemon=True)
        self.thread.start()
        logger.info("AlarmClock started")
    
    def stop(self):
        if not self.running:
            return
        
        self.running = False
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        try:
            from kivy.app import App
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        self._alarm_active = False
        self._snooze_until = None
        self._last_trigger_time = None
        self.alarm_popup = None
        
        logger.info("AlarmClock stopped")
    
    def _check_alarm_loop(self):
        while self.running and not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                current_time_str = current_time.strftime("%H:%M")
                
                # Сброс времени последнего срабатывания при смене минуты
                if self._last_trigger_time and self._last_trigger_time != current_time_str:
                    self._last_trigger_time = None
                
                # Проверка отложенного срабатывания
                if self._snooze_until and current_time >= self._snooze_until:
                    self._snooze_until = None
                    self._trigger_alarm_popup()
                
                # Проверка основного будильника
                elif self._should_alarm_trigger():
                    self._trigger_alarm_popup()
                
                self._stop_event.wait(10)
                
            except Exception as e:
                logger.error(f"Error in alarm loop: {e}")
                self._stop_event.wait(5)
    
    def _should_alarm_trigger(self):
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                return False
            
            alarm = app.alarm_service.get_alarm()
            if not alarm or not alarm.get("enabled", False):
                return False
            
            current_time = datetime.now()
            current_time_str = current_time.strftime("%H:%M")
            alarm_time = alarm.get("time", "07:30")
            
            if current_time_str != alarm_time:
                return False
            
            # Защита от повторного срабатывания в одну минуту
            if self._last_trigger_time == current_time_str:
                return False
            
            # Проверка дня недели
            repeat_days = alarm.get("repeat", [])
            if repeat_days:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                current_day = day_names[current_time.weekday()]
                if current_day not in repeat_days:
                    return False
            
            if self._alarm_active:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking alarm: {e}")
            return False
    
    def _trigger_alarm_popup(self):
        try:
            from kivy.app import App
            from kivy.clock import Clock
            
            current_time_str = datetime.now().strftime("%H:%M")
            app = App.get_running_app()
            
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                return
            
            alarm = app.alarm_service.get_alarm()
            if not alarm:
                return
            
            alarm_time = alarm.get("time", "--:--")
            ringtone = alarm.get("ringtone", "robot.mp3")
            
            self._alarm_active = True
            self._last_trigger_time = current_time_str
            
            def create_popup(dt):
                try:
                    from services.alarm_popup import AlarmPopup
                    
                    self.alarm_popup = AlarmPopup(
                        alarm_time=alarm_time,
                        ringtone=ringtone
                    )
                    self.alarm_popup.open_alarm()
                    
                except Exception as e:
                    logger.error(f"Error creating popup: {e}")
                    self._alarm_active = False
                    self._last_trigger_time = None
            
            Clock.schedule_once(create_popup, 0)
            
        except Exception as e:
            logger.error(f"Error triggering alarm: {e}")
            self._alarm_active = False
            self._last_trigger_time = None
    
    def _force_stop_alarm_internal(self):
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
            
            self._alarm_active = False
            self._snooze_until = None
            self.alarm_popup = None
            
        except Exception as e:
            logger.error(f"Error stopping alarm: {e}")
    
    def stop_alarm(self):
        self._force_stop_alarm_internal()
    
    def snooze_alarm(self, minutes=5):
        try:
            self._force_stop_alarm_internal()
            self._snooze_until = datetime.now() + timedelta(minutes=minutes)
            self._last_trigger_time = None
            
        except Exception as e:
            logger.error(f"Error snoozing alarm: {e}")
    
    def trigger_alarm(self, ringtone="robot.mp3", fadein=False):
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'audio_service') and app.audio_service:
                import os
                ringtone_path = os.path.join("media", "ringtones", ringtone)
                
                if os.path.exists(ringtone_path):
                    fadein_time = 2.0 if fadein else 0
                    app.audio_service.play(ringtone_path, fadein=fadein_time)
                    
        except Exception as e:
            logger.error(f"Error triggering test alarm: {e}")
    
    def is_alarm_active(self):
        return self._alarm_active
    
    def get_snooze_info(self):
        if self._snooze_until:
            return {
                "active": True,
                "until": self._snooze_until.isoformat(),
                "remaining_minutes": int((self._snooze_until - datetime.now()).total_seconds() / 60)
            }
        return {"active": False}
    
    def get_status(self):
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            status = {
                "service_running": self.running,
                "alarm_active": self._alarm_active,
                "popup_open": self.alarm_popup is not None,
                "snooze_info": self.get_snooze_info(),
                "last_trigger_time": self._last_trigger_time
            }
            
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    status.update({
                        "alarm_enabled": alarm.get("enabled", False),
                        "alarm_time": alarm.get("time", "--:--"),
                        "alarm_days": alarm.get("repeat", []),
                        "ringtone": alarm.get("ringtone", "")
                    })
                else:
                    status.update({
                        "alarm_enabled": False,
                        "alarm_time": "--:--", 
                        "alarm_days": [],
                        "ringtone": ""
                    })
            else:
                status.update({
                    "alarm_enabled": False,
                    "alarm_time": "--:--",
                    "alarm_days": [],
                    "ringtone": ""
                })
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "service_running": False,
                "alarm_active": False,
                "popup_open": False,
                "alarm_enabled": False,
                "alarm_time": "--:--",
                "alarm_days": [],
                "ringtone": "",
                "snooze_info": {"active": False},
                "last_trigger_time": None
            }