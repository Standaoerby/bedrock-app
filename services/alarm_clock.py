"""
AlarmClock - ИСПРАВЛЕННЫЙ основной сервис для проверки времени будильника и его срабатывания
ИСПРАВЛЕНИЯ:
- ✅ Thread-safe доступ к критическим переменным
- ✅ Все импорты перенесены в начало
- ✅ Улучшенная логика popup creation
- ✅ Defensive programming против race conditions
- ✅ Улучшенное логирование для диагностики
"""
import threading
import time
from datetime import datetime, timedelta
from app.logger import app_logger as logger

# ИСПРАВЛЕНО: Все импорты в начале файла
from kivy.app import App
from kivy.clock import Clock


class AlarmClock:
    def __init__(self):
        self.running = False
        self.thread = None
        self.alarm_popup = None
        self._stop_event = threading.Event()
        self._snooze_until = None
        
        # ИСПРАВЛЕНО: Thread-safe переменные с Lock
        self._lock = threading.RLock()  # Реентрантный lock для nested calls
        self._alarm_active = False
        self._last_trigger_time = None
        self._popup_creation_in_progress = False
        
        logger.info("AlarmClock initialized with thread-safe mechanisms")
    
    def start(self):
        """Запуск сервиса с защитой от двойного запуска"""
        with self._lock:
            if self.running:
                logger.warning("AlarmClock already running, ignoring start request")
                return
            
            self.running = True
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._check_alarm_loop, daemon=True, name="AlarmClockThread")
            self.thread.start()
            logger.info("✅ AlarmClock started successfully")
    
    def stop(self):
        """Остановка сервиса с корректным cleanup"""
        with self._lock:
            if not self.running:
                logger.warning("AlarmClock not running, ignoring stop request")
                return
            
            logger.info("Stopping AlarmClock...")
            self.running = False
            self._stop_event.set()
        
        # Ждем завершения потока ВНЕ lock'а чтобы избежать deadlock
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
            if self.thread.is_alive():
                logger.warning("AlarmClock thread did not terminate gracefully")
        
        # Cleanup в main thread
        Clock.schedule_once(self._cleanup_on_main_thread, 0)
        
        logger.info("✅ AlarmClock stopped")
    
    def _cleanup_on_main_thread(self, dt):
        """Cleanup который должен выполняться в main thread"""
        try:
            # Останавливаем аудио
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
            
            # Закрываем popup если открыт
            if self.alarm_popup:
                try:
                    self.alarm_popup.dismiss()
                except Exception as e:
                    logger.error(f"Error dismissing popup during cleanup: {e}")
            
            # Сбрасываем состояние
            with self._lock:
                self._alarm_active = False
                self._snooze_until = None
                self._last_trigger_time = None
                self._popup_creation_in_progress = False
                self.alarm_popup = None
                
        except Exception as e:
            logger.error(f"Error during main thread cleanup: {e}")
    
    def _check_alarm_loop(self):
        """ИСПРАВЛЕННЫЙ основной цикл проверки будильника"""
        logger.info("Alarm check loop started")
        
        while self.running and not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                current_time_str = current_time.strftime("%H:%M")
                
                # Thread-safe проверка и сброс времени последнего срабатывания
                with self._lock:
                    if self._last_trigger_time and self._last_trigger_time != current_time_str:
                        self._last_trigger_time = None
                        logger.debug(f"Reset last trigger time on minute change: {current_time_str}")
                
                # Проверка отложенного срабатывания (snooze)
                snooze_triggered = False
                with self._lock:
                    if self._snooze_until and current_time >= self._snooze_until:
                        self._snooze_until = None
                        snooze_triggered = True
                        logger.info("Snooze time reached, triggering alarm")
                
                if snooze_triggered:
                    self._safe_trigger_alarm_popup()
                # Проверка основного будильника
                elif self._should_alarm_trigger():
                    logger.info("Regular alarm trigger condition met")
                    self._safe_trigger_alarm_popup()
                
                # Ждем 10 секунд или до сигнала остановки
                self._stop_event.wait(10)
                
            except Exception as e:
                logger.error(f"Error in alarm loop: {e}")
                import traceback
                logger.error(f"Alarm loop traceback: {traceback.format_exc()}")
                # При ошибке ждем меньше чтобы быстрее восстановиться
                self._stop_event.wait(5)
        
        logger.info("Alarm check loop finished")
    
    def _should_alarm_trigger(self):
        """ИСПРАВЛЕННАЯ проверка условий срабатывания будильника"""
        try:
            # Быстрая проверка активности без блокировок
            with self._lock:
                if self._alarm_active or self._popup_creation_in_progress:
                    return False
            
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
            
            # Thread-safe проверка последнего срабатывания
            with self._lock:
                if self._last_trigger_time == current_time_str:
                    return False
            
            # Проверка дня недели
            repeat_days = alarm.get("repeat", [])
            if repeat_days:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                current_day = day_names[current_time.weekday()]
                if current_day not in repeat_days:
                    logger.debug(f"Alarm skipped - wrong day: {current_day}, expected: {repeat_days}")
                    return False
            
            logger.info(f"✅ Alarm should trigger: {alarm_time} on {current_time_str}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking alarm trigger conditions: {e}")
            return False
    
    def _safe_trigger_alarm_popup(self):
        """ИСПРАВЛЕННЫЙ thread-safe метод создания popup"""
        try:
            current_time_str = datetime.now().strftime("%H:%M")
            
            # Thread-safe установка состояния
            with self._lock:
                if self._alarm_active or self._popup_creation_in_progress:
                    logger.warning("Alarm already active or popup creation in progress")
                    return
                
                self._popup_creation_in_progress = True
                self._last_trigger_time = current_time_str
            
            # Получаем данные будильника
            app = App.get_running_app()
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                logger.error("AlarmService not available")
                with self._lock:
                    self._popup_creation_in_progress = False
                return
            
            alarm = app.alarm_service.get_alarm()
            if not alarm:
                logger.error("No alarm configuration found")
                with self._lock:
                    self._popup_creation_in_progress = False
                return
            
            alarm_time = alarm.get("time", "--:--")
            ringtone = alarm.get("ringtone", "Bathtime In Clerkenwell.mp3")
            
            logger.info(f"🚨 Triggering alarm popup: {alarm_time} with ringtone: {ringtone}")
            
            # Планируем создание popup в main thread
            Clock.schedule_once(
                lambda dt: self._create_popup_on_main_thread(alarm_time, ringtone), 
                0
            )
            
        except Exception as e:
            logger.error(f"Error in safe trigger alarm popup: {e}")
            with self._lock:
                self._popup_creation_in_progress = False
    
    def _create_popup_on_main_thread(self, alarm_time, ringtone):
        """Создание popup в main thread с полной защитой от ошибок"""
        try:
            logger.info(f"Creating alarm popup in main thread: {alarm_time}")
            
            # Импортируем popup class
            from services.alarm_popup import AlarmPopup
            
            # Создаем popup
            self.alarm_popup = AlarmPopup(
                alarm_time=alarm_time,
                ringtone=ringtone
            )
            
            # Thread-safe установка активности
            with self._lock:
                self._alarm_active = True
                self._popup_creation_in_progress = False
            
            # Открываем popup (воспроизводит звук)
            self.alarm_popup.open_alarm()
            
            logger.info("✅ Alarm popup created and opened successfully")
            
        except ImportError as ie:
            logger.error(f"Cannot import AlarmPopup: {ie}")
            self._handle_popup_creation_error()
        except Exception as e:
            logger.error(f"Error creating popup on main thread: {e}")
            import traceback
            logger.error(f"Popup creation traceback: {traceback.format_exc()}")
            self._handle_popup_creation_error()
    
    def _handle_popup_creation_error(self):
        """Обработка ошибок создания popup"""
        with self._lock:
            self._alarm_active = False
            self._popup_creation_in_progress = False
            self._last_trigger_time = None
        
        # Пытаемся воспроизвести хотя бы звук
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                if hasattr(app, 'theme_manager') and app.theme_manager:
                    error_sound = app.theme_manager.get_sound("error")
                    if error_sound:
                        app.audio_service.play(error_sound)
        except Exception as sound_error:
            logger.error(f"Cannot even play error sound: {sound_error}")
    
    def _force_stop_alarm_internal(self):
        """ИСПРАВЛЕННАЯ внутренняя остановка будильника"""
        try:
            logger.info("Force stopping alarm...")
            
            # Останавливаем аудио
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
            
            # Thread-safe сброс состояния
            with self._lock:
                self._alarm_active = False
                self._snooze_until = None
                self._popup_creation_in_progress = False
                
                # Очищаем popup reference
                if self.alarm_popup:
                    try:
                        # Popup должен быть закрыт в main thread
                        Clock.schedule_once(lambda dt: self._dismiss_popup_safely(), 0)
                    except Exception as e:
                        logger.error(f"Error scheduling popup dismiss: {e}")
                    finally:
                        self.alarm_popup = None
            
            logger.info("✅ Alarm stopped successfully")
            
        except Exception as e:
            logger.error(f"Error force stopping alarm: {e}")
    
    def _dismiss_popup_safely(self):
        """Безопасное закрытие popup в main thread"""
        try:
            if self.alarm_popup:
                self.alarm_popup.dismiss()
                self.alarm_popup = None
        except Exception as e:
            logger.error(f"Error dismissing popup safely: {e}")
    
    # ========================================
    # ПУБЛИЧНЫЕ МЕТОДЫ API
    # ========================================
    
    def stop_alarm(self):
        """Публичный метод остановки будильника"""
        self._force_stop_alarm_internal()
    
    def snooze_alarm(self, minutes=5):
        """ИСПРАВЛЕННЫЙ метод отложенного срабатывания"""
        try:
            logger.info(f"Snoozing alarm for {minutes} minutes")
            
            # Останавливаем текущий будильник
            self._force_stop_alarm_internal()
            
            # Thread-safe установка времени повтора
            with self._lock:
                self._snooze_until = datetime.now() + timedelta(minutes=minutes)
                self._last_trigger_time = None  # Разрешаем повторное срабатывание
            
            logger.info(f"✅ Alarm snoozed until {self._snooze_until.strftime('%H:%M')}")
            
        except Exception as e:
            logger.error(f"Error snoozing alarm: {e}")
    
    def trigger_alarm(self, ringtone="Bathtime In Clerkenwell.mp3", fadein=False):
        """Ручной тест будильника"""
        try:
            logger.info(f"Manual alarm trigger: {ringtone}, fadein={fadein}")
            
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                import os
                ringtone_path = os.path.join("media", "ringtones", ringtone)
                
                if os.path.exists(ringtone_path):
                    fadein_time = 2.0 if fadein else 0
                    app.audio_service.play(ringtone_path, fadein=fadein_time)
                    logger.info("✅ Manual alarm triggered successfully")
                else:
                    logger.error(f"Ringtone file not found: {ringtone_path}")
            else:
                logger.error("AudioService not available for manual trigger")
                
        except Exception as e:
            logger.error(f"Error triggering manual alarm: {e}")
    
    def is_alarm_active(self):
        """Thread-safe проверка активности будильника"""
        with self._lock:
            return self._alarm_active
    
    def get_snooze_info(self):
        """Thread-safe получение информации о snooze"""
        with self._lock:
            if self._snooze_until:
                remaining_seconds = (self._snooze_until - datetime.now()).total_seconds()
                return {
                    "active": True,
                    "until": self._snooze_until.isoformat(),
                    "remaining_minutes": max(0, int(remaining_seconds / 60))
                }
            return {"active": False}
    
    def get_status(self):
        """ИСПРАВЛЕННОЕ получение полного статуса с thread-safety"""
        try:
            app = App.get_running_app()
            
            # Thread-safe получение внутреннего состояния
            with self._lock:
                status = {
                    "service_running": self.running,
                    "alarm_active": self._alarm_active,
                    "popup_open": self.alarm_popup is not None,
                    "popup_creation_in_progress": self._popup_creation_in_progress,
                    "snooze_info": self.get_snooze_info(),
                    "last_trigger_time": self._last_trigger_time,
                    "thread_alive": self.thread.is_alive() if self.thread else False
                }
            
            # Получаем данные будильника
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
            logger.error(f"Error getting alarm status: {e}")
            return {
                "service_running": False,
                "alarm_active": False,
                "popup_open": False,
                "popup_creation_in_progress": False,
                "alarm_enabled": False,
                "alarm_time": "--:--",
                "alarm_days": [],
                "ringtone": "",
                "snooze_info": {"active": False},
                "last_trigger_time": None,
                "thread_alive": False,
                "error": str(e)
            }