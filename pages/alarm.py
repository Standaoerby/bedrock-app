from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.app import App
import os
import time
from app.logger import app_logger as logger

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def play_theme_sound(name):
    """Воспроизведение звука темы"""
    try:
        app = App.get_running_app()
        if hasattr(app, "theme_manager") and hasattr(app, "audio_service"):
            path = app.theme_manager.get_sound(name)
            if path and os.path.exists(path):
                app.audio_service.play(path)
    except Exception as e:
        logger.error(f"Error playing theme sound {name}: {e}")

class AlarmScreen(Screen):
    """Экран настройки будильника"""

    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("robot.mp3")
    ringtone_list = ListProperty([])
    alarm_fadein = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Защита от повторных действий
        self._last_button_press = 0
        self._button_debounce_time = 0.3  # Уменьшено с 0.5
        
        # Состояние звука
        self._sound_playing = False
        self._button_processing = False
        self._sound_check_event = None
        
        # Автосохранение
        self._auto_save_event = None
        self._settings_changed = False
        self._last_save_time = 0

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering AlarmScreen")
        # НЕ вызываем _reset_state() сразу - это останавливает звук клика из меню
        Clock.schedule_once(lambda dt: self._reset_state_delayed(), 0.2)
        self.load_ringtones()
        self.load_alarm_config()
        self.update_ui()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        logger.info("Leaving AlarmScreen")
        self._cleanup()

    def _reset_state(self):
        """Сброс состояния экрана"""
        # НЕ останавливаем звук сразу - может играть звук клика из меню
        self._sound_playing = False
        self._button_processing = False
        self._settings_changed = False
        
        # Отменяем все отложенные события
        if self._auto_save_event:
            self._auto_save_event.cancel()
            self._auto_save_event = None
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def _reset_state_delayed(self):
        """Отложенный сброс состояния - останавливаем только рингтоны"""
        self.stop_ringtone()  # Теперь можно безопасно остановить рингтоны
        self._reset_play_button()

    def _cleanup(self):
        """Очистка ресурсов при выходе"""
        # Финальное сохранение если есть изменения
        if self._settings_changed:
            self.save_alarm(silent=True)
        
        self.stop_ringtone()
        self._reset_play_button()
        
        # Отменяем все события
        if self._auto_save_event:
            self._auto_save_event.cancel()
            self._auto_save_event = None
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def _schedule_auto_save(self, delay=1.5):
        """Запланировать автосохранение с задержкой"""
        # Отменяем предыдущее автосохранение
        if self._auto_save_event:
            self._auto_save_event.cancel()
        
        # Отмечаем что есть изменения
        self._settings_changed = True
        
        # Планируем новое автосохранение
        self._auto_save_event = Clock.schedule_once(
            lambda dt: self._auto_save(), delay
        )

    def _auto_save(self):
        """Автоматическое сохранение"""
        if self._settings_changed:
            self.save_alarm(silent=True)
            self._settings_changed = False
            self._last_save_time = time.time()

    def _can_perform_action(self):
        """Проверка возможности выполнения действия"""
        current_time = time.time()
        if current_time - self._last_button_press < self._button_debounce_time:
            return False
        if self._button_processing:
            return False
        return True

    def _mark_action_performed(self):
        """Отметка выполнения действия"""
        self._last_button_press = time.time()

    def load_ringtones(self):
        """Загрузка списка мелодий"""
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
                logger.info(f"Loaded {len(self.ringtone_list)} ringtones")
            else:
                self.ringtone_list = ["robot.mp3", "morning.mp3", "gentle.mp3", "loud.mp3"]
                self.selected_ringtone = "robot.mp3"
                
        except Exception as e:
            logger.error(f"Error loading ringtones: {e}")
            self.ringtone_list = ["robot.mp3", "morning.mp3", "gentle.mp3", "loud.mp3"]
            self.selected_ringtone = "robot.mp3"

    def load_alarm_config(self):
        """Загрузка конфигурации будильника"""
        app = App.get_running_app()
        if not hasattr(app, 'alarm_service'):
            logger.error("AlarmService not found")
            return
            
        try:
            alarm = app.alarm_service.get_alarm()
            if alarm:
                self.alarm_time = alarm.get("time", "07:30")
                self.alarm_active = alarm.get("enabled", True)
                
                # Обработка дней недели
                repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
                if repeat and all(isinstance(x, int) for x in repeat):
                    self.alarm_repeat = [DAYS_EN[i-1] for i in repeat if 1 <= i <= 7]
                else:
                    self.alarm_repeat = repeat if repeat else ["Mon", "Tue", "Wed", "Thu", "Fri"]
                    
                self.selected_ringtone = alarm.get("ringtone", "robot.mp3")
                self.alarm_fadein = alarm.get("fadein", False)
                logger.info(f"Loaded alarm config: {alarm}")
        except Exception as e:
            logger.error(f"Error loading alarm config: {e}")

    def save_alarm(self, silent=False):
        """Сохранение настроек будильника"""
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
                if not silent:
                    logger.info(f"Saved alarm config: {alarm}")
                else:
                    logger.debug(f"Auto-saved alarm config")
            return success
        except Exception as e:
            logger.error(f"Error saving alarm: {e}")
            if not silent:
                play_theme_sound("error")
            return False

    def update_ui(self):
        """Обновление интерфейса"""
        try:
            # Обновляем часы и минуты
            hours, minutes = self.alarm_time.split(':')
            if 'hour_label' in self.ids:
                self.ids.hour_label.text = hours
            if 'minute_label' in self.ids:
                self.ids.minute_label.text = minutes

            # Обновляем кнопку активации
            if 'active_button' in self.ids:
                active_button = self.ids.active_button
                active_button.text = "ON" if self.alarm_active else "OFF"
                active_button.state = "down" if self.alarm_active else "normal"

            # Обновляем кнопку fadein
            if 'fadein_button' in self.ids:
                fadein_button = self.ids.fadein_button
                fadein_button.text = "ON" if self.alarm_fadein else "OFF"
                fadein_button.state = "down" if self.alarm_fadein else "normal"

            # Обновляем кнопки дней недели
            for day in DAYS_EN:
                btn_id = f"repeat_{day.lower()}"
                if btn_id in self.ids:
                    button = self.ids[btn_id]
                    button.state = "down" if day in self.alarm_repeat else "normal"

            # Обновляем спиннер мелодий
            if 'ringtone_spinner' in self.ids:
                self.ids.ringtone_spinner.text = self.selected_ringtone

            self._reset_play_button()
            
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

    def _reset_play_button(self):
        """Сброс кнопки воспроизведения"""
        if 'play_button' in self.ids:
            play_button = self.ids.play_button
            play_button.state = 'normal'
            play_button.text = 'Play'
        self._sound_playing = False
        self._button_processing = False

    def increment_hour(self):
        """Увеличение часов"""
        if not self._can_perform_action():
            return
        
        self._mark_action_performed()
        play_theme_sound("click")
        
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) + 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        
        if 'hour_label' in self.ids:
            self.ids.hour_label.text = f"{new_hour:02d}"
        
        # Запланировать автосохранение
        self._schedule_auto_save()

    def decrement_hour(self):
        """Уменьшение часов"""
        if not self._can_perform_action():
            return
            
        self._mark_action_performed()
        play_theme_sound("click")
        
        hours, minutes = self.alarm_time.split(':')
        new_hour = (int(hours) - 1) % 24
        self.alarm_time = f"{new_hour:02d}:{minutes}"
        
        if 'hour_label' in self.ids:
            self.ids.hour_label.text = f"{new_hour:02d}"
        
        # Запланировать автосохранение
        self._schedule_auto_save()

    def increment_minute(self):
        """Увеличение минут"""
        if not self._can_perform_action():
            return
            
        self._mark_action_performed()
        play_theme_sound("click")
        
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) + 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        
        if 'minute_label' in self.ids:
            self.ids.minute_label.text = f"{new_minute:02d}"
        
        # Запланировать автосохранение
        self._schedule_auto_save()

    def decrement_minute(self):
        """Уменьшение минут"""
        if not self._can_perform_action():
            return
            
        self._mark_action_performed()
        play_theme_sound("click")
        
        hours, minutes = self.alarm_time.split(':')
        new_minute = (int(minutes) - 1) % 60
        self.alarm_time = f"{hours}:{new_minute:02d}"
        
        if 'minute_label' in self.ids:
            self.ids.minute_label.text = f"{new_minute:02d}"
        
        # Запланировать автосохранение
        self._schedule_auto_save()

    def on_active_toggled(self, active):
        """Переключение активности будильника"""
        if active != self.alarm_active:
            play_theme_sound("confirm" if active else "click")
            self.alarm_active = active
            self.update_ui()
            self._schedule_auto_save()

    def toggle_repeat(self, day, state):
        """Переключение дня недели"""
        play_theme_sound("click")
        day = day.capitalize()
        
        if state == "down" and day not in self.alarm_repeat:
            self.alarm_repeat.append(day)
            self._schedule_auto_save()
        elif state == "normal" and day in self.alarm_repeat:
            self.alarm_repeat.remove(day)
            self._schedule_auto_save()

    def select_ringtone(self, name):
        """Выбор мелодии"""
        if name != self.selected_ringtone:
            play_theme_sound("click")
            self.selected_ringtone = name
            self.stop_ringtone()
            self._reset_play_button()
            self._schedule_auto_save()

    def toggle_play_ringtone(self, state):
        """Переключение воспроизведения мелодии"""
        if not self._can_perform_action():
            return
            
        self._mark_action_performed()
        self._button_processing = True
        
        try:
            play_theme_sound("click")
            
            if state == 'down' and not self._sound_playing:
                # Запуск воспроизведения
                if 'play_button' in self.ids:
                    self.ids.play_button.text = 'Stop'
                self.play_ringtone()
            else:
                # Остановка воспроизведения
                if 'play_button' in self.ids:
                    self.ids.play_button.text = 'Play'
                self.stop_ringtone()
                
        except Exception as e:
            logger.error(f"Error toggling ringtone: {e}")
            self._reset_play_button()
        finally:
            # Сбрасываем флаг processing через небольшую задержку
            Clock.schedule_once(lambda dt: setattr(self, '_button_processing', False), 0.1)

    def play_ringtone(self):
        """Воспроизведение мелодии"""
        self.stop_ringtone()  # Останавливаем любое текущее воспроизведение
        
        try:
            folder = "media/ringtones"
            path = os.path.join(folder, self.selected_ringtone)
            
            if not os.path.exists(path):
                logger.warning(f"Ringtone file not found: {path}")
                play_theme_sound("error")
                self._reset_play_button()
                return
                
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                fadein_time = 2.0 if self.alarm_fadein else 0
                app.audio_service.play(path, fadein=fadein_time)
                self._sound_playing = True
                
                # Запускаем проверку статуса воспроизведения
                self._start_sound_monitoring()
            else:
                logger.error("AudioService not available")
                play_theme_sound("error")
                self._reset_play_button()
                
        except Exception as e:
            logger.error(f"Error playing ringtone: {e}")
            play_theme_sound("error")
            self._reset_play_button()

    def _start_sound_monitoring(self):
        """Запуск мониторинга воспроизведения"""
        # Отменяем предыдущий мониторинг
        if self._sound_check_event:
            self._sound_check_event.cancel()
        
        # Запускаем новый мониторинг
        self._sound_check_event = Clock.schedule_interval(self._check_sound_status, 0.5)

    def _check_sound_status(self, dt):
        """Проверка статуса воспроизведения"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                if not app.audio_service.is_busy():
                    self._on_sound_finished()
                    return False  # Останавливаем таймер
            return True  # Продолжаем проверку
        except Exception as e:
            logger.error(f"Error checking sound status: {e}")
            self._on_sound_finished()
            return False

    def _on_sound_finished(self):
        """Обработка окончания воспроизведения"""
        self._sound_playing = False
        self._reset_play_button()
        
        # Останавливаем мониторинг
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def stop_ringtone(self):
        """Остановка воспроизведения мелодии"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service'):
                # Проверяем что сейчас играет именно рингтон, а не короткий звук
                if (self._sound_playing and 
                    hasattr(app.audio_service, 'current_file') and 
                    app.audio_service.current_file and
                    'ringtones' in app.audio_service.current_file):
                    app.audio_service.stop()
                    logger.debug("Stopped ringtone playback")
            
            self._sound_playing = False
            
            # Останавливаем мониторинг
            if self._sound_check_event:
                self._sound_check_event.cancel()
                self._sound_check_event = None
                
        except Exception as e:
            logger.error(f"Error stopping ringtone: {e}")
            self._sound_playing = False

    def on_fadein_toggled(self, active):
        """Переключение плавного появления звука"""
        if active != self.alarm_fadein:
            play_theme_sound("confirm" if active else "click")
            self.alarm_fadein = active
            self.update_ui()
            self._schedule_auto_save()

    def test_alarm_sound(self):
        """Тестирование срабатывания будильника"""
        if not self._can_perform_action():
            return
            
        self._mark_action_performed()
        
        try:
            app = App.get_running_app()
            
            # Воспроизводим звук подтверждения
            play_theme_sound("confirm")
            
            # Тестируем срабатывание будильника через AlarmClock
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                # Используем текущие настройки для теста
                ringtone = self.selected_ringtone
                fadein = self.alarm_fadein
                
                app.alarm_clock.trigger_alarm(ringtone=ringtone, fadein=fadein)
                logger.info(f"Test alarm triggered with {ringtone}, fadein: {fadein}")
            else:
                logger.error("AlarmClock not available for testing")
                play_theme_sound("error")
                
        except Exception as e:
            logger.error(f"Error testing alarm: {e}")
            play_theme_sound("error")

    def on_leave(self, *args):
        """Обработка выхода с экрана"""
        logger.info("Alarm screen cleanup completed")
        super().on_leave()