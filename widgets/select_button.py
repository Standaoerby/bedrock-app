# widgets/select_button.py
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import ListProperty, StringProperty
from kivy.event import EventDispatcher
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from app.logger import app_logger as logger


class SelectButton(Button, EventDispatcher):
    """🔥 ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ кастомная кнопка выбора"""
    
    values = ListProperty([])
    selected_value = StringProperty("")
    popup_title = StringProperty("Select Option")
    
    # 🔥 ИСПРАВЛЕНО: Правильная регистрация событий
    __events__ = ('on_select',)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._popup = None
        self._popup_open = False
        self._bind_events()
        
    def _bind_events(self):
        """🔥 ИСПРАВЛЕННАЯ привязка событий"""
        try:
            self.bind(selected_value=self._update_text)
            self.bind(on_release=self._on_button_release)
            logger.debug(f"✅ SelectButton events bound for {self.popup_title}")
        except Exception as e:
            logger.error(f"❌ Error binding SelectButton events: {e}")

    def _on_button_release(self, *args):
        """🔥 ИСПРАВЛЕННЫЙ обработчик нажатия кнопки"""
        if not self._popup_open and self.values:
            # Отложенный вызов для предотвращения конфликтов UI
            Clock.schedule_once(lambda dt: self.open_selection(), 0.1)
            logger.debug(f"🔍 SelectButton pressed: {self.popup_title}")
        elif not self.values:
            logger.warning(f"⚠️ SelectButton has no values: {self.popup_title}")
        
    def _update_text(self, instance, value):
        """🔥 ИСПРАВЛЕННОЕ обновление текста кнопки"""
        try:
            if value and '.' in value:
                # Убираем расширение файла для отображения
                display_text = value.rsplit('.', 1)[0]
            else:
                display_text = value or "Select..."
            
            self.text = display_text
            logger.debug(f"📝 SelectButton text updated: {display_text}")
        except Exception as e:
            logger.error(f"❌ Error updating SelectButton text: {e}")
            self.text = "Select..."

    def open_selection(self):
        """🔥 ИСПРАВЛЕННОЕ открытие окна выбора"""
        if self._popup_open or not self.values:
            return
            
        try:
            self._popup_open = True
            content = self._create_popup_content()
            
            self._popup = Popup(
                title=self.popup_title,
                content=content,
                size_hint=(0.8, 0.8),
                auto_dismiss=True
            )
            
            self._popup.bind(on_dismiss=self._on_popup_dismiss)
            self._popup.open()
            logger.info(f"📋 Popup opened: {self.popup_title}")
            
        except Exception as e:
            logger.error(f"❌ Error opening SelectButton popup: {e}")
            self._popup_open = False

    def _create_popup_content(self):
        """🔥 УЛУЧШЕННОЕ создание содержимого popup"""
        main_layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        
        # Скроллинг для списка опций
        scroll = ScrollView()
        options_layout = BoxLayout(
            orientation='vertical', 
            spacing=dp(4),
            size_hint_y=None
        )
        options_layout.bind(minimum_height=options_layout.setter('height'))
        
        # Получаем theme_manager для стилизации
        tm = self._get_theme_manager()
        
        # Создаем кнопки для каждого значения
        for value in self.values:
            display_text = value
            if value and '.' in value:
                display_text = value.rsplit('.', 1)[0]
                
            btn = Button(
                text=display_text,
                size_hint_y=None,
                height=dp(44),
                font_size='16sp'
            )
            
            # 🔥 НОВОЕ: Применяем тему если доступно
            if tm and tm.is_loaded():
                btn.font_name = tm.get_font("main")
                btn.color = tm.get_rgba("text")
                
                # Выделяем текущий выбор
                if value == self.selected_value:
                    btn.color = tm.get_rgba("primary")
            
            # 🔥 ИСПРАВЛЕНО: Безопасная привязка с отложенным вызовом
            btn.bind(on_release=lambda btn, val=value: self._safe_select_value(val))
            options_layout.add_widget(btn)
        
        scroll.add_widget(options_layout)
        main_layout.add_widget(scroll)
        
        # 🔥 НОВОЕ: Кнопка отмены
        cancel_btn = Button(
            text="Cancel",
            size_hint_y=None,
            height=dp(44),
            font_size='16sp'
        )
        
        if tm and tm.is_loaded():
            cancel_btn.font_name = tm.get_font("main")
            cancel_btn.color = tm.get_rgba("text_secondary")
        
        cancel_btn.bind(on_release=self._cancel_selection)
        main_layout.add_widget(cancel_btn)
        
        return main_layout

    def _safe_select_value(self, value):
        """🔥 НОВОЕ: Безопасная обработка выбора с отложенным вызовом"""
        Clock.schedule_once(lambda dt: self._select_value(value), 0.1)
    
    def _select_value(self, value):
        """🔥 ИСПРАВЛЕННАЯ обработка выбора значения"""
        try:
            if value != self.selected_value:
                old_value = self.selected_value
                self.selected_value = value
                
                # 🔥 ИСПРАВЛЕНО: Безопасная диспетчеризация события
                try:
                    self.dispatch('on_select', value, old_value)
                    logger.info(f"✅ SelectButton value selected: {value}")
                except Exception as dispatch_error:
                    logger.error(f"❌ Error dispatching on_select: {dispatch_error}")
            
            # Закрываем popup с задержкой
            Clock.schedule_once(lambda dt: self._close_popup(), 0.2)
                
        except Exception as e:
            logger.error(f"❌ Error selecting value in SelectButton: {e}")
            self._close_popup()
    
    def _cancel_selection(self, *args):
        """Отмена выбора"""
        logger.debug("🚫 Selection cancelled")
        self._close_popup()
    
    def _close_popup(self):
        """🔥 ИСПРАВЛЕННОЕ безопасное закрытие popup"""
        try:
            if self._popup:
                self._popup.dismiss()
        except Exception as e:
            logger.error(f"❌ Error closing SelectButton popup: {e}")
        finally:
            self._popup_open = False
    
    def _on_popup_dismiss(self, *args):
        """Обработка закрытия popup"""
        self._popup = None
        self._popup_open = False
        logger.debug("📋 Popup dismissed")
    
    def on_select(self, value, old_value):
        """🔥 НОВОЕ: Базовое событие выбора - переопределяется в подклассах"""
        logger.debug(f"🔍 Base on_select called: {old_value} → {value}")
        pass
    
    def _get_theme_manager(self):
        """Безопасное получение theme_manager"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'theme_manager') and app.theme_manager:
                return app.theme_manager
        except Exception as e:
            logger.error(f"❌ Error getting theme manager: {e}")
        return None
    
    def set_values(self, values):
        """🔥 НОВОЕ: Установка новых значений"""
        try:
            self.values = list(values) if values else []
            logger.debug(f"📋 SelectButton values set: {len(self.values)} items")
            
            # Если текущее значение не в списке, сбрасываем
            if self.selected_value and self.selected_value not in self.values:
                self.selected_value = ""
                
        except Exception as e:
            logger.error(f"❌ Error setting SelectButton values: {e}")
    
    def set_selection(self, value):
        """🔥 НОВОЕ: Программная установка выбранного значения"""
        try:
            if not value:
                self.selected_value = ""
            elif value in self.values:
                self.selected_value = value
                logger.debug(f"📋 SelectButton selection set: {value}")
            else:
                logger.warning(f"⚠️ SelectButton value '{value}' not in values list")
        except Exception as e:
            logger.error(f"❌ Error setting SelectButton selection: {e}")

# ИСПРАВЛЕНИЕ: Специализированные классы с корректной инициализацией
class ThemeSelectButton(SelectButton):
    """🔥 ИСПРАВЛЕННАЯ кнопка выбора темы"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Theme"
        # Отложенная привязка к родительскому экрану
        Clock.schedule_once(self._delayed_parent_binding, 1.0)
    
    def _delayed_parent_binding(self, dt):
        """🔥 НОВОЕ: Отложенная привязка к родительскому экрану"""
        try:
            settings_screen = self._find_settings_screen()
            if settings_screen:
                logger.info("✅ ThemeSelectButton found settings screen")
            else:
                logger.warning("⚠️ ThemeSelectButton could not find settings screen")
        except Exception as e:
            logger.error(f"❌ Error in delayed parent binding: {e}")

    def on_select(self, value, old_value):
        """🔥 ИСПРАВЛЕННАЯ обработка выбора темы"""
        try:
            settings_screen = self._find_settings_screen()
            if settings_screen and hasattr(settings_screen, 'on_theme_select'):
                # Воспроизводим звук если доступно
                if hasattr(settings_screen, '_play_sound'):
                    settings_screen._play_sound("click")
                
                # Вызываем метод смены темы с отложенным вызовом
                Clock.schedule_once(lambda dt: settings_screen.on_theme_select(value), 0.1)
                logger.info(f"🎨 Theme selected: {value}")
            else:
                logger.error("❌ Cannot find settings screen or on_theme_select method")
        except Exception as e:
            logger.error(f"❌ Error in ThemeSelectButton.on_select: {e}")
    
    def _find_settings_screen(self):
        """Поиск родительского экрана настроек"""
        parent = self.parent
        attempts = 0
        while parent and attempts < 10:  # Защита от бесконечного цикла
            if hasattr(parent, 'on_theme_select'):
                return parent
            parent = getattr(parent, 'parent', None)
            attempts += 1
        return None


class VariantSelectButton(SelectButton):
    """🔥 ИСПРАВЛЕННАЯ кнопка выбора варианта темы"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Variant"
    
    def on_select(self, value, old_value):
        """Обработка выбора варианта"""
        try:
            settings_screen = self._find_settings_screen()
            if settings_screen and hasattr(settings_screen, 'on_variant_select'):
                if hasattr(settings_screen, '_play_sound'):
                    settings_screen._play_sound("click")
                Clock.schedule_once(lambda dt: settings_screen.on_variant_select(value), 0.1)
                logger.info(f"🎨 Variant selected: {value}")
        except Exception as e:
            logger.error(f"❌ Error in VariantSelectButton.on_select: {e}")
    
    def _find_settings_screen(self):
        """Поиск родительского экрана настроек"""
        parent = self.parent
        attempts = 0
        while parent and attempts < 10:
            if hasattr(parent, 'on_variant_select'):
                return parent
            parent = getattr(parent, 'parent', None)
            attempts += 1
        return None


class LanguageSelectButton(SelectButton):
    """🔥 ИСПРАВЛЕННАЯ кнопка выбора языка"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Language"
    
    def on_select(self, value, old_value):
        """Обработка выбора языка"""
        try:
            settings_screen = self._find_settings_screen()
            if settings_screen and hasattr(settings_screen, 'on_language_select'):
                if hasattr(settings_screen, '_play_sound'):
                    settings_screen._play_sound("click")
                Clock.schedule_once(lambda dt: settings_screen.on_language_select(value), 0.1)
                logger.info(f"🌐 Language selected: {value}")
        except Exception as e:
            logger.error(f"❌ Error in LanguageSelectButton.on_select: {e}")
    
    def _find_settings_screen(self):
        """Поиск родительского экрана настроек"""
        parent = self.parent
        attempts = 0
        while parent and attempts < 10:
            if hasattr(parent, 'on_language_select'):
                return parent
            parent = getattr(parent, 'parent', None)
            attempts += 1
        return None


class RingtoneSelectButton(SelectButton):
    """Кнопка выбора рингтона с правильной привязкой событий"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Ringtone"
    
    def on_select(self, value, old_value):
        """Обработка выбора рингтона"""
        try:
            # ИСПРАВЛЕНО: Ищем именно AlarmScreen и вызываем select_ringtone
            screen = self._find_alarm_screen()
            if screen and hasattr(screen, 'select_ringtone'):
                Clock.schedule_once(lambda dt: screen.select_ringtone(value), 0.1)
                logger.debug(f"RingtoneSelectButton: Called select_ringtone with {value}")
            else:
                logger.warning(f"AlarmScreen not found or doesn't have select_ringtone method")
        except Exception as e:
            logger.error(f"Error in RingtoneSelectButton.on_select: {e}")
    
    def _find_alarm_screen(self):
        """Поиск родительского экрана будильника"""
        parent = self.parent
        while parent:
            # ИСПРАВЛЕНО: Проверяем класс и метод
            if hasattr(parent, '__class__') and 'AlarmScreen' in str(parent.__class__):
                return parent
            if hasattr(parent, 'select_ringtone'):
                return parent
            parent = getattr(parent, 'parent', None)
        return None