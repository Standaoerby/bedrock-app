from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.app import App
import os
import time
import logging

logger = logging.getLogger("AlarmScreen")

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def play_theme_sound(name):
    app = App.get_running_app()
    if hasattr(app, "theme_manager") and hasattr(app, "audio_service"):
        path = app.theme_manager.get_sound(name)
        if path:
            app.audio_service.play(path)

class AlarmScreen(Screen):
    """Экран настройки будильника"""

    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("morning.mp3")
    ringtone_list = ListProperty([])
    alarm_fadein = BooleanProperty(False)
    current_sound = ObjectProperty(None, allownone=True)

    _last_button_press = 0
    _button_debounce_time = 0.5  # 500ms защита от повторных нажатий
    _sound_playing = False
    _button_processing = False

    def on_pre_enter(self, *args):
        logger.info("Entering AlarmScreen")
        self.stop_ringtone()
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()

    def load_ringtones(self):
        folder = "media/ringtones"
        if os.path.exists(folder):
            try:
                self.ringtone_list = [f for f in os.listdir(folder)
                    if f.lower().endswith((".mp3", ".ogg", ".wav"))]
                if self.selected_ringtone not in self.ringtone_list and self.ringtone_list:
                    self.selected_ringtone = self.ringtone_list[0]
                logger.info(f"Loaded {len(self.ringtone_list)} ringtones")
            except Exception as e:
                logger.error(f"Error loading ringtones: {e}")
                self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]
        else:
            try:
                os.makedirs(folder, exist_ok=True)
                logger.info(f"Created ringtones folder: {folder}")
            except Exception as e:
                logger.error(f"Failed to create ringtones folder: {e}")
            self.ringtone_list = ["morning.mp3", "gentle.mp3", "loud.mp3", "robot.mp3"]

    def load_alarm_config(self):
        app = App.get_running_app()
        alarm = app.alarm_service.get_alarm()
        if alarm:
            self.alarm_time = alarm.get("time", "07:30")
            self.alarm_active = alarm.get("enabled", True)
            repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
            if repeat and all(isinstance(x, int) for x in repeat):
                days_map = DAYS_EN
                self.alarm_repeat = [days_map[i-1] for i in repeat if 1 <= i <= 7]
            else:
                self.alarm_repeat = repeat
            self.selected_ringtone = alarm.get("ringtone", self.selected_ringtone)
            self.alarm_fadein = alarm.get("fadein", False)
            logger.info(f"Loaded alarm config: {alarm}")

    def save_alarm(self):
        play_theme_sound("success")
        app = App.get_running_app()
        alarm = {
            "time": self.alarm_time,
            "enabled": self.alarm_active,
            "repeat": self.alarm_repeat,
            "ringtone": self.selected_ringtone,
            "fadein": self.alarm_fadein,
        }
        app.alarm_service.set_alarm(alarm)
        logger.info(f"Saved alarm config: {alarm}")
        self.update_ui()

    def update_ui(self):
        # Update hours and minutes
        hours, minutes = self.alarm_time.split(':')
        if 'hour_label' in self.ids:
            self.ids.hour_label.text = hours
        if 'minute_label' in self.ids:
            self.ids.minute_label.text = minutes

        # Update the active button
        if 'active_button' in self.ids:
            active_button = self.ids.active_button
            active_button.text = "ON" if self.alarm_active else "OFF"
            app = App.get_running_app()
            if self.alarm_active:
                active_button.color = app.theme_manager.get_rgba("primary")
            else:
                active_button.color = app.theme_manager.get_rgba("text_secondary")

        # Update fadein button
        if 'fadein_button' in self.ids:
            fadein_button = self.ids.fadein_button
            fadein_button.text = "ON" if self.alarm_fadein else "OFF"
            app = App.get_running_app()
            if self.alarm_fadein:
                fadein_button.color = app.theme_manager.get_rgba("primary")
            else:
                fadein_button.color = app.theme_manager.get_rgba("text_secondary")

        # Update day buttons
        for day in DAYS_EN:
            btn_id = f"repeat_{day.lower()}"
            if btn_id in self.ids:
                button = self.ids[btn_id]
                button.state = "down" if day in self.alarm_repeat else "normal"

        # Update ringtone spinner
        if 'ringtone_spinner' in self.ids:
            self.ids.ringtone_spinner.text = self.selected_ringtone

        self._reset_play_button()

    def _reset_play_button(self):
        if 'play_button' in self.ids:
            play_button = self.ids.play_button
            play_button.state = 'normal'
            play_button.text = 'Play'
            self._sound_playing = False
            self._button_processing = False

    def increment_hour(self):
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) + 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        if 'hour_label' in self.ids:
            self.ids.hour_label.text = f"{new_hour:02d}"

    def decrement_hour(self):
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) - 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        if 'hour_label' in self.ids:
            self.ids.hour_label.text = f"{new_hour:02d}"

    def increment_minute(self):
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) + 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        if 'minute_label' in self.ids:
            self.ids.minute_label.text = f"{new_minute:02d}"

    def decrement_minute(self):
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) - 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        if 'minute_label' in self.ids:
            self.ids.minute_label.text = f"{new_minute:02d}"

    def on_active_toggled(self, active):
        if active and not self.alarm_active:
            play_theme_sound("success")
        self.alarm_active = active
        self.update_ui()

    def toggle_repeat(self, day, state):
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)

    def select_ringtone(self, name):
        self.selected_ringtone = name
        self.stop_ringtone()
        self._reset_play_button()

    def toggle_play_ringtone(self, state):
        current_time = time.time()
        if current_time - self._last_button_press < self._button_debounce_time:
            return
        if self._button_processing:
            return
        self._last_button_press = current_time
        self._button_processing = True
        try:
            play_theme_sound("click")
            if state == 'down' and not self._sound_playing:
                if 'play_button' in self.ids:
                    self.ids.play_button.text = 'Stop'
                self.play_ringtone()
            elif state == 'normal' and self._sound_playing:
                if 'play_button' in self.ids:
                    self.ids.play_button.text = 'Play'
                self.stop_ringtone()
            else:
                self._sync_button_state()
        except Exception:
            self._reset_play_button()
        finally:
            Clock.schedule_once(lambda dt: setattr(self, '_button_processing', False), 0.1)

    def _sync_button_state(self):
        if 'play_button' not in self.ids:
            return
        play_button = self.ids.play_button
        actual_playing = self.current_sound and hasattr(self.current_sound, 'state') and self.current_sound.state != 'stop'
        if actual_playing != self._sound_playing:
            self._sound_playing = actual_playing
        if self._sound_playing:
            play_button.state = 'down'
            play_button.text = 'Stop'
        else:
            play_button.state = 'normal'
            play_button.text = 'Play'

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
            self.current_sound = app.sound_service.load_sound_file(path)
            if self.current_sound and hasattr(self.current_sound, '_sound') and self.current_sound._sound:
                self.current_sound.volume = 0.7
                self.current_sound.play()
                self._sound_playing = True
                self._schedule_sound_check()
            else:
                play_theme_sound("error")
                self._reset_play_button()
        except Exception:
            play_theme_sound("error")
            self._reset_play_button()

    def _schedule_sound_check(self):
        Clock.schedule_interval(self._check_sound_status, 0.5)

    def _check_sound_status(self, dt):
        try:
            if not self.current_sound:
                self._on_sound_finished()
                return False
            if hasattr(self.current_sound, 'state'):
                if self.current_sound.state == 'stop':
                    self._on_sound_finished()
                    return False
            return True
        except Exception:
            self._on_sound_finished()
            return False

    def _on_sound_finished(self):
        self._sound_playing = False
        self._reset_play_button()

    def stop_ringtone(self):
        try:
            if self.current_sound:
                if hasattr(self.current_sound, 'stop') and hasattr(self.current_sound, 'state'):
                    if self.current_sound.state != 'stop':
                        self.current_sound.stop()
                self.current_sound = None
            self._sound_playing = False
        except Exception:
            self.current_sound = None
            self._sound_playing = False

    def on_fadein_toggled(self, active):
        if active and not self.alarm_fadein:
            play_theme_sound("success")
        self.alarm_fadein = active
        self.update_ui()

    def on_leave(self, *args):
        logger.info("Leaving alarm screen")
        self.stop_ringtone()
        self._reset_play_button()
        super().on_leave()
        logger.info("Alarm screen cleanup completed")
