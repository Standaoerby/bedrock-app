# services/alarm_popup.py
"""
ИСПРАВЛЕННЫЙ AlarmPopup - правильные пути к рингтонам
"""
import os
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.app import App
from kivy.clock import Clock
from app.logger import app_logger as logger


class AlarmPopup(ModalView):
    def __init__(self, alarm_time="--:--", ringtone="", **kwargs):
        super().__init__(**kwargs)
        self.alarm_time = alarm_time
        self.ringtone = ringtone
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = False
        
        logger.info(f"AlarmPopup created: {alarm_time}, ringtone: {ringtone}")
        
        self._build_ui()
        
        # Автоматическое закрытие через 10 минут
        self._auto_dismiss_event = Clock.schedule_once(self._auto_dismiss, 600)
    
    def _find_ringtone_path(self, ringtone_filename):
        """ИСПРАВЛЕНО: Поиск правильного пути к рингтону (как в alarm.py)"""
        if not ringtone_filename:
            logger.error("No ringtone filename provided")
            return None
            
        # Те же пути что использует alarm.py
        possible_paths = [
            f"assets/sounds/ringtones/{ringtone_filename}",
            f"sounds/ringtones/{ringtone_filename}",
            f"assets/ringtones/{ringtone_filename}",
            f"ringtones/{ringtone_filename}",
            f"media/ringtones/{ringtone_filename}"
        ]
        
        logger.debug(f"Searching for ringtone: {ringtone_filename}")
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"✅ Found ringtone: {path}")
                return path
            else:
                logger.debug(f"❌ Not found: {path}")
        
        logger.error(f"❌ Ringtone not found in any location: {ringtone_filename}")
        return None
    
    def _build_ui(self):
        """Создание интерфейса"""
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Заголовок
        title_label = Label(
            text="WAKE UP!",
            font_size='48sp',
            size_hint_y=0.3,
            halign='center',
            color=[1, 0.2, 0.2, 1]
        )
        main_layout.add_widget(title_label)
        
        # Время
        time_label = Label(
            text=f"",
            font_size='24sp',
            size_hint_y=0.3,
            halign='center'
        )
        main_layout.add_widget(time_label)
        
        # Кнопки
        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        
        stop_button = Button(
            text="STOP",
            background_color=[1, 0.2, 0.2, 1],
            font_size='20sp'
        )
        stop_button.bind(on_press=self._stop_alarm)
        button_layout.add_widget(stop_button)
        
        snooze_button = Button(
            text="SNOOZE",
            background_color=[1, 0.6, 0.2, 1],
            font_size='18sp'
        )
        snooze_button.bind(on_press=self._snooze_alarm)
        button_layout.add_widget(snooze_button)
        
        main_layout.add_widget(button_layout)
        self.add_widget(main_layout)
    
    def open_alarm(self):
        """Открытие popup и воспроизведение звука"""
        try:
            logger.info(f"🔔 Opening alarm popup: {self.alarm_time}")
            
            # ИСПРАВЛЕНО: Ищем правильный путь к рингтону
            ringtone_path = self._find_ringtone_path(self.ringtone)
            
            if ringtone_path:
                # Воспроизводим звук
                app = App.get_running_app()
                if hasattr(app, 'audio_service') and app.audio_service:
                    try:
                        logger.info(f"🎵 Playing ringtone: {ringtone_path}")
                        app.audio_service.play(ringtone_path, loop=True)
                        logger.info("✅ Ringtone playback started")
                    except Exception as audio_error:
                        logger.error(f"❌ Error playing ringtone: {audio_error}")
                else:
                    logger.warning("❌ Audio service not available")
            else:
                logger.error(f"❌ Cannot play ringtone - file not found: {self.ringtone}")
            
            # Открываем popup в любом случае
            self.open()
            logger.info("✅ Alarm popup opened")
            
        except Exception as e:
            logger.error(f"❌ Error opening alarm popup: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # В случае ошибки все равно показываем popup
            try:
                self.open()
                logger.info("⚠️ Alarm popup opened without sound")
            except:
                logger.error("💥 Failed to open popup at all")
    
    def _stop_alarm(self, instance):
        """Остановка будильника"""
        try:
            logger.info("🛑 Stop button pressed")
            
            # Получаем alarm_clock и останавливаем
            app = App.get_running_app()
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                app.alarm_clock.stop_alarm()
            else:
                # Fallback - останавливаем аудио и закрываем popup
                if hasattr(app, 'audio_service'):
                    app.audio_service.stop()
                self.dismiss()
                
        except Exception as e:
            logger.error(f"❌ Error stopping alarm: {e}")
            self.dismiss()
    
    def _snooze_alarm(self, instance):
        """Отложить будильник на 5 минут"""
        try:
            logger.info("😴 Snooze button pressed")
            
            # Получаем alarm_clock и откладываем
            app = App.get_running_app()
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                app.alarm_clock.snooze_alarm(5)
            else:
                # Fallback - просто останавливаем
                if hasattr(app, 'audio_service'):
                    app.audio_service.stop()
                self.dismiss()
                
        except Exception as e:
            logger.error(f"❌ Error snoozing alarm: {e}")
            self.dismiss()
    
    def _auto_dismiss(self, dt):
        """Автоматическое закрытие через 10 минут"""
        try:
            logger.info("⏰ Auto-dismissing alarm after 10 minutes")
            
            app = App.get_running_app()
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                app.alarm_clock.stop_alarm()
            else:
                if hasattr(app, 'audio_service'):
                    app.audio_service.stop()
                self.dismiss()
                
        except Exception as e:
            logger.error(f"❌ Error auto-dismissing alarm: {e}")
            self.dismiss()
    
    def dismiss(self, *args):
        """Переопределенное закрытие popup"""
        try:
            # Отменяем автоматическое закрытие
            if hasattr(self, '_auto_dismiss_event'):
                self._auto_dismiss_event.cancel()
            
            # Закрываем popup
            super().dismiss(*args)
            logger.info("❌ Alarm popup dismissed")
            
        except Exception as e:
            logger.error(f"❌ Error dismissing popup: {e}")
            super().dismiss(*args)