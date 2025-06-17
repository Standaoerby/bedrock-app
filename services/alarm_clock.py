# services/alarm_clock.py
"""
УЛУЧШЕННЫЙ AlarmClock - надежный будильник с расширенной диагностикой
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
        
        # НОВОЕ: Статистика и диагностика
        self._version = "2.1.1"
        self._instance_id = id(self)
        self._check_count = 0
        self._last_check_time = None
        self._last_alarm_config = None
        
        logger.info(f"AlarmClock v{self._version} initialized (ID: {self._instance_id})")
    
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
        
        logger.info(f"✅ AlarmClock v{self._version} started (thread: {self.thread.name})")
    
    def stop(self):
        """Остановка сервиса будильника"""
        if not self.running:
            return
        
        logger.info(f"Stopping AlarmClock v{self._version}...")
        self.running = False
        self._stop_event.set()
        
        # Останавливаем будильник если активен
        if self._alarm_active:
            self.stop_alarm()
        
        # Ждем завершения потока
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        logger.info(f"✅ AlarmClock v{self._version} stopped")
    
    def _alarm_check_loop(self):
        """Основной цикл проверки будильника"""
        logger.info("Alarm check loop started")
        
        while self.running and not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                self._check_count += 1
                self._last_check_time = current_time
                
                # Логируем каждую 10-ю проверку для диагностики
                if self._check_count % 10 == 0:
                    logger.debug(f"Alarm check #{self._check_count} at {current_time.strftime('%H:%M:%S')}")
                
                # Проверяем snooze
                if self._snooze_until and current_time >= self._snooze_until:
                    logger.info(f"⏰ Snooze time elapsed, re-triggering alarm")
                    self._snooze_until = None
                    self._trigger_alarm()
                    
                # Проверяем основной будильник
                elif not self._alarm_active and self._should_trigger_alarm():
                    self._trigger_alarm()
                
                # Ждем 30 секунд
                self._stop_event.wait(30)
                
            except Exception as e:
                logger.error(f"Error in alarm check loop: {e}")
                import traceback
                logger.error(f"Alarm check traceback: {traceback.format_exc()}")
                self._stop_event.wait(10)
        
        logger.info(f"Alarm check loop finished (total checks: {self._check_count})")
    
    def _should_trigger_alarm(self):
        """Проверка условий срабатывания будильника с диагностикой"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'alarm_service'):
                logger.debug("No alarm_service available")
                return False
            
            alarm = app.alarm_service.get_alarm()
            if not alarm:
                logger.debug("No alarm configuration found")
                return False
                
            if not alarm.get("enabled", False):
                logger.debug("Alarm is disabled")
                return False
            
            current_time = datetime.now()
            current_time_str = current_time.strftime("%H:%M")
            alarm_time = alarm.get("time", "07:30")
            
            # НОВОЕ: Кэшируем конфигурацию для сравнения изменений
            current_config = {
                "time": alarm_time,
                "enabled": alarm.get("enabled", False),
                "repeat": alarm.get("repeat", [])
            }
            
            if self._last_alarm_config != current_config:
                logger.info(f"📋 Alarm config changed: {current_config}")
                self._last_alarm_config = current_config
            
            if current_time_str != alarm_time:
                # Логируем только каждую минуту чтобы не спамить
                if current_time.second < 30:
                    logger.debug(f"⏱️ Current: {current_time_str}, Target: {alarm_time}")
                return False
            
            # Проверяем дни недели
            repeat_days = alarm.get("repeat", [])
            if repeat_days:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                current_day = day_names[current_time.weekday()]
                if current_day not in repeat_days:
                    logger.info(f"⏸️ Alarm skipped - wrong day: {current_day} not in {repeat_days}")
                    return False
                else:
                    logger.info(f"✅ Alarm day match: {current_day} in {repeat_days}")
            
            logger.info(f"🚨 ALARM TRIGGER CONDITION MET: {alarm_time} on {current_time.strftime('%A')}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking alarm trigger: {e}")
            return False
    
    def _trigger_alarm(self):
        """Запуск будильника с улучшенной диагностикой"""
        try:
            if self._alarm_active:
                logger.warning("Alarm already active, skipping trigger")
                return
            
            self._alarm_active = True
            
            # Получаем данные будильника
            app = App.get_running_app()
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                logger.error("Cannot trigger alarm - alarm_service not available")
                self._alarm_active = False
                return
                
            alarm = app.alarm_service.get_alarm()
            if not alarm:
                logger.error("Cannot trigger alarm - no alarm configuration")
                self._alarm_active = False
                return
                
            alarm_time = alarm.get("time", "--:--")
            ringtone = alarm.get("ringtone", "Bathtime In Clerkenwell.mp3")
            
            logger.info(f"🚨 TRIGGERING ALARM: time={alarm_time}, ringtone={ringtone}")
            
            # Создаем popup в главном потоке
            Clock.schedule_once(
                lambda dt: self._create_alarm_popup(alarm_time, ringtone), 0
            )
            
            logger.info("🔔 Alarm popup scheduled for main thread")
            
        except Exception as e:
            logger.error(f"Error triggering alarm: {e}")
            import traceback
            logger.error(f"Alarm trigger traceback: {traceback.format_exc()}")
            self._alarm_active = False
    
    def _create_alarm_popup(self, alarm_time, ringtone):
        """Создание popup будильника в главном потоке"""
        try:
            from services.alarm_popup import AlarmPopup
            
            logger.info(f"📱 Creating alarm popup: {alarm_time}, {ringtone}")
            
            self.alarm_popup = AlarmPopup(
                alarm_time=alarm_time,
                ringtone=ringtone
            )
            
            self.alarm_popup.open_alarm()
            logger.info("✅ Alarm popup opened successfully")
            
        except Exception as e:
            logger.error(f"Error creating alarm popup: {e}")
            import traceback
            logger.error(f"Alarm popup traceback: {traceback.format_exc()}")
            self._alarm_active = False
            
            # Пытаемся хотя бы воспроизвести звук как fallback
            try:
                logger.info("🔊 Attempting fallback audio playback")
                app = App.get_running_app()
                if hasattr(app, 'audio_service') and app.audio_service:
                    app.audio_service.play(f"ringtones/{ringtone}")
                    logger.info("✅ Fallback audio started")
                else:
                    logger.error("❌ No audio_service available for fallback")
            except Exception as audio_error:
                logger.error(f"❌ Fallback audio failed: {audio_error}")
    
    def stop_alarm(self):
        """Остановка будильника"""
        if not self._alarm_active:
            logger.debug("No active alarm to stop")
            return
        
        logger.info("🛑 Stopping alarm...")
        
        try:
            # Останавливаем аудио
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
                logger.info("🔇 Alarm audio stopped")
            
            # Закрываем popup
            if self.alarm_popup:
                self.alarm_popup.dismiss()
                self.alarm_popup = None
                logger.info("❌ Alarm popup dismissed")
            
            self._alarm_active = False
            self._snooze_until = None
            
            logger.info("✅ Alarm stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping alarm: {e}")
            # Принудительно сбрасываем состояние
            self._alarm_active = False
            self._snooze_until = None
            self.alarm_popup = None
    
    def snooze_alarm(self, minutes=5):
        """Отложить будильник"""
        if not self._alarm_active:
            logger.warning("No active alarm to snooze")
            return
        
        logger.info(f"😴 Snoozing alarm for {minutes} minutes")
        
        # Останавливаем текущий будильник
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
            
            # Закрываем popup
            if self.alarm_popup:
                self.alarm_popup.dismiss()
                self.alarm_popup = None
            
            # Устанавливаем время снова разбудить
            self._snooze_until = datetime.now() + timedelta(minutes=minutes)
            self._alarm_active = False
            
            logger.info(f"💤 Alarm snoozed until {self._snooze_until.strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Error snoozing alarm: {e}")
            # В случае ошибки просто останавливаем
            self.stop_alarm()
    
    def get_status(self):
        """НОВОЕ: Получение текущего статуса для диагностики"""
        status = {
            "version": self._version,
            "instance_id": self._instance_id,
            "running": self.running,
            "alarm_active": self._alarm_active,
            "check_count": self._check_count,
            "last_check": self._last_check_time.strftime('%H:%M:%S') if self._last_check_time else None,
            "snooze_until": self._snooze_until.strftime('%H:%M:%S') if self._snooze_until else None,
            "last_config": self._last_alarm_config,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }
        return status
    
    def diagnose(self):
        """НОВОЕ: Полная диагностика состояния AlarmClock"""
        logger.info("🔧 === ALARM CLOCK DIAGNOSTIC ===")
        
        status = self.get_status()
        for key, value in status.items():
            logger.info(f"[{key:15}] {value}")
            
        # Проверяем доступность зависимостей
        app = App.get_running_app()
        
        alarm_service_available = hasattr(app, 'alarm_service') and app.alarm_service is not None
        audio_service_available = hasattr(app, 'audio_service') and app.audio_service is not None
        
        logger.info(f"[alarm_service   ] {'✅ Available' if alarm_service_available else '❌ Missing'}")
        logger.info(f"[audio_service   ] {'✅ Available' if audio_service_available else '❌ Missing'}")
        
        if alarm_service_available:
            try:
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    logger.info(f"[alarm_config    ] time={alarm.get('time')}, enabled={alarm.get('enabled')}")
                else:
                    logger.info(f"[alarm_config    ] ❌ No configuration")
            except Exception as e:
                logger.info(f"[alarm_config    ] ❌ Error: {e}")
        
        logger.info("🔧 === END DIAGNOSTIC ===")
        
        return status