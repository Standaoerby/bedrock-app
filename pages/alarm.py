from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.app import App
import os
from app.event_bus import event_bus
from app.logger import app_logger as logger

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ИСПРАВЛЕНИЕ: Константа для настройки дебаунсинга кнопок времени
TIME_BUTTON_DEBOUNCE_DELAY = 0.15  # 150ms между нажатиями

class AlarmScreen(Screen):
    """Экран настройки будильника"""
    
    # Основные свойства будильника
    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("robot.mp3")
    
    # ListProperty для значений спиннера (устанавливается один раз)
    ringtone_list = ListProperty(["robot.mp3"])
    
    alarm_fadein = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auto_save_event = None
        self._settings_changed = False
        self._sound_playing = False
        self._sound_check_event = None
        self._initialized = False
        
        # ИСПРАВЛЕНИЕ: Добавляем дебаунсинг для кнопок времени
        self._last_time_change = 0
        self._time_change_delay = TIME_BUTTON_DEBOUNCE_DELAY
        self._time_buttons_locked = False
        
        # Подписка на события
        event_bus.subscribe("theme_changed", self._on_theme_changed_delayed)
        event_bus.subscribe("language_changed", self.refresh_text)

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering AlarmScreen")
        try:
            Clock.schedule_once(lambda dt: self.stop_ringtone(), 0.2)
            self.load_ringtones()  # Устанавливает ringtone_list один раз
            self.load_alarm_config()
            self.update_ui()
            # Отложенная инициализация темы
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
            Clock.schedule_once(lambda dt: self.refresh_text(), 0.1)
            Clock.schedule_once(lambda dt: self._setup_ringtone_button(), 0.2)  # Настройка кнопки
            
            # ИСПРАВЛЕНИЕ: Информация о дебаунсинге для отладки
            logger.info(f"Time button debounce delay: {self._time_change_delay:.3f}s")
            
            # ДИАГНОСТИКА: Автоматическая проверка аудио-системы
            Clock.schedule_once(lambda dt: self.diagnose_audio_system(), 1.0)
            
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
            
            # Отменяем отложенные события
            if self._auto_save_event:
                self._auto_save_event.cancel()
                self._auto_save_event = None
            if self._sound_check_event:
                self._sound_check_event.cancel()
                self._sound_check_event = None
        except Exception as e:
            logger.error(f"Error in AlarmScreen.on_pre_leave: {e}")

    def _setup_ringtone_button(self):
        """Настройка кнопки выбора мелодии"""
        try:
            if not hasattr(self, 'ids') or 'ringtone_button' not in self.ids:
                return
                
            ringtone_button = self.ids.ringtone_button
            ringtone_button.values = self.ringtone_list
            ringtone_button.selected_value = self.selected_ringtone
            
            logger.debug("Ringtone button configured")
                
        except Exception as e:
            logger.error(f"Error setting up ringtone button: {e}")

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

    def _can_change_time(self):
        """Проверка возможности изменения времени (дебаунсинг)"""
        # ИСПРАВЛЕНИЕ: Двойная защита - временная блокировка + временной интервал
        if self._time_buttons_locked:
            logger.debug("Time change blocked - buttons locked")
            return False
            
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_time_change
        
        if time_since_last < self._time_change_delay:
            logger.debug(f"Time change blocked by debouncing (since last: {time_since_last:.3f}s, required: {self._time_change_delay:.3f}s)")
            return False
            
        self._last_time_change = current_time
        logger.debug(f"Time change allowed (since last: {time_since_last:.3f}s)")
        return True

    def _lock_time_buttons(self):
        """Временная блокировка кнопок времени"""
        self._time_buttons_locked = True
        Clock.schedule_once(lambda dt: setattr(self, '_time_buttons_locked', False), 0.1)

    def set_time_debounce_delay(self, delay_seconds):
        """Настройка задержки дебаунсинга для кнопок времени"""
        self._time_change_delay = max(0.05, min(1.0, delay_seconds))  # От 50ms до 1s
        logger.info(f"Time button debounce delay set to {self._time_change_delay:.3f}s")

    def _schedule_auto_save(self, delay=1.5):
        """Планирование автосохранения"""
        if self._auto_save_event:
            self._auto_save_event.cancel()
        self._settings_changed = True
        self._auto_save_event = Clock.schedule_once(lambda dt: self._auto_save(), delay)

    def _auto_save(self):
        """Автосохранение настроек - оптимизированное"""
        if self._settings_changed:
            try:
                # Сохраняем БЕЗ звуков и логирования для бесшовности
                app = App.get_running_app()
                if hasattr(app, 'alarm_service') and app.alarm_service:
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
                        logger.debug("Auto-saved alarm settings")
                        
            except Exception as e:
                logger.error(f"Error auto-saving alarm: {e}")
        
        # Очищаем событие
        self._auto_save_event = None

    def load_ringtones(self):
        """Загрузка списка мелодий будильника - устанавливает ringtone_list ОДИН РАЗ"""
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
                
            logger.debug(f"Loaded {len(self.ringtone_list)} ringtones: {self.ringtone_list}")
            
            # Проверяем файлы для отладки
            self._check_ringtone_files()
            
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
            
            # НЕ сбрасываем кнопку Play если звук играет
            if not self._sound_playing:
                self._reset_play_button()
            
            # Обновляем кнопку выбора мелодии
            if hasattr(self, 'ids') and 'ringtone_button' in self.ids:
                ringtone_button = self.ids.ringtone_button
                ringtone_button.values = self.ringtone_list
                ringtone_button.selected_value = self.selected_ringtone
            
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

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

    def _on_theme_changed_delayed(self, *args):
        """Асинхронная обработка смены темы"""
        # Отложенное обновление темы, чтобы не конфликтовать со спиннерами
        Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)

    # === ОБРАБОТЧИКИ СОБЫТИЙ UI ===

    def increment_hour(self):
        """Увеличение часа"""
        # ИСПРАВЛЕНИЕ: Дебаунсинг + блокировка для предотвращения множественных нажатий
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_hour = (int(hours) + 1) % 24
            self.alarm_time = f"{new_hour:02d}:{minutes}"
            if hasattr(self, 'ids') and 'hour_label' in self.ids:
                self.ids.hour_label.text = f"{new_hour:02d}"
            self._schedule_auto_save()
            logger.debug(f"Hour incremented to {new_hour:02d}")
        except Exception as e:
            logger.error(f"Error incrementing hour: {e}")

    def decrement_hour(self):
        """Уменьшение часа"""
        # ИСПРАВЛЕНИЕ: Дебаунсинг + блокировка для предотвращения множественных нажатий
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_hour = (int(hours) - 1) % 24
            self.alarm_time = f"{new_hour:02d}:{minutes}"
            if hasattr(self, 'ids') and 'hour_label' in self.ids:
                self.ids.hour_label.text = f"{new_hour:02d}"
            self._schedule_auto_save()
            logger.debug(f"Hour decremented to {new_hour:02d}")
        except Exception as e:
            logger.error(f"Error decrementing hour: {e}")

    def increment_minute(self):
        """Увеличение минут"""
        # ИСПРАВЛЕНИЕ: Дебаунсинг + блокировка для предотвращения множественных нажатий
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_minute = (int(minutes) + 1) % 60
            self.alarm_time = f"{hours}:{new_minute:02d}"
            if hasattr(self, 'ids') and 'minute_label' in self.ids:
                self.ids.minute_label.text = f"{new_minute:02d}"
            self._schedule_auto_save()
            logger.debug(f"Minute incremented to {new_minute:02d}")
        except Exception as e:
            logger.error(f"Error incrementing minute: {e}")

    def decrement_minute(self):
        """Уменьшение минут"""
        # ИСПРАВЛЕНИЕ: Дебаунсинг + блокировка для предотвращения множественных нажатий
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_sound("click")
        try:
            hours, minutes = self.alarm_time.split(':')
            new_minute = (int(minutes) - 1) % 60
            self.alarm_time = f"{hours}:{new_minute:02d}"
            if hasattr(self, 'ids') and 'minute_label' in self.ids:
                self.ids.minute_label.text = f"{new_minute:02d}"
            self._schedule_auto_save()
            logger.debug(f"Minute decremented to {new_minute:02d}")
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
        """Выбор мелодии - БЕЗ автоматического воспроизведения"""
        if name != self.selected_ringtone and name in self.ringtone_list:
            logger.debug(f"AlarmScreen.select_ringtone called with: {name}")
            
            # Останавливаем текущее воспроизведение если играет
            if self._sound_playing:
                self.stop_ringtone()
                self._reset_play_button()
            
            # Воспроизводим звук клика
            self._play_sound("click")
            
            # Обновляем выбранную мелодию
            old_ringtone = self.selected_ringtone
            self.selected_ringtone = name
            
            # Планируем автосохранение
            self._schedule_auto_save()
            
            logger.info(f"Ringtone changed from {old_ringtone} to {name}")

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
                logger.warning(f"Ringtone file not found: {path}")
                self._play_sound("error")
                self._reset_play_button()
                return

            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                fadein_time = 2.0 if self.alarm_fadein else 0
                app.audio_service.play(path, fadein=fadein_time)
                self._sound_playing = True
                self._start_sound_monitoring()
                logger.debug(f"Playing ringtone: {self.selected_ringtone}")
            else:
                logger.warning("Audio service not available")
                self._play_sound("error")
                self._reset_play_button()
        except Exception as e:
            logger.error(f"Error playing ringtone: {e}")
            self._play_sound("error")
            self._reset_play_button()

    def _start_sound_monitoring(self):
        """Запуск мониторинга воспроизведения звука"""
        logger.info("🔄 Starting sound monitoring...")
        if self._sound_check_event:
            self._sound_check_event.cancel()
        self._sound_check_event = Clock.schedule_interval(self._check_sound_status, 0.5)

    def _check_sound_status(self, dt):
        """Проверка статуса воспроизведения звука"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                # Проверяем, что аудио-сервис ещё воспроизводит звук
                is_busy = app.audio_service.is_busy()
                current_file = getattr(app.audio_service, 'current_file', None)
                
                logger.debug(f"🔍 Sound check: is_busy={is_busy}, current_file={current_file}, _sound_playing={self._sound_playing}")
                
                if not is_busy:
                    logger.info("🔇 Audio service reports sound finished")
                    self._on_sound_finished()
                    return False
                else:
                    logger.debug("🔊 Sound still playing...")
                    
            else:
                logger.warning("Audio service not available during sound check")
                self._on_sound_finished()
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error checking sound: {e}")
            self._on_sound_finished()
            return False

    def _check_ringtone_files(self):
        """Проверка доступности файлов мелодий для отладки"""
        try:
            folder = "media/ringtones"
            logger.info(f"🔍 Checking ringtone folder: {folder}")
            
            if not os.path.exists(folder):
                logger.warning(f"❌ Ringtone folder does not exist: {folder}")
                return
                
            files = os.listdir(folder)
            logger.info(f"📁 Files in ringtone folder: {files}")
            
            for ringtone in self.ringtone_list:
                path = os.path.join(folder, ringtone)
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                logger.info(f"🎵 Ringtone {ringtone}: exists={exists}, size={size} bytes")
                
        except Exception as e:
            logger.error(f"Error checking ringtone files: {e}")

    def diagnose_audio_system(self):
        """Полная диагностика аудио-системы для отладки"""
        logger.info("🔧 === AUDIO SYSTEM DIAGNOSIS ===")
        
        try:
            app = App.get_running_app()
            logger.info(f"App instance: {app}")
            
            # Проверка audio_service
            if hasattr(app, 'audio_service'):
                audio_service = app.audio_service
                logger.info(f"AudioService instance: {audio_service}")
                logger.info(f"AudioService type: {type(audio_service)}")
                
                if hasattr(audio_service, 'get_device_info'):
                    device_info = audio_service.get_device_info()
                    logger.info(f"Audio device info: {device_info}")
                
                logger.info(f"AudioService is_playing: {getattr(audio_service, 'is_playing', 'N/A')}")
                logger.info(f"AudioService current_file: {getattr(audio_service, 'current_file', 'N/A')}")
                logger.info(f"AudioService is_busy(): {audio_service.is_busy() if hasattr(audio_service, 'is_busy') else 'N/A'}")
                
            else:
                logger.error("❌ AudioService not found in app")
            
            # Проверка theme_manager (для звуков темы)
            if hasattr(app, 'theme_manager'):
                tm = app.theme_manager
                logger.info(f"ThemeManager instance: {tm}")
                if tm and hasattr(tm, 'get_sound'):
                    test_sound = tm.get_sound("click")
                    logger.info(f"Test theme sound path: {test_sound}")
                    if test_sound:
                        logger.info(f"Theme sound exists: {os.path.exists(test_sound)}")
            else:
                logger.error("❌ ThemeManager not found in app")
            
            # Проверка файлов мелодий
            self._check_ringtone_files()
            
            # Проверка состояния AlarmScreen
            logger.info(f"AlarmScreen _sound_playing: {self._sound_playing}")
            logger.info(f"AlarmScreen selected_ringtone: {self.selected_ringtone}")
            logger.info(f"AlarmScreen ringtone_list: {self.ringtone_list}")
            
        except Exception as e:
            logger.error(f"Error in audio system diagnosis: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        logger.info("🔧 === DIAGNOSIS COMPLETE ===")

    def test_ringtone_playback(self):
        """Тестовое воспроизведение мелодии с диагностикой"""
        logger.info("🧪 === TESTING RINGTONE PLAYBACK ===")
        
        # Сначала диагностика
        self.diagnose_audio_system()
        
        # Затем попытка воспроизведения
        logger.info("Attempting test playback...")
        self.play_ringtone()

    def _on_sound_finished(self):
        """Обработка завершения воспроизведения"""
        self._sound_playing = False
        self._reset_play_button()
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def stop_ringtone(self):
        """Остановка воспроизведения мелодии"""
        logger.info(f"=== STOPPING RINGTONE ===")
        logger.info(f"_sound_playing before stop: {self._sound_playing}")
        
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                audio_service = app.audio_service
                current_file = getattr(audio_service, 'current_file', None)
                is_busy = audio_service.is_busy()
                
                logger.info(f"Audio service current_file: {current_file}")
                logger.info(f"Audio service is_busy: {is_busy}")
                
                # Останавливаем только если это наша мелодия
                if (self._sound_playing and current_file and 'ringtones' in current_file):
                    logger.info("Stopping ringtone audio...")
                    audio_service.stop()
                    logger.info("Audio stopped")
                elif self._sound_playing:
                    logger.info("Stopping any audio (our flag says we're playing)...")
                    audio_service.stop()
                    logger.info("Audio stopped")
                else:
                    logger.info("Not stopping audio - _sound_playing=False")
                    
            else:
                logger.warning("Audio service not available for stop")
                
            # Сбрасываем состояние
            self._sound_playing = False
            if self._sound_check_event:
                self._sound_check_event.cancel()
                self._sound_check_event = None
                logger.info("Sound monitoring stopped")
                
            logger.info("✅ Ringtone stop completed")
            
        except Exception as e:
            logger.error(f"❌ Error stopping ringtone: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._sound_playing = False

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        if not self._initialized:
            return
            
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return
        
        try:
            # Список виджетов для обновления темы
            widgets = [
                "hour_label", "minute_label", "active_button", "fadein_button", 
                "play_button", "ringtone_button"
            ]
            
            for widget_id in widgets:
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    
                    if hasattr(widget, 'font_name'):
                        widget.font_name = tm.get_font("main")
                    if hasattr(widget, 'color'):
                        widget.color = tm.get_rgba("primary") if widget_id in ["hour_label", "minute_label"] else tm.get_rgba("text")
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