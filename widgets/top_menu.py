# widgets/top_menu.py - ИСПРАВЛЕНО: Принудительное обновление всех элементов

from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.app import App
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger


class TopMenu(BoxLayout):
    """Верхнее меню навигации с принудительным обновлением темы"""
    
    current_page = StringProperty("home")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
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
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
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
            from app.sound_manager import sound_manager
            sound_manager.play_click()
        except Exception as e:
            logger.error(f"Error playing click sound: {e}")

    def refresh_theme(self, *args):
        """Оптимизированное обновление темы меню"""
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
            
            # 🚨 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Принудительно обновляем ВСЕ элементы
            self._force_update_all_elements()
            
            logger.debug("TopMenu theme refreshed")
            
        except Exception as e:
            logger.error(f"Error in _do_refresh_theme: {e}")

    def force_complete_refresh(self):
        """🚨 КРИТИЧЕСКОЕ: Принудительное полное обновление TopMenu"""
        try:
            logger.debug("TopMenu: Force complete refresh")
            # Сбрасываем ограничения времени для принудительного обновления
            self._last_refresh_time = 0
            self._refresh_scheduled = False
            
            # Выполняем полное обновление
            self._force_update_all_elements()
            self.refresh_text()
            
            # Принудительно обновляем canvas
            if hasattr(self, 'canvas'):
                self.canvas.ask_update()
                
        except Exception as e:
            logger.error(f"Error in force_complete_refresh: {e}")

    def _force_update_all_elements(self):
        """🚨 КРИТИЧЕСКОЕ: Принудительное обновление ВСЕХ элементов TopMenu"""
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                return
            
            # 1. Обновляем высоту самого TopMenu
            menu_height = tm.get_param("menu_height") or 56
            if self.height != menu_height:
                self.height = menu_height
                self.size_hint_y = None
                logger.debug(f"✅ TopMenu height updated to: {menu_height}")
            
            # 2. Обновляем background color
            menu_color = tm.get_rgba("menu_color")
            if hasattr(self, 'canvas'):
                # Принудительно перерисовываем background
                self.canvas.ask_update()
                logger.debug("✅ TopMenu background color updated")
            
            # 3. Принудительно обновляем ВСЕ кнопки
            if hasattr(self, 'ids'):
                button_ids = ['btn_home', 'btn_alarm', 'btn_schedule', 'btn_weather', 'btn_pigs', 'btn_settings']
                for button_id in button_ids:
                    if button_id in self.ids:
                        button = self.ids[button_id]
                        self._force_update_button(button, tm)
            
            logger.debug("✅ All TopMenu elements force updated")
            
        except Exception as e:
            logger.error(f"Error in _force_update_all_elements: {e}")

    def _force_update_button(self, button, tm):
        """Принудительное обновление одной кнопки"""
        try:
            # Обновляем размеры кнопки
            button_width = tm.get_param("menu_button_width") or 120
            button_height = tm.get_param("menu_button_height") or 40
            
            if button.width != button_width:
                button.width = button_width
                button.size_hint_x = None
            if button.height != button_height:
                button.height = button_height
                button.size_hint_y = None
            
            # Обновляем шрифт
            font_name = tm.get_font("main")
            if button.font_name != font_name:
                button.font_name = font_name
            
            # Обновляем цвета (зависит от active состояния)
            is_active = getattr(button, 'active', False)
            if is_active:
                button.color = tm.get_rgba("menu_button_text_active")
            else:
                button.color = tm.get_rgba("menu_button_text")
            
            # Обновляем background изображения
            if is_active:
                bg_image = tm.get_image("menu_button_bg_active")
            else:
                bg_image = tm.get_image("menu_button_bg")
            
            if bg_image:
                button.background_normal = bg_image
                button.background_down = tm.get_image("menu_button_bg_active") or bg_image
            
            logger.debug(f"✅ Button {getattr(button, 'screen_name', 'unknown')} force updated")
            
        except Exception as e:
            logger.error(f"Error force updating button: {e}")

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
                # Принудительно обновляем active состояния кнопок
                self._update_button_active_states()
                logger.debug(f"TopMenu active page set to: {page_name}")
        except Exception as e:
            logger.error(f"Error setting active page: {e}")

    def _update_button_active_states(self):
        """Обновление active состояний всех кнопок"""
        try:
            if hasattr(self, 'ids'):
                # Определяем какая кнопка должна быть активной
                button_mappings = {
                    'btn_home': 'home',
                    'btn_alarm': 'alarm', 
                    'btn_schedule': 'schedule',
                    'btn_weather': 'weather',
                    'btn_pigs': 'pigs',
                    'btn_settings': 'settings'
                }
                
                tm = self.get_theme_manager()
                if not tm:
                    return
                
                for button_id, page_name in button_mappings.items():
                    if button_id in self.ids:
                        button = self.ids[button_id]
                        is_active = (page_name == self.current_page)
                        
                        # Обновляем active свойство
                        if hasattr(button, 'active'):
                            button.active = is_active
                        
                        # Принудительно обновляем кнопку с новым состоянием
                        self._force_update_button(button, tm)
                        
        except Exception as e:
            logger.error(f"Error updating button active states: {e}")