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

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in RootWidget")
        return None
        
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
            tm = self.get_theme_manager()
            if tm and tm.is_loaded() and hasattr(self, 'ids') and 'overlay_image' in self.ids:
                new_overlay = tm.get_image("overlay_" + self.current_page)
                if new_overlay and new_overlay != self.ids.overlay_image.source:
                    self.ids.overlay_image.source = new_overlay
                    logger.debug(f"Updated overlay for page: {self.current_page}")
            else:
                logger.warning("Cannot update overlay - theme manager not available or not loaded")
        except Exception as e:
            logger.error(f"Error updating overlay: {e}")

    def refresh_theme_everywhere(self, *args, **kwargs):
        """Обновление темы для всех элементов"""
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                logger.warning("ThemeManager not loaded, cannot refresh theme")
                return
            
            # Получаем новые пути к изображениям
            new_bg = tm.get_image("background")
            new_overlay = tm.get_image("overlay_" + self.current_page)
            
            # Обновляем только если изображения действительно изменились и существуют
            if hasattr(self, 'ids'):
                if 'background_image' in self.ids and new_bg and self.ids.background_image.source != new_bg:
                    self.ids.background_image.source = new_bg
                    logger.debug(f"Updated background image: {new_bg}")
                    
                if 'overlay_image' in self.ids and new_overlay and self.ids.overlay_image.source != new_overlay:
                    self.ids.overlay_image.source = new_overlay
                    logger.debug(f"Updated overlay image: {new_overlay}")
                
                # Обновляем тему меню
                if 'topmenu' in self.ids and hasattr(self.ids.topmenu, 'refresh_theme'):
                    self.ids.topmenu.refresh_theme()
                    logger.debug("Updated top menu theme")
            
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

    def on_current_page(self, instance, value):
        """Вызывается при изменении current_page"""
        try:
            # Обновляем overlay при смене страницы
            self._update_overlay()
            
            # Обновляем состояние меню
            if hasattr(self, 'ids') and 'topmenu' in self.ids:
                self.ids.topmenu.current_page = value
                if hasattr(self.ids.topmenu, 'refresh_theme'):
                    self.ids.topmenu.refresh_theme()
        except Exception as e:
            logger.error(f"Error in on_current_page: {e}")