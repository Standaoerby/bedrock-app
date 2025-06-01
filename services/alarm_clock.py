"""
AlarmClock - основной сервис для проверки времени будильника и его срабатывания
"""
import threading
import time
from datetime import datetime, timedelta
from app.logger import app_logger as logger


class AlarmClock:
    """Сервис для проверки и срабатывания будильника"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.alarm_popup = None
        self._stop_event = threading.Event()
        self._snooze_until = None
        self._alarm_active = False
        
        logger.info("AlarmClock initialized")
    
    def start(self):
        """Запуск сервиса проверки будильника"""
        if self.running:
            logger.warning("AlarmClock already running")
            return
        
        self.running = True
        self._stop_event.clear()
        
        # Запускаем поток проверки
        self.thread = threading.Thread(target=self._check_alarm_loop, daemon=True)
        self.thread.start()
        
        logger.info("AlarmClock started")
    
    def stop(self):
        """Остановка сервиса будильника"""
        if not self.running:
            logger.debug("AlarmClock already stopped")
            return
        
        logger.info("Stopping AlarmClock...")
        
        # Останавливаем поток
        self.running = False
        self._stop_event.set()
        
        # Ждем завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning("AlarmClock thread did not stop gracefully")
        
        # Закрываем активный попап будильника
        self.stop_alarm()
        
        logger.info("AlarmClock stopped")
    
    def _check_alarm_loop(self):
        """Основной цикл проверки времени будильника"""
        logger.info("AlarmClock monitoring loop started")
        
        while self.running and not self._stop_event.is_set():
            try:
                # Проверяем не находимся ли в режиме отложенного срабатывания
                if self._snooze_until:
                    current_time = datetime.now()
                    if current_time >= self._snooze_until:
                        logger.info("Snooze time expired, triggering alarm")
                        self._snooze_until = None
                        self._trigger_alarm_popup()
                
                # Проверяем основной будильник
                elif self._should_alarm_trigger():
                    logger.info("Alarm time reached, triggering alarm")
                    self._trigger_alarm_popup()
                
                # Ждем 10 секунд перед следующей проверкой
                self._stop_event.wait(10)
                
            except Exception as e:
                logger.error(f"Error in alarm check loop: {e}")
                self._stop_event.wait(5)  # Короткая пауза при ошибке
        
        logger.info("AlarmClock monitoring loop stopped")
    
    def _should_alarm_trigger(self):
        """Проверка, должен ли срабатывать будильник"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                return False
            
            # Получаем настройки будильника
            alarm = app.alarm_service.get_alarm()
            if not alarm or not alarm.get("enabled", False):
                return False
            
            # Проверяем время
            alarm_time = alarm.get("time", "07:30")
            current_time = datetime.now()
            current_time_str = current_time.strftime("%H:%M")
            
            # Срабатываем только когда время точно совпадает (с точностью до минуты)
            if current_time_str != alarm_time:
                return False
            
            # Проверяем день недели
            repeat_days = alarm.get("repeat", [])
            if repeat_days:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                current_day = day_names[current_time.weekday()]
                
                if current_day not in repeat_days:
                    return False
            
            # Проверяем что будильник уже не активен
            if self._alarm_active:
                return False
            
            logger.info(f"Alarm should trigger: {alarm_time} on {current_time.strftime('%A')}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking alarm trigger: {e}")
            return False
    
    def _trigger_alarm_popup(self):
        """Срабатывание будильника - показ попапа"""
        try:
            from kivy.app import App
            from kivy.clock import Clock
            
            app = App.get_running_app()
            
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                logger.error("AlarmService not available for alarm trigger")
                return
            
            # Получаем настройки будильника
            alarm = app.alarm_service.get_alarm()
            if not alarm:
                logger.error("No alarm configuration found")
                return
            
            alarm_time = alarm.get("time", "--:--")
            ringtone = alarm.get("ringtone", "robot.mp3")
            
            # Отмечаем что будильник активен
            self._alarm_active = True
            
            # Создаем и показываем попап в главном потоке
            def create_popup(dt):
                try:
                    # Импортируем AlarmPopup
                    from services.alarm_popup import AlarmPopup
                    
                    # Создаем попап
                    self.alarm_popup = AlarmPopup(
                        alarm_time=alarm_time,
                        ringtone=ringtone
                    )
                    
                    # Открываем попап
                    self.alarm_popup.open_alarm()
                    
                    logger.info(f"Alarm popup shown for {alarm_time}")
                    
                except Exception as e:
                    logger.error(f"Error creating alarm popup: {e}")
                    self._alarm_active = False
            
            # Планируем создание попапа в главном потоке
            Clock.schedule_once(create_popup, 0)
            
        except Exception as e:
            logger.error(f"Error triggering alarm popup: {e}")
            self._alarm_active = False
    
    def stop_alarm(self):
        """Остановка активного будильника"""
        try:
            # Останавливаем аудио
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
            
            # Закрываем попап
            if self.alarm_popup:
                try:
                    self.alarm_popup.dismiss()
                except Exception as e:
                    logger.warning(f"Error dismissing alarm popup: {e}")
                finally:
                    self.alarm_popup = None
            
            # Сбрасываем флаг активности
            self._alarm_active = False
            self._snooze_until = None
            
            logger.info("Alarm stopped")
            
        except Exception as e:
            logger.error(f"Error stopping alarm: {e}")
    
    def snooze_alarm(self, minutes=5):
        """Отложить будильник на указанное количество минут"""
        try:
            # Останавливаем текущий будильник
            self.stop_alarm()
            
            # Устанавливаем время отложенного срабатывания
            self._snooze_until = datetime.now() + timedelta(minutes=minutes)
            
            logger.info(f"Alarm snoozed for {minutes} minutes until {self._snooze_until.strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Error snoozing alarm: {e}")
    
    def trigger_alarm(self, ringtone="robot.mp3", fadein=False):
        """Принудительное срабатывание будильника (для тестирования)"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'audio_service') and app.audio_service:
                import os
                ringtone_path = os.path.join("media", "ringtones", ringtone)
                
                if os.path.exists(ringtone_path):
                    fadein_time = 2.0 if fadein else 0
                    app.audio_service.play(ringtone_path, fadein=fadein_time)
                    logger.info(f"Test alarm triggered with {ringtone}")
                else:
                    logger.warning(f"Ringtone file not found: {ringtone_path}")
            
        except Exception as e:
            logger.error(f"Error triggering test alarm: {e}")
    
    def is_alarm_active(self):
        """Проверка активности будильника"""
        return self._alarm_active
    
    def get_snooze_info(self):
        """Получение информации об отложенном будильнике"""
        if self._snooze_until:
            return {
                "active": True,
                "until": self._snooze_until.isoformat(),
                "remaining_minutes": int((self._snooze_until - datetime.now()).total_seconds() / 60)
            }
        return {"active": False}