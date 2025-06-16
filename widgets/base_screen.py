# widgets/base_screen.py
"""
Базовый класс для всех страниц приложения с централизованным управлением темами
"""

from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger


class BaseScreen(Screen):
    """
    Базовый класс для всех экранов приложения.
    Содержит всю логику управления темами и локализацией.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Флаги для оптимизации обновлений
        self._theme_refresh_scheduled = False
        self._text_refresh_scheduled = False
        self._is_initialized = False
        
        # Подписка на глобальные события
        self._subscribe_to_events()
        
        # Планируем инициализацию после создания экрана
        Clock.schedule_once(self._delayed_initialization, 0.1)

    def _subscribe_to_events(self):
        """Подписка на события системы"""
        try:
            event_bus.subscribe("theme_changed", self._schedule_theme_refresh)
            event_bus.subscribe("language_changed", self._schedule_text_refresh)
            logger.debug(f"Events subscribed for {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error subscribing to events in {self.__class__.__name__}: {e}")

    def _delayed_initialization(self, dt):
        """Отложенная инициализация после создания виджетов"""
        try:
            self._is_initialized = True
            self.on_screen_initialized()
            logger.debug(f"Screen initialized: {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error in delayed initialization for {self.__class__.__name__}: {e}")

    def on_screen_initialized(self):
        """
        Переопределяемый метод для дочерних классов.
        Вызывается после полной инициализации экрана.
        """
        pass

    # ======================================
    # УПРАВЛЕНИЕ ТЕМАМИ
    # ======================================

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'theme_manager') and app.theme_manager:
                return app.theme_manager
            logger.warning(f"ThemeManager not available in {self.__class__.__name__}")
            return None
        except Exception as e:
            logger.error(f"Error getting theme manager in {self.__class__.__name__}: {e}")
            return None

    def _schedule_theme_refresh(self, *args):
        """Планирование обновления темы (избегаем множественные вызовы)"""
        if not self._theme_refresh_scheduled:
            self._theme_refresh_scheduled = True
            Clock.schedule_once(self._execute_theme_refresh, 0.1)

    def _execute_theme_refresh(self, dt):
        """Выполнение обновления темы"""
        try:
            self._theme_refresh_scheduled = False
            if self._is_initialized:
                self.refresh_theme()
        except Exception as e:
            logger.error(f"Error executing theme refresh in {self.__class__.__name__}: {e}")

    def refresh_theme(self):
        """
        Основной метод обновления темы.
        Автоматически обновляет все виджеты с учетом текущей темы.
        """
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                logger.warning(f"Theme manager not available for {self.__class__.__name__}")
                return

            # 1. Обновляем основные элементы через ids
            self._update_main_elements(tm)
            
            # 2. Рекурсивно обновляем все дочерние виджеты
            self._update_all_children(self, tm)
            
            # 3. Вызываем пользовательскую логику обновления темы
            self.on_theme_refresh(tm)
            
            logger.debug(f"Theme refreshed for {self.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Error refreshing theme in {self.__class__.__name__}: {e}")

    def _update_main_elements(self, tm):
        """Обновление основных элементов через ids"""
        if not hasattr(self, 'ids'):
            return
            
        # Маппинг типовых элементов к их стилям
        element_styles = {
            # Заголовки
            'title_label': {'font_name': tm.get_font("title"), 'color': tm.get_rgba("primary")},
            'header_label': {'font_name': tm.get_font("title"), 'color': tm.get_rgba("primary")},
            
            # Обычный текст
            'text_label': {'font_name': tm.get_font("main"), 'color': tm.get_rgba("text")},
            'info_label': {'font_name': tm.get_font("main"), 'color': tm.get_rgba("text")},
            
            # Вторичный текст
            'secondary_label': {'font_name': tm.get_font("main"), 'color': tm.get_rgba("text_secondary")},
            'description_label': {'font_name': tm.get_font("main"), 'color': tm.get_rgba("text_secondary")},
            
            # Акцентированный текст
            'accent_label': {'font_name': tm.get_font("main"), 'color': tm.get_rgba("text_accent")},
            'primary_label': {'font_name': tm.get_font("main"), 'color': tm.get_rgba("primary")},
            
            # Кнопки
            'button': {
                'background_normal': tm.get_image("button_bg"),
                'background_down': tm.get_image("button_bg_active"),
                'color': tm.get_rgba("text")
            },
            
            # Overlay изображения
            'overlay_image': {'source': tm.get_image("overlay_" + self.name, "overlay_default")},
        }
        
        # Применяем стили к элементам
        for element_id, styles in element_styles.items():
            if element_id in self.ids:
                widget = self.ids[element_id]
                for prop, value in styles.items():
                    if hasattr(widget, prop) and value:
                        setattr(widget, prop, value)

    def _update_all_children(self, widget, tm):
        """Рекурсивное обновление всех дочерних виджетов"""
        try:
            # Обновляем текущий виджет
            self._update_single_widget(widget, tm)
            
            # Рекурсивно обновляем детей
            if hasattr(widget, 'children'):
                for child in widget.children:
                    self._update_all_children(child, tm)
                    
        except Exception as e:
            logger.debug(f"Minor error updating widget {widget}: {e}")

    def _update_single_widget(self, widget, tm):
        """Обновление одного виджета в соответствии с темой"""
        try:
            widget_class = widget.__class__.__name__
            
            # Label виджеты
            if 'Label' in widget_class:
                if not hasattr(widget, '_theme_updated'):
                    # Определяем тип лейбла по его свойствам
                    if hasattr(widget, 'font_size'):
                        size = getattr(widget, 'font_size', '14sp')
                        if isinstance(size, str) and ('20sp' in size or '24sp' in size):
                            # Заголовок
                            widget.font_name = tm.get_font("title")
                            widget.color = tm.get_rgba("primary")
                        else:
                            # Обычный текст
                            widget.font_name = tm.get_font("main")
                            widget.color = tm.get_rgba("text")
                    widget._theme_updated = True
            
            # Button виджеты
            elif 'Button' in widget_class:
                if hasattr(widget, 'background_normal'):
                    widget.background_normal = tm.get_image("button_bg")
                if hasattr(widget, 'background_down'):
                    widget.background_down = tm.get_image("button_bg_active")
                if hasattr(widget, 'font_name'):
                    widget.font_name = tm.get_font("main")
                if hasattr(widget, 'color'):
                    widget.color = tm.get_rgba("text")
            
            # Image виджеты с overlay
            elif 'Image' in widget_class and hasattr(widget, 'source'):
                source = getattr(widget, 'source', '')
                if 'overlay' in source:
                    # Обновляем overlay для текущей страницы
                    new_source = tm.get_image("overlay_" + self.name, "overlay_default")
                    if new_source != source:
                        widget.source = new_source
                        
        except Exception as e:
            logger.debug(f"Minor error updating single widget {widget}: {e}")

    def on_theme_refresh(self, theme_manager):
        """
        Переопределяемый метод для дочерних классов.
        Вызывается после автоматического обновления темы.
        Используйте для специфичной логики обновления темы.
        """
        pass

    # ======================================
    # УПРАВЛЕНИЕ ЛОКАЛИЗАЦИЕЙ
    # ======================================

    def _schedule_text_refresh(self, *args):
        """Планирование обновления текстов"""
        if not self._text_refresh_scheduled:
            self._text_refresh_scheduled = True
            Clock.schedule_once(self._execute_text_refresh, 0.1)

    def _execute_text_refresh(self, dt):
        """Выполнение обновления текстов"""
        try:
            self._text_refresh_scheduled = False
            if self._is_initialized:
                self.refresh_text()
        except Exception as e:
            logger.error(f"Error executing text refresh in {self.__class__.__name__}: {e}")

    def refresh_text(self):
        """
        Основной метод обновления локализованных текстов.
        Переопределите в дочерних классах для специфичных обновлений.
        """
        try:
            app = App.get_running_app()
            if not hasattr(app, 'localizer') or not app.localizer:
                return
                
            # Вызываем пользовательскую логику обновления текстов
            self.on_text_refresh(app.localizer)
            
            logger.debug(f"Text refreshed for {self.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Error refreshing text in {self.__class__.__name__}: {e}")

    def on_text_refresh(self, localizer):
        """
        Переопределяемый метод для обновления локализованных текстов.
        
        Args:
            localizer: Объект локализатора для получения переводов
        """
        pass

    # ======================================
    # LIFECYCLE МЕТОДЫ
    # ======================================

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        try:
            logger.info(f"Entering {self.__class__.__name__}")
            
            # Принудительно обновляем тему и тексты при входе
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
            Clock.schedule_once(lambda dt: self.refresh_text(), 0.2)
            
            # Вызываем пользовательскую логику
            self.on_screen_enter()
            
        except Exception as e:
            logger.error(f"Error in on_pre_enter for {self.__class__.__name__}: {e}")

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        try:
            # Вызываем пользовательскую логику
            self.on_screen_leave()
            
            logger.debug(f"Leaving {self.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Error in on_pre_leave for {self.__class__.__name__}: {e}")

    def on_screen_enter(self):
        """Переопределяемый метод для входа на экран"""
        pass

    def on_screen_leave(self):
        """Переопределяемый метод для выхода с экрана"""
        pass

    # ======================================
    # УТИЛИТЫ
    # ======================================

    def get_localizer(self):
        """Безопасное получение локализатора"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                return app.localizer
            return None
        except Exception as e:
            logger.error(f"Error getting localizer: {e}")
            return None

    def tr(self, key, default=""):
        """Быстрый перевод текста"""
        localizer = self.get_localizer()
        if localizer:
            return localizer.tr(key, default)
        return default

    def clear_theme_cache(self):
        """Очистка кэша темы для принудительного обновления"""
        try:
            # Удаляем флаги обновления у всех виджетов
            self._clear_theme_flags(self)
            # Планируем обновление
            self._schedule_theme_refresh()
        except Exception as e:
            logger.error(f"Error clearing theme cache: {e}")

    def _clear_theme_flags(self, widget):
        """Рекурсивная очистка флагов темы"""
        try:
            if hasattr(widget, '_theme_updated'):
                delattr(widget, '_theme_updated')
            
            if hasattr(widget, 'children'):
                for child in widget.children:
                    self._clear_theme_flags(child)
        except Exception as e:
            logger.debug(f"Minor error clearing theme flags: {e}")