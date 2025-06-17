# services/alarm_clock.py
"""
ФИНАЛЬНЫЙ AlarmClock - простой и надежный будильник
"""
import threading
from datetime import datetime, timedelta
from kivy.app import App
from kivy.clock import Clock
from app.logger import app_logger as logger


class AlarmClock:
    def __init__(self):
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        
        # Простое состояние
        self._alarm_active = False
        self._snooze_until = None
        self.alarm_popup = None
        
        logger.info("AlarmClock initialized")
    
    def start(self):
        """Запуск сервиса будильника"""
        if self.running:
            logger.warning("AlarmClock already running")
            return
        
        self.running = True
        self._stop_event.clear()
        
        # Запускаем поток проверки
        self.thread = threading.Thread(target=self._alarm_check_loop, daemon=True)
        self.thread.start()
        
        logger.info("✅ AlarmClock started")
    
    def stop(self):
        """Остановка сервиса будильника"""
        if not self.running:
            return
        
        logger.info("Stopping AlarmClock...")
        self.running = False
        self._stop_event.set()
        
        # Останавливаем будильник если активен
        if self._alarm_active:
            self.stop_alarm()
        
        # Ждем завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        logger.info("✅ AlarmClock stopped")
    
    def _alarm_check_loop(self):
        """Основной цикл проверки будильника"""
        logger.info("Alarm check loop started")
        
        while self.running and not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                
                # Проверяем snooze
                if self._snooze_until and current_time >= self._snooze_until:
                    self._snooze_until = None
                    self._trigger_alarm()
                    
                # Проверяем основной будильник
                elif not self._alarm_active and self._should_trigger_alarm():
                    self._trigger_alarm()
                
                # Ждем 30 секунд
                self._stop_event.wait(30)
                
            except Exception as e:
                logger.error(f"Error in alarm check loop: {e}")
                self._stop_event.wait(10)
        
        logger.info("Alarm check loop finished")
    
    def _should_trigger_alarm(self):
        """Проверка условий срабатывания будильника"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'alarm_service'):
                return False
            
            alarm = app.alarm_service.get_alarm()
            if not alarm or not alarm.get("enabled", False):
                return False
            
            current_time = datetime.now()
            current_time_str = current_time.strftime("%H:%M")
            alarm_time = alarm.get("time", "07:30")
            
            if current_time_str != alarm_time:
                return False
            
            # Проверяем дни недели
            repeat_days = alarm.get("repeat", [])
            if repeat_days:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                current_day = day_names[current_time.weekday()]
                if current_day not in repeat_days:
                    return False
            
            logger.info(f"✅ Alarm trigger: {alarm_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking alarm trigger: {e}")
            return False
    
    def _trigger_alarm(self):
        """Запуск будильника"""
        try:
            if self._alarm_active:
                return
            
            self._alarm_active = True
            
            # Получаем данные будильника
            app = App.get_running_app()
            alarm = app.alarm_service.get_alarm()
            alarm_time = alarm.get("time", "--:--")
            ringtone = alarm.get("ringtone", "Bathtime In Clerkenwell.mp3")
            
            logger.info(f"🚨 Triggering alarm: {alarm_time}")
            
            # Создаем popup в главном потоке
            Clock.schedule_once(
                lambda dt: self._create_alarm_popup(alarm_time, ringtone), 0
            )
            
        except Exception as e:
            logger.error(f"Error triggering alarm: {e}")
            self._alarm_active = False
    
    def _create_alarm_popup(self, alarm_time, ringtone):
        """Создание popup будильника в главном потоке"""
        try:
            from services.alarm_popup import AlarmPopup
            
            self.alarm_popup = AlarmPopup(
                alarm_time=alarm_time,
                ringtone=ringtone
            )
            
            self.alarm_popup.open_alarm()
            logger.info("✅ Alarm popup opened")
            
        except Exception as e:
            logger.error(f"Error creating alarm popup: {e}")
            self._alarm_active = False
            
            # Пытаемся хотя бы воспроизвести звук
            try:
                app = App.get_running_app()
                if hasattr(app, 'audio_service'):
                    app.audio_service.play(f"ringtones/{ringtone}")
            except:
                pass
    
    def stop_alarm(self):
        """Остановка будильника"""
        if not self._alarm_active:
            return
        
        logger.info("Stopping alarm...")
        
        try:
            # Останавливаем аудио
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                app.audio_service.stop()
            
            # Закрываем popup
            if self.alarm_popup:
                self.alarm_popup.dismiss()
                self.alarm_popup = None
            
            self._alarm_active = False
            self._snooze_until = None
            
            logger.info("✅ Alarm stopped")
            
        except Exception as e:
            logger.error(f"Error stopping alarm: {e}")
    
    def snooze_alarm(self, minutes=5):
        """Отложить будильник"""
        if not self._alarm_active:
            return
        
        logger.info(f"Snoozing alarm for {minutes} minutes")
        
        # Останавливаем текущий будильник
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                app.audio_service.stop()
            
            if self.alarm_popup:
                self.alarm_popup.dismiss()
                self.alarm_popup = None
                
        except Exception as e:
            logger.error(f"Error during snooze: {e}")
        
        # Устанавливаем время повтора
        self._snooze_until = datetime.now() + timedelta(minutes=minutes)
        self._alarm_active = False
        
        logger.info(f"Alarm snoozed until {self._snooze_until.strftime('%H:%M')}")
    
    def get_snooze_info(self):
        """Информация о snooze"""
        if not self._snooze_until:
            return {"active": False}
        
        remaining = self._snooze_until - datetime.now()
        if remaining.total_seconds() <= 0:
            return {"active": False}
        
        return {
            "active": True,
            "until": self._snooze_until.strftime("%H:%M"),
            "remaining_minutes": max(0, int(remaining.total_seconds() / 60))
        }
    
    def get_status(self):
        """Получение статуса будильника"""
        try:
            app = App.get_running_app()
            
            status = {
                "service_running": self.running,
                "alarm_active": self._alarm_active,
                "popup_open": self.alarm_popup is not None,
                "snooze_info": self.get_snooze_info(),
                "thread_alive": self.thread.is_alive() if self.thread else False
            }
            
            # Данные будильника
            if hasattr(app, 'alarm_service'):
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    status.update({
                        "alarm_enabled": alarm.get("enabled", False),
                        "alarm_time": alarm.get("time", "--:--"),
                        "alarm_days": alarm.get("repeat", []),
                        "ringtone": alarm.get("ringtone", "")
                    })
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"error": str(e)}