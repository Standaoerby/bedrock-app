from kivy.properties import StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from app.event_bus import event_bus
from app.logger import app_logger as logger


class RootWidget(FloatLayout):
    """Корневой виджет приложения"""
    
    current_page = StringProperty("home")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme_everywhere)
        
    def switch_screen(self, page_name):
        """Переключение экрана"""
        try:
            if hasattr(self, 'ids') and 'sm' in self.ids:
                self.ids.sm.current = page_name
                self.current_page = page_name
                
                # Обновляем overlay для новой страницы
                self._update_overlay()
                
                logger.debug(f"Switched to screen: {page_name}")
            else:
                logger.error("ScreenManager not found in root widget")
        except Exception as e:
            logger.error(f"Error switching screen to {page_name}: {e}")

    def _update_overlay(self):
        """Обновление overlay изображения для текущей страницы"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'theme_manager') and hasattr(self, 'ids') and 'overlay_image' in self.ids:
                new_overlay = app.theme_manager.get_image("overlay_" + self.current_page)
                if new_overlay != self.ids.overlay_image.source:
                    self.ids.overlay_image.source = new_overlay
        except Exception as e:
            logger.error(f"Error updating overlay: {e}")

    def refresh_theme_everywhere(self, *args, **kwargs):
        """Обновление темы для всех элементов"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'theme_manager'):
                return
            
            # Получаем новые пути к изображениям
            new_bg = app.theme_manager.get_image("background")
            new_overlay = app.theme_manager.get_image("overlay_" + self.current_page)
            
            # Обновляем только если изображения действительно изменились
            if hasattr(self, 'ids'):
                if 'background_image' in self.ids and self.ids.background_image.source != new_bg:
                    self.ids.background_image.source = new_bg
                    
                if 'overlay_image' in self.ids and self.ids.overlay_image.source != new_overlay:
                    self.ids.overlay_image.source = new_overlay
                
                # Обновляем тему меню
                if 'topmenu' in self.ids:
                    self.ids.topmenu.refresh_theme()
            
            logger.debug("Theme refreshed everywhere")
                
        except Exception as e:
            logger.error(f"Error refreshing theme: {e}")

    def on_kv_post(self, base_widget):
        """Вызывается после загрузки KV файла"""
        try:
            # Инициализируем тему после загрузки KV
            self.refresh_theme_everywhere()
        except Exception as e:
            logger.error(f"Error in on_kv_post: {e}")