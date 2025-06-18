# widgets/root_widget.py
# ИСПРАВЛЕНО: Добавлено полное обновление темы для RootWidget

from kivy.properties import StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from app.event_bus import event_bus
from app.logger import app_logger as logger


class RootWidget(FloatLayout):
    """ИСПРАВЛЕНО: Корневой виджет с полным обновлением темы"""
    
    current_page = StringProperty("home")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ИСПРАВЛЕНО: Подписка на полное обновление темы + overlay
        event_bus.subscribe("theme_changed", self.refresh_theme_completely)
        
        # Инициализируем screen_manager как None
        # Будет установлен после загрузки KV файла
        self.screen_manager = None

    def on_kv_post(self, base_widget):
        """Вызывается после загрузки KV файла"""
        try:
            # Устанавливаем screen_manager из ids после загрузки KV
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
        """Переключение экрана с улучшенной обработкой ошибок"""
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

    def refresh_theme_completely(self, *args):
        """🚨 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: ПОЛНОЕ обновление темы RootWidget"""
        try:
            logger.debug("RootWidget: Complete theme refresh")
            
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                logger.warning("ThemeManager not loaded, cannot refresh RootWidget theme")
                return
            
            # 1. Обновляем background изображение
            if hasattr(self, 'ids') and 'background_image' in self.ids:
                new_bg = tm.get_image("background")
                if new_bg and new_bg != self.ids.background_image.source:
                    self.ids.background_image.source = new_bg
                    logger.debug(f"✅ RootWidget background updated: {new_bg}")
            
            # 2. Обновляем overlay изображение для текущей страницы
            self._update_overlay()
            
            # 3. Обновляем canvas если есть фоновые цвета
            if hasattr(self, 'canvas'):
                self.canvas.ask_update()
                logger.debug("✅ RootWidget canvas updated")
            
            # 4. Если есть другие UI элементы в RootWidget - обновляем их
            self._update_root_ui_elements()
            
            logger.debug("🎉 RootWidget theme completely refreshed")
            
        except Exception as e:
            logger.error(f"Error in RootWidget complete theme refresh: {e}")

    def _update_overlay(self, *args):
        """Обновление overlay изображения для текущей страницы"""
        try:
            tm = self.get_theme_manager()
            if tm and tm.is_loaded() and hasattr(self, 'ids') and 'overlay_image' in self.ids:
                overlay_name = f"overlay_{self.current_page}"
                new_overlay = tm.get_image(overlay_name)
                if new_overlay and new_overlay != self.ids.overlay_image.source:
                    self.ids.overlay_image.source = new_overlay
                    logger.debug(f"✅ Overlay updated for page: {self.current_page}")
                elif not new_overlay:
                    logger.debug(f"⚠️ No overlay image found for page: {self.current_page}")
            else:
                logger.debug("Cannot update overlay - theme manager not available or not loaded")
        except Exception as e:
            logger.error(f"Error updating overlay: {e}")

    def _update_root_ui_elements(self):
        """Обновление других UI элементов в RootWidget"""
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                return
            
            # Если в RootWidget есть другие элементы (кнопки, лейблы и т.д.) - обновляем их
            if hasattr(self, 'ids'):
                for widget_id, widget in self.ids.items():
                    # Обновляем цвета текста если есть
                    if hasattr(widget, 'color') and widget_id != 'background_image' and widget_id != 'overlay_image':
                        if hasattr(widget, 'text'):  # Это текстовый элемент
                            widget.color = tm.get_rgba("text")
                            logger.debug(f"✅ Updated color for {widget_id}")
                    
                    # Обновляем шрифты если есть
                    if hasattr(widget, 'font_name'):
                        widget.font_name = tm.get_font("main")
                        logger.debug(f"✅ Updated font for {widget_id}")
                        
        except Exception as e:
            logger.error(f"Error updating root UI elements: {e}")

    # Оставляем остальные методы без изменений
    def get_current_screen(self):
        """Получить текущий экран"""
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
        """Получить экран по имени"""
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
        """Диагностика состояния RootWidget"""
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
        """Верификация экземпляра RootWidget"""
        return {
            "class_name": self.__class__.__name__,
            "has_screen_manager": hasattr(self, 'screen_manager'),
            "screen_manager_value": str(self.screen_manager),
            "methods": [method for method in dir(self) if not method.startswith('_')]
        }