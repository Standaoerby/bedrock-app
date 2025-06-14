# app/theme_manager.py
# ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ с защитой от циклических рекурсий

import os
import json
from app.logger import app_logger as logger


class ThemeManager:
    """
    Менеджер тем с защитой от циклических рекурсий.
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
        """🔥 ОСНОВНОЙ МЕТОД: Загрузка темы с защитой от циклов"""
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
        """🔥 УВЕДОМЛЕНИЕ О СМЕНЕ ТЕМЫ с защитой от циклов"""
        try:
            # Дополнительная защита
            if self._loading_in_progress:
                logger.debug("Skipping theme notification - loading in progress")
                return
                
            from app.event_bus import event_bus
            event_bus.publish("theme_changed", {
                "theme": self.theme_name,
                "variant": self.variant,
                "source": "theme_manager"  # 🔥 УКАЗЫВАЕМ ИСТОЧНИК для предотвращения циклов
            })
            logger.debug(f"Theme change event published: {self.theme_name}/{self.variant}")
        except Exception as e:
            logger.error(f"Error notifying theme change: {e}")

    # ================================================
    # МЕТОДЫ ПОЛУЧЕНИЯ РЕСУРСОВ ТЕМЫ
    # ================================================

    def get_color(self, name, fallback="#ffffff"):
        """Получить hex-цвет по имени"""
        try:
            color = self.theme_data.get("colors", {}).get(name)
            if color:
                return color
            return fallback
        except Exception:
            return fallback

    def get_rgba(self, name, fallback="#ffffff"):
        """Получить цвет в формате RGBA для Kivy (tuple 0..1)"""
        try:
            from kivy.utils import get_color_from_hex
            hex_color = self.get_color(name, fallback)
            
            # Проверяем валидность
            if not isinstance(hex_color, str):
                logger.warning(f"Color {name} is not a string: {hex_color}, using fallback")
                hex_color = fallback
                
            if not hex_color.startswith('#'):
                logger.warning(f"Color {name} invalid format: {hex_color}, using fallback")
                hex_color = fallback
                
            return get_color_from_hex(hex_color)
        except Exception as e:
            logger.error(f"Error getting RGBA color {name}: {e}")
            return [1, 1, 1, 1]

    def get_param(self, name, fallback=None):
        """Получить параметр темы из любой секции"""
        try:
            # Ищем в разных секциях
            for section_name, section_data in self.theme_data.items():
                if isinstance(section_data, dict) and name in section_data:
                    return section_data[name]
            return fallback
        except Exception:
            return fallback

    def get_font(self, name, fallback=""):
        """Получить путь к шрифту или пустую строку для дефолта"""
        try:
            font_file = self.theme_data.get("fonts", {}).get(name)
            
            # Если шрифт не задан, возвращаем пустую строку (дефолтный шрифт)
            if not font_file:
                return ""
            
            if not self.theme_name:
                logger.warning("Theme not loaded, using default font")
                return ""
            
            # Проверяем полный путь vs относительный
            if os.path.sep in font_file or '/' in font_file:
                path = font_file
            else:
                # Шрифты лежат в папке темы, НЕ в папке варианта
                path = os.path.join(self.themes_dir, self.theme_name, "fonts", font_file)
            
            path = os.path.normpath(path)
                
            if not os.path.isfile(path):
                logger.warning(f"Font not found: {path}, using default")
                return ""  # Пустая строка = дефолтный шрифт Kivy
                
            return path
        except Exception as e:
            logger.error(f"Error getting font {name}: {e}")
            return ""

    def get_image(self, name):
        """Получить путь к изображению"""
        try:
            img_file = self.theme_data.get("images", {}).get(name)
            if not img_file:
                # Фолбэк: имя файла совпадает с именем
                img_file = f"{name}.png"
            
            if not self.theme_name or not self.variant:
                logger.warning("Theme not loaded, using fallback")
                return ""
            
            # Проверяем полный путь vs относительный
            if os.path.sep in img_file or '/' in img_file:
                path = img_file
            else:
                # Изображения лежат в папке варианта
                path = os.path.join(self.themes_dir, self.theme_name, self.variant, img_file)
            
            path = os.path.normpath(path)
                
            if not os.path.isfile(path):
                logger.warning(f"Image not found: {path}, trying fallback")
                # Фолбэк на дефолтный фон
                fallback_path = os.path.join(
                    self.themes_dir, self.theme_name, self.variant, "background.png"
                )
                fallback_path = os.path.normpath(fallback_path)
                if os.path.isfile(fallback_path):
                    return fallback_path
                else:
                    logger.warning(f"Fallback image also not found: {fallback_path}")
                    return ""
            return path
        except Exception as e:
            logger.error(f"Error getting image {name}: {e}")
            return ""

    def get_overlay(self, page_name):
        """Получить путь к overlay-файлу для страницы"""
        try:
            overlay_name = f"overlay_{page_name}.png"
            if not self.theme_name or not self.variant:
                return ""
                
            path = os.path.join(self.themes_dir, self.theme_name, self.variant, overlay_name)
            path = os.path.normpath(path)
            
            if os.path.isfile(path):
                return path
            
            # Фолбэк: overlay_default.png
            fallback = os.path.join(
                self.themes_dir, self.theme_name, self.variant, "overlay_default.png"
            )
            fallback = os.path.normpath(fallback)
            if os.path.isfile(fallback):
                return fallback
            return ""
        except Exception as e:
            logger.error(f"Error getting overlay {page_name}: {e}")
            return ""

    def get_sound(self, name):
        """Получить путь к звуковому файлу"""
        try:
            sound_file = self.theme_data.get("sounds", {}).get(name)
            if not sound_file:
                sound_file = f"{name}.ogg"
            
            if not self.theme_name:
                return ""
            
            # Проверяем полный путь vs относительный
            if os.path.sep in sound_file or '/' in sound_file:
                path = sound_file
            else:
                # Звуки лежат в папке темы, НЕ в папке варианта
                path = os.path.join(self.themes_dir, self.theme_name, "sounds", sound_file)
            
            path = os.path.normpath(path)
                
            if not os.path.isfile(path):
                logger.warning(f"Sound not found: {path}")
                return ""
            return path
        except Exception as e:
            logger.error(f"Error getting sound {name}: {e}")
            return ""

    # ================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ================================================

    def is_loaded(self):
        """Проверить, загружена ли тема"""
        return self.theme_name is not None and self.variant is not None

    def diagnose_state(self):
        """Диагностика состояния ThemeManager"""
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
            "sounds_count": len(self.theme_data.get("sounds", {}))
        }


# ================================================
# ГЛОБАЛЬНЫЕ ФУНКЦИИ
# ================================================

# Глобальный экземпляр
theme_manager = ThemeManager()


def get_theme_manager():
    """Безопасное получение экземпляра ThemeManager"""
    return theme_manager


def validate_theme_manager_module():
    """Валидация модуля ThemeManager для отладки"""
    try:
        tm = ThemeManager()
        
        # Проверяем наличие всех методов
        required_methods = [
            'load_theme', 'load', 'load_silently', 'force_reload',
            'get_color', 'get_rgba', 'get_param', 'get_font', 
            'get_image', 'get_overlay', 'get_sound',
            'is_loaded', 'diagnose_state'
        ]
        
        for method in required_methods:
            assert hasattr(tm, method), f"{method} method missing"
        
        # Проверяем защиту от циклов
        assert hasattr(tm, '_loading_in_progress'), "_loading_in_progress flag missing"
        assert hasattr(tm, '_notification_disabled'), "_notification_disabled flag missing"
        
        print("✅ ThemeManager module validation passed")
        return True
    except Exception as e:
        print(f"❌ ThemeManager module validation failed: {e}")
        return False


# Только в режиме разработки
if __name__ == "__main__":
    validate_theme_manager_module()