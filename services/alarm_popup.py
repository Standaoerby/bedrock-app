"""
AlarmPopup - ИСПРАВЛЕННЫЙ popup для будильника
ИСПРАВЛЕНИЯ:
- ✅ Улучшенная обработка ошибок аудио
- ✅ Robust fallback механизмы
- ✅ Улучшенная интеграция с AlarmClock
- ✅ Defensive programming
- ✅ Лучшее логирование
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
        
        self._action = None
        self._audio_playing = False
        self._cleanup_scheduled = False
        
        logger.info(f"AlarmPopup created: time={alarm_time}, ringtone={ringtone}")
        
        # Создаем UI
        self._build_ui()
        
        # Планируем автоматическое закрытие через 10 минут если не отвечают
        self._auto_dismiss_event = Clock.schedule_once(self._auto_dismiss_callback, 600)  # 10 минут
    
    def _build_ui(self):
        """Построение пользовательского интерфейса"""
        try:
            # Основной контейнер
            main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
            
            # Заголовок с анимацией
            title_label = Label(
                text="🚨 ALARM! 🚨",
                font_size='48sp',
                size_hint_y=0.3,
                halign='center',
                color=[1, 0.2, 0.2, 1]  # Красный цвет для привлечения внимания
            )
            main_layout.add_widget(title_label)
            
            # Время будильника
            time_label = Label(
                text=f"Wake up! {self.alarm_time}",
                font_size='24sp',
                size_hint_y=0.2,
                halign='center',
                color=[1, 1, 1, 1]
            )
            main_layout.add_widget(time_label)
            
            # Информация о мелодии
            if self.ringtone:
                ringtone_display = self.ringtone.replace('.mp3', '').replace('.wav', '')
                ringtone_label = Label(
                    text=f"♪ {ringtone_display}",
                    font_size='16sp',
                    size_hint_y=0.1,
                    halign='center',
                    color=[0.8, 0.8, 0.8, 1]
                )
                main_layout.add_widget(ringtone_label)
            
            # Кнопки управления
            button_layout = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=0.2)
            
            # Кнопка Snooze
            snooze_btn = Button(
                text="😴 Snooze 5min",
                font_size='18sp',
                size_hint_x=0.5,
                background_color=[0.3, 0.3, 0.8, 1]  # Синий
            )
            snooze_btn.bind(on_release=self.on_snooze)
            button_layout.add_widget(snooze_btn)
            
            # Кнопка Dismiss
            dismiss_btn = Button(
                text="✅ Dismiss",
                font_size='18sp',
                size_hint_x=0.5,
                background_color=[0.8, 0.3, 0.3, 1]  # Красный
            )
            dismiss_btn.bind(on_release=self.on_dismiss_button)
            button_layout.add_widget(dismiss_btn)
            
            main_layout.add_widget(button_layout)
            self.add_widget(main_layout)
            
            logger.info("✅ AlarmPopup UI built successfully")
            
        except Exception as e:
            logger.error(f"Error building AlarmPopup UI: {e}")
            # Fallback UI
            self._create_fallback_ui()
    
    def _create_fallback_ui(self):
        """Простой fallback UI если основной не удался"""
        try:
            fallback_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
            
            fallback_layout.add_widget(Label(
                text="ALARM!",
                font_size='32sp',
                halign='center'
            ))
            
            fallback_layout.add_widget(Label(
                text=f"Time: {self.alarm_time}",
                font_size='18sp',
                halign='center'
            ))
            
            dismiss_btn = Button(text="Dismiss", size_hint_y=0.3)
            dismiss_btn.bind(on_release=self.on_dismiss_button)
            fallback_layout.add_widget(dismiss_btn)
            
            self.add_widget(fallback_layout)
            logger.info("Fallback UI created")
            
        except Exception as e:
            logger.error(f"Even fallback UI failed: {e}")

    def on_snooze(self, button):
        """Обработка нажатия кнопки Snooze"""
        try:
            logger.info("Snooze button pressed")
            
            # Воспроизводим звук подтверждения
            self._play_ui_sound("confirm")
            
            self._action = "snooze"
            self.dismiss()
            
        except Exception as e:
            logger.error(f"Error in on_snooze: {e}")
            # Все равно пытаемся закрыть
            self._action = "snooze"
            self.dismiss()

    def on_dismiss_button(self, button):
        """Обработка нажатия кнопки Dismiss"""
        try:
            logger.info("Dismiss button pressed")
            
            # Воспроизводим звук клика
            self._play_ui_sound("click")
            
            self._action = "dismiss"
            self.dismiss()
            
        except Exception as e:
            logger.error(f"Error in on_dismiss_button: {e}")
            # Все равно пытаемся закрыть
            self._action = "dismiss"
            self.dismiss()
    
    def _auto_dismiss_callback(self, dt):
        """Автоматическое закрытие через 10 минут"""
        try:
            logger.warning("Auto-dismissing alarm after 10 minutes of inactivity")
            self._action = "auto_dismiss"
            self.dismiss()
        except Exception as e:
            logger.error(f"Error in auto dismiss: {e}")

    def on_dismiss(self):
        """ИСПРАВЛЕННАЯ обработка закрытия popup"""
        try:
            logger.info(f"AlarmPopup dismissing with action: {self._action}")
            
            # Отменяем auto-dismiss если он еще не сработал
            if self._auto_dismiss_event:
                self._auto_dismiss_event.cancel()
                self._auto_dismiss_event = None
            
            # Останавливаем аудио
            self._stop_audio()
            
            # Получаем alarm_clock для обработки действий
            app = App.get_running_app()
            if hasattr(app, 'alarm_clock') and app.alarm_clock:
                alarm_clock = app.alarm_clock
                
                if self._action == "snooze":
                    logger.info("Processing snooze action")
                    alarm_clock.snooze_alarm(5)  # 5 минут
                elif self._action == "dismiss" or self._action == "auto_dismiss":
                    logger.info(f"Processing {self._action} action")
                    alarm_clock.stop_alarm()
                else:
                    # Fallback - просто останавливаем
                    logger.warning(f"Unknown action '{self._action}', stopping alarm")
                    alarm_clock.stop_alarm()
            else:
                logger.error("AlarmClock not available in app")
            
            # Планируем cleanup
            if not self._cleanup_scheduled:
                self._cleanup_scheduled = True
                Clock.schedule_once(self._final_cleanup, 0.1)
            
        except Exception as e:
            logger.error(f"Error in AlarmPopup.on_dismiss: {e}")
            import traceback
            logger.error(f"Dismiss traceback: {traceback.format_exc()}")
        
        # Всегда возвращаем False чтобы popup закрылся
        return False
    
    def _final_cleanup(self, dt):
        """Финальная очистка ресурсов"""
        try:
            self._stop_audio()
            self._auto_dismiss_event = None
            logger.info("AlarmPopup cleanup completed")
        except Exception as e:
            logger.error(f"Error in final cleanup: {e}")

    def open_alarm(self):
        """ИСПРАВЛЕННОЕ открытие будильника с воспроизведением звука"""
        try:
            logger.info(f"Opening alarm popup with ringtone: {self.ringtone}")
            
            # Сначала открываем popup
            self.open()
            
            # Затем запускаем аудио
            self._start_audio()
            
            logger.info("✅ Alarm popup opened successfully")
            
        except Exception as e:
            logger.error(f"Error opening alarm popup: {e}")
            # Все равно пытаемся открыть без звука
            try:
                self.open()
            except Exception as open_error:
                logger.error(f"Cannot even open popup: {open_error}")
    
    def _start_audio(self):
        """Запуск аудио для будильника"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'audio_service') or not app.audio_service:
                logger.error("AudioService not available")
                self._play_fallback_sound()
                return
            
            audio_service = app.audio_service
            
            # Проверяем что mixer инициализирован
            if not audio_service.is_mixer_initialized():
                logger.warning("Audio mixer not initialized, trying fallback")
                self._play_fallback_sound()
                return
            
            # Пытаемся воспроизвести рингтон
            if self.ringtone:
                ringtone_path = os.path.join("media", "ringtones", self.ringtone)
                
                if os.path.exists(ringtone_path):
                    logger.info(f"Playing ringtone: {ringtone_path}")
                    
                    # Используем async если доступен
                    if hasattr(audio_service, 'play_async'):
                        audio_service.play_async(ringtone_path)
                    else:
                        audio_service.play(ringtone_path)
                    
                    self._audio_playing = True
                    logger.info("✅ Ringtone started successfully")
                else:
                    logger.error(f"Ringtone file not found: {ringtone_path}")
                    self._play_fallback_sound()
            else:
                logger.warning("No ringtone specified, playing fallback")
                self._play_fallback_sound()
                
        except Exception as e:
            logger.error(f"Error starting audio: {e}")
            self._play_fallback_sound()
    
    def _play_fallback_sound(self):
        """Воспроизведение fallback звука"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'theme_manager') and app.theme_manager:
                # Пытаемся найти подходящий звук
                for sound_name in ["notify", "error", "confirm"]:
                    try:
                        from app.sound_manager import sound_manager
                        
                        if sound_name == "notify":
                            if sound_manager.play_notify():
                                self._audio_playing = True
                                break
                        elif sound_name == "error":
                            if sound_manager.play_error():
                                self._audio_playing = True
                                break
                        elif sound_name == "confirm":
                            if sound_manager.play_confirm():
                                self._audio_playing = True
                                break
                    except Exception as e:
                        logger.error(f"Error playing fallback sound '{sound_name}': {e}")
                else:
                    logger.warning("No fallback sounds available")
            else:
                logger.error("ThemeManager not available for fallback sounds")
                
        except Exception as e:
            logger.error(f"Error playing fallback sound: {e}")
    
    def _play_ui_sound(self, sound_name):
        """Воспроизведение UI звука через sound_manager"""
        try:
            from app.sound_manager import sound_manager
            
            if sound_name == "click":
                sound_manager.play_click()
            elif sound_name == "confirm":
                sound_manager.play_confirm()
            elif sound_name == "error":
                sound_manager.play_error()
            else:
                # Fallback для других звуков
                sound_manager._play_sound(sound_name)
                
        except Exception as e:
            logger.error(f"Error playing UI sound '{sound_name}': {e}")
    
    def _stop_audio(self):
        """Остановка воспроизведения аудио"""
        try:
            if self._audio_playing:
                app = App.get_running_app()
                if hasattr(app, 'audio_service') and app.audio_service:
                    app.audio_service.stop()
                    logger.info("Audio stopped")
                
                self._audio_playing = False
                
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")