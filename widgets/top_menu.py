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
        """Отложенное воспроизведение звука клика"""
        try:
            app = App.get_running_app()
            tm = self.get_theme_manager()
            if hasattr(app, 'audio_service') and app.audio_service and tm:
                sound_file = tm.get_sound("click")
                if sound_file:
                    # Remove the priority parameter since AudioService doesn't support it
                    app.audio_service.play(sound_file)
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
            if not tm or not tm.is_loaded():
                logger.warning("ThemeManager not loaded in TopMenu.refresh_theme")
                return
            
            # Получаем пути к ресурсам один раз
            bg_normal = tm.get_image("menu_button_bg")
            bg_active = tm.get_image("menu_button_bg_active")
            font_path = tm.get_font("main")
            color_normal = tm.get_rgba("menu_button_text")
            color_active = tm.get_rgba("menu_button_text_active")
            
            # Обновляем все кнопки меню одним проходом
            menu_buttons = ["btn_home", "btn_alarm", "btn_schedule", "btn_weather", "btn_pigs", "btn_settings"]
            
            for btn_id in menu_buttons:
                if hasattr(self, 'ids') and btn_id in self.ids:
                    btn = self.ids[btn_id]
                    
                    # Получаем имя экрана для этой кнопки
                    screen_name = getattr(btn, 'screen_name', '')
                    is_active = screen_name == self.current_page
                    
                    # Обновляем все свойства кнопки
                    if hasattr(btn, 'background_normal') and bg_normal:
                        btn.background_normal = bg_normal
                    if hasattr(btn, 'background_down') and bg_active:
                        btn.background_down = bg_active
                    if hasattr(btn, 'color'):
                        btn.color = color_active if is_active else color_normal
                    if hasattr(btn, 'font_name') and font_path:
                        btn.font_name = font_path
            
            logger.debug("Menu theme refreshed efficiently - responding to theme_changed event")
                   
        except Exception as e:
            logger.error(f"Error in _do_refresh_theme: {e}")
                
    def refresh_text(self, *args):
        """Оптимизированное обновление локализованного текста"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'localizer') or not app.localizer:
                return
            
            # Получаем все переводы одним вызовом
            localizer = app.localizer
            
            # Маппинг кнопок к ключам локализации
            button_texts = {
                "btn_home": localizer.tr("menu_home", "Home"),
                "btn_alarm": localizer.tr("menu_alarm", "Alarm"),
                "btn_schedule": localizer.tr("menu_schedule", "School"),
                "btn_weather": localizer.tr("menu_weather", "Weather"),
                "btn_pigs": localizer.tr("menu_pigs", "Pigs"),
                "btn_settings": localizer.tr("menu_settings", "Settings")
            }
            
            # Обновляем тексты кнопок
            for btn_id, text in button_texts.items():
                if hasattr(self, 'ids') and btn_id in self.ids:
                    self.ids[btn_id].text = text
            
            logger.debug("Menu texts refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing menu text: {e}")

    def on_current_page(self, instance, value):
        """Вызывается при изменении current_page"""
        try:
            # Обновляем темы кнопок при смене страницы - отложенно
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.05)
        except Exception as e:
            logger.error(f"Error in TopMenu.on_current_page: {e}")