# pages/alarm.py - ПОЛНОЕ ИСПРАВЛЕНИЕ с консистентностью
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.app import App
import os
import time
from app.event_bus import event_bus
from app.logger import app_logger as logger
import threading

DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ИСПРАВЛЕНИЕ: Константы для дебаунсинга
TIME_BUTTON_DEBOUNCE_DELAY = 0.25   # 250ms между нажатиями времени  
TOGGLE_BUTTON_DEBOUNCE_DELAY = 0.30 # 300ms для toggle кнопок

class AlarmScreen(Screen):
    """Экран настройки будильника"""
    
    # Основные свойства будильника
    alarm_time = StringProperty("07:30")
    alarm_active = BooleanProperty(True)
    alarm_repeat = ListProperty(["Mon", "Tue", "Wed", "Thu", "Fri"])
    selected_ringtone = StringProperty("Bathtime In Clerkenwell.mp3")
    
    # ListProperty для значений спиннера (устанавливается один раз)
    ringtone_list = ListProperty(["Bathtime In Clerkenwell.mp3"])
    
    alarm_fadein = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auto_save_event = None
        self._settings_changed = False
        self._sound_playing = False
        self._sound_check_event = None
        self._initialized = False
        
        # ИСПРАВЛЕНИЕ: Добавляем дебаунсинг для всех типов кнопок
        self._last_time_change = 0
        self._time_change_delay = TIME_BUTTON_DEBOUNCE_DELAY
        self._time_buttons_locked = False
        
        self._last_toggle_change = 0
        self._toggle_change_delay = TOGGLE_BUTTON_DEBOUNCE_DELAY
        self._toggle_buttons_locked = False
        
        # Подписка на события
        event_bus.subscribe("theme_changed", self._on_theme_changed_delayed)
        event_bus.subscribe("language_changed", self.refresh_text)

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран - ИСПРАВЛЕНО"""
        logger.info("Entering AlarmScreen")
        try:
            Clock.schedule_once(lambda dt: self.stop_ringtone(), 0.2)
            self.load_ringtones()
            
            # ИСПРАВЛЕНО: Сначала пытаемся загрузить из сервиса, затем из файла
            if not self.load_alarm_from_service():
                logger.info("Service load failed, loading from config file")
                self.load_alarm_config()
            
            self.update_ui()
            # Отложенная инициализация темы
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
            Clock.schedule_once(lambda dt: self.refresh_text(), 0.1)
            Clock.schedule_once(lambda dt: self._setup_ringtone_button(), 0.2)
            
            logger.info(f"Time button debounce delay: {self._time_change_delay:.3f}s")
            logger.info(f"Toggle button debounce delay: {self._toggle_change_delay:.3f}s")
            
            # ДИАГНОСТИКА: Автоматическая проверка аудио-системы
            Clock.schedule_once(lambda dt: self.test_audio_system(), 1.0)
            event_bus.subscribe("alarm_changed", self._on_alarm_changed)
            self._initialized = True
        except Exception as e:
            logger.error(f"Error in AlarmScreen.on_pre_enter: {e}")

    def load_alarm_from_service(self):
        """НОВОЕ: Загрузка настроек будильника из alarm_service"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                logger.warning("alarm_service not available for loading")
                return False
            
            alarm = app.alarm_service.get_alarm()
            if not alarm:
                logger.warning("No alarm configuration found in service")
                return False
            
            # Загружаем настройки
            self.alarm_time = alarm.get("time", "07:30")
            self.alarm_active = alarm.get("enabled", False)
            self.alarm_repeat = alarm.get("repeat", ["Mon", "Tue", "Wed", "Thu", "Fri"])
            self.selected_ringtone = alarm.get("ringtone", "Bathtime In Clerkenwell.mp3")
            self.alarm_fadein = alarm.get("fadein", False)
            
            # Проверяем что выбранный рингтон существует в списке
            if self.selected_ringtone not in self.ringtone_list:
                logger.warning(f"Selected ringtone '{self.selected_ringtone}' not in available list")
                if self.ringtone_list:
                    self.selected_ringtone = self.ringtone_list[0]
                    logger.info(f"Reset ringtone to: {self.selected_ringtone}")
            
            logger.info(f"Alarm loaded from service: {self.alarm_time}, enabled={self.alarm_active}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading alarm from service: {e}")
            return False

    def save_alarm_via_service(self, silent=False):
        """НОВОЕ: Сохранение через alarm_service"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                logger.warning("alarm_service not available, using file save")
                return self.save_alarm_config_original(silent)
            
            # Формируем конфигурацию
            config = {
                'time': self.alarm_time,
                'enabled': self.alarm_active,
                'repeat': list(self.alarm_repeat),
                'ringtone': self.selected_ringtone,
                'fadein': self.alarm_fadein
            }
            
            # Сохраняем через alarm_service
            success = app.alarm_service.set_alarm(config)
            
            if success:
                logger.info(f"Alarm config saved via service: {self.alarm_time}")
                if not silent:
                    self._play_sound("confirm")
                return True
            else:
                logger.error("Failed to save via service, trying file save")
                return self.save_alarm_config_original(silent)
                
        except Exception as e:
            logger.error(f"Error saving via service: {e}")
            # Fallback к оригинальному методу
            return self.save_alarm_config_original(silent)

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        try:
            if self._settings_changed:
                self.save_alarm_config(silent=True)
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
        try:
            event_bus.unsubscribe("alarm_changed", self._on_alarm_changed)
        except Exception as e:
            logger.error(f"Error unsubscribing from alarm_changed: {e}")

    # ========================================
    # ИСПРАВЛЕНО: Методы времени соответствуют KV файлу
    # ========================================
    
    def increment_hour(self):
        """Увеличение часа - СООТВЕТСТВУЕТ alarm.kv"""
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_click_sound()
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
        """Уменьшение часа - СООТВЕТСТВУЕТ alarm.kv"""
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_click_sound()
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
        """Увеличение минут - СООТВЕТСТВУЕТ alarm.kv"""
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_click_sound()
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
        """Уменьшение минут - СООТВЕТСТВУЕТ alarm.kv"""
        if not self._can_change_time():
            return
            
        self._lock_time_buttons()
        self._play_click_sound()
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

    # ========================================
    # ИСПРАВЛЕНО: Toggle методы соответствуют KV файлу
    # ========================================
    
    def _on_alarm_changed(self, event_data):
        """НОВОЕ: Обработчик изменений настроек будильника из других источников"""
        try:
            # Игнорируем события от самой страницы alarm
            source = event_data.get("source", "")
            if source in ["set_alarm", "update_api"]:
                logger.debug("Ignoring alarm change from self")
                return
                
            # Обновляем UI если данные изменились извне (например, через toggle на главной)
            alarm = event_data.get("alarm", {})
            if alarm:
                old_time = self.alarm_time
                old_active = self.alarm_active
                
                self.alarm_time = alarm.get("time", self.alarm_time)
                self.alarm_active = alarm.get("enabled", self.alarm_active)
                self.alarm_repeat = alarm.get("repeat", self.alarm_repeat)
                self.selected_ringtone = alarm.get("ringtone", self.selected_ringtone)
                self.alarm_fadein = alarm.get("fadein", self.alarm_fadein)
                
                # Обновляем UI если что-то изменилось
                if old_time != self.alarm_time or old_active != self.alarm_active:
                    self.update_ui()
                    logger.debug(f"Alarm UI updated from external change (source: {source})")
                
        except Exception as e:
            logger.error(f"Error handling alarm change event: {e}")

    def on_active_toggled(self, active):
        """Переключение активности будильника - СООТВЕТСТВУЕТ alarm.kv"""
        if not self._can_change_toggle():
            return
            
        self._lock_toggle_buttons()
        
        try:
            if active != self.alarm_active:
                self._play_sound("confirm" if active else "click")
                self.alarm_active = active
                self._update_toggle_buttons()
                self._schedule_auto_save()
                logger.info(f"Alarm {'activated' if active else 'deactivated'}")
        except Exception as e:
            logger.error(f"Error toggling alarm active: {e}")

    def on_fadein_toggled(self, active):
        """Переключение fade-in - СООТВЕТСТВУЕТ alarm.kv"""
        if not self._can_change_toggle():
            return
            
        self._lock_toggle_buttons()
        
        try:
            if active != self.alarm_fadein:
                self._play_sound("confirm" if active else "click")
                self.alarm_fadein = active
                self._update_toggle_buttons()
                self._schedule_auto_save()
                logger.info(f"Alarm fade-in {'enabled' if active else 'disabled'}")
        except Exception as e:
            logger.error(f"Error toggling alarm fadein: {e}")

    def toggle_repeat(self, day, state):
        """Переключение дня недели - СООТВЕТСТВУЕТ alarm.kv"""
        if not self._can_change_toggle():
            return
            
        self._lock_toggle_buttons()
        
        try:
            self._play_click_sound()
            day = day.capitalize()
            
            # Создаем новый список для избежания проблем с привязкой
            new_repeat = list(self.alarm_repeat)
            
            if state == "down" and day not in new_repeat:
                new_repeat.append(day)
                logger.info(f"Added {day} to alarm repeat")
            elif state == "normal" and day in new_repeat:
                new_repeat.remove(day)
                logger.info(f"Removed {day} from alarm repeat")
            
            # Обновляем только если изменилось
            if new_repeat != self.alarm_repeat:
                self.alarm_repeat = new_repeat
                self._schedule_auto_save()
                
        except Exception as e:
            logger.error(f"Error toggling repeat for {day}: {e}")

    def toggle_play_ringtone(self, state):
        """Переключение воспроизведения мелодии - СООТВЕТСТВУЕТ alarm.kv"""
        logger.info(f"🎮 Toggle play ringtone: state={state}, current _sound_playing={self._sound_playing}")
        
        try:
            if state == 'down' and not self._sound_playing:
                logger.info("▶️ Starting ringtone playback...")
                if hasattr(self, 'ids') and 'play_button' in self.ids:
                    self.ids.play_button.text = 'Stop'
                self.play_ringtone()
            else:
                logger.info("⏹️ Stopping ringtone playback...")
                if hasattr(self, 'ids') and 'play_button' in self.ids:
                    self.ids.play_button.text = 'Play'
                    self.ids.play_button.state = 'normal'
                self.stop_ringtone()
                
        except Exception as e:
            logger.error(f"❌ Error toggling ringtone: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._reset_play_button()

    # ========================================
    # МЕТОДЫ ДЕБАУНСИНГА
    # ========================================

    def _can_change_time(self):
        """Проверка возможности изменения времени (дебаунсинг)"""
        if self._time_buttons_locked:
            logger.debug("Time change blocked - buttons locked")
            return False
            
        current_time = time.time()
        time_since_last = current_time - self._last_time_change
        
        if time_since_last < self._time_change_delay:
            logger.debug(f"Time change blocked by debouncing (since last: {time_since_last:.3f}s)")
            return False
            
        self._last_time_change = current_time
        return True

    def _lock_time_buttons(self):
        """Временная блокировка кнопок времени"""
        self._time_buttons_locked = True
        Clock.schedule_once(lambda dt: setattr(self, '_time_buttons_locked', False), 
                          self._time_change_delay)

    def _can_change_toggle(self):
        """Проверка возможности изменения toggle кнопок (дебаунсинг)"""
        if self._toggle_buttons_locked:
            logger.debug("Toggle change blocked - buttons locked")
            return False
            
        current_time = time.time()
        time_since_last = current_time - self._last_toggle_change
        
        if time_since_last < self._toggle_change_delay:
            logger.debug(f"Toggle change blocked by debouncing (since last: {time_since_last:.3f}s)")
            return False
            
        self._last_toggle_change = current_time
        return True

    def _lock_toggle_buttons(self):
        """Временная блокировка toggle кнопок"""
        self._toggle_buttons_locked = True
        Clock.schedule_once(lambda dt: setattr(self, '_toggle_buttons_locked', False), 
                          self._toggle_change_delay)

    # ========================================
    # РАБОТА С РИНГТОНАМИ - RingtoneSelectButton integration
    # ========================================

    def select_ringtone(self, name):
        """Выбор мелодии - вызывается из RingtoneSelectButton"""
        if name != self.selected_ringtone and name in self.ringtone_list:
            logger.debug(f"AlarmScreen.select_ringtone called with: {name}")
            
            # Останавливаем текущее воспроизведение если играет
            if self._sound_playing:
                self.stop_ringtone()
                self._reset_play_button()
            
            # Воспроизводим звук клика
            self._play_click_sound()
            
            # Обновляем выбранную мелодию
            old_ringtone = self.selected_ringtone
            self.selected_ringtone = name
            
            # Обновляем кнопку выбора
            if hasattr(self, 'ids') and 'ringtone_button' in self.ids:
                self.ids.ringtone_button.selected_value = name
            
            # Планируем автосохранение
            self._schedule_auto_save()
            
            logger.info(f"Ringtone changed from {old_ringtone} to {name}")

    def _setup_ringtone_button(self):
        """ИСПРАВЛЕНО: Настройка кнопки выбора рингтона"""
        try:
            if not hasattr(self, 'ids') or 'ringtone_button' not in self.ids:
                logger.warning("Ringtone button not found in ids")
                return
                
            ringtone_button = self.ids.ringtone_button
            
            # Устанавливаем значения и текущий выбор
            ringtone_button.set_values(self.ringtone_list)
            ringtone_button.set_selection(self.selected_ringtone)
            
            logger.debug(f"Ringtone button configured with {len(self.ringtone_list)} options")
                
        except Exception as e:
            logger.error(f"Error setting up ringtone button: {e}")

    # ========================================
    # АУДИО ВОСПРОИЗВЕДЕНИЕ
    # ========================================
    def _play_sound(self, sound_name):
        """ИСПРАВЛЕНО: Воспроизведение звуков с улучшенным fallback"""
        try:
            # Используем sound_manager для UI звуков
            from app.sound_manager import sound_manager
            
            if sound_name == "click":
                sound_manager.play_click()
            elif sound_name == "error":
                sound_manager.play_error()
            elif sound_name == "confirm":
                sound_manager.play_confirm()
            else:
                # Попытка через универсальный метод
                if hasattr(sound_manager, '_play_sound'):
                    sound_manager._play_sound(sound_name)
                else:
                    logger.warning(f"Unknown sound: {sound_name}")
                    
        except ImportError:
            logger.warning("sound_manager not available, trying audio_service")
            try:
                # Fallback через audio_service
                app = App.get_running_app()
                if hasattr(app, 'audio_service') and app.audio_service:
                    sound_file = f"sounds/{sound_name}.ogg"
                    if os.path.exists(sound_file):
                        app.audio_service.play(sound_file)
                    else:
                        logger.warning(f"Sound file not found: {sound_file}")
            except Exception as fallback_error:
                logger.error(f"Fallback sound failed: {fallback_error}")
        except Exception as e:
            logger.error(f"Error playing sound '{sound_name}': {e}")
    def play_ringtone(self):
        """ИСПРАВЛЕНО: Воспроизведение рингтона с проверкой AudioService"""
        try:
            if not self.selected_ringtone:
                logger.error("❌ No ringtone selected")
                self._play_sound("error")
                self._reset_play_button()
                return

            # Проходим по возможным путям к рингтонам
            possible_paths = [
                f"assets/sounds/ringtones/{self.selected_ringtone}",
                f"sounds/ringtones/{self.selected_ringtone}",
                f"assets/ringtones/{self.selected_ringtone}",
                f"ringtones/{self.selected_ringtone}",
                f"media/ringtones/{self.selected_ringtone}"
            ]
            
            path = None
            for p in possible_paths:
                if os.path.exists(p):
                    path = p
                    break
                    
            if not path:
                logger.error(f"❌ Ringtone file not found: {self.selected_ringtone}")
                self._play_sound("error")
                self._reset_play_button()
                return

            # Проверка размера файла
            try:
                file_size = os.path.getsize(path)
                logger.info(f"Ringtone file size: {file_size} bytes")
                if file_size == 0:
                    logger.error(f"❌ Ringtone file is empty: {path}")
                    self._play_sound("error")
                    self._reset_play_button()
                    return
            except Exception as e:
                logger.error(f"❌ Error checking file size: {e}")

            app = App.get_running_app()
            if not hasattr(app, 'audio_service') or not app.audio_service:
                logger.error("❌ Audio service not available")
                self._play_sound("error")
                self._reset_play_button()
                return
                
            audio_service = app.audio_service
            
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверяем что mixer инициализирован
            if not audio_service.is_mixer_initialized():
                logger.error("❌ Audio mixer not initialized")
                self._play_sound("error")
                self._reset_play_button()
                return
                
            logger.info(f"AudioService before play - mixer initialized: {audio_service.is_mixer_initialized()}")
            
            # Небольшая задержка для стабильности
            time.sleep(0.1)
            
            # Воспроизводим рингтон
            fadein_time = 2.0 if self.alarm_fadein else 0
            logger.info(f"🎵 Calling audio_service.play with fadein={fadein_time}")
            
            try:
                audio_service.play(path, fadein=fadein_time)
                logger.info(f"✅ audio_service.play() completed successfully")
                
                # Проверяем что воспроизведение началось
                if audio_service.is_busy():
                    self._sound_playing = True
                    self._start_sound_monitoring()
                    logger.info("🎵 Ringtone playback started successfully")
                else:
                    logger.warning("⚠️ Audio service reported play completed but not busy")
                    self._reset_play_button()
                
            except Exception as play_error:
                logger.error(f"❌ Error in audio_service.play(): {play_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self._play_sound("error")
                self._reset_play_button()
                return
                
        except Exception as e:
            logger.error(f"❌ Error playing ringtone: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._reset_play_button()

    def stop_ringtone(self):
        """Остановка воспроизведения рингтона"""
        try:
            logger.info("⏹️ Stopping ringtone...")
            
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
                
            self._sound_playing = False
            self._stop_sound_monitoring()
            self._reset_play_button()
            
            logger.info("🔇 Ringtone stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Error stopping ringtone: {e}")
            # Всегда сбрасываем состояние даже при ошибке
            self._sound_playing = False
            self._stop_sound_monitoring()
            self._reset_play_button()

    def _start_sound_monitoring(self):
        """Запуск мониторинга воспроизведения звука"""
        logger.info("🔄 Starting ringtone sound monitoring...")
        if self._sound_check_event:
            self._sound_check_event.cancel()
        
        self._sound_check_event = Clock.schedule_interval(self._check_sound_status, 1.0)
 
    def _check_sound_status(self, dt):
        """ИСПРАВЛЕНО: Проверка статуса воспроизведения звука"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                audio_service = app.audio_service
                
                # ИСПРАВЛЕНИЕ: Проверяем mixer перед вызовом is_busy
                if not audio_service.is_mixer_initialized():
                    logger.info("🔇 Audio mixer not initialized - stopping monitoring")
                    self._sound_playing = False
                    self._stop_sound_monitoring()
                    self._reset_play_button()
                    return
                    
                is_busy = audio_service.is_busy()
                current_file = getattr(audio_service, 'current_file', None)
                
                logger.debug(f"🔍 Ringtone check: is_busy={is_busy}, current_file={current_file}, _sound_playing={self._sound_playing}")
                
                # Проверяем что это действительно наш рингтон
                if not is_busy and self._sound_playing:
                    if current_file and 'ringtones' in current_file:
                        logger.info("🔇 Ringtone finished playing")
                    else:
                        logger.info("🔇 Audio finished but wasn't ringtone")
                    
                    self._sound_playing = False
                    self._stop_sound_monitoring()
                    self._reset_play_button()
                    
        except Exception as e:
            logger.error(f"❌ Error checking sound status: {e}")
            # При ошибке останавливаем мониторинг
            self._sound_playing = False
            self._stop_sound_monitoring()
            self._reset_play_button()

    def _stop_sound_monitoring(self):
        """Остановка мониторинга звука"""
        if self._sound_check_event:
            self._sound_check_event.cancel()
            self._sound_check_event = None

    def _reset_play_button(self):
        """Сброс кнопки воспроизведения"""
        if hasattr(self, 'ids') and 'play_button' in self.ids:
            play_button = self.ids.play_button
            play_button.text = 'Play'
            play_button.state = 'normal'
        self._sound_playing = False

    def _play_sound(self, sound_name):
        """ИСПРАВЛЕНО: Использование sound_manager для UI звуков"""
        try:
            # Используем sound_manager для UI звуков
            from app.sound_manager import sound_manager
            
            if sound_name == "click":
                sound_manager.play_click()
            elif sound_name == "error":
                sound_manager.play_error()
            elif sound_name == "confirm":
                sound_manager.play_confirm()
            else:
                # Fallback для других звуков
                sound_manager._play_sound(sound_name)
                
        except Exception as e:
            logger.error(f"Error playing sound '{sound_name}': {e}")
    def _play_click_sound(self):
        """ИСПРАВЛЕНО: Воспроизведение звука клика с использованием sound_manager"""
        try:
            from app.sound_manager import sound_manager
            sound_manager.play_click()
        except ImportError:
            # Fallback если sound_manager недоступен
            self._play_sound("click")
        except Exception as e:
            logger.error(f"Error playing click sound: {e}")

    # ========================================
    # UI ОБНОВЛЕНИЕ И КОНФИГУРАЦИЯ
    # ========================================

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
                ringtone_button.set_values(self.ringtone_list)
                ringtone_button.set_selection(self.selected_ringtone)
            
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

    def _update_toggle_buttons(self):
        """ИСПРАВЛЕНО: Обновление кнопок переключения"""
        try:
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
                
        except Exception as e:
            logger.error(f"Error updating toggle buttons: {e}")

    def _update_day_buttons(self):
        """ИСПРАВЛЕНО: Обновление кнопок дней недели"""
        try:
            if not hasattr(self, 'ids'):
                return
                
            for day in DAYS_EN:
                btn_id = f"repeat_{day.lower()}"
                if btn_id in self.ids:
                    button = self.ids[btn_id]
                    button.state = "down" if day in self.alarm_repeat else "normal"
                    
        except Exception as e:
            logger.error(f"Error updating day buttons: {e}")

    # ========================================
    # ЗАГРУЗКА И СОХРАНЕНИЕ
    # ========================================

    def load_ringtones(self):
        """Загрузка списка мелодий будильника"""
        try:
            ringtones = []
            ringtone_dirs = [
                "assets/sounds/ringtones",
                "sounds/ringtones", 
                "assets/ringtones",
                "ringtones",
                "media/ringtones"
            ]
            
            for ringtone_dir in ringtone_dirs:
                if os.path.exists(ringtone_dir):
                    for file in os.listdir(ringtone_dir):
                        if file.endswith(('.mp3', '.wav', '.ogg')):
                            ringtones.append(file)
                    break
            
            if not ringtones:
                ringtones = ["Bathtime In Clerkenwell.mp3"]  # Fallback
                
            self.ringtone_list = sorted(ringtones)
            logger.info(f"Loaded {len(ringtones)} ringtones")
            
        except Exception as e:
            logger.error(f"Error loading ringtones: {e}")
            self.ringtone_list = ["Bathtime In Clerkenwell.mp3"]

    def load_alarm_config(self):
        """Загрузка конфигурации будильника"""
        try:
            config_path = "config/alarm.json"
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                alarm_config = config.get('alarm', {})
                self.alarm_time = alarm_config.get('time', '07:30')
                self.alarm_active = alarm_config.get('enabled', True)
                self.alarm_repeat = alarm_config.get('repeat', ["Mon", "Tue", "Wed", "Thu", "Fri"])
                self.selected_ringtone = alarm_config.get('ringtone', 'Bathtime In Clerkenwell.mp3')
                self.alarm_fadein = alarm_config.get('fadein', False)
                
                logger.info(f"Alarm config loaded: {self.alarm_time}, active: {self.alarm_active}")
                
        except Exception as e:
            logger.error(f"Error loading alarm config: {e}")

    def save_alarm_config(self, silent=False):
        """Сохранение конфигурации будильника - ИСПРАВЛЕНО"""
        return self.save_alarm_via_service(silent)
    def _schedule_auto_save(self, delay=1.5):
        """Планирование автоматического сохранения"""
        if self._auto_save_event:
            self._auto_save_event.cancel()
        
        self._settings_changed = True
        self._auto_save_event = Clock.schedule_once(
            lambda dt: self.save_alarm_config(silent=True), delay
        )
    def save_alarm_config_original(self, silent=False):
        """Оригинальный метод сохранения в файл"""
        try:
            config = {
                'alarm': {
                    'time': self.alarm_time,
                    'enabled': self.alarm_active,
                    'repeat': list(self.alarm_repeat),
                    'ringtone': self.selected_ringtone,
                    'fadein': self.alarm_fadein
                }
            }
            
            os.makedirs("config", exist_ok=True)
            
            import json
            with open("config/alarm.json", 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Alarm config saved to file: {self.alarm_time}")
            
            # Отправляем событие для синхронизации
            try:
                event_bus.publish("alarm_settings_changed", {
                    "time": self.alarm_time,
                    "enabled": self.alarm_active,
                    "repeat": list(self.alarm_repeat),
                    "ringtone": self.selected_ringtone,
                    "fadein": self.alarm_fadein,
                    "source": "alarm_screen"
                })
                logger.debug("Alarm settings change event published")
            except Exception as event_error:
                logger.error(f"Error publishing alarm settings event: {event_error}")
            
            if not silent:
                self._play_sound("confirm")
                
            return True
        except Exception as e:
            logger.error(f"Error saving alarm to file: {e}")
            if not silent:
                self._play_sound("error")
            return False

    # ========================================
    # ДИАГНОСТИКА И ОБСЛУЖИВАНИЕ - ИСПРАВЛЕНО
    # ========================================

    def test_audio_system(self):
        """ИСПРАВЛЕНО: Простая проверка аудио системы без избыточного логирования"""
        try:
            app = App.get_running_app()
            
            logger.info("🔧 === ALARM SCREEN AUDIO DIAGNOSIS ===")
            
            if hasattr(app, 'audio_service') and app.audio_service:
                logger.info("✅ app.audio_service exists")
                
                # Простая проверка состояния
                if hasattr(app.audio_service, 'diagnose_state'):
                    logger.info("✅ diagnose_state method exists")
                    
                    # Выполняем диагностику
                    diagnosis = app.audio_service.diagnose_state()
                    
                    # Логируем только основные параметры
                    logger.info(f"instance_id: {diagnosis.get('instance_id')}")
                    logger.info(f"service_version: {diagnosis.get('service_version')}")
                    logger.info(f"mixer_initialized: {diagnosis.get('mixer_initialized')}")
                    logger.info(f"is_playing: {diagnosis.get('is_playing')}")
                    logger.info(f"current_file: {diagnosis.get('current_file')}")
                    logger.info(f"is_long_audio: {diagnosis.get('is_long_audio')}")
                    logger.info(f"pygame_busy: {diagnosis.get('pygame_busy')}")
                    logger.info(f"pygame_init: {diagnosis.get('pygame_init')}")
                    logger.info(f"audio_device: {diagnosis.get('audio_device')}")
                    logger.info(f"alsa_available: {diagnosis.get('alsa_available')}")
                    
                    # Проверяем доступность рингтонов
                    logger.info(f"Selected ringtone: {self.selected_ringtone}")
                    logger.info(f"Available ringtones: {len(self.ringtone_list)}")
                    
                    return diagnosis
                else:
                    logger.error("❌ diagnose_state method missing from AudioService")
                    return {"error": "diagnose_state_method_missing"}
            else:
                logger.error("❌ app.audio_service not available")
                return {"error": "audio_service_not_available"}
                
        except Exception as e:
            logger.error(f"❌ Error in audio system test: {e}")
            return {"error": f"test_failed: {e}"}

    def refresh_theme(self):
        """Обновление темы"""
        try:
            # Принудительное обновление темы через event_bus
            event_bus.publish("theme_refresh_request", {"screen": "alarm"})
        except Exception as e:
            logger.error(f"Error refreshing theme: {e}")

    def refresh_text(self):
        """Обновление текста интерфейса"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'localization') and app.localization:
                # Здесь можно обновить локализованные тексты
                pass
        except Exception as e:
            logger.error(f"Error refreshing text: {e}")

    def _on_theme_changed_delayed(self, event_data):
        """Отложенное обновление темы"""
        Clock.schedule_once(lambda dt: self.refresh_theme(), 0.5)