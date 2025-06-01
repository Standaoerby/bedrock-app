from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.app import App
from app.logger import app_logger as logger


class AlarmPopup(ModalView):
    def __init__(self, alarm_time="--:--", ringtone="", **kwargs):
        super().__init__(**kwargs)
        self.alarm_time = alarm_time
        self.ringtone = ringtone
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = False
        
        self._action = None
        
        # Основной контейнер
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Заголовок
        title_label = Label(
            text="ALARM!",
            font_size='48sp',
            size_hint_y=0.3,
            halign='center'
        )
        main_layout.add_widget(title_label)
        
        # Время будильника
        time_label = Label(
            text=f"Wake up! {self.alarm_time}",
            font_size='24sp',
            size_hint_y=0.2,
            halign='center'
        )
        main_layout.add_widget(time_label)
        
        # Кнопки
        button_layout = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=0.2)
        
        snooze_btn = Button(
            text="Snooze 5min",
            font_size='18sp',
            size_hint_x=0.5
        )
        snooze_btn.bind(on_release=self.on_snooze)
        button_layout.add_widget(snooze_btn)
        
        dismiss_btn = Button(
            text="Dismiss",
            font_size='18sp',
            size_hint_x=0.5
        )
        dismiss_btn.bind(on_release=self.on_dismiss_button)
        button_layout.add_widget(dismiss_btn)
        
        main_layout.add_widget(button_layout)
        self.add_widget(main_layout)

    def on_snooze(self, button):
        app = App.get_running_app()
        if hasattr(app, 'audio_service') and hasattr(app, 'theme_manager'):
            sound_file = app.theme_manager.get_sound("confirm")
            if sound_file:
                app.audio_service.play(sound_file)
        
        self._action = "snooze"
        self.dismiss()

    def on_dismiss_button(self, button):
        app = App.get_running_app()
        if hasattr(app, 'audio_service') and hasattr(app, 'theme_manager'):
            sound_file = app.theme_manager.get_sound("click")
            if sound_file:
                app.audio_service.play(sound_file)
        
        self._action = "dismiss"
        self.dismiss()

    def on_dismiss(self):
        try:
            app = App.get_running_app()
            
            if self._action == "snooze":
                if hasattr(app, 'alarm_clock') and app.alarm_clock:
                    app.alarm_clock.snooze_alarm(5)
            elif self._action == "dismiss":
                if hasattr(app, 'alarm_clock') and app.alarm_clock:
                    app.alarm_clock._force_stop_alarm_internal()
            else:
                if hasattr(app, 'alarm_clock') and app.alarm_clock:
                    app.alarm_clock._force_stop_alarm_internal()
            
        except Exception as e:
            logger.error(f"Error in on_dismiss: {e}")
        
        return False

    def open_alarm(self):
        app = App.get_running_app()
        if hasattr(app, 'audio_service'):
            try:
                import os
                
                if self.ringtone:
                    ringtone_path = os.path.join("media", "ringtones", self.ringtone)
                    if os.path.exists(ringtone_path):
                        app.audio_service.play(ringtone_path)
                    else:
                        self._play_fallback_sound(app)
                else:
                    self._play_fallback_sound(app)
                    
            except Exception as e:
                logger.error(f"Error playing alarm: {e}")
                self._play_fallback_sound(app)
        
        self.open()
    
    def _play_fallback_sound(self, app):
        try:
            if hasattr(app, 'theme_manager'):
                fallback_sound = app.theme_manager.get_sound("notify")
                if fallback_sound:
                    app.audio_service.play(fallback_sound)
        except Exception as e:
            logger.error(f"Error playing fallback sound: {e}")