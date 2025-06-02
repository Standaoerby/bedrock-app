from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.app import App
import os
from app.event_bus import event_bus
from app.logger import app_logger as logger

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

class AlarmScreen(Screen):
    """Экран настройки будильника"""
    
    # Основные свойства будильника
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
        self._initialized = False
        
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme)
        event_bus.subscribe("language_changed", self.refresh_text)

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering AlarmScreen")
        try:
            Clock.schedule_once(lambda dt: self.stop_ringtone(), 0.2)
            self.load_ringtones()
            self.load_alarm_config()
            self.update_ui()
            self.refresh_theme()
            self.refresh_text()
            self._initialized = True
        except Exception as e:
            logger.error(f"Error in AlarmScreen.on_pre_enter: {e}")

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        try:
            if self._settings_changed:
                self.save_alarm(silent=True)
            self.stop_ringtone()
            self._reset_play_button()
            self._cleanup_spinners()
            
            # Отменяем отложенные события
            if self._auto_save_event:
                self._auto_save_event.cancel()
                self._auto_save_event = None
            if self._sound_check_event:
                self._sound_check_event.cancel()
                self._sound_check_event = None
        except Exception as e:
            logger.error(f"Error in AlarmScreen.on_pre_leave: {e}")

    def _cleanup_spinners(self):
        """Очистка Spinner виджетов для предотвращения ошибок DropDown"""
        try:
            if hasattr(self, 'ids') and 'ringtone_spinner' in self.ids:
                spinner = self.ids.ringtone_spinner
                if hasattr(spinner, '_dropdown') and spinner._dropdown:
                    try:
                        if spinner._dropdown.parent:
                            spinner._dropdown.parent.remove_widget(spinner._dropdown)
                        spinner._dropdown.dismiss()
                        spinner.is_open = False
                    except Exception as e:
                        logger.warning(f"Error cleaning up ringtone spinner: {e}")
        except Exception as e:
            logger.error(f"Error in _cleanup_spinners: {e}")

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in AlarmScreen")
        return None

    def _play_sound(self, sound_name):
        """Воспроизведение звука темы"""
        try:
            app = App.get_running_app()
            if hasattr(app, "theme_manager") and hasattr(app, "audio_service"):
                path = app.theme_manager.get_sound(sound_name)
                if path and os.path.exists(path):
                    app.audio_service.play(path)
        except Exception as e:
            logger.error(f"Error playing sound {sound_name}: {e}")

    def _schedule_auto_save(self, delay=1.5):
        """Планирование автосохранения"""
        if self._auto_save_event:
            self._auto_save_event.cancel()
        self._settings_changed = True
        self._auto_save_event = Clock.schedule_once(lambda dt: self._auto_save(), delay)

    def _auto_save(self):
        """Автосохранение настроек"""
        if self._settings_changed:
            self.save_alarm(silent=True)
            self._settings_changed = False

    def load_ringtones(self):
        """Загрузка списка мелодий будильника"""
        folder = "media/ringtones"
        try:
            os.makedirs(folder, exist_ok=True)
            if os.path.exists(folder):
                files = [f for f in os.listdir(folder)
                        if f.lower().endswith((".mp3", ".ogg", ".wav"))]
                if files:
                    self.ringtone_list = sorted(files)
                    if self.selected_ringtone not in self.ringtone_list:
                        self.selected_ringtone = self.ringtone_list[0]
                else:
                    # Fallback мелодии если папка пуста
                    self.ringtone_list = ["robot.mp3", "morning.mp3", "gentle.mp3", "loud.mp3"]
                    self.selected_ringtone = "robot.mp3"
            else:
                self.ringtone_list = ["robot.mp3", "morning.mp3", "gentle.mp3", "loud.mp3"]
                self.selected_ringtone = "robot.mp3"
                
            logger.debug(f"Loaded {len(self.ringtone_list)} ringtones")
        except Exception as e:
            logger.error(f"Error loading ringtones: {e}")
            self.ringtone_list = ["robot.mp3"]
            self.selected_ringtone = "robot.mp3"

    def load_alarm_config(self):
        """Загрузка конфигурации будильника"""
        app = App.get_running_app()
        if not hasattr(app, 'alarm_service') or not app.alarm_service:
            return
            
        try:
            alarm = app.alarm_service.get_alarm()
            if alarm:
                self.alarm_time = alarm.get("time", "07:30")
                self.alarm_active = alarm.get("enabled", True)
                
                # Обработка дней недели (поддерживаем старый формат с числами)
                repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
                if repeat and all(isinstance(x, int) for x in repeat):
                    # Конвертируем числа в названия дней
                    self.alarm_repeat = [DAYS_EN[i-1] for i in repeat if 1 <= i <= 7]
                else:
                    self.alarm_repeat = repeat if repeat else ["Mon", "Tue", "Wed", "Thu", "Fri"]
                
                self.selected_ringtone = alarm.get("ringtone", "robot.mp3")
                self.alarm_fadein = alarm.get("fadein", False)
                
                logger.info(f"Loaded alarm config: {self.alarm_time}, active: {self.alarm_active}")
        except Exception as e:
            logger.error(f"Error loading alarm config: {e}")

    def save_alarm(self, silent=False):
        """Сохранение настроек будильника"""
        if not silent:
            self._play_sound("confirm")
            
        app = App.get_running_app()
        if not hasattr(app, 'alarm_service') or not app.alarm_service:
            if not silent:
                self._play_sound("error")
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
                if not silent:
                    logger.info("Alarm settings saved successfully")
            return success
        except Exception as e:
            logger.error(f"Error saving alarm: {e}")
            if not silent:
                self._play_sound("error")
            return False

    def update_ui(self):
        """Обновление интерфейса после изменения данных"""
        try:
            # Обновляем время
            if ":" in self.alarm_time:
                hours, minutes = self.alarm_time.split(':')
                if hasattr(self, 'ids'):
                    if 'hour_label' in self.ids:
                        self.ids.hour_label.text = hours
                    if 'minute_label' in self.ids:
                        self.ids.minute_label.text = minutes

            self._update_toggle_buttons()
            self._update_day_buttons()
            self._reset_play_button()
            
            # Обновляем spinner, если он существует
            Clock.schedule_once(lambda dt: self._update_spinner(), 0.1)
            
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

    def _update_spinner(self):
        """Безопасное обновление спиннера"""
        try:
            if hasattr(self, 'ids') and 'ringtone_spinner' in self.ids:
                spinner = self.ids.ringtone_spinner
                if self.ringtone_list and self.selected_ringtone in self.ringtone_list:
                    spinner.values = self.ringtone_list
                    spinner.text = self.selected_ringtone
        except Exception as e:
            logger.error(f"Error updating spinner: {e}")

    def _update_toggle_buttons(self):
        """Обновление кнопок переключения"""
        app = App.get_running_app()
        
        # Кнопка включения будильника
        if hasattr(self, 'ids') and 'active_button' in self.ids:
            active_button = self.ids.active_button
            active_button.text = "ON" if self.alarm_active else "OFF"
            active_button.state = "down" if self.alarm_active else "normal"

        # Кнопка fade-in
        if hasattr(self, 'ids') and 'fadein_button' in self.ids:
            fadein_button = self.ids.fadein_button
            fadein_button.text = "ON" if self.alarm_fadein else "OFF"
            fadein_button.state = "down" if self.alarm_fadein else "normal"

    def _update_day_buttons(self):
        """Обновление кнопок дней недели"""
        if not hasattr(self, 'ids'):
            return
            
        for day in DAYS_EN:
            btn_id = f"repeat_{day.lower()}"
            if btn_id in self.ids:
                button = self.ids[btn_id]
                button.state = "down" if day in self.alarm_repeat else "normal"

    def _reset_play_button(self):
        """Сброс кнопки воспроизведения"""
        if hasattr(self, 'ids') and 'play_button' in self.ids:
            play_button = self.ids.play_button
            play_button.text = 'Play'
            play_button.state = 'normal'
        self._sound_playing = False

    # === ОБРАБОТЧИКИ СОБЫТИЙ UI ===

    def increment_hour(self):
        """Увеличение часа"""
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_hour = (int(hours) + 1) % 24
            self.alarm_time = f"{new_hour:02d}:{minutes}"
            if hasattr(self, 'ids') and 'hour_label' in self.ids:
                self.ids.hour_label.text = f"{new_hour:02d}"
            self._schedule_auto_save()
        except Exception as e:
            logger.error(f"Error incrementing hour: {e}")

    def decrement_hour(self):
        """Уменьшение часа"""
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_hour = (int(hours) - 1) % 24
            self.alarm_time = f"{new_hour:02d}:{minutes}"
            if hasattr(self, 'ids') and 'hour_label' in self.ids:
                self.ids.hour_label.text = f"{new_hour:02d}"
            self._schedule_auto_save()
        except Exception as e:
            logger.error(f"Error decrementing hour: {e}")

    def increment_minute(self):
        """Увеличение минут"""
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_minute = (int(minutes) + 1) % 60
            self.alarm_time = f"{hours}:{new_minute:02d}"
            if hasattr(self, 'ids') and 'minute_label' in self.ids:
                self.ids.minute_label.text = f"{new_minute:02d}"
            self._schedule_auto_save()
        except Exception as e:
            logger.error(f"Error incrementing minute: {e}")

    def decrement_minute(self):
        """Уменьшение минут"""
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_minute = (int(minutes) - 1) % 60
            self.alarm_time = f"{hours}:{new_minute:02d}"
            if hasattr(self, 'ids') and 'minute_label' in self.ids:
                self.ids.minute_label.text = f"{new_minute:02d}"
            self._schedule_auto_save()
        except Exception as e:
            logger.error(f"Error decrementing minute: {e}")

    def on_active_toggled(self, active):
        """Переключение активности будильника"""
        if active != self.alarm_active:
            self._play_sound("confirm" if active else "click")
            self.alarm_active = active
            self._update_toggle_buttons()
            self._schedule_auto_save()

    def toggle_repeat(self, day, state):
        """Переключение дня недели"""
        self._play_sound("click")
        day = day.capitalize()
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
            self._schedule_auto_save()
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)
            self._schedule_auto_save()

    def on_fadein_toggled(self, active):
        """Переключение fade-in"""
        if active != self.alarm_fadein:
            self._play_sound("confirm" if active else "click")
            self.alarm_fadein = active
            self._update_toggle_buttons()
            self._schedule_auto_save()

    def select_ringtone(self, name):
        """Выбор мелодии"""
        if name != self.selected_ringtone and name in self.ringtone_list:
            self._play_sound("click")
            self.selected_ringtone = name
            self.stop_ringtone()
            self._reset_play_button()
            self._schedule_auto_save()
            logger.debug(f"Selected ringtone: {name}")

    def toggle_play_ringtone(self, state):
        """Переключение воспроизведения мелодии"""
        try:
            self._play_sound("click")
            if state == 'down' and not self._sound_playing:
                if hasattr(self, 'ids') and 'play_button' in self.ids:
                    self.ids.play_button.text = 'Stop'
                self.play_ringtone()
            else:
                if hasattr(self, 'ids') and 'play_button' in self.ids:
                    self.ids.play_button.text = 'Play'
                self.stop_ringtone()
        except Exception as e:
            logger.error(f"Error toggling ringtone: {e}")
            self._reset_play_button()

    def play_ringtone(self):
        """Воспроизведение выбранной мелодии"""
        self.stop_ringtone()
        try:
            folder = "media/ringtones"
            path = os.path.join(folder, self.selected_ringtone)
            if not os.path.exists(path):
                self._play_sound("error")
                self._reset_play_button()
                return

            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                fadein_time = 2.0 if self.alarm_fadein else 0
                app.audio_service.play(path, fadein=fadein_time)
                self._sound_playing = True
                self._start_sound_monitoring()
                logger.debug(f"Playing ringtone: {self.selected_ringtone}")
            else:
                self._play_sound("error")
                self._reset_play_button()
        except Exception as e:
            logger.error(f"Error playing ringtone: {e}")
            self._play_sound("error")
            self._reset_play_button()

    def _start_sound_monitoring(self):
        """Запуск мониторинга воспроизведения звука"""
        if self._sound_check_event:
            self._sound_check_event.cancel()
        self._sound_check_event = Clock.schedule_interval(self._check_sound_status, 0.5)

    def _check_sound_status(self, dt):
        """Проверка статуса воспроизведения звука"""
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
        """Обработка завершения воспроизведения"""
        self._sound_playing = False
        self._reset_play_button()
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def stop_ringtone(self):
        """Остановка воспроизведения мелодии"""
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

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        if not self._initialized:
            return
            
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return
        
        try:
            widgets = [
                "hour_label", "minute_label", "active_button", "fadein_button", 
                "play_button", "ringtone_spinner"
            ]
            
            for widget_id in widgets:
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    
                    if hasattr(widget, 'font_name'):
                        widget.font_name = tm.get_font("main")
                    if hasattr(widget, 'color'):
                        widget.color = tm.get_rgba("primary")
                    if hasattr(widget, 'background_normal'):
                        widget.background_normal = tm.get_image("button_bg")
                        widget.background_down = tm.get_image("button_bg_active")
        except Exception as e:
            logger.error(f"Error refreshing theme: {e}")

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        if not self._initialized:
            return
        # Обновляем тексты кнопок
        self._update_toggle_buttons()