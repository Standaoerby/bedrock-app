# widgets/base_screen.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
"""
КРИТИЧЕСКИЕ ОПТИМИЗАЦИИ BaseScreen:
✅ Защита от множественных обновлений темы
✅ Кэширование тем на уровне экрана
✅ Умное планирование обновлений
✅ Группировка обновлений виджетов
✅ Устранение избыточных вызовов get_font()
"""

from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from app.event_bus import event_bus
from app.logger import app_logger as logger
import time


class BaseScreen(Screen):
    """
    ОПТИМИЗИРОВАННЫЙ базовый класс для всех экранов приложения.
    Устраняет множественные обновления темы и кэширует ресурсы.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # ✅ НОВОЕ: Защита от множественных обновлений
        self._theme_refresh_scheduled = False
        self._text_refresh_scheduled = False
        self._theme_update_in_progress = False
        self._is_initialized = False
        
        # ✅ НОВОЕ: Кэширование темы на уровне экрана
        self._cached_theme_data = {}
        self._last_theme_version = None
        self._theme_applied = False
        
        # ✅ НОВОЕ: Группировка обновлений
        self._pending_updates = set()
        self._update_batch_event = None
        
        # ✅ НОВОЕ: Статистика для оптимизации
        self._refresh_count = 0
        self._last_refresh_time = 0
        
        # Подписка на глобальные события
        self._subscribe_to_events()
        
        # Планируем инициализацию после создания экрана
        Clock.schedule_once(self._delayed_initialization, 0.1)

    def _subscribe_to_events(self):
        """Подписка на события системы с дедупликацией"""
        try:
            # Используем уникальные колбэки для каждого экрана
            screen_id = id(self)
            
            event_bus.subscribe(
                "theme_changed", 
                lambda *args: self._schedule_theme_refresh(f"theme_changed_{screen_id}")
            )
            event_bus.subscribe(
                "language_changed", 
                lambda *args: self._schedule_text_refresh(f"language_changed_{screen_id}")
            )
            
            logger.debug(f"Events subscribed for {self.__class__.__name__} (ID: {screen_id})")
            
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
    # ОПТИМИЗИРОВАННОЕ УПРАВЛЕНИЕ ТЕМАМИ
    # ======================================

    def get_theme_manager(self):
        """Безопасное получение theme_manager с кэшированием"""
        try:
            app = App.get_running_app()
            if app and hasattr(app, 'theme_manager') and app.theme_manager:
                return app.theme_manager
            logger.warning(f"ThemeManager not available in {self.__class__.__name__}")
            return None
        except Exception as e:
            logger.error(f"Error getting theme manager in {self.__class__.__name__}: {e}")
            return None

    def _get_current_theme_version(self):
        """✅ ИСПРАВЛЕНО: Стабильное версионирование темы"""
        tm = self.get_theme_manager()
        if tm and tm.is_loaded():
            # ✅ ИСПРАВЛЕНО: Используем timestamp загрузки + hash содержимого вместо id()
            theme_hash = hash(str(tm.theme_data)) if tm.theme_data else 0
            return f"{tm.current_theme}_{tm.current_variant}_{theme_hash}_{tm._loading_in_progress}"
        return None

    def _should_update_theme(self):
        """Проверка, нужно ли обновлять тему"""
        current_version = self._get_current_theme_version()
        
        # Проверяем изменение версии темы
        if current_version != self._last_theme_version:
            self._last_theme_version = current_version
            return True
            
        # Проверяем, была ли тема уже применена
        if not self._theme_applied:
            return True
            
        return False

    def _schedule_theme_refresh(self, event_source="unknown"):
        """✅ УМНОЕ планирование обновления темы (избегаем множественные вызовы)"""
        
        # Защита от частых обновлений (максимум раз в 100ms)
        now = time.time()
        if now - self._last_refresh_time < 0.1:
            logger.debug(f"Theme refresh throttled for {self.__class__.__name__} from {event_source}")
            return
            
        # Защита от повторных планирований
        if self._theme_refresh_scheduled or self._theme_update_in_progress:
            logger.debug(f"Theme refresh already scheduled/in progress for {self.__class__.__name__}")
            return
            
        # Проверяем, действительно ли нужно обновление
        if not self._should_update_theme():
            logger.debug(f"Theme refresh not needed for {self.__class__.__name__}")
            return
            
        self._theme_refresh_scheduled = True
        self._last_refresh_time = now
        
        # Планируем обновление с небольшой задержкой для группировки
        Clock.schedule_once(self._execute_theme_refresh, 0.05)
        
        logger.debug(f"Theme refresh scheduled for {self.__class__.__name__} from {event_source}")

    def _schedule_text_refresh(self, event_source="unknown"):
        """Планирование обновления текстов"""
        if not self._text_refresh_scheduled:
            self._text_refresh_scheduled = True
            Clock.schedule_once(self._execute_text_refresh, 0.1)

    def _execute_theme_refresh(self, dt):
        """✅ ИСПРАВЛЕНО: Выполнение обновления темы с принудительной очисткой кэша"""
        
        # Сброс флага планирования
        self._theme_refresh_scheduled = False
        
        # Проверка состояния
        if self._theme_update_in_progress:
            logger.debug(f"Theme update already in progress for {self.__class__.__name__}")
            return
            
        if not self._is_initialized:
            logger.debug(f"Screen not initialized yet: {self.__class__.__name__}")
            return
            
        try:
            self._theme_update_in_progress = True
            self._refresh_count += 1
            
            # ✅ КРИТИЧНО: Принудительно очищаем локальный кэш при смене темы
            self._cached_theme_data.clear()
            self._theme_applied = False
            self._last_theme_version = None
            
            # Выполняем обновление
            self.refresh_theme()
            
            # Отмечаем, что тема применена
            self._theme_applied = True
            
            logger.debug(f"Theme refresh executed for {self.__class__.__name__} (#{self._refresh_count})")
            
        except Exception as e:
            logger.error(f"Error executing theme refresh in {self.__class__.__name__}: {e}")
        finally:
            self._theme_update_in_progress = False

    def _execute_text_refresh(self, dt):
        """Выполнение обновления текстов"""
        try:
            self._text_refresh_scheduled = False
            if self._is_initialized:
                self.refresh_text()
        except Exception as e:
            logger.error(f"Error executing text refresh in {self.__class__.__name__}: {e}")

    def refresh_theme(self):
        """
        ✅ ОПТИМИЗИРОВАННЫЙ основной метод обновления темы.
        Группирует обновления и использует кэширование.
        """
        try:
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                logger.debug(f"Theme manager not available for {self.__class__.__name__}")
                return

            # Получаем и кэшируем ресурсы темы ОДИН раз
            theme_resources = self._get_cached_theme_resources(tm)
            
            # 1. Обновляем основные элементы через ids (группированно)
            self._update_main_elements_batch(theme_resources)
            
            # 2. Рекурсивно обновляем все дочерние виджеты (оптимизированно)
            self._update_all_children_batch(self, theme_resources)
            
            # 3. Вызываем пользовательскую логику обновления темы
            self.on_theme_refresh(tm)
            
            logger.debug(f"Theme refreshed efficiently for {self.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Error refreshing theme in {self.__class__.__name__}: {e}")

    def _get_cached_theme_resources(self, theme_manager):
        """✅ Кэшированное получение ресурсов темы"""
        current_version = self._get_current_theme_version()
        
        # Проверяем кэш
        if (current_version in self._cached_theme_data and 
            self._cached_theme_data[current_version]):
            return self._cached_theme_data[current_version]
        
        # Загружаем ресурсы ОДИН раз для всего экрана
        try:
            resources = {
                'fonts': {
                    'main': theme_manager.get_font("main"),
                    'title': theme_manager.get_font("title"),
                    'clock': theme_manager.get_font("clock"),
                },
                'colors': {
                    'primary': theme_manager.get_rgba("primary"),
                    'secondary': theme_manager.get_rgba("secondary"),
                    'text': theme_manager.get_rgba("text"),
                    'text_secondary': theme_manager.get_rgba("text_secondary"),
                    'text_accent': theme_manager.get_rgba("text_accent"),
                    'text_inactive': theme_manager.get_rgba("text_inactive"),
                    'background': theme_manager.get_rgba("background"),
                },
                'images': {
                    'button_bg': theme_manager.get_image("button_bg"),
                    'button_bg_active': theme_manager.get_image("button_bg_active"),
                }
            }
            
            # Кэшируем результат
            self._cached_theme_data[current_version] = resources
            
            # Очищаем старые кэши (оставляем только последний)
            old_versions = [v for v in self._cached_theme_data.keys() if v != current_version]
            for old_version in old_versions:
                del self._cached_theme_data[old_version]
                
            logger.debug(f"Theme resources cached for {self.__class__.__name__}")
            return resources
            
        except Exception as e:
            logger.error(f"Error caching theme resources: {e}")
            return {
                'fonts': {'main': '', 'title': '', 'clock': ''},
                'colors': {'primary': [1,1,1,1], 'text': [1,1,1,1], 'text_secondary': [0.7,0.7,0.7,1]},
                'images': {}
            }

    def _update_main_elements_batch(self, resources):
        """✅ Группированное обновление основных элементов через ids"""
        if not hasattr(self, 'ids'):
            return
            
        try:
            fonts = resources['fonts']
            colors = resources['colors']
            
            # Группируем обновления по типу элемента
            element_updates = {
                # Заголовки
                'title_elements': {
                    'ids': ['title_label', 'header_label'],
                    'font': fonts['title'],
                    'color': colors['primary']
                },
                
                # Обычный текст
                'text_elements': {
                    'ids': ['text_label', 'info_label'],
                    'font': fonts['main'],
                    'color': colors['text']
                },
                
                # Вторичный текст
                'secondary_elements': {
                    'ids': ['secondary_label', 'description_label'],
                    'font': fonts['main'],
                    'color': colors['text_secondary']
                },
                
                # Часы
                'clock_elements': {
                    'ids': ['clock_label', 'time_label'],
                    'font': fonts['clock'],
                    'color': colors['primary']
                }
            }
            
            # Применяем обновления группами
            updated_count = 0
            for group_name, config in element_updates.items():
                for widget_id in config['ids']:
                    if widget_id in self.ids:
                        widget = self.ids[widget_id]
                        
                        # Обновляем только если значения изменились
                        if hasattr(widget, 'font_name') and widget.font_name != config['font']:
                            widget.font_name = config['font']
                            updated_count += 1
                            
                        if hasattr(widget, 'color') and widget.color != config['color']:
                            widget.color = config['color']
                            updated_count += 1
                            
            if updated_count > 0:
                logger.debug(f"Updated {updated_count} main elements in {self.__class__.__name__}")
                
        except Exception as e:
            logger.error(f"Error updating main elements: {e}")

    def _update_all_children_batch(self, widget, resources):
        """✅ Оптимизированное рекурсивное обновление всех дочерних виджетов"""
        try:
            fonts = resources['fonts']
            colors = resources['colors']
            
            updated_count = 0
            
            # Обходим все дочерние виджеты
            for child in widget.children:
                # Рекурсивный вызов для вложенных контейнеров
                if hasattr(child, 'children') and child.children:
                    updated_count += self._update_all_children_batch(child, resources)
                
                # Обновляем виджет, только если нужно
                if self._should_update_widget(child):
                    if self._update_widget_theme(child, fonts, colors):
                        updated_count += 1
            
            if updated_count > 0:
                logger.debug(f"Updated {updated_count} child widgets in {self.__class__.__name__}")
                
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating children: {e}")
            return 0

    def _should_update_widget(self, widget):
        """Проверка, нужно ли обновлять конкретный виджет"""
        # Пропускаем виджеты без свойств темы
        return (hasattr(widget, 'font_name') or 
                hasattr(widget, 'color') or 
                hasattr(widget, 'background_normal'))

    def _update_widget_theme(self, widget, fonts, colors):
        """Обновление темы для конкретного виджета"""
        try:
            updated = False
            
            # Определяем тип виджета и применяем соответствующий стиль
            widget_type = widget.__class__.__name__
            
            if widget_type in ['Label']:
                if hasattr(widget, 'font_name') and fonts['main']:
                    widget.font_name = fonts['main']
                    updated = True
                if hasattr(widget, 'color'):
                    widget.color = colors['text']
                    updated = True
                    
            elif widget_type in ['Button']:
                if hasattr(widget, 'font_name') and fonts['main']:
                    widget.font_name = fonts['main'] 
                    updated = True
                if hasattr(widget, 'color'):
                    widget.color = colors['text']
                    updated = True
                    
            elif widget_type in ['TextInput']:
                if hasattr(widget, 'font_name') and fonts['main']:
                    widget.font_name = fonts['main']
                    updated = True
                if hasattr(widget, 'foreground_color'):
                    widget.foreground_color = colors['text']
                    updated = True
                    
            return updated
            
        except Exception as e:
            logger.debug(f"Error updating widget {widget}: {e}")
            return False

    def on_theme_refresh(self, theme_manager):
        """
        Переопределяемый метод для дочерних классов.
        Вызывается после стандартного обновления темы.
        """
        pass

    def refresh_text(self):
        """
        Обновление текстов интерфейса.
        Переопределяется в дочерних классах.
        """
        try:
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                self.on_text_refresh(app.localizer)
        except Exception as e:
            logger.error(f"Error refreshing text in {self.__class__.__name__}: {e}")

    def on_text_refresh(self, localizer):
        """
        Переопределяемый метод для обновления текстов.
        """
        pass

    # ======================================
    # ДИАГНОСТИКА И ОТЛАДКА  
    # ======================================

    def get_theme_stats(self):
        """Получение статистики темы для отладки"""
        return {
            'class_name': self.__class__.__name__,
            'refresh_count': self._refresh_count,
            'theme_applied': self._theme_applied,
            'cached_versions': len(self._cached_theme_data),
            'last_theme_version': self._last_theme_version,
            'is_initialized': self._is_initialized
        }

    def force_theme_refresh(self):
        """Принудительное обновление темы (для отладки)"""
        self._theme_applied = False
        self._last_theme_version = None
        self._schedule_theme_refresh("force_refresh")

    def clear_theme_cache(self):
        """Очистка кэша темы (для отладки)"""
        self._cached_theme_data.clear()
        self._theme_applied = False
        logger.debug(f"Theme cache cleared for {self.__class__.__name__}")

    def __del__(self):
        """Очистка при удалении экрана"""
        try:
            # Очищаем кэши
            self._cached_theme_data.clear()
            
            # Отменяем запланированные события
            if self._update_batch_event:
                self._update_batch_event.cancel()
                
        except Exception:
            pass  # Игнорируем ошибки при удалении