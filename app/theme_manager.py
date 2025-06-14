# app/theme_manager.py
# 🔥 ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ ФАЙЛ с устранением всех багов

import os
import json
from app.logger import app_logger as logger
from app.event_bus import event_bus


class ThemeManager:
    """
    🔥 ИСПРАВЛЕННЫЙ менеджер тем с защитой от циклических рекурсий.
    Отвечает за загрузку, хранение и отдачу ресурсов темы:
    цвета, изображения, шрифты, иконки, оверлеи, звуки и т.д.
    """
    
    def __init__(self, themes_dir="themes"):
        self.themes_dir = themes_dir
        self.theme_name = None
        self.variant = None
        self.theme_data = {}
        
        # Совместимость с существующим кодом
        self.current_theme = None
        self.current_variant = None
        
        # 🔥 ЗАЩИТА ОТ ЦИКЛИЧЕСКИХ РЕКУРСИЙ
        self._loading_in_progress = False
        self._notification_disabled = False
        
        # 🔥 НОВОЕ: Кэширование ресурсов для производительности
        self._resource_cache = {}
        
        # Дефолтная тема для предотвращения ошибок
        self.default_theme = {
            "colors": {
                "primary": "#40916c",
                "background": "#f0efeb",
                "accent": "#277da1",
                "text": "#000000",
                "text_secondary": "#666666",
                "text_inactive": "#999999",
                "text_accent": "#277da1",
                "text_accent_2": "#40916c",
                "clock_main": "#000000",
                "background_highlighted": "#e8e8e8",
                "overlay_card": "#ffffff",
                "menu_color": "#25252580",
                "menu_button_text": "#ffffff",
                "menu_button_text_active": "#40916c"
            },
            "fonts": {
                "main": "",  # Пустая строка = дефолтный шрифт Kivy
                "title": ""
            },
            "images": {
                "background": "background.png",
                "button_bg": "btn_bg.png",
                "button_bg_active": "btn_bg_active.png",
                "menu_button_bg": "menu_btn.png",
                "menu_button_bg_active": "menu_btn_active.png",
                "overlay_home": "overlay_home.png",
                "overlay_alarm": "overlay_alarm.png",
                "overlay_schedule": "overlay_schedule.png",
                "overlay_weather": "overlay_weather.png",
                "overlay_pigs": "overlay_pigs.png",
                "overlay_settings": "overlay_settings.png",
                "overlay_default": "overlay_default.png"
            },
            "menu": {
                "menu_height": 64,
                "menu_button_height": 48,
                "menu_button_width": 152
            },
            "sounds": {
                "click": "click.ogg",
                "confirm": "confirm.ogg",
                "error": "error.ogg",
                "notify": "notify.ogg",
                "startup": "startup.ogg"
            }
        }

    # ================================================
    # ОСНОВНЫЕ МЕТОДЫ ЗАГРУЗКИ ТЕМЫ
    # ================================================

    def load_theme(self, theme_name, variant="light"):
        """Совместимость: алиас для load()"""
        return self.load(theme_name, variant)

    def load(self, theme_name, variant="light"):
        """🔥 ИСПРАВЛЕННЫЙ ОСНОВНОЙ МЕТОД: Загрузка темы с защитой от циклов"""
        try:
            # 🔥 ЗАЩИТА ОТ ЦИКЛИЧЕСКОЙ РЕКУРСИИ
            if self._loading_in_progress:
                logger.warning(f"Theme loading already in progress, skipping: {theme_name}/{variant}")
                return True
                
            self._loading_in_progress = True
            logger.info(f"Loading theme: {theme_name}/{variant}")
            
            # Проверяем не загружена ли уже эта тема
            if (self.theme_name == theme_name and 
                self.variant == variant and 
                self.theme_data and 
                not self._notification_disabled):
                logger.debug(f"Theme {theme_name}/{variant} already loaded")
                return True
            
            # Устанавливаем значения сразу для предотвращения ошибок
            old_theme = self.theme_name
            old_variant = self.variant
            
            self.theme_name = theme_name
            self.variant = variant
            self.current_theme = theme_name  # Совместимость
            self.current_variant = variant   # Совместимость
            
            # 🔥 ОЧИЩАЕМ КЭШ при смене темы
            self._clear_resource_cache()
            
            # Загружаем данные темы
            success = self._load_theme_data(theme_name, variant)
            
            if success:
                logger.info(f"✅ Theme loaded: {theme_name}/{variant}")
                
                # 🔥 УСЛОВНАЯ ПУБЛИКАЦИЯ СОБЫТИЯ (только если не отключена)
                if not self._notification_disabled:
                    self._notify_theme_changed()
            else:
                # Откатываем при неудаче
                self.theme_name = old_theme
                self.variant = old_variant
                self.current_theme = old_theme
                self.current_variant = old_variant
                logger.error(f"Failed to load theme {theme_name}/{variant}, rolled back")
            
            return success
            
        except Exception as ex:
            logger.error(f"Critical error loading theme {theme_name}/{variant}: {ex}")
            return False
        finally:
            # 🔥 ОБЯЗАТЕЛЬНО СБРАСЫВАЕМ ФЛАГ
            self._loading_in_progress = False

    def load_silently(self, theme_name, variant="light"):
        """🔥 НОВЫЙ: Загрузка темы БЕЗ публикации событий"""
        try:
            self._notification_disabled = True
            return self.load(theme_name, variant)
        finally:
            self._notification_disabled = False

    def force_reload(self, theme_name=None, variant=None):
        """🔥 НОВЫЙ: Принудительная перезагрузка темы"""
        theme_name = theme_name or self.theme_name
        variant = variant or self.variant
        
        if theme_name and variant:
            # Сбрасываем все флаги и состояние
            self._loading_in_progress = False
            self._notification_disabled = False
            self.theme_data = {}
            self._clear_resource_cache()
            return self.load(theme_name, variant)
        return False

    def _load_theme_data(self, theme_name, variant):
        """Внутренний метод загрузки данных темы"""
        try:
            theme_path = os.path.join(self.themes_dir, theme_name, variant, "theme.json")
            
            if not os.path.isfile(theme_path):
                logger.error(f"Theme file not found: {theme_path}")
                logger.info("Using default theme")
                self.theme_data = self.default_theme.copy()
                return False
                
            with open(theme_path, encoding="utf-8") as f:
                loaded_data = json.load(f)
                
            # Мерджим с дефолтными значениями
            self.theme_data = self._merge_with_defaults(loaded_data)
            return True
            
        except Exception as ex:
            logger.warning(f"Failed to load theme data {theme_name}/{variant}: {ex}")
            logger.info("Using default theme")
            self.theme_data = self.default_theme.copy()
            return False

    def _merge_with_defaults(self, loaded_data):
        """Мерджим загруженные данные с дефолтными для предотвращения ошибок"""
        merged = self.default_theme.copy()
        
        for section, values in loaded_data.items():
            if section in merged and isinstance(values, dict):
                merged[section].update(values)
            else:
                merged[section] = values
                
        return merged

    def _notify_theme_changed(self):
        """🔥 ИСПРАВЛЕННОЕ УВЕДОМЛЕНИЕ О СМЕНЕ ТЕМЫ с защитой от циклов"""
        try:
            if self._notification_disabled:
                logger.debug("Theme notification disabled, skipping event")
                return
                
            # 🔥 ЕДИНСТВЕННАЯ точка публикации события с указанием источника
            event_bus.publish("theme_changed", {
                "theme": self.theme_name,
                "variant": self.variant,
                "source": "theme_manager"  # 🔥 КРИТИЧНО: указываем источник
            })
            
            # Также публикуем отдельное событие для варианта
            event_bus.publish("variant_changed", {
                "variant": self.variant,
                "source": "theme_manager"
            })
            
            logger.info(f"🎨 Theme changed event published: {self.theme_name}/{self.variant}")
            
        except Exception as e:
            logger.error(f"Error notifying theme change: {e}")

    # ================================================
    # МЕТОДЫ ПОЛУЧЕНИЯ РЕСУРСОВ С КЭШИРОВАНИЕМ
    # ================================================

    def _clear_resource_cache(self):
        """🔥 НОВОЕ: Очистка кэша ресурсов"""
        self._resource_cache.clear()
        logger.debug("Resource cache cleared")

    def get_color(self, color_name, fallback="#FFFFFF"):
        """Получить цвет в HEX формате с кэшированием"""
        cache_key = f"color_{color_name}_{self.theme_name}_{self.variant}"
        
        if cache_key not in self._resource_cache:
            try:
                color_value = self.theme_data.get("colors", {}).get(color_name, fallback)
                self._resource_cache[cache_key] = color_value
            except Exception as e:
                logger.warning(f"Error getting color {color_name}: {e}")
                self._resource_cache[cache_key] = fallback
                
        return self._resource_cache[cache_key]

    def get_rgba(self, color_name, fallback=(1, 1, 1, 1)):
        """Получить цвет в RGBA формате с кэшированием"""
        cache_key = f"rgba_{color_name}_{self.theme_name}_{self.variant}"
        
        if cache_key not in self._resource_cache:
            try:
                hex_color = self.get_color(color_name)
                rgba = self._hex_to_rgba(hex_color)
                self._resource_cache[cache_key] = rgba
            except Exception as e:
                logger.warning(f"Error converting color {color_name} to RGBA: {e}")
                self._resource_cache[cache_key] = fallback
                
        return self._resource_cache[cache_key]

    def get_param(self, param_name, fallback=None):
        """Получить параметр темы (размеры, отступы и т.д.)"""
        try:
            # Ищем в разных секциях
            for section in ["menu", "layout", "params"]:
                if section in self.theme_data:
                    value = self.theme_data[section].get(param_name)
                    if value is not None:
                        return value
            return fallback
        except Exception as e:
            logger.warning(f"Error getting param {param_name}: {e}")
            return fallback

    def get_font(self, font_name, fallback=""):
        """Получить шрифт"""
        try:
            font_path = self.theme_data.get("fonts", {}).get(font_name, fallback)
            if font_path and font_path != "":
                # Если указан относительный путь, делаем его абсолютным
                if not os.path.isabs(font_path):
                    theme_font_dir = os.path.join(self.themes_dir, self.theme_name, "fonts")
                    full_path = os.path.join(theme_font_dir, font_path)
                    if os.path.isfile(full_path):
                        return full_path
                    else:
                        logger.warning(f"Font file not found: {full_path}")
                        return fallback
                return font_path
            return fallback
        except Exception as e:
            logger.warning(f"Error getting font {font_name}: {e}")
            return fallback

    def get_image(self, image_name, fallback=""):
        """Получить путь к изображению"""
        try:
            image_path = self.theme_data.get("images", {}).get(image_name, fallback)
            if image_path and image_path != "":
                # Если указан относительный путь, делаем его абсолютным
                if not os.path.isabs(image_path):
                    theme_images_dir = os.path.join(self.themes_dir, self.theme_name, self.variant, "images")
                    full_path = os.path.join(theme_images_dir, image_path)
                    if os.path.isfile(full_path):
                        return full_path
                    else:
                        logger.warning(f"Image file not found: {full_path}")
                        return fallback
                return image_path
            return fallback
        except Exception as e:
            logger.warning(f"Error getting image {image_name}: {e}")
            return fallback

    def get_overlay(self, page_name):
        """Получить оверлей для страницы"""
        return self.get_image(f"overlay_{page_name}", self.get_image("overlay_default"))

    def get_sound(self, sound_name, fallback=""):
        """Получить путь к звуку"""
        try:
            sound_path = self.theme_data.get("sounds", {}).get(sound_name, fallback)
            if sound_path and sound_path != "":
                # Если указан относительный путь, делаем его абсолютным
                if not os.path.isabs(sound_path):
                    theme_sounds_dir = os.path.join(self.themes_dir, self.theme_name, "sounds")
                    full_path = os.path.join(theme_sounds_dir, sound_path)
                    if os.path.isfile(full_path):
                        return full_path
                    else:
                        logger.warning(f"Sound file not found: {full_path}")
                        return fallback
                return sound_path
            return fallback
        except Exception as e:
            logger.warning(f"Error getting sound {sound_name}: {e}")
            return fallback

    # ================================================
    # УТИЛИТЫ И ДИАГНОСТИКА
    # ================================================

    def _hex_to_rgba(self, hex_color):
        """Конвертировать HEX в RGBA"""
        try:
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                return (r, g, b, 1.0)
            else:
                logger.warning(f"Invalid hex color format: #{hex_color}")
                return (1.0, 1.0, 1.0, 1.0)
        except Exception as e:
            logger.error(f"Error converting hex to RGBA: {e}")
            return (1.0, 1.0, 1.0, 1.0)

    def is_loaded(self):
        """Проверить, загружена ли тема"""
        return self.theme_name is not None and self.variant is not None and bool(self.theme_data)

    def diagnose_state(self):
        """🔥 НОВОЕ: Диагностика состояния ThemeManager для отладки"""
        return {
            "theme_name": self.theme_name,
            "variant": self.variant,
            "current_theme": self.current_theme,
            "current_variant": self.current_variant,
            "is_loaded": self.is_loaded(),
            "loading_in_progress": self._loading_in_progress,
            "notification_disabled": self._notification_disabled,
            "themes_dir": self.themes_dir,
            "theme_data_keys": list(self.theme_data.keys()) if self.theme_data else [],
            "colors_count": len(self.theme_data.get("colors", {})),
            "fonts_count": len(self.theme_data.get("fonts", {})),
            "images_count": len(self.theme_data.get("images", {})),
            "sounds_count": len(self.theme_data.get("sounds", {})),
            "cache_size": len(self._resource_cache)
        }

    def force_refresh_all_screens(self):
        """🔥 ИСПРАВЛЕНО: Принудительное обновление всех экранов с проверками"""
        try:
            from kivy.app import App
            from kivy.clock import Clock
            
            app = App.get_running_app()
            if not app:
                logger.warning("Cannot access running app for screen refresh")
                return
                
            # 🔥 ИСПРАВЛЕНО: Множественные способы доступа к screen_manager
            sm = None
            
            # Способ 1: Через app.root.screen_manager
            if hasattr(app, 'root') and app.root:
                if hasattr(app.root, 'screen_manager') and app.root.screen_manager:
                    sm = app.root.screen_manager
                # Способ 2: Через app.root.ids.sm (KV файл)
                elif hasattr(app.root, 'ids') and 'sm' in app.root.ids:
                    sm = app.root.ids.sm
                    
            if sm and hasattr(sm, 'screens') and sm.screens:
                refresh_count = 0
                for screen in sm.screens:
                    if hasattr(screen, 'refresh_theme'):
                        Clock.schedule_once(
                            lambda dt, s=screen: s.refresh_theme(), 0.1
                        )
                        refresh_count += 1
                        
                logger.info(f"Force refresh scheduled for {refresh_count} screens")
            else:
                logger.warning("Cannot access screen manager or no screens available")
                # 🔥 НОВОЕ: Публикуем событие как fallback
                event_bus.publish("theme_force_refresh", {
                    "source": "theme_manager_fallback"
                })
                
        except Exception as e:
            logger.error(f"Error force refreshing screens: {e}")


# ================================================
# ГЛОБАЛЬНЫЕ ФУНКЦИИ
# ================================================

# Глобальный экземпляр
theme_manager = ThemeManager()


def get_theme_manager():
    """Безопасное получение экземпляра ThemeManager"""
    return theme_manager


def validate_theme_manager_module():
    """🔥 НОВОЕ: Валидация модуля ThemeManager для отладки"""
    try:
        tm = ThemeManager()
        
        # Проверяем наличие всех методов
        required_methods = [
            'load_theme', 'load', 'load_silently', 'force_reload',
            'get_color', 'get_rgba', 'get_param', 'get_font', 
            'get_image', 'get_overlay', 'get_sound',
            'is_loaded', 'diagnose_state', 'force_refresh_all_screens'
        ]
        
        for method in required_methods:
            assert hasattr(tm, method), f"{method} method missing"
        
        # Проверяем защиту от циклов
        assert hasattr(tm, '_loading_in_progress'), "_loading_in_progress flag missing"
        assert hasattr(tm, '_notification_disabled'), "_notification_disabled flag missing"
        assert hasattr(tm, '_resource_cache'), "_resource_cache missing"
        
        print("✅ ThemeManager module validation passed")
        return True
    except Exception as e:
        print(f"❌ ThemeManager module validation failed: {e}")
        return False


# Только в режиме разработки
if __name__ == "__main__":
    validate_theme_manager_module()