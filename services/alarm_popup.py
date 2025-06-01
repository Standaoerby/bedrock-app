from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.app import App
from app.logger import app_logger as logger


class AlarmPopup(ModalView):
    """Попап для срабатывания будильника - УПРОЩЕННАЯ ЛОГИКА"""
    
    def __init__(self, alarm_time="--:--", ringtone="", **kwargs):
        super().__init__(**kwargs)
        self.alarm_time = alarm_time
        self.ringtone = ringtone
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = False  # Не закрываем автоматически
        
        # ДОБАВЛЕНО: флаг для предотвращения множественных вызовов on_dismiss
        self._dismiss_called = False
        self._dismiss_action = None  # "dismiss", "snooze", или None
        
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
        
        # Кнопка отложить (snooze)
        snooze_btn = Button(
            text="Snooze 5min",
            font_size='18sp',
            size_hint_x=0.5
        )
        snooze_btn.bind(on_release=self.on_snooze)
        button_layout.add_widget(snooze_btn)
        
        # Кнопка отключить
        dismiss_btn = Button(
            text="Dismiss",
            font_size='18sp',
            size_hint_x=0.5
        )
        dismiss_btn.bind(on_release=self.on_dismiss_button)
        button_layout.add_widget(dismiss_btn)
        
        main_layout.add_widget(button_layout)
        self.add_widget(main_layout)
        
        logger.info(f"AlarmPopup created for {alarm_time}")

    def on_snooze(self, button):
        """УПРОЩЕНО: Кнопка отложить - только закрывает попап"""
        if self._dismiss_called:
            return  # Избегаем повторных вызовов
        
        logger.info("Snooze button pressed")
        
        # Воспроизводим звук подтверждения
        app = App.get_running_app()
        if hasattr(app, 'audio_service') and hasattr(app, 'theme_manager'):
            sound_file = app.theme_manager.get_sound("confirm")
            if sound_file:
                app.audio_service.play(sound_file)
        
        # Устанавливаем действие и закрываем попап
        self._dismiss_action = "snooze"
        self.dismiss()

    def on_dismiss_button(self, button):
        """УПРОЩЕНО: Кнопка отключить - только закрывает попап"""
        if self._dismiss_called:
            return  # Избегаем повторных вызовов
        
        logger.info("Dismiss button pressed")
        
        # Воспроизводим звук подтверждения
        app = App.get_running_app()
        if hasattr(app, 'audio_service') and hasattr(app, 'theme_manager'):
            sound_file = app.theme_manager.get_sound("click")
            if sound_file:
                app.audio_service.play(sound_file)
        
        # Устанавливаем действие и закрываем попап
        self._dismiss_action = "dismiss"
        self.dismiss()

    def on_dismiss(self):
        """УПРОЩЕНО: Всегда останавливает будильник, обрабатывает действие"""
        # Защита от множественных вызовов
        if self._dismiss_called:
            logger.debug("on_dismiss already called, skipping")
            return False
        
        self._dismiss_called = True
        logger.info(f"AlarmPopup on_dismiss called (action: {self._dismiss_action})")
        
        try:
            app = App.get_running_app()
            
            # Выполняем действие в зависимости от того, как закрыли попап
            if self._dismiss_action == "snooze":
                logger.info("Processing snooze action")
                # Отложить будильник на 5 минут
                if hasattr(app, 'alarm_clock') and app.alarm_clock:
                    app.alarm_clock.snooze_alarm(5)
            elif self._dismiss_action == "dismiss":
                logger.info("Processing dismiss action")
                # Просто останавливаем будильник (без снуза)
                if hasattr(app, 'alarm_clock') and app.alarm_clock:
                    app.alarm_clock._force_stop_alarm_internal()
            else:
                # Попап закрыт другим способом (ESC, клик вне попапа и т.д.)
                logger.info("Processing system dismiss")
                if hasattr(app, 'alarm_clock') and app.alarm_clock:
                    app.alarm_clock._force_stop_alarm_internal()
            
        except Exception as e:
            logger.error(f"Error in on_dismiss: {e}")
        
        # Важно: возвращаем False, чтобы попап действительно закрылся
        return False

    def open_alarm(self):
        """Открытие попапа будильника"""
        logger.info("Opening alarm popup")
        
        # Воспроизводим звук будильника
        app = App.get_running_app()
        if hasattr(app, 'audio_service'):
            try:
                import os
                
                # Попытка воспроизвести указанный рингтон
                if self.ringtone:
                    ringtone_path = os.path.join("media", "ringtones", self.ringtone)
                    if os.path.exists(ringtone_path):
                        app.audio_service.play(ringtone_path)
                        logger.info(f"Playing alarm ringtone: {self.ringtone}")
                    else:
                        logger.warning(f"Ringtone file not found: {ringtone_path}")
                        self._play_fallback_sound(app)
                else:
                    self._play_fallback_sound(app)
                    
            except Exception as e:
                logger.error(f"Error playing alarm ringtone: {e}")
                self._play_fallback_sound(app)
        
        # Открываем попап
        self.open()
    
    def _play_fallback_sound(self, app):
        """Воспроизведение резервного звука будильника"""
        try:
            # Пытаемся воспроизвести звук из темы
            if hasattr(app, 'theme_manager'):
                fallback_sound = app.theme_manager.get_sound("notify")
                if fallback_sound:
                    app.audio_service.play(fallback_sound)
                    logger.info("Playing fallback alarm sound from theme")
                    return
            
            logger.warning("No fallback alarm sound available")
            
        except Exception as e:
            logger.error(f"Error playing fallback alarm sound: {e}")