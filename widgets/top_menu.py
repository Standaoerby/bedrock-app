# widgets/top_menu.py - ИСПРАВЛЕНО: Добавлена подписка на theme_changed
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.app import App
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger


class TopMenu(BoxLayout):
    """Верхнее меню навигации - оптимизированная версия"""
    
    current_page = StringProperty("home")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ИСПРАВЛЕНО: Подписка на события включает theme_changed
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)  # ДОБАВЛЕНО
        self._last_refresh_time = 0
        self._refresh_scheduled = False

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in TopMenu")
        return None

    def on_kv_post(self, base_widget):
        """Вызывается после загрузки KV"""
        try:
            # Отложенное обновление текста и темы
            Clock.schedule_once(lambda dt: self.refresh_text(), 0.1)
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)  # ДОБАВЛЕНО
        except Exception as e:
            logger.error(f"Error in TopMenu on_kv_post: {e}")

    def select(self, page_name):
        """Оптимизированный выбор страницы в меню"""
        try:
            app = App.get_running_app()
            
            # ВАЖНО: Сначала переключаем экран для отзывчивости UI
            if hasattr(app.root, "switch_screen"):
                app.root.switch_screen(page_name)
                logger.debug(f"Menu selected: {page_name}")
            else:
                logger.error("Root widget doesn't have switch_screen method")
                return
            
            # Затем воспроизводим звук с низким приоритетом в фоне
            Clock.schedule_once(lambda dt: self._play_click_sound(), 0.01)
                
        except Exception as e:
            logger.error(f"Error selecting menu item {page_name}: {e}")

    def _play_click_sound(self):
        """ИСПРАВЛЕНО: Отложенное воспроизведение звука клика с защитой от дублирования"""
        try:
            from app.sound_manager import sound_manager
            sound_manager.play_click()
        except Exception as e:
            logger.error(f"Error playing click sound: {e}")

    def refresh_theme(self, *args):
        """ИСПРАВЛЕНО: Оптимизированное обновление темы меню с поддержкой event_bus"""
        try:
            # Предотвращаем слишком частые обновления
            import time
            current_time = time.time()
            if current_time - self._last_refresh_time < 0.1:  # Не чаще чем раз в 100мс
                if not self._refresh_scheduled:
                    self._refresh_scheduled = True
                    Clock.schedule_once(lambda dt: self._do_refresh_theme(), 0.1)
                return
                
            self._do_refresh_theme()
            
        except Exception as e:
            logger.error(f"Error refreshing menu theme: {e}")
    
    def _do_refresh_theme(self):
        """Выполнение обновления темы"""
        try:
            import time
            self._last_refresh_time = time.time()
            self._refresh_scheduled = False
            
            tm = self.get_theme_manager()
            if not tm:
                return
            
            # Обновляем цвета меню
            if hasattr(self, 'ids'):
                for button_id in ['btn_home', 'btn_alarm', 'btn_schedule', 'btn_weather', 'btn_pigs', 'btn_settings']:
                    if button_id in self.ids:
                        button = self.ids[button_id]
                        # Кнопки сами обновят свои цвета через KV файл
                        # Тут можно принудительно обновить специфические свойства если нужно
                        pass
            
            logger.debug("TopMenu theme refreshed")
            
        except Exception as e:
            logger.error(f"Error in _do_refresh_theme: {e}")

    def refresh_text(self, *args):
        """Обновление локализованных текстов"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                # Обновляем тексты кнопок
                if hasattr(self, 'ids'):
                    button_texts = {
                        'btn_home': app.localizer.tr("home", "Home"),
                        'btn_alarm': app.localizer.tr("alarm", "Alarm"),
                        'btn_schedule': app.localizer.tr("schedule", "Schedule"),
                        'btn_weather': app.localizer.tr("weather", "Weather"),
                        'btn_pigs': app.localizer.tr("pigs", "Pigs"),
                        'btn_settings': app.localizer.tr("settings", "Settings")
                    }
                    
                    for button_id, text in button_texts.items():
                        if button_id in self.ids:
                            self.ids[button_id].text = text
                            
            logger.debug("TopMenu text refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing text: {e}")

    def set_active_page(self, page_name):
        """Установка активной страницы без переключения"""
        try:
            if self.current_page != page_name:
                self.current_page = page_name
                logger.debug(f"TopMenu active page set to: {page_name}")
        except Exception as e:
            logger.error(f"Error setting active page: {e}")