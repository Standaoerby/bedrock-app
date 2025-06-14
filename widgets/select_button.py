"""
Custom Select Button widgets for Bedrock UI
🔥 КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
- Устранены WeakProxy проблемы
- Исправлена логика поиска родительского экрана
- Добавлены weak references для предотвращения циклических ссылок
- Правильная обработка событий
"""
import weakref
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
        self._parent_ref = None  # 🔥 НОВОЕ: WeakReference для предотвращения циклических ссылок
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
                self.text = display_text
            else:
                self.text = value or "Select..."
                
            logger.debug(f"SelectButton text updated to: {self.text}")
        except Exception as e:
            logger.error(f"Error updating SelectButton text: {e}")

    def open_selection(self):
        """🔥 ИСПРАВЛЕННОЕ открытие popup для выбора"""
        if self._popup_open or not self.values:
            return
            
        try:
            self._popup_open = True
            
            # Создаем содержимое popup
            content = BoxLayout(orientation='vertical', spacing=dp(10))
            
            # Создаем scrollable список кнопок
            scroll = ScrollView()
            buttons_layout = BoxLayout(
                orientation='vertical', 
                spacing=dp(5),
                size_hint_y=None
            )
            buttons_layout.bind(minimum_height=buttons_layout.setter('height'))
            
            # Создаем кнопки для каждого значения
            for value in self.values:
                btn = Button(
                    text=value,
                    size_hint_y=None,
                    height=dp(40),
                    background_normal='',
                    background_color=(0.2, 0.2, 0.2, 1) if value != self.selected_value else (0.3, 0.5, 0.8, 1)
                )
                btn.bind(on_release=lambda x, val=value: self._select_value(val))
                buttons_layout.add_widget(btn)
            
            scroll.add_widget(buttons_layout)
            content.add_widget(scroll)
            
            # Создаем popup
            self._popup = Popup(
                title=self.popup_title,
                content=content,
                size_hint=(0.8, 0.8),
                auto_dismiss=True
            )
            
            # Привязываем событие закрытия
            self._popup.bind(on_dismiss=self._on_popup_dismiss)
            
            # Открываем popup
            self._popup.open()
            
        except Exception as e:
            logger.error(f"Error opening selection popup: {e}")
            self._popup_open = False

    def _select_value(self, value):
        """🔥 ИСПРАВЛЕННЫЙ выбор значения"""
        try:
            old_value = self.selected_value
            self.selected_value = value
            
            # Закрываем popup
            if self._popup:
                self._popup.dismiss()
            
            # Вызываем событие on_select
            self.dispatch('on_select', value, old_value)
            
            logger.debug(f"✅ Value selected: {value}")
            
        except Exception as e:
            logger.error(f"Error selecting value: {e}")

    def _on_popup_dismiss(self, popup):
        """Обработка закрытия popup"""
        self._popup_open = False
        self._popup = None

    def on_select(self, value, old_value):
        """🔥 НОВОЕ: Base event handler - переопределяется в дочерних классах"""
        logger.debug(f"SelectButton on_select: {old_value} → {value}")

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

    def _find_settings_screen(self):
        """🔥 ИСПРАВЛЕНО: Более надежный поиск родительского экрана"""
        try:
            parent = self.parent
            attempts = 0
            while parent and attempts < 15:  # Увеличили лимит попыток
                # Проверяем тип более аккуратно
                parent_type = type(parent).__name__
                
                # 🔥 КРИТИЧНО: Исключаем WeakProxy и другие проблемные типы
                if 'WeakProxy' in parent_type:
                    logger.debug(f"⚠️ Skipping WeakProxy: {parent_type}")
                    parent = getattr(parent, 'parent', None)
                    attempts += 1
                    continue
                
                # Проверяем на правильный тип более безопасно
                try:
                    if (hasattr(parent, 'on_variant_select') or 
                        hasattr(parent, 'on_theme_select') or
                        hasattr(parent, 'on_language_select') or
                        'SettingsScreen' in parent_type):
                        logger.debug(f"✅ Found settings screen: {parent_type}")
                        return parent
                except Exception as check_e:
                    logger.debug(f"Error checking parent type: {check_e}")
                    
                parent = getattr(parent, 'parent', None)
                attempts += 1
                
            logger.warning(f"❌ Could not find settings screen after {attempts} attempts")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding settings screen: {e}")
            return None


class VariantSelectButton(SelectButton):
    """🔥 ИСПРАВЛЕННАЯ кнопка выбора варианта темы"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Variant"
        
        # 🔥 ИСПРАВЛЕНО: Отложенная привязка без WeakProxy проблем
        Clock.schedule_once(self._delayed_setup, 0.5)
    
    def _delayed_setup(self, dt):
        """🔥 НОВОЕ: Безопасная отложенная настройка"""
        try:
            settings_screen = self._find_settings_screen()
            if settings_screen:
                # Создаем weak reference для предотвращения циклических ссылок
                self._parent_ref = weakref.ref(settings_screen)
                logger.debug("✅ VariantSelectButton: Settings screen linked")
            else:
                logger.warning("⚠️ VariantSelectButton: Settings screen not found")
        except Exception as e:
            logger.error(f"❌ Error in delayed setup: {e}")

    def on_select(self, value, old_value):
        """🔥 ИСПРАВЛЕННАЯ обработка выбора варианта"""
        try:
            # Используем weak reference если доступен
            if self._parent_ref:
                settings_screen = self._parent_ref()
                if settings_screen and hasattr(settings_screen, 'on_variant_select'):
                    if hasattr(settings_screen, '_play_sound'):
                        settings_screen._play_sound("click")
                    Clock.schedule_once(lambda dt: settings_screen.on_variant_select(value), 0.1)
                    logger.info(f"🎨 Variant selected: {value}")
                    return
            
            # Fallback на обычный поиск
            settings_screen = self._find_settings_screen()
            if settings_screen and hasattr(settings_screen, 'on_variant_select'):
                if hasattr(settings_screen, '_play_sound'):
                    settings_screen._play_sound("click")
                Clock.schedule_once(lambda dt: settings_screen.on_variant_select(value), 0.1)
                logger.info(f"🎨 Variant selected: {value}")
            else:
                logger.error("❌ Cannot find settings screen or on_variant_select method")
                
        except Exception as e:
            logger.error(f"❌ Error in VariantSelectButton.on_select: {e}")


class ThemeSelectButton(SelectButton):
    """🔥 ИСПРАВЛЕННАЯ кнопка выбора темы"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Theme"
        Clock.schedule_once(self._delayed_setup, 0.5)
    
    def _delayed_setup(self, dt):
        """🔥 НОВОЕ: Безопасная отложенная настройка"""
        try:
            settings_screen = self._find_settings_screen()
            if settings_screen:
                self._parent_ref = weakref.ref(settings_screen)
                logger.debug("✅ ThemeSelectButton: Settings screen linked")
            else:
                logger.warning("⚠️ ThemeSelectButton: Settings screen not found")
        except Exception as e:
            logger.error(f"❌ Error in theme delayed setup: {e}")

    def on_select(self, value, old_value):
        """🔥 ИСПРАВЛЕННАЯ обработка выбора темы"""
        try:
            # Используем weak reference если доступен
            if self._parent_ref:
                settings_screen = self._parent_ref()
                if settings_screen and hasattr(settings_screen, 'on_theme_select'):
                    if hasattr(settings_screen, '_play_sound'):
                        settings_screen._play_sound("click")
                    Clock.schedule_once(lambda dt: settings_screen.on_theme_select(value), 0.1)
                    logger.info(f"🎨 Theme selected: {value}")
                    return
            
            # Fallback на обычный поиск
            settings_screen = self._find_settings_screen()
            if settings_screen and hasattr(settings_screen, 'on_theme_select'):
                if hasattr(settings_screen, '_play_sound'):
                    settings_screen._play_sound("click")
                Clock.schedule_once(lambda dt: settings_screen.on_theme_select(value), 0.1)
                logger.info(f"🎨 Theme selected: {value}")
            else:
                logger.error("❌ Cannot find settings screen or on_theme_select method")
                
        except Exception as e:
            logger.error(f"❌ Error in ThemeSelectButton.on_select: {e}")


class LanguageSelectButton(SelectButton):
    """🔥 ИСПРАВЛЕННАЯ кнопка выбора языка"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Language"
        Clock.schedule_once(self._delayed_setup, 0.5)
    
    def _delayed_setup(self, dt):
        """🔥 НОВОЕ: Безопасная отложенная настройка"""
        try:
            settings_screen = self._find_settings_screen()
            if settings_screen:
                self._parent_ref = weakref.ref(settings_screen)
                logger.debug("✅ LanguageSelectButton: Settings screen linked")
            else:
                logger.warning("⚠️ LanguageSelectButton: Settings screen not found")
        except Exception as e:
            logger.error(f"❌ Error in language delayed setup: {e}")

    def on_select(self, value, old_value):
        """🔥 ИСПРАВЛЕННАЯ обработка выбора языка"""
        try:
            # Используем weak reference если доступен
            if self._parent_ref:
                settings_screen = self._parent_ref()
                if settings_screen and hasattr(settings_screen, 'on_language_select'):
                    if hasattr(settings_screen, '_play_sound'):
                        settings_screen._play_sound("click")
                    Clock.schedule_once(lambda dt: settings_screen.on_language_select(value), 0.1)
                    logger.info(f"🌐 Language selected: {value}")
                    return
            
            # Fallback на обычный поиск
            settings_screen = self._find_settings_screen()
            if settings_screen and hasattr(settings_screen, 'on_language_select'):
                if hasattr(settings_screen, '_play_sound'):
                    settings_screen._play_sound("click")
                Clock.schedule_once(lambda dt: settings_screen.on_language_select(value), 0.1)
                logger.info(f"🌐 Language selected: {value}")
            else:
                logger.error("❌ Cannot find settings screen or on_language_select method")
                
        except Exception as e:
            logger.error(f"❌ Error in LanguageSelectButton.on_select: {e}")


class RingtoneSelectButton(SelectButton):
    """🔥 ИСПРАВЛЕННАЯ кнопка выбора рингтона с правильной привязкой событий"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.popup_title = "Select Ringtone"
        Clock.schedule_once(self._delayed_setup, 0.5)
    
    def _delayed_setup(self, dt):
        """Отложенная настройка для alarm screen"""
        try:
            alarm_screen = self._find_alarm_screen()
            if alarm_screen:
                self._parent_ref = weakref.ref(alarm_screen)
                logger.debug("✅ RingtoneSelectButton: Alarm screen linked")
            else:
                logger.warning("⚠️ RingtoneSelectButton: Alarm screen not found")
        except Exception as e:
            logger.error(f"❌ Error in ringtone delayed setup: {e}")

    def on_select(self, value, old_value):
        """Обработка выбора рингтона"""
        try:
            # Используем weak reference если доступен
            if self._parent_ref:
                alarm_screen = self._parent_ref()
                if alarm_screen and hasattr(alarm_screen, 'select_ringtone'):
                    Clock.schedule_once(lambda dt: alarm_screen.select_ringtone(value), 0.1)
                    logger.debug(f"RingtoneSelectButton: Called select_ringtone with {value}")
                    return
            
            # Fallback на обычный поиск
            alarm_screen = self._find_alarm_screen()
            if alarm_screen and hasattr(alarm_screen, 'select_ringtone'):
                Clock.schedule_once(lambda dt: alarm_screen.select_ringtone(value), 0.1)
                logger.debug(f"RingtoneSelectButton: Called select_ringtone with {value}")
            else:
                logger.warning(f"AlarmScreen not found or doesn't have select_ringtone method")
                
        except Exception as e:
            logger.error(f"Error in RingtoneSelectButton.on_select: {e}")
    
    def _find_alarm_screen(self):
        """Поиск родительского экрана будильника"""
        try:
            parent = self.parent
            attempts = 0
            while parent and attempts < 15:
                parent_type = type(parent).__name__
                
                # Исключаем WeakProxy
                if 'WeakProxy' in parent_type:
                    parent = getattr(parent, 'parent', None)
                    attempts += 1
                    continue
                
                # Проверяем класс и метод
                if hasattr(parent, '__class__') and 'AlarmScreen' in str(parent.__class__):
                    return parent
                if hasattr(parent, 'select_ringtone'):
                    return parent
                    
                parent = getattr(parent, 'parent', None)
                attempts += 1
                
            return None
        except Exception as e:
            logger.error(f"Error finding alarm screen: {e}")
            return None