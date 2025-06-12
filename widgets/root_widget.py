# widgets/root_widget.py
# ИСПРАВЛЕНО: Добавлен атрибут screen_manager для совместимости

from kivy.properties import StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from app.event_bus import event_bus
from app.logger import app_logger as logger


class RootWidget(FloatLayout):
    """ИСПРАВЛЕНО: Корневой виджет приложения с правильными атрибутами"""
    
    current_page = StringProperty("home")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme_everywhere)
        
        # ИСПРАВЛЕНО: Инициализируем screen_manager как None
        # Будет установлен после загрузки KV файла
        self.screen_manager = None

    def on_kv_post(self, base_widget):
        """НОВОЕ: Вызывается после загрузки KV файла"""
        try:
            # ИСПРАВЛЕНО: Устанавливаем screen_manager из ids после загрузки KV
            if hasattr(self, 'ids') and 'sm' in self.ids:
                self.screen_manager = self.ids.sm
                logger.debug("screen_manager initialized from KV")
            else:
                logger.warning("ScreenManager 'sm' not found in KV file")
        except Exception as e:
            logger.error(f"Error in RootWidget on_kv_post: {e}")

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in RootWidget")
        return None
        
    def switch_screen(self, page_name):
        """ИСПРАВЛЕНО: Переключение экрана с улучшенной обработкой ошибок"""
        try:
            # Метод 1: Используем screen_manager атрибут
            if self.screen_manager:
                self.screen_manager.current = page_name
                self.current_page = page_name
                
                # Обновляем overlay для новой страницы
                self._update_overlay()
                
                logger.debug(f"Switched to screen: {page_name}")
                return True
                
            # Метод 2: Используем ids.sm
            elif hasattr(self, 'ids') and 'sm' in self.ids:
                self.ids.sm.current = page_name
                self.current_page = page_name
                
                # Устанавливаем screen_manager если не был установлен
                if not self.screen_manager:
                    self.screen_manager = self.ids.sm
                
                # Обновляем overlay для новой страницы
                self._update_overlay()
                
                logger.debug(f"Switched to screen: {page_name} via ids.sm")
                return True
            else:
                logger.error("ScreenManager not found in root widget - no sm in ids and no screen_manager attribute")
                return False
                
        except Exception as e:
            logger.error(f"Error switching screen to {page_name}: {e}")
            return False

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
                logger.debug("Cannot update overlay - theme manager not available or not loaded")
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
                    
        except Exception as e:
            logger.error(f"Error refreshing theme: {e}")

    def get_current_screen(self):
        """НОВОЕ: Получить текущий экран"""
        try:
            if self.screen_manager:
                return self.screen_manager.current_screen
            elif hasattr(self, 'ids') and 'sm' in self.ids:
                return self.ids.sm.current_screen
            return None
        except Exception as e:
            logger.error(f"Error getting current screen: {e}")
            return None

    def get_screen_by_name(self, name):
        """НОВОЕ: Получить экран по имени"""
        try:
            if self.screen_manager:
                return self.screen_manager.get_screen(name)
            elif hasattr(self, 'ids') and 'sm' in self.ids:
                return self.ids.sm.get_screen(name)
            return None
        except Exception as e:
            logger.error(f"Error getting screen {name}: {e}")
            return None

    def diagnose_state(self):
        """НОВОЕ: Диагностика состояния RootWidget"""
        try:
            return {
                "current_page": self.current_page,
                "has_screen_manager": bool(self.screen_manager),
                "has_ids": hasattr(self, 'ids'),
                "has_sm_in_ids": hasattr(self, 'ids') and 'sm' in self.ids if hasattr(self, 'ids') else False,
                "screen_manager_type": type(self.screen_manager).__name__ if self.screen_manager else None,
                "available_screens": list(self.screen_manager.screen_names) if self.screen_manager else [],
                "theme_manager_available": bool(self.get_theme_manager())
            }
        except Exception as e:
            return {"error": str(e)}

    def verify_instance(self):
        """НОВОЕ: Верификация экземпляра RootWidget"""
        return {
            "class_name": self.__class__.__name__,
            "has_screen_manager": hasattr(self, 'screen_manager'),
            "screen_manager_value": str(self.screen_manager),
            "methods": [method for method in dir(self) if not method.startswith('_')]
        }


def validate_root_widget_module():
    """НОВОЕ: Валидация модуля RootWidget для отладки"""
    try:
        widget = RootWidget()
        assert hasattr(widget, 'screen_manager'), "screen_manager attribute missing"
        assert hasattr(widget, 'switch_screen'), "switch_screen method missing"
        assert hasattr(widget, 'current_page'), "current_page property missing"
        print("✅ RootWidget module validation passed")
        return True
    except Exception as e:
        print(f"❌ RootWidget module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_root_widget_module()