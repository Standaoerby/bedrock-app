# services/alarm_popup.py
"""
ПОЛНОСТЬЮ ПЕРЕДЕЛАННЫЙ AlarmPopup с темизацией и правильным аудио воспроизведением
"""
import os
import time
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from app.logger import app_logger as logger


class AlarmPopup(ModalView):
    def __init__(self, alarm_time="--:--", ringtone="", **kwargs):
        super().__init__(**kwargs)
        self.alarm_time = alarm_time
        self.ringtone = ringtone
        self.size_hint = (0.9, 0.7)
        self.auto_dismiss = False
        
        # Состояние аудио
        self._audio_playing = False
        self._audio_path = None
        self._audio_monitor_event = None
        
        logger.info(f"🚨 AlarmPopup created: {alarm_time}, ringtone: {ringtone}")
        
        # Применяем тему к popup
        self._apply_theme_to_popup()
        
        # Строим UI
        self._build_themed_ui()
        
        # Автоматическое закрытие через 10 минут
        self._auto_dismiss_event = Clock.schedule_once(self._auto_dismiss, 600)

    def _apply_theme_to_popup(self):
        """Применение темы к самому popup"""
        try:
            tm = self._get_theme_manager()
            if tm and tm.is_loaded():
                # Применяем цвет фона popup
                background_color = tm.get_rgba("popup_bg")
                if background_color:
                    self.background_color = background_color
                    
                # Устанавливаем цвет разделителя
                separator_color = tm.get_rgba("border") 
                if separator_color:
                    self.separator_color = separator_color
                    
                logger.debug("Theme applied to AlarmPopup")
            else:
                logger.warning("ThemeManager not available for popup styling")
                # Fallback цвета
                self.background_color = [0.1, 0.1, 0.1, 0.95]  # Темно-серый полупрозрачный
                
        except Exception as e:
            logger.error(f"Error applying theme to popup: {e}")
            self.background_color = [0.1, 0.1, 0.1, 0.95]

    def _get_theme_manager(self):
        """Безопасное получение ThemeManager"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'theme_manager') and app.theme_manager:
                return app.theme_manager
        except Exception as e:
            logger.error(f"Error getting theme manager: {e}")
        return None

    # СРОЧНОЕ ИСПРАВЛЕНИЕ services/alarm_popup.py
    # ЗАМЕНИТЕ метод _build_themed_ui полностью:

    def _build_themed_ui(self):
        """Создание тематизированного интерфейса - ИСПРАВЛЕНО без fallback"""
        main_layout = BoxLayout(
            orientation='vertical', 
            padding=dp(24), 
            spacing=dp(20)
        )
        
        tm = self._get_theme_manager()
        
        # === ЗАГОЛОВОК ===
        title_label = Label(
            text="WAKE UP CUTIE! :)",
            font_size='42sp',
            size_hint_y=0.25,
            halign='center',
            valign='middle'
        )
        title_label.bind(size=title_label.setter('text_size'))
        
        # Применяем тему к заголовку
        if tm and tm.is_loaded():
            title_label.font_name = tm.get_font("title") or ""
            title_label.color = tm.get_rgba("primary")
        else:
            title_label.color = [1, 0.3, 0.3, 1]  # Красный fallback
            
        main_layout.add_widget(title_label)
        
        # === ВРЕМЯ БУДИЛЬНИКА ===
        time_label = Label(
            text=f"🕐 Alarm Time: {self.alarm_time}",
            font_size='26sp',
            size_hint_y=0.2,
            halign='center',
            valign='middle'
        )
        time_label.bind(size=time_label.setter('text_size'))
        
        # Применяем тему ко времени
        if tm and tm.is_loaded():
            time_label.font_name = tm.get_font("main") or ""
            time_label.color = tm.get_rgba("text")
        else:
            time_label.color = [1, 1, 1, 1]  # Белый fallback
            
        main_layout.add_widget(time_label)
        
        # === ИНФОРМАЦИЯ О РИНГТОНЕ ===
        ringtone_display = self.ringtone
        if '.' in ringtone_display:
            ringtone_display = ringtone_display.rsplit('.', 1)[0]
            
        ringtone_label = Label(
            text=f"🎵 {ringtone_display}",
            font_size='18sp',
            size_hint_y=0.15,
            halign='center',
            valign='middle'
        )
        ringtone_label.bind(size=ringtone_label.setter('text_size'))
        
        # Применяем тему к информации о рингтоне
        if tm and tm.is_loaded():
            ringtone_label.font_name = tm.get_font("main") or ""
            ringtone_label.color = tm.get_rgba("text_secondary")
        else:
            ringtone_label.color = [0.8, 0.8, 0.8, 1]  # Светло-серый fallback
            
        main_layout.add_widget(ringtone_label)
        
        # === КНОПКИ УПРАВЛЕНИЯ ===
        button_layout = BoxLayout(
            orientation='horizontal', 
            spacing=dp(16), 
            size_hint_y=0.4
        )
        
        # Кнопка STOP
        stop_button = Button(
            text="🛑 STOP",
            font_size='22sp',
            size_hint_x=0.5
        )
        
        # Кнопка SNOOZE  
        snooze_button = Button(
            text="😴 SNOOZE (5 min)",
            font_size='18sp',
            size_hint_x=0.5
        )
        
        # ИСПРАВЛЕНО: Применяем тему к кнопкам БЕЗ fallback параметров
        if tm and tm.is_loaded():
            # Кнопка STOP
            stop_button.font_name = tm.get_font("main") or ""
            stop_button.color = tm.get_rgba("text")
            
            # ИСПРАВЛЕНО: БЕЗ fallback параметров!
            stop_bg = tm.get_image("button_bg")
            stop_bg_active = tm.get_image("button_bg_active")
            if stop_bg:
                stop_button.background_normal = stop_bg
            if stop_bg_active:
                stop_button.background_down = stop_bg_active
            # Красный фон для кнопки STOP
            stop_button.background_color = [0.8, 0.2, 0.2, 1]
            
            # Кнопка SNOOZE
            snooze_button.font_name = tm.get_font("main") or ""
            snooze_button.color = tm.get_rgba("text")
            
            # ИСПРАВЛЕНО: БЕЗ fallback параметров!
            snooze_bg = tm.get_image("button_bg")
            snooze_bg_active = tm.get_image("button_bg_active")
            if snooze_bg:
                snooze_button.background_normal = snooze_bg
            if snooze_bg_active:
                snooze_button.background_down = snooze_bg_active
            # Оранжевый фон для кнопки SNOOZE
            snooze_button.background_color = [1, 0.6, 0.2, 1]
        else:
            # Fallback цвета без темы
            stop_button.color = [1, 1, 1, 1]
            stop_button.background_color = [0.8, 0.2, 0.2, 1]  # Красный
            
            snooze_button.color = [1, 1, 1, 1]
            snooze_button.background_color = [1, 0.6, 0.2, 1]  # Оранжевый
        
        # Привязываем события кнопок
        stop_button.bind(on_press=self._stop_alarm)
        snooze_button.bind(on_press=self._snooze_alarm)
        
        button_layout.add_widget(stop_button)
        button_layout.add_widget(snooze_button)
        main_layout.add_widget(button_layout)
        
        self.add_widget(main_layout)
        logger.debug("Themed UI built successfully")

    # ========================================
    # ИСПРАВЛЕНИЕ services/alarm_popup.py - метод _find_ringtone_path
    # ========================================

    def _find_ringtone_path(self, ringtone_filename):
        """ИСПРАВЛЕНО: Правильные пути с media/ringtones"""
        if not ringtone_filename:
            logger.error("No ringtone filename provided")
            return None
            
        # ИСПРАВЛЕНО: Правильные пути с media/ringtones первым!
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        possible_paths = [
            # ИСПРАВЛЕНО: media/ringtones первым!
            os.path.join(base_dir, "media", "ringtones", ringtone_filename),
            os.path.join(base_dir, "assets", "sounds", "ringtones", ringtone_filename),
            os.path.join(base_dir, "sounds", "ringtones", ringtone_filename),
            os.path.join(base_dir, "assets", "ringtones", ringtone_filename),
            os.path.join(base_dir, "ringtones", ringtone_filename),
            # Также относительные пути
            f"media/ringtones/{ringtone_filename}",
            f"assets/sounds/ringtones/{ringtone_filename}",
            f"sounds/ringtones/{ringtone_filename}",
            f"assets/ringtones/{ringtone_filename}",
            f"ringtones/{ringtone_filename}"
        ]
        
        logger.debug(f"🔍 Searching for ringtone: {ringtone_filename}")
        
        for path in possible_paths:
            try:
                abs_path = os.path.abspath(path)
                logger.debug(f"  Checking: {abs_path}")
                
                if os.path.exists(abs_path):
                    file_size = os.path.getsize(abs_path)
                    if file_size > 0:
                        logger.info(f"✅ Found ringtone: {abs_path} ({file_size} bytes)")
                        return abs_path
                    else:
                        logger.warning(f"⚠️ Ringtone file is empty: {abs_path}")
                else:
                    logger.debug(f"  ❌ Not found: {abs_path}")
            except Exception as e:
                logger.debug(f"  ⚠️ Error checking path {path}: {e}")
        
        logger.error(f"❌ Ringtone not found in any location: {ringtone_filename}")
        return None

    # ========================================
    # ИСПРАВЛЕНИЕ services/alarm_clock.py - метод _attempt_fallback_audio
    # ========================================

    def _attempt_fallback_audio(self, ringtone):
        """ИСПРАВЛЕНО: Fallback аудио с правильными путями"""
        try:
            logger.info("🔊 Attempting fallback audio playback")
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                # ИСПРАВЛЕНО: Правильные пути с media/ringtones!
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                possible_paths = [
                    # ИСПРАВЛЕНО: media/ringtones первым!
                    os.path.join(base_dir, "media", "ringtones", ringtone),
                    os.path.join(base_dir, "assets", "sounds", "ringtones", ringtone),
                    os.path.join(base_dir, "sounds", "ringtones", ringtone),
                    os.path.join(base_dir, "assets", "ringtones", ringtone),
                    os.path.join(base_dir, "ringtones", ringtone),
                    # Относительные пути
                    f"media/ringtones/{ringtone}",
                    f"assets/sounds/ringtones/{ringtone}",
                    f"sounds/ringtones/{ringtone}",
                    f"assets/ringtones/{ringtone}",
                    f"ringtones/{ringtone}"
                ]
                
                for path in possible_paths:
                    try:
                        if os.path.exists(path):
                            file_size = os.path.getsize(path)
                            if file_size > 0:
                                logger.info(f"🎵 Trying fallback path: {path}")
                                
                                if hasattr(app.audio_service, 'play_loop'):
                                    app.audio_service.play_loop(path)
                                else:
                                    app.audio_service.play(path)
                                    
                                logger.info("✅ Fallback audio started")
                                return
                    except Exception as play_error:
                        logger.error(f"❌ Fallback audio failed for {path}: {play_error}")
                        continue
                
                logger.error("❌ All fallback audio attempts failed")
            else:
                logger.error("❌ No audio_service available for fallback")
                
        except Exception as e:
            logger.error(f"❌ Error in fallback audio: {e}")

    def _start_audio_playback(self):
        """ИСПРАВЛЕНО: Запуск аудио без лишних проверок"""
        try:
            if self._audio_playing:
                logger.info("Audio already playing, skipping")
                return True
                
            # Находим путь к рингтону
            ringtone_path = self._find_ringtone_path(self.ringtone)
            if not ringtone_path:
                logger.error(f"Cannot start audio - ringtone not found: {self.ringtone}")
                return False
            
            # Получаем audio_service
            app = App.get_running_app()
            if not hasattr(app, 'audio_service') or not app.audio_service:
                logger.error("Cannot start audio - audio_service not available")
                return False
            
            audio_service = app.audio_service
            
            # Проверяем mixer
            if hasattr(audio_service, 'is_mixer_initialized'):
                if not audio_service.is_mixer_initialized():
                    logger.error("Cannot start audio - mixer not initialized")
                    return False
                logger.debug("✅ Audio mixer is initialized")
            
            # Запускаем воспроизведение
            logger.info(f"🎵 Starting audio playback: {ringtone_path}")
            
            try:
                # ИСПРАВЛЕНО: Простой вызов без loop
                audio_service.play(ringtone_path, fadein=0)
                
                # ИСПРАВЛЕНО: Простая проверка через is_busy
                time.sleep(0.2)  # Короткая пауза для запуска
                
                if hasattr(audio_service, 'is_busy') and audio_service.is_busy():
                    self._audio_playing = True
                    self._audio_path = ringtone_path
                    self._start_audio_monitoring()
                    logger.info("🔊 Alarm audio playback started successfully")
                    return True
                else:
                    logger.warning("⚠️ Audio may not have started properly")
                    # Все равно помечаем как играющее
                    self._audio_playing = True
                    self._audio_path = ringtone_path
                    self._start_audio_monitoring()
                    return True
                
            except Exception as play_error:
                logger.error(f"❌ Error in audio playback: {play_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting audio playbook: {e}")
            return False

    # ТАКЖЕ ДОБАВЬТЕ НЕДОСТАЮЩИЙ МЕТОД (если нужен):
    def _verify_playback_started(self, audio_service):
        """Проверка что воспроизведение началось"""
        try:
            for attempt in range(10):  # Ждем до 1 секунды
                if hasattr(audio_service, 'is_busy') and audio_service.is_busy():
                    return True
                elif hasattr(audio_service, 'is_playing') and audio_service.is_playing:
                    return True
                time.sleep(0.1)
            return False
        except Exception as e:
            logger.error(f"Error verifying playback: {e}")
            return False

    # ИСПРАВЛЕНИЕ: Замените метод _restart_audio_playback:
    def _restart_audio_playback(self):
        """ИСПРАВЛЕНО: Перезапуск без loop параметра"""
        try:
            if self._audio_path and os.path.exists(self._audio_path):
                app = App.get_running_app()
                if hasattr(app, 'audio_service') and app.audio_service:
                    audio_service = app.audio_service
                    
                    logger.info(f"🔄 Restarting audio: {self._audio_path}")
                    
                    try:
                        # ИСПРАВЛЕНО: Без loop параметра!
                        audio_service.play(self._audio_path, fadein=0)
                        logger.info("✅ Audio restarted successfully")
                    except Exception as e:
                        logger.error(f"Error restarting audio: {e}")
            else:
                logger.error("Cannot restart audio - path invalid")
                
        except Exception as e:
            logger.error(f"Error restarting audio: {e}")


    def _start_audio_monitoring(self):
        """Запуск мониторинга состояния аудио"""
        if self._audio_monitor_event:
            self._audio_monitor_event.cancel()
        
        self._audio_monitor_event = Clock.schedule_interval(self._check_audio_status, 2.0)
        logger.debug("🔄 Audio monitoring started")

    def _check_audio_status(self, dt):
        """Проверка состояния воспроизведения"""
        try:
            if not self._audio_playing:
                return False  # Останавливаем мониторинг
            
            app = App.get_running_app()
            if not hasattr(app, 'audio_service') or not app.audio_service:
                logger.warning("Audio service disappeared during monitoring")
                return False
            
            audio_service = app.audio_service
            
            # Проверяем статус воспроизведения
            is_playing = False
            if hasattr(audio_service, 'is_busy'):
                is_playing = audio_service.is_busy()
            elif hasattr(audio_service, 'is_playing'):
                is_playing = audio_service.is_playing()
            
            if not is_playing:
                logger.info("🔇 Audio playback stopped, attempting restart...")
                # Пытаемся перезапустить воспроизведение
                self._restart_audio_playback()
            
            return True  # Продолжаем мониторинг
            
        except Exception as e:
            logger.error(f"Error in audio monitoring: {e}")
            return False

 
    def _stop_audio_playback(self):
        """Остановка воспроизведения аудио"""
        try:
            if not self._audio_playing:
                return
                
            logger.info("🛑 Stopping alarm audio...")
            
            # Останавливаем мониторинг
            if self._audio_monitor_event:
                self._audio_monitor_event.cancel()
                self._audio_monitor_event = None
            
            # Останавливаем аудио
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and app.audio_service:
                app.audio_service.stop()
                logger.info("🔇 Audio service stop() called")
            
            # Сбрасываем состояние
            self._audio_playing = False
            self._audio_path = None
            
            logger.info("✅ Audio playback stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping audio playback: {e}")
            # Всегда сбрасываем состояние
            self._audio_playing = False
            self._audio_path = None

    def open_alarm(self):
        """ИСПРАВЛЕНО: Открытие popup с правильным запуском аудио"""
        try:
            logger.info(f"🚨 Opening alarm popup: {self.alarm_time}")
            
            # Сначала открываем popup
            self.open()
            logger.info("📱 Alarm popup opened")
            
            # Затем запускаем аудио с небольшой задержкой
            Clock.schedule_once(lambda dt: self._delayed_audio_start(), 0.3)
            
        except Exception as e:
            logger.error(f"❌ Error opening alarm popup: {e}")
            import traceback
            logger.error(f"Open alarm traceback: {traceback.format_exc()}")

    def _delayed_audio_start(self):
        """Отложенный запуск аудио после открытия popup"""
        try:
            success = self._start_audio_playback()
            if success:
                logger.info("🔊 Alarm audio started successfully")
            else:
                logger.error("❌ Failed to start alarm audio")
                # Показываем уведомление пользователю
                self._show_audio_error()
                
        except Exception as e:
            logger.error(f"Error in delayed audio start: {e}")

    def _show_audio_error(self):
        """Показать ошибку воспроизведения в UI (опционально)"""
        try:
            # Можно добавить текст об ошибке аудио в popup
            # Для простоты пока просто логируем
            logger.warning("⚠️ Alarm popup opened but audio playback failed")
        except Exception as e:
            logger.error(f"Error showing audio error: {e}")

    def _stop_alarm(self, instance):
        """ИСПРАВЛЕНО: Остановка будильника через alarm_clock"""
        try:
            logger.info("🛑 Stop button pressed")
            
            # Останавливаем аудио
            self._stop_audio_playback()
            
            # Получаем alarm_clock и останавливаем будильник
            app = App.get_running_app()
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                app.alarm_clock.stop_alarm()
                logger.info("✅ Alarm stopped via alarm_clock")
            else:
                logger.warning("alarm_clock not available, closing popup directly")
                self.dismiss()
                
        except Exception as e:
            logger.error(f"❌ Error stopping alarm: {e}")
            # В любом случае закрываем popup
            try:
                self._stop_audio_playback()
                self.dismiss()
            except:
                pass

    def _snooze_alarm(self, instance):
        """ИСПРАВЛЕНО: Отложить будильник на 5 минут"""
        try:
            logger.info("😴 Snooze button pressed")
            
            # Останавливаем аудио
            self._stop_audio_playback()
            
            # Получаем alarm_clock и откладываем
            app = App.get_running_app()
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                app.alarm_clock.snooze_alarm(5)
                logger.info("✅ Alarm snoozed for 5 minutes")
            else:
                logger.warning("alarm_clock not available, just closing popup")
                self.dismiss()
                
        except Exception as e:
            logger.error(f"❌ Error snoozing alarm: {e}")
            # В любом случае закрываем popup  
            try:
                self._stop_audio_playback()
                self.dismiss()
            except:
                pass

    def _auto_dismiss(self, dt):
        """Автоматическое закрытие через 10 минут"""
        try:
            logger.info("⏰ Auto-dismissing alarm after 10 minutes")
            
            # Останавливаем аудио
            self._stop_audio_playback()
            
            # Останавливаем будильник
            app = App.get_running_app()
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                app.alarm_clock.stop_alarm()
            else:
                self.dismiss()
                
        except Exception as e:
            logger.error(f"❌ Error auto-dismissing alarm: {e}")
            try:
                self.dismiss()
            except:
                pass

    def dismiss(self, *args):
        """ИСПРАВЛЕНО: Переопределенное закрытие popup с очисткой ресурсов"""
        try:
            # Останавливаем все события
            if self._auto_dismiss_event:
                self._auto_dismiss_event.cancel()
                self._auto_dismiss_event = None
                
            if self._audio_monitor_event:
                self._audio_monitor_event.cancel()
                self._audio_monitor_event = None
            
            # Останавливаем аудио
            self._stop_audio_playback()
            
            # Закрываем popup
            super().dismiss(*args)
            logger.info("❌ Alarm popup dismissed and cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Error dismissing alarm popup: {e}")
            try:
                super().dismiss(*args)
            except:
                pass

    # НОВОЕ: Методы для диагностики
    def diagnose_audio_state(self):
        """Диагностика состояния аудио в popup"""
        logger.info("🔧 === ALARM POPUP AUDIO DIAGNOSTIC ===")
        
        app = App.get_running_app()
        audio_available = hasattr(app, 'audio_service') and app.audio_service is not None
        
        logger.info(f"[audio_service      ] {'✅ Available' if audio_available else '❌ Missing'}")
        logger.info(f"[ringtone_file      ] {self.ringtone}")
        logger.info(f"[audio_playing      ] {self._audio_playing}")
        logger.info(f"[audio_path         ] {self._audio_path}")
        
        if audio_available:
            audio_service = app.audio_service
            if hasattr(audio_service, 'is_mixer_initialized'):
                mixer_init = audio_service.is_mixer_initialized()
                logger.info(f"[mixer_initialized  ] {mixer_init}")
            
            if hasattr(audio_service, 'is_busy'):
                is_busy = audio_service.is_busy()
                logger.info(f"[audio_busy         ] {is_busy}")
        
        # Проверяем путь к файлу
        ringtone_path = self._find_ringtone_path(self.ringtone)
        logger.info(f"[ringtone_found     ] {'✅' if ringtone_path else '❌'}")
        if ringtone_path:
            logger.info(f"[ringtone_path      ] {ringtone_path}")
        
        logger.info("🔧 === END POPUP DIAGNOSTIC ===")