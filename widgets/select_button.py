# widgets/select_button.py
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import ListProperty, StringProperty, ObjectProperty
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
    on_select = ObjectProperty(allownone=True)
    popup_title = StringProperty("Select Option")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._popup = None
        self.bind(selected_value=self._update_text)
        self.bind(on_release=self.open_selection)
        
    def _update_text(self, instance, value):
        """Обновление текста кнопки при изменении выбранного значения"""
        self.text = value if value else "Select..."
        
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
            btn = Button(
                text=value,
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
                
                # Вызываем callback если установлен
                if self.on_select:
                    self.on_select(self, value, old_value)
                
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


class LanguageSelectButton(SelectButton):
    """Специализированная кнопка выбора языка"""
    
    def __init__(self, **kwargs):
        kwargs.setdefault('popup_title', 'Select Language')
        super().__init__(**kwargs)


class RingtoneSelectButton(SelectButton):
    """Специализированная кнопка выбора мелодии"""
    
    def __init__(self, **kwargs):
        kwargs.setdefault('popup_title', 'Select Ringtone')
        super().__init__(**kwargs)