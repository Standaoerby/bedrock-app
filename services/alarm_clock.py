"""
AlarmClock - основной сервис для проверки времени будильника и его срабатывания
ФИНАЛЬНАЯ ВЕРСИЯ: четкое разделение ответственности, без рекурсии
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
        
        # ДОБАВЛЕНО: защита от множественного срабатывания в одну минуту
        self._last_trigger_time = None
        
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
        
        # Принудительно останавливаем будильник и сбрасываем ВСЕ состояния
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
            
            # При полной остановке сервиса сбрасываем ВСЁ, включая время
            self._alarm_active = False
            self._snooze_until = None
            self._last_trigger_time = None  # Сбрасываем при полной остановке
            self.alarm_popup = None
            
            logger.info("AlarmClock fully stopped and reset")
            
        except Exception as e:
            logger.error(f"Error during AlarmClock shutdown: {e}")
        
        logger.info("AlarmClock stopped")
    
    def _check_alarm_loop(self):
        """Основной цикл проверки времени будильника"""
        logger.info("AlarmClock monitoring loop started")
        
        while self.running and not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                current_time_str = current_time.strftime("%H:%M")
                
                # ДОБАВЛЕНО: Автоматический сброс времени последнего срабатывания при смене минуты
                if self._last_trigger_time and self._last_trigger_time != current_time_str:
                    logger.info(f"⏰ Time changed from {self._last_trigger_time} to {current_time_str}, resetting last trigger")
                    self._last_trigger_time = None
                
                # Проверяем не находимся ли в режиме отложенного срабатывания
                if self._snooze_until:
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
            
            current_time = datetime.now()
            current_time_str = current_time.strftime("%H:%M")
            
            # ОТЛАДКА: подробное логирование - только если что-то потенциально может сработать
            alarm_might_trigger = False
            
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                return False
            
            # Получаем настройки будильника
            alarm = app.alarm_service.get_alarm()
            if not alarm or not alarm.get("enabled", False):
                return False
            
            # Проверяем время
            alarm_time = alarm.get("time", "07:30")
            
            # Только если время совпадает, делаем подробную проверку
            if current_time_str == alarm_time:
                alarm_might_trigger = True
                logger.info(f"🔍 ALARM CHECK {current_time_str} (time matches {alarm_time})")
                logger.info(f"  _alarm_active: {self._alarm_active}")
                logger.info(f"  _last_trigger_time: {self._last_trigger_time}")
                logger.info(f"  _snooze_until: {self._snooze_until}")
            
            # Срабатываем только когда время точно совпадает (с точностью до минуты)
            if current_time_str != alarm_time:
                return False
            
            # ДОБАВЛЕНО: Защита от множественного срабатывания в одну минуту
            if self._last_trigger_time == current_time_str:
                logger.info(f"⏸️ Alarm already triggered at {current_time_str}, SKIPPING")
                return False
            
            # Проверяем день недели
            repeat_days = alarm.get("repeat", [])
            if repeat_days:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                current_day = day_names[current_time.weekday()]
                logger.info(f"  current_day: {current_day}, repeat_days: {repeat_days}")
                
                if current_day not in repeat_days:
                    logger.info(f"❌ Day {current_day} not in repeat list, SKIPPING")
                    return False
            
            # Проверяем что будильник уже не активен
            if self._alarm_active:
                logger.info(f"❌ Alarm already active, SKIPPING")
                return False
            
            logger.info(f"✅ Alarm SHOULD trigger: {alarm_time} on {current_time.strftime('%A')}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking alarm trigger: {e}")
            return False
    
    def _trigger_alarm_popup(self):
        """Срабатывание будильника - показ попапа"""
        try:
            from kivy.app import App
            from kivy.clock import Clock
            
            current_time_str = datetime.now().strftime("%H:%M")
            logger.info(f"🚨 TRIGGERING ALARM at {current_time_str}")
            
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
            
            # Отмечаем что будильник активен и время последнего срабатывания
            self._alarm_active = True
            self._last_trigger_time = current_time_str
            logger.info(f"🔒 SET _last_trigger_time = {self._last_trigger_time}, _alarm_active = {self._alarm_active}")
            
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
                    self._last_trigger_time = None
            
            # Планируем создание попапа в главном потоке
            Clock.schedule_once(create_popup, 0)
            
        except Exception as e:
            logger.error(f"Error triggering alarm popup: {e}")
            self._alarm_active = False
            self._last_trigger_time = None
    
    def _force_stop_alarm_internal(self):
        """НОВЫЙ МЕТОД: Внутренняя остановка будильника БЕЗ закрытия попапа"""
        try:
            logger.info(f"🛑 FORCE STOPPING alarm (was active: {self._alarm_active}, last_trigger: {self._last_trigger_time})")
            
            # Останавливаем аудио
            from kivy.app import App
            app = App.get_running_app()
            
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
            
            # Сбрасываем флаги, но НЕ трогаем попап
            self._alarm_active = False
            self._snooze_until = None
            # НЕ СБРАСЫВАЕМ _last_trigger_time! Это предотвратит повторное срабатывание в ту же минуту
            self.alarm_popup = None  # Просто обнуляем ссылку
            
            logger.info(f"🔓 AFTER STOP: _alarm_active = {self._alarm_active}, _last_trigger_time = {self._last_trigger_time}")
            
        except Exception as e:
            logger.error(f"Error force-stopping alarm internally: {e}")
    
    def stop_alarm(self):
        """УСТАРЕВШИЙ МЕТОД: Оставлен для совместимости, просто вызывает внутренний метод"""
        logger.info("stop_alarm called (legacy)")
        self._force_stop_alarm_internal()
    
    def snooze_alarm(self, minutes=5):
        """Отложить будильник на указанное количество минут"""
        try:
            logger.info(f"Snoozing alarm for {minutes} minutes")
            
            # Останавливаем текущий будильник внутренне
            self._force_stop_alarm_internal()
            
            # Устанавливаем время отложенного срабатывания
            self._snooze_until = datetime.now() + timedelta(minutes=minutes)
            # Сбрасываем время последнего срабатывания чтобы snooze мог сработать
            self._last_trigger_time = None
            
            logger.info(f"Alarm snoozed until {self._snooze_until.strftime('%H:%M:%S')}")
            
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
    
    def get_status(self):
        """Получение статуса будильника для отображения в UI"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            # Базовый статус
            status = {
                "service_running": self.running,
                "alarm_active": self._alarm_active,
                "popup_open": self.alarm_popup is not None,
                "snooze_info": self.get_snooze_info(),
                "last_trigger_time": self._last_trigger_time
            }
            
            # Добавляем информацию о настройках будильника
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
                "alarm_enabled": False,
                "alarm_time": "--:--",
                "alarm_days": [],
                "ringtone": "",
                "snooze_info": {"active": False},
                "last_trigger_time": None,
                "error": str(e)
            }