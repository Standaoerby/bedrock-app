# widgets/root_widget.py
"""
УЛУЧШЕННЫЙ RootWidget с централизованным управлением темами
Содержит логику для принудительного обновления всех экранов
"""

from kivy.properties import StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger


class RootWidget(FloatLayout):
    """
    Улучшенный корневой виджет с централизованным управлением темами.
    Координирует обновление темы для всех экранов приложения.
    """
    
    current_page = StringProperty("home")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Подписка на события
        event_bus.subscribe("theme_changed", self.on_global_theme_changed)
        event_bus.subscribe("language_changed", self.on_global_language_changed)
        
        # Менеджер экранов
        self.screen_manager = None
        
        # Флаги для предотвращения дублирования обновлений
        self._theme_update_in_progress = False
        self._language_update_in_progress = False
        
        # Кэш всех экранов для быстрого доступа
        self._screen_cache = {}

    def on_kv_post(self, base_widget):
        """Вызывается после загрузки KV файла"""
        try:
            # Устанавливаем screen_manager из ids после загрузки KV
            if hasattr(self, 'ids') and 'sm' in self.ids:
                self.screen_manager = self.ids.sm
                
                # Кэшируем все экраны для быстрого доступа
                self._cache_all_screens()
                
                logger.debug("RootWidget initialized with screen manager")
            else:
                logger.warning("ScreenManager 'sm' not found in KV file")
        except Exception as e:
            logger.error(f"Error in RootWidget on_kv_post: {e}")

    def _cache_all_screens(self):
        """Кэширование всех экранов для быстрого доступа"""
        try:
            if self.screen_manager and hasattr(self.screen_manager, 'screens'):
                for screen in self.screen_manager.screens:
                    self._screen_cache[screen.name] = screen
                logger.debug(f"Cached {len(self._screen_cache)} screens")
        except Exception as e:
            logger.error(f"Error caching screens: {e}")

    # ======================================
    # НАВИГАЦИЯ МЕЖДУ ЭКРАНАМИ
    # ======================================

    def switch_screen(self, page_name):
        """Улучшенное переключение экрана с обработкой ошибок"""
        try:
            # Метод 1: Используем screen_manager атрибут
            if self.screen_manager:
                self.screen_manager.current = page_name
                self.current_page = page_name
                
                # Обновляем overlay для новой страницы
                self._update_overlay()
                
                # Убеждаемся, что новый экран имеет актуальную тему
                self._ensure_screen_theme_updated(page_name)
                
                logger.debug(f"Switched to screen: {page_name}")
                return True
                
            # Метод 2: Используем ids.sm
            elif hasattr(self, 'ids') and 'sm' in self.ids:
                self.ids.sm.current = page_name
                self.current_page = page_name
                
                # Устанавливаем screen_manager если не был установлен
                if not self.screen_manager:
                    self.screen_manager = self.ids.sm
                    self._cache_all_screens()
                
                # Обновляем overlay для новой страницы
                self._update_overlay()
                
                # Убеждаемся, что новый экран имеет актуальную тему
                self._ensure_screen_theme_updated(page_name)
                
                logger.debug(f"Switched to screen: {page_name} via ids.sm")
                return True
            else:
                logger.error("ScreenManager not found in root widget")
                return False
                
        except Exception as e:
            logger.error(f"Error switching screen to {page_name}: {e}")
            return False

    def _ensure_screen_theme_updated(self, screen_name):
        """Убеждаемся, что экран имеет актуальную тему"""
        try:
            screen = self._screen_cache.get(screen_name)
            if screen and hasattr(screen, 'refresh_theme'):
                # Планируем обновление темы для экрана с небольшой задержкой
                Clock.schedule_once(lambda dt: screen.refresh_theme(), 0.1)
        except Exception as e:
            logger.debug(f"Minor error ensuring theme update for {screen_name}: {e}")

    def _update_overlay(self):
        """Обновление overlay изображения для текущей страницы"""
        try:
            tm = self.get_theme_manager()
            if tm and tm.is_loaded() and hasattr(self, 'ids') and 'overlay_image' in self.ids:
                new_overlay = tm.get_image("overlay_" + self.current_page)
                if new_overlay and new_overlay != self.ids.overlay_image.source:
                    self.ids.overlay_image.source = new_overlay
                    logger.debug(f"Updated overlay for page: {self.current_page}")
        except Exception as e:
            logger.error(f"Error updating overlay: {e}")

    # ======================================
    # ЦЕНТРАЛИЗОВАННОЕ УПРАВЛЕНИЕ ТЕМАМИ
    # ======================================

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'theme_manager') and app.theme_manager:
                return app.theme_manager
            logger.warning("ThemeManager not available in RootWidget")
            return None
        except Exception as e:
            logger.error(f"Error getting theme manager: {e}")
            return None

    def on_global_theme_changed(self, *args):
        """Обработка глобального изменения темы"""
        if self._theme_update_in_progress:
            logger.debug("Theme update already in progress, skipping")
            return
            
        try:
            self._theme_update_in_progress = True
            logger.info("Processing global theme change")
            
            # Планируем обновление с задержкой для предотвращения блокировки UI
            Clock.schedule_once(self._execute_global_theme_update, 0.1)
            
        except Exception as e:
            logger.error(f"Error handling global theme change: {e}")
            self._theme_update_in_progress = False

    def _execute_global_theme_update(self, dt):
        """Выполнение глобального обновления темы"""
        try:
            # 1. Обновляем корневой виджет
            self._update_root_theme()
            
            # 2. Обновляем все экраны
            self._update_all_screens_theme()
            
            # 3. Обновляем специальные виджеты
            self._update_special_widgets_theme()
            
            logger.info("Global theme update completed")
            
        except Exception as e:
            logger.error(f"Error executing global theme update: {e}")
        finally:
            self._theme_update_in_progress = False

    def _update_root_theme(self):
        """Обновление темы корневого виджета"""
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                return
            
            # Обновляем overlay
            self._update_overlay()
            
            # Обновляем фон, если есть
            if hasattr(self, 'ids') and 'background_image' in self.ids:
                bg_image = tm.get_image("background")
                if bg_image:
                    self.ids.background_image.source = bg_image
                    
        except Exception as e:
            logger.error(f"Error updating root theme: {e}")

    def _update_all_screens_theme(self):
        """Обновление темы для всех экранов"""
        try:
            updated_count = 0
            
            # Проходим по всем кэшированным экранам
            for screen_name, screen in self._screen_cache.items():
                try:
                    if hasattr(screen, 'refresh_theme'):
                        # Планируем обновление с индивидуальной задержкой
                        delay = updated_count * 0.05  # Небольшие задержки между экранами
                        Clock.schedule_once(
                            lambda dt, s=screen: s.refresh_theme(), 
                            delay
                        )
                        updated_count += 1
                except Exception as e:
                    logger.debug(f"Error updating theme for screen {screen_name}: {e}")
            
            logger.debug(f"Scheduled theme updates for {updated_count} screens")
            
        except Exception as e:
            logger.error(f"Error updating all screens theme: {e}")

    def _update_special_widgets_theme(self):
        """Обновление темы для специальных виджетов (меню, overlay и т.д.)"""
        try:
            # Обновляем верхнее меню
            if hasattr(self, 'ids') and 'top_menu' in self.ids:
                menu = self.ids.top_menu
                if hasattr(menu, 'refresh_theme'):
                    Clock.schedule_once(lambda dt: menu.refresh_theme(), 0.2)
            
            # Обновляем другие специальные виджеты
            special_widgets = ['bottom_panel', 'side_menu', 'notification_bar']
            for widget_id in special_widgets:
                if hasattr(self, 'ids') and widget_id in self.ids:
                    widget = self.ids[widget_id]
                    if hasattr(widget, 'refresh_theme'):
                        Clock.schedule_once(lambda dt, w=widget: w.refresh_theme(), 0.3)
                        
        except Exception as e:
            logger.error(f"Error updating special widgets theme: {e}")

    def force_refresh_all_themes(self):
        """Принудительное обновление темы для всех компонентов"""
        try:
            logger.info("Force refreshing all themes")
            
            # Сбрасываем флаг, если он застрял
            self._theme_update_in_progress = False
            
            # Очищаем кэш тем у всех экранов
            for screen in self._screen_cache.values():
                if hasattr(screen, 'clear_theme_cache'):
                    screen.clear_theme_cache()
            
            # Запускаем обновление
            self.on_global_theme_changed()
            
        except Exception as e:
            logger.error(f"Error force refreshing themes: {e}")

    # ======================================
    # ЦЕНТРАЛИЗОВАННОЕ УПРАВЛЕНИЕ ЛОКАЛИЗАЦИЕЙ
    # ======================================

    def on_global_language_changed(self, *args):
        """Обработка глобального изменения языка"""
        if self._language_update_in_progress:
            logger.debug("Language update already in progress, skipping")
            return
            
        try:
            self._language_update_in_progress = True
            logger.info("Processing global language change")
            
            # Планируем обновление с задержкой
            Clock.schedule_once(self._execute_global_language_update, 0.1)
            
        except Exception as e:
            logger.error(f"Error handling global language change: {e}")
            self._language_update_in_progress = False

    def _execute_global_language_update(self, dt):
        """Выполнение глобального обновления языка"""
        try:
            updated_count = 0
            
            # Обновляем все экраны
            for screen_name, screen in self._screen_cache.items():
                try:
                    if hasattr(screen, 'refresh_text'):
                        # Планируем обновление с небольшой задержкой
                        delay = updated_count * 0.03
                        Clock.schedule_once(
                            lambda dt, s=screen: s.refresh_text(),
                            delay
                        )
                        updated_count += 1
                except Exception as e:
                    logger.debug(f"Error updating language for screen {screen_name}: {e}")
            
            # Обновляем специальные виджеты
            self._update_special_widgets_language()
            
            logger.info(f"Global language update completed for {updated_count} screens")
            
        except Exception as e:
            logger.error(f"Error executing global language update: {e}")
        finally:
            self._language_update_in_progress = False

    def _update_special_widgets_language(self):
        """Обновление языка для специальных виджетов"""
        try:
            # Обновляем верхнее меню
            if hasattr(self, 'ids') and 'top_menu' in self.ids:
                menu = self.ids.top_menu
                if hasattr(menu, 'refresh_text'):
                    Clock.schedule_once(lambda dt: menu.refresh_text(), 0.1)
                    
        except Exception as e:
            logger.error(f"Error updating special widgets language: {e}")

    # ======================================
    # УТИЛИТЫ И ДИАГНОСТИКА
    # ======================================

    def get_screen_by_name(self, screen_name):
        """Получение экрана по имени"""
        return self._screen_cache.get(screen_name)

    def get_current_screen(self):
        """Получение текущего активного экрана"""
        return self._screen_cache.get(self.current_page)

    def diagnose_theme_state(self):
        """Диагностика состояния тем для отладки"""
        try:
            tm = self.get_theme_manager()
            current_screen = self.get_current_screen()
            
            info = {
                "theme_manager_available": tm is not None,
                "theme_loaded": tm.is_loaded() if tm else False,
                "current_theme": getattr(tm, 'theme_name', None) if tm else None,
                "current_variant": getattr(tm, 'variant', None) if tm else None,
                "current_page": self.current_page,
                "current_screen_available": current_screen is not None,
                "screen_cache_size": len(self._screen_cache),
                "theme_update_in_progress": self._theme_update_in_progress,
                "language_update_in_progress": self._language_update_in_progress
            }
            
            logger.info(f"Theme state diagnosis: {info}")
            return info
            
        except Exception as e:
            logger.error(f"Error diagnosing theme state: {e}")
            return {"error": str(e)}

    def emergency_theme_reset(self):
        """Экстренный сброс состояния тем"""
        try:
            logger.warning("Performing emergency theme reset")
            
            # Сбрасываем все флаги
            self._theme_update_in_progress = False
            self._language_update_in_progress = False
            
            # Принудительно обновляем всё
            self.force_refresh_all_themes()
            
        except Exception as e:
            logger.error(f"Error in emergency theme reset: {e}")