# widgets/select_button.py
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.event import EventDispatcher
from kivy.metrics import dp
from kivy.app import App
from app.logger import app_logger as logger


class SelectButton(Button):
    """
    Кастомная замена для Spinner, использующая Button + Popup
    Полностью избегает проблем с DropDown
    """
    
    values = ListProperty([])
    selected_value = StringProperty("")
    popup_title = StringProperty("Select Option")
    
    # ИСПРАВЛЕНИЕ: Регистрируем событие on_select
    __events__ = ('on_select',)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._popup = None
        self.bind(selected_value=self._update_text)
        self.bind(on_release=self.open_selection)
        
    def _update_text(self, instance, value):
        """Обновление текста кнопки при изменении выбранного значения"""
        # Показываем имя файла без расширения для мелодий
        if value and '.' in value:
            display_text = value.rsplit('.', 1)[0]  # Убираем расширение
        else:
            display_text = value if value else "Select..."
        self.text = display_text
        
    def open_selection(self, *args):
        """Открытие popup с выбором"""
        try:
            if self._popup:
                self._popup.dismiss()
                self._popup = None
                return
                
            if not self.values:
                logger.warning("No values to select from")
                return
                
            # Создаем содержимое popup
            content = self._create_popup_content()
            
            # Создаем popup
            self._popup = Popup(
                title=self.popup_title,
                content=content,
                size_hint=(0.6, 0.8),
                auto_dismiss=True
            )
            
            # Привязываем событие закрытия
            self._popup.bind(on_dismiss=self._on_popup_dismiss)
            
            # Открываем popup
            self._popup.open()
            
        except Exception as e:
            logger.error(f"Error opening selection popup: {e}")
    
    def _create_popup_content(self):
        """Создание содержимого popup"""
        # Основной контейнер
        main_layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        # Скроллируемый список опций
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        options_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        options_layout.bind(minimum_height=options_layout.setter('height'))
        
        # Получаем theme_manager для стилизации
        app = App.get_running_app()
        tm = getattr(app, 'theme_manager', None)
        
        # Создаем кнопки для каждого значения
        for value in self.values:
            # Показываем имя файла без расширения для мелодий
            if value and '.' in value:
                display_text = value.rsplit('.', 1)[0]
            else:
                display_text = value
                
            btn = Button(
                text=display_text,
                size_hint_y=None,
                height=dp(44),
                font_size='16sp'
            )
            
            # Применяем тему если доступно
            if tm and tm.is_loaded():
                btn.font_name = tm.get_font("main")
                btn.color = tm.get_rgba("text")
                btn.background_normal = tm.get_image("button_bg")
                btn.background_down = tm.get_image("button_bg_active")
                
                # Выделяем текущий выбор
                if value == self.selected_value:
                    btn.color = tm.get_rgba("primary")
            
            # Привязываем выбор
            btn.bind(on_release=lambda btn, val=value: self._select_value(val))
            options_layout.add_widget(btn)
        
        scroll.add_widget(options_layout)
        main_layout.add_widget(scroll)
        
        # Кнопка отмены
        cancel_btn = Button(
            text="Cancel",
            size_hint_y=None,
            height=dp(44),
            font_size='16sp'
        )
        
        if tm and tm.is_loaded():
            cancel_btn.font_name = tm.get_font("main")
            cancel_btn.color = tm.get_rgba("text_secondary")
            cancel_btn.background_normal = tm.get_image("button_bg")
            cancel_btn.background_down = tm.get_image("button_bg_active")
        
        cancel_btn.bind(on_release=self._cancel_selection)
        main_layout.add_widget(cancel_btn)
        
        return main_layout
    
    def _select_value(self, value):
        """Обработка выбора значения"""
        try:
            if value != self.selected_value:
                old_value = self.selected_value
                self.selected_value = value
                
                # ИСПРАВЛЕНИЕ: Теперь это событие корректно зарегистрировано
                self.dispatch('on_select', value, old_value)
                
                logger.debug(f"Selected value: {value}")
            
            # Закрываем popup
            if self._popup:
                self._popup.dismiss()
                
        except Exception as e:
            logger.error(f"Error selecting value: {e}")
    
    def _cancel_selection(self, *args):
        """Отмена выбора"""
        if self._popup:
            self._popup.dismiss()
    
    def _on_popup_dismiss(self, *args):
        """Обработка закрытия popup"""
        self._popup = None
    
    def on_select(self, value, old_value):
        """Событие выбора - переопределяется в подклассах или привязывается извне"""
        pass
    
    def set_values(self, values):
        """Установка новых значений"""
        self.values = list(values) if values else []
        
        # Если текущее значение не в списке, сбрасываем
        if self.selected_value and self.selected_value not in self.values:
            self.selected_value = ""
    
    def set_selection(self, value):
        """Программная установка выбранного значения"""
        if value in self.values:
            self.selected_value = value
        else:
            logger.warning(f"Value '{value}' not in values list")


class ThemeSelectButton(SelectButton):
    """Специализированная кнопка выбора темы"""
    
    def __init__(self, **kwargs):
        kwargs.setdefault('popup_title', 'Select Theme')
        super().__init__(**kwargs)
    
    def on_select(self, value, old_value):
        """Обработка выбора темы"""
        # Получаем parent screen для вызова метода обработки
        from pages.settings import SettingsScreen
        screen = self._find_parent_screen()
        if isinstance(screen, SettingsScreen):
            # ИСПРАВЛЕНИЕ: Определяем тип кнопки по popup_title
            if hasattr(self, 'popup_title') and 'Mode' in self.popup_title:
                screen.on_variant_select(value)
            else:
                screen.on_theme_select(value)

    def _find_parent_screen(self):
        """Поиск родительского экрана"""
        parent = self.parent
        while parent:
            if hasattr(parent, '__class__') and hasattr(parent.__class__, '__name__'):
                if 'Screen' in parent.__class__.__name__:
                    return parent
            parent = getattr(parent, 'parent', None)
        return None


class LanguageSelectButton(SelectButton):
    """Специализированная кнопка выбора языка"""
    
    def __init__(self, **kwargs):
        kwargs.setdefault('popup_title', 'Select Language')
        super().__init__(**kwargs)
    
    def on_select(self, value, old_value):
        """Обработка выбора языка"""
        from pages.settings import SettingsScreen
        screen = self._find_parent_screen()
        if isinstance(screen, SettingsScreen):
            screen.on_language_select(value)

    def _find_parent_screen(self):
        """Поиск родительского экрана"""
        parent = self.parent
        while parent:
            if hasattr(parent, '__class__') and hasattr(parent.__class__, '__name__'):
                if 'Screen' in parent.__class__.__name__:
                    return parent
            parent = getattr(parent, 'parent', None)
        return None


class RingtoneSelectButton(SelectButton):
    """Специализированная кнопка выбора мелодии"""
    
    def __init__(self, **kwargs):
        kwargs.setdefault('popup_title', 'Select Ringtone')
        super().__init__(**kwargs)
    
    def on_select(self, value, old_value):
        """Обработка выбора мелодии"""
        try:
            from pages.alarm import AlarmScreen
            screen = self._find_parent_screen()
            if isinstance(screen, AlarmScreen):
                # ИСПРАВЛЕНИЕ: Вызываем правильный метод
                screen.select_ringtone(value)
                logger.debug(f"RingtoneSelectButton: Called select_ringtone with {value}")
            else:
                logger.warning(f"Parent screen not found or not AlarmScreen: {type(screen)}")
        except Exception as e:
            logger.error(f"Error in RingtoneSelectButton.on_select: {e}")

    def _find_parent_screen(self):
        """Поиск родительского экрана"""
        parent = self.parent
        while parent:
            if hasattr(parent, '__class__') and hasattr(parent.__class__, '__name__'):
                if 'Screen' in parent.__class__.__name__:
                    return parent
            parent = getattr(parent, 'parent', None)
        return None