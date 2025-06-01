from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.app import App
from app.event_bus import event_bus
from app.logger import app_logger as logger


class TopMenu(BoxLayout):
    """Верхнее меню навигации"""
    
    current_page = StringProperty("home")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)

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
            self.refresh_text()
        except Exception as e:
            logger.error(f"Error in TopMenu on_kv_post: {e}")

    def select(self, page_name):
        """Выбор страницы в меню"""
        try:
            app = App.get_running_app()
            
            # Воспроизводим звук ДО смены экрана
            tm = self.get_theme_manager()
            if hasattr(app, 'audio_service') and app.audio_service and tm:
                sound_file = tm.get_sound("click")
                if sound_file:
                    app.audio_service.play(sound_file)
            
            # Меняем экран
            if hasattr(app.root, "switch_screen"):
                app.root.switch_screen(page_name)
                logger.debug(f"Menu selected: {page_name}")
            else:
                logger.error("Root widget doesn't have switch_screen method")
                
        except Exception as e:
            logger.error(f"Error selecting menu item {page_name}: {e}")

    def refresh_theme(self):
        """Обновление темы меню"""
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                logger.warning("ThemeManager not loaded in TopMenu.refresh_theme")
                return
            
            # Обновляем все кнопки меню
            menu_buttons = ["btn_home", "btn_alarm", "btn_schedule", "btn_weather", "btn_pigs", "btn_settings"]
            
            for btn_id in menu_buttons:
                if hasattr(self, 'ids') and btn_id in self.ids:
                    btn = self.ids[btn_id]
                    
                    # Обновляем фон кнопки
                    if hasattr(btn, 'background_normal'):
                        bg_normal = tm.get_image("menu_button_bg")
                        bg_active = tm.get_image("menu_button_bg_active")
                        if bg_normal:
                            btn.background_normal = bg_normal
                        if bg_active:
                            btn.background_down = bg_active
                    
                    # Обновляем цвет текста кнопки
                    if hasattr(btn, 'color'):
                        # Проверяем активность кнопки
                        screen_name = getattr(btn, 'screen_name', '')
                        is_active = screen_name == self.current_page
                        
                        if is_active:
                            btn.color = tm.get_rgba("menu_button_text_active")
                        else:
                            btn.color = tm.get_rgba("menu_button_text")
                    
                    # Обновляем шрифт
                    if hasattr(btn, 'font_name'):
                        font_path = tm.get_font("main")
                        if font_path:
                            btn.font_name = font_path
            
            logger.debug("Menu theme refreshed")
                        
        except Exception as e:
            logger.error(f"Error refreshing menu theme: {e}")
                
    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'localizer') or not app.localizer:
                return
            
            # Маппинг кнопок к ключам локализации
            button_texts = {
                "btn_home": ("menu_home", "Home"),
                "btn_alarm": ("menu_alarm", "Alarm"),
                "btn_schedule": ("menu_schedule", "School"),
                "btn_weather": ("menu_weather", "Weather"),
                "btn_pigs": ("menu_pigs", "Pigs"),
                "btn_settings": ("menu_settings", "Settings")
            }
            
            for btn_id, (key, default) in button_texts.items():
                if hasattr(self, 'ids') and btn_id in self.ids:
                    self.ids[btn_id].text = app.localizer.tr(key, default)
            
            logger.debug("Menu texts refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing menu text: {e}")

    def on_current_page(self, instance, value):
        """Вызывается при изменении current_page"""
        try:
            # Обновляем темы кнопок при смене страницы
            self.refresh_theme()
        except Exception as e:
            logger.error(f"Error in TopMenu.on_current_page: {e}")