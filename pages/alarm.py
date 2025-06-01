from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.app import App
import os
import time
from app.logger import app_logger as logger

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def play_theme_sound(name):
    try:
        app = App.get_running_app()
        if hasattr(app, "theme_manager") and hasattr(app, "audio_service"):
            path = app.theme_manager.get_sound(name)
            if path and os.path.exists(path):
                app.audio_service.play(path)
    except Exception as e:
        logger.error(f"Error playing sound {name}: {e}")

class AlarmScreen(Screen):
    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("robot.mp3")
    ringtone_list = ListProperty([])
    alarm_fadein = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auto_save_event = None
        self._settings_changed = False
        self._sound_playing = False
        self._sound_check_event = None

    def on_pre_enter(self, *args):
        Clock.schedule_once(lambda dt: self.stop_ringtone(), 0.2)
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()
        self.refresh_theme()
        self.refresh_text()

    def on_pre_leave(self, *args):
        if self._settings_changed:
            self.save_alarm(silent=True)
        self.stop_ringtone()
        self._reset_play_button()
        if self._auto_save_event:
            self._auto_save_event.cancel()
            self._auto_save_event = None
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def refresh_theme(self, *args):
        app = App.get_running_app()
        if not hasattr(app, 'theme_manager'):
            return
        tm = app.theme_manager
        widgets = [
            "hour_label", "minute_label", "active_button", "fadein_button", "play_button",
            "ringtone_spinner"
        ]
        for w in widgets:
            if hasattr(self, 'ids') and w in self.ids:
                widget = self.ids[w]
                if hasattr(widget, 'font_name'):
                    widget.font_name = tm.get_font("main")
                if hasattr(widget, 'color'):
                    widget.color = tm.get_rgba("primary_text")
                if hasattr(widget, 'background_normal'):
                    widget.background_normal = tm.get_image("button_bg")
                    widget.background_down = tm.get_image("button_bg_active")

    def refresh_text(self, *args):
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
        lz = app.localizer
        if hasattr(self, 'ids'):
            if 'active_button' in self.ids:
                self.ids.active_button.text = lz.t("alarm_on") if self.alarm_active else lz.t("alarm_off")
            if 'fadein_button' in self.ids:
                self.ids.fadein_button.text = lz.t("fadein_on") if self.alarm_fadein else lz.t("fadein_off")
            if 'play_button' in self.ids:
                self.ids.play_button.text = lz.t("play")
            if 'ringtone_spinner' in self.ids:
                self.ids.ringtone_spinner.text = self.selected_ringtone

    def _schedule_auto_save(self, delay=1.5):
        if self._auto_save_event:
            self._auto_save_event.cancel()
        self._settings_changed = True
        self._auto_save_event = Clock.schedule_once(
            lambda dt: self._auto_save(), delay
        )

    def _auto_save(self):
        if self._settings_changed:
            self.save_alarm(silent=True)
            self._settings_changed = False

    def load_ringtones(self):
        folder = "media/ringtones"
        try:
            os.makedirs(folder, exist_ok=True)
            if os.path.exists(folder):
                files = [f for f in os.listdir(folder)
                        if f.lower().endswith((".mp3", ".ogg", ".wav"))]
                if files:
                    self.ringtone_list = files
                    if self.selected_ringtone not in self.ringtone_list:
                        self.selected_ringtone = self.ringtone_list[0]
                else:
                    self.ringtone_list = ["robot.mp3", "morning.mp3", "gentle.mp3", "loud.mp3"]
                    self.selected_ringtone = "robot.mp3"
            else:
                self.ringtone_list = ["robot.mp3", "morning.mp3", "gentle.mp3", "loud.mp3"]
                self.selected_ringtone = "robot.mp3"
        except Exception as e:
            logger.error(f"Error loading ringtones: {e}")
            self.ringtone_list = ["robot.mp3", "morning.mp3", "gentle.mp3", "loud.mp3"]
            self.selected_ringtone = "robot.mp3"

    def load_alarm_config(self):
        app = App.get_running_app()
        if not hasattr(app, 'alarm_service'):
            return
        try:
            alarm = app.alarm_service.get_alarm()
            if alarm:
                self.alarm_time = alarm.get("time", "07:30")
                self.alarm_active = alarm.get("enabled", True)
                repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
                if repeat and all(isinstance(x, int) for x in repeat):
                    self.alarm_repeat = [DAYS_EN[i-1] for i in repeat if 1 <= i <= 7]
                else:
                    self.alarm_repeat = repeat if repeat else ["Mon", "Tue", "Wed", "Thu", "Fri"]
                self.selected_ringtone = alarm.get("ringtone", "robot.mp3")
                self.alarm_fadein = alarm.get("fadein", False)
        except Exception as e:
            logger.error(f"Error loading alarm config: {e}")

    def save_alarm(self, silent=False):
        if not silent:
            play_theme_sound("confirm")
        app = App.get_running_app()
        if not hasattr(app, 'alarm_service'):
            if not silent:
                play_theme_sound("error")
            return False
        try:
            alarm = {
                "time": self.alarm_time,
                "enabled": self.alarm_active,
                "repeat": self.alarm_repeat,
                "ringtone": self.selected_ringtone,
                "fadein": self.alarm_fadein,
            }
            success = app.alarm_service.set_alarm(alarm)
            if success:
                self._settings_changed = False
            return success
        except Exception as e:
            logger.error(f"Error saving alarm: {e}")
            if not silent:
                play_theme_sound("error")
            return False

    def update_ui(self):
        try:
            hours, minutes = self.alarm_time.split(':')
            if 'hour_label' in self.ids:
                self.ids.hour_label.text = hours
            if 'minute_label' in self.ids:
                self.ids.minute_label.text = minutes
            if 'active_button' in self.ids:
                active_button = self.ids.active_button
                app = App.get_running_app()
                if hasattr(app, 'localizer'):
                    active_button.text = app.localizer.t("alarm_on") if self.alarm_active else app.localizer.t("alarm_off")
                else:
                    active_button.text = "ON" if self.alarm_active else "OFF"
                active_button.state = "down" if self.alarm_active else "normal"
            if 'fadein_button' in self.ids:
                fadein_button = self.ids.fadein_button
                app = App.get_running_app()
                if hasattr(app, 'localizer'):
                    fadein_button.text = app.localizer.t("fadein_on") if self.alarm_fadein else app.localizer.t("fadein_off")
                else:
                    fadein_button.text = "ON" if self.alarm_fadein else "OFF"
                fadein_button.state = "down" if self.alarm_fadein else "normal"
            for day in DAYS_EN:
                btn_id = f"repeat_{day.lower()}"
                if btn_id in self.ids:
                    button = self.ids[btn_id]
                    button.state = "down" if day in self.alarm_repeat else "normal"
            if 'ringtone_spinner' in self.ids:
                self.ids.ringtone_spinner.text = self.selected_ringtone
            self._reset_play_button()
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

    def _reset_play_button(self):
        if 'play_button' in self.ids:
            play_button = self.ids.play_button
            app = App.get_running_app()
            if hasattr(app, 'localizer'):
                play_button.text = app.localizer.t("play")
            else:
                play_button.text = 'Play'
            play_button.state = 'normal'
        self._sound_playing = False

    def increment_hour(self):
        play_theme_sound("click")
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) + 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        if 'hour_label' in self.ids:
            self.ids.hour_label.text = f"{new_hour:02d}"
        self._schedule_auto_save()

    def decrement_hour(self):
        play_theme_sound("click")
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) - 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        if 'hour_label' in self.ids:
            self.ids.hour_label.text = f"{new_hour:02d}"
        self._schedule_auto_save()

    def increment_minute(self):
        play_theme_sound("click")
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) + 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        if 'minute_label' in self.ids:
            self.ids.minute_label.text = f"{new_minute:02d}"
        self._schedule_auto_save()

    def decrement_minute(self):
        play_theme_sound("click")
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) - 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        if 'minute_label' in self.ids:
            self.ids.minute_label.text = f"{new_minute:02d}"
        self._schedule_auto_save()

    def on_active_toggled(self, active):
        if active != self.alarm_active:
            play_theme_sound("confirm" if active else "click")
            self.alarm_active = active
            self.update_ui()
            self._schedule_auto_save()

    def toggle_repeat(self, day, state):
        play_theme_sound("click")
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
            self._schedule_auto_save()
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)
            self._schedule_auto_save()

    def select_ringtone(self, name):
        if name != self.selected_ringtone:
            play_theme_sound("click")
            self.selected_ringtone = name
            self.stop_ringtone()
            self._reset_play_button()
            self._schedule_auto_save()

    def toggle_play_ringtone(self, state):
        try:
            play_theme_sound("click")
            if state == 'down' and not self._sound_playing:
                if 'play_button' in self.ids:
                    app = App.get_running_app()
                    if hasattr(app, 'localizer'):
                        self.ids.play_button.text = app.localizer.t("stop")
                    else:
                        self.ids.play_button.text = 'Stop'
                self.play_ringtone()
            else:
                if 'play_button' in self.ids:
                    app = App.get_running_app()
                    if hasattr(app, 'localizer'):
                        self.ids.play_button.text = app.localizer.t("play")
                    else:
                        self.ids.play_button.text = 'Play'
                self.stop_ringtone()
        except Exception as e:
            logger.error(f"Error toggling ringtone: {e}")
            self._reset_play_button()

    def play_ringtone(self):
        self.stop_ringtone()
        try:
            folder = "media/ringtones"
            path = os.path.join(folder, self.selected_ringtone)
            if not os.path.exists(path):
                play_theme_sound("error")
                self._reset_play_button()
                return
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                fadein_time = 2.0 if self.alarm_fadein else 0
                app.audio_service.play(path, fadein=fadein_time)
                self._sound_playing = True
                self._start_sound_monitoring()
            else:
                play_theme_sound("error")
                self._reset_play_button()
        except Exception as e:
            logger.error(f"Error playing ringtone: {e}")
            play_theme_sound("error")
            self._reset_play_button()

    def _start_sound_monitoring(self):
        if self._sound_check_event:
            self._sound_check_event.cancel()
        self._sound_check_event = Clock.schedule_interval(self._check_sound_status, 0.5)

    def _check_sound_status(self, dt):
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                if not app.audio_service.is_busy():
                    self._on_sound_finished()
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking sound: {e}")
            self._on_sound_finished()
            return False

    def _on_sound_finished(self):
        self._sound_playing = False
        self._reset_play_button()
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def stop_ringtone(self):
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                if (self._sound_playing and 
                    hasattr(app.audio_service, 'current_file') and 
                    app.audio_service.current_file and
                    'ringtones' in app.audio_service.current_file):
                    app.audio_service.stop()
            self._sound_playing = False
            if self._sound_check_event:
                self._sound_check_event.cancel()
                self._sound_check_event = None
        except Exception as e:
            logger.error(f"Error stopping ringtone: {e}")
            self._sound_playing = False

    def on_fadein_toggled(self, active):
        if active != self.alarm_fadein:
            play_theme_sound("confirm" if active else "click")
            self.alarm_fadein = active
            self.update_ui()
            self._schedule_auto_save()

    def test_alarm_sound(self):
        try:
            app = App.get_running_app()
            play_theme_sound("confirm")
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                ringtone = self.selected_ringtone
                fadein = self.alarm_fadein
                app.alarm_clock.trigger_alarm(ringtone=ringtone, fadein=fadein)
            else:
                play_theme_sound("error")
        except Exception as e:
            logger.error(f"Error testing alarm: {e}")
            play_theme_sound("error")
