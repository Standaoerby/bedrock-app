# app/theme_manager.py
# ИСПРАВЛЕНО: Добавлен метод load_theme, исправлены ошибки с путями и шрифтами

import os
import json
from app.logger import app_logger as logger

class ThemeManager:
    """
    ИСПРАВЛЕНО: Менеджер тем с правильными методами загрузки
    Отвечает за загрузку, хранение и отдачу ресурсов темы:
    цвета, изображения, шрифты, иконки, оверлеи, звуки и т.д.
    """
    def __init__(self, themes_dir="themes"):
        self.themes_dir = themes_dir
        self.theme_name = None
        self.variant = None
        self.theme_data = {}
        self.current_theme = None  # ДОБАВЛЕНО для совместимости
        self.current_variant = None  # ДОБАВЛЕНО для совместимости
        
        self.default_theme = {
            "colors": {
                "primary": "#40916c",
                "background": "#f0efeb",
                "accent": "#277da1",
                "text": "#000000",  # ИСПРАВЛЕНО: темный текст для светлой темы
                "text_secondary": "#666666",  # ИСПРАВЛЕНО: правильный цвет
                "menu_color": "#25252580",
                "menu_button_text": "#ffffff",
                "menu_button_text_active": "#40916c",
                "overlay_card": "#ffffff"  # ДОБАВЛЕНО
            },
            "fonts": {
                "main": "",  # ИСПРАВЛЕНО: пустая строка = дефолтный шрифт
                "title": ""  # ИСПРАВЛЕНО: пустая строка = дефолтный шрифт
            },
            "images": {
                "background": "background.png",
                "button_bg": "btn_bg.png",
                "button_bg_active": "btn_bg_active.png",
                "menu_button_bg": "menu_btn.png",
                "menu_button_bg_active": "menu_btn_active.png"
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

    def load_theme(self, theme_name, variant="light"):
        """ИСПРАВЛЕНО: Правильный метод для загрузки темы (используется в main.py)"""
        return self.load(theme_name, variant)

    def load(self, theme_name, variant="light"):
        """Загрузка новой темы и варианта (light/dark)."""
        self.theme_name = theme_name
        self.variant = variant
        self.current_theme = theme_name  # Для совместимости
        self.current_variant = variant   # Для совместимости
        
        theme_path = os.path.join(
            self.themes_dir, theme_name, variant, "theme.json"
        )
        
        try:
            with open(theme_path, encoding="utf-8") as f:
                loaded_data = json.load(f)
                
            # Мерджим с дефолтными значениями для предотвращения ошибок
            self.theme_data = self._merge_with_defaults(loaded_data)
            logger.info(f"Theme loaded: {theme_name}/{variant}")
            return True
            
        except Exception as ex:
            logger.warning(f"Failed to load theme {theme_name}/{variant}: {ex}")
            logger.info("Using default theme")
            self.theme_data = self.default_theme.copy()
            return False

    def _merge_with_defaults(self, loaded_data):
        """НОВОЕ: Мерджим загруженные данные с дефолтными для предотвращения ошибок"""
        merged = self.default_theme.copy()
        
        for section, values in loaded_data.items():
            if section in merged and isinstance(values, dict):
                merged[section].update(values)
            else:
                merged[section] = values
                
        return merged

    def get_color(self, name, fallback="#ffffff"):
        """Вернуть hex-цвет по имени (например, 'primary')."""
        try:
            color = self.theme_data.get("colors", {}).get(name)
            if color:
                return color
            return fallback
        except Exception:
            return fallback

    def get_rgba(self, name, fallback="#ffffff"):
        """ИСПРАВЛЕНО: Вернуть цвет в формате RGBA для Kivy (tuple 0..1)."""
        try:
            from kivy.utils import get_color_from_hex
            hex_color = self.get_color(name, fallback)
            
            # ИСПРАВЛЕНИЕ: Проверяем что hex_color это строка
            if not isinstance(hex_color, str):
                logger.warning(f"Color {name} is not a string: {hex_color}, using fallback")
                hex_color = fallback
                
            # Проверяем формат hex
            if not hex_color.startswith('#'):
                logger.warning(f"Color {name} invalid format: {hex_color}, using fallback")
                hex_color = fallback
                
            return get_color_from_hex(hex_color)
        except Exception as e:
            logger.error(f"Error getting RGBA color {name}: {e}")
            return [1, 1, 1, 1]

    def get_param(self, name, fallback=None):
        """Получить параметр темы (например, menu_height, button_width)."""
        try:
            # Ищем в разных секциях
            for section_name, section_data in self.theme_data.items():
                if isinstance(section_data, dict) and name in section_data:
                    return section_data[name]
            return fallback
        except Exception:
            return fallback

    def get_font(self, name, fallback=""):
        """ИСПРАВЛЕНО: Вернуть путь к шрифту или пустую строку для дефолта."""
        try:
            font_file = self.theme_data.get("fonts", {}).get(name)
            
            # ИСПРАВЛЕНИЕ: Если шрифт не задан или пустой, возвращаем пустую строку
            if not font_file:
                return ""
            
            if not self.theme_name:
                logger.warning("Theme not loaded, using default font")
                return ""
            
            # Проверяем, не является ли font_file уже полным путем
            if os.path.sep in font_file or '/' in font_file:
                path = font_file
            else:
                # ИСПРАВЛЕНО: Шрифты лежат в папке темы, а НЕ в папке варианта!
                path = os.path.join(
                    self.themes_dir, self.theme_name, "fonts", font_file
                )
            
            path = os.path.normpath(path)
                
            if not os.path.isfile(path):
                logger.warning(f"Font not found: {path}, using default")
                return ""  # Пустая строка = дефолтный шрифт Kivy
                
            return path
        except Exception as e:
            logger.error(f"Error getting font {name}: {e}")
            return ""

    def get_image(self, name):
        """ИСПРАВЛЕНО: Вернуть путь к изображению или пустую строку."""
        try:
            img_file = self.theme_data.get("images", {}).get(name)
            if not img_file:
                # Фолбэк: совпадает с именем файла
                img_file = f"{name}.png"
            
            if not self.theme_name or not self.variant:
                logger.warning("Theme not loaded, using fallback")
                return ""
            
            # ИСПРАВЛЕНИЕ: Проверяем, не является ли img_file уже полным путем
            if os.path.sep in img_file or '/' in img_file:
                # Если в img_file уже есть путь, используем его как есть
                path = img_file
            else:
                # Если это просто имя файла, формируем полный путь
                path = os.path.join(
                    self.themes_dir, self.theme_name, self.variant, img_file
                )
            
            # Нормализуем путь
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
        """Вернуть путь к overlay-файлу для страницы."""
        try:
            overlay_name = f"overlay_{page_name}.png"
            if not self.theme_name or not self.variant:
                return ""
                
            path = os.path.join(
                self.themes_dir, self.theme_name, self.variant, overlay_name
            )
            path = os.path.normpath(path)
            
            if os.path.isfile(path):
                return path
            # fallback: overlay_default.png
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
        """ИСПРАВЛЕНО: Вернуть путь к звуковому файлу по имени (например, 'click')."""
        try:
            sound_file = self.theme_data.get("sounds", {}).get(name)
            if not sound_file:
                sound_file = f"{name}.ogg"
            
            if not self.theme_name:
                return ""
            
            # ИСПРАВЛЕНИЕ: Проверяем, не является ли sound_file уже полным путем
            if os.path.sep in sound_file or '/' in sound_file:
                # Если в sound_file уже есть путь, используем его как есть
                path = sound_file
            else:
                # ИСПРАВЛЕНО: Звуки лежат в папке темы, а НЕ в папке варианта!
                path = os.path.join(
                    self.themes_dir, self.theme_name, "sounds", sound_file
                )
            
            # Нормализуем путь
            path = os.path.normpath(path)
                
            if not os.path.isfile(path):
                logger.warning(f"Sound not found: {path}")
                return ""
            return path
        except Exception as e:
            logger.error(f"Error getting sound {name}: {e}")
            return ""

    def is_loaded(self):
        """Проверить, загружена ли тема."""
        return self.theme_name is not None and self.variant is not None

    def diagnose_state(self):
        """НОВОЕ: Диагностика состояния ThemeManager"""
        return {
            "theme_name": self.theme_name,
            "variant": self.variant,
            "current_theme": self.current_theme,
            "current_variant": self.current_variant,
            "is_loaded": self.is_loaded(),
            "themes_dir": self.themes_dir,
            "theme_data_keys": list(self.theme_data.keys()) if self.theme_data else [],
            "colors_count": len(self.theme_data.get("colors", {})),
            "fonts_count": len(self.theme_data.get("fonts", {})),
            "images_count": len(self.theme_data.get("images", {})),
            "sounds_count": len(self.theme_data.get("sounds", {}))
        }

# ИСПРАВЛЕНО: Создаем глобальный экземпляр с правильной инициализацией
theme_manager = ThemeManager()

def get_theme_manager():
    """НОВОЕ: Безопасное получение экземпляра ThemeManager"""
    return theme_manager

def validate_theme_manager_module():
    """НОВОЕ: Валидация модуля ThemeManager для отладки"""
    try:
        tm = ThemeManager()
        assert hasattr(tm, 'load_theme'), "load_theme method missing"
        assert hasattr(tm, 'load'), "load method missing"
        assert hasattr(tm, 'get_color'), "get_color method missing"
        assert hasattr(tm, 'get_rgba'), "get_rgba method missing"
        assert hasattr(tm, 'get_font'), "get_font method missing"
        print("✅ ThemeManager module validation passed")
        return True
    except Exception as e:
        print(f"❌ ThemeManager module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_theme_manager_module()