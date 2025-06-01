import os
import json
from app.logger import app_logger as logger

class ThemeManager:
    """
    Менеджер тем. Отвечает за загрузку, хранение и отдачу ресурсов темы:
    цвета, изображения, шрифты, иконки, оверлеи, звуки и т.д.
    """
    def __init__(self, themes_dir="themes"):
        self.themes_dir = themes_dir
        self.theme_name = None
        self.variant = None
        self.theme_data = {}
        self.default_theme = {
            "colors": {
                "primary": "#40916c",
                "background": "#f0efeb",
                "accent": "#277da1",
                "text": "#ffffff",
                "text_secondary": "#aaaaaa",
                "menu_color": "#25252580"
            },
            "fonts": {
                "main": "Minecraftia-Regular.ttf",
                "title": "Minecraftia-Regular.ttf"
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

    def load(self, theme_name, variant="light"):
        """Загрузка новой темы и варианта (light/dark)."""
        self.theme_name = theme_name
        self.variant = variant
        theme_path = os.path.join(
            self.themes_dir, theme_name, variant, "theme.json"
        )
        try:
            with open(theme_path, encoding="utf-8") as f:
                self.theme_data = json.load(f)
            logger.info(f"Theme loaded: {theme_name}/{variant}")
        except Exception as ex:
            logger.warning(f"Failed to load theme {theme_name}/{variant}: {ex}")
            self.theme_data = self.default_theme.copy()

    def get_color(self, name, fallback="#ffffff"):
        """Вернуть hex-цвет по имени (например, 'primary')."""
        try:
            return self.theme_data.get("colors", {}).get(name) or fallback
        except Exception:
            return fallback

    def get_rgba(self, name, fallback="#ffffff"):
        """Вернуть цвет в формате RGBA для Kivy (tuple 0..1)."""
        try:
            from kivy.utils import get_color_from_hex
            hex_color = self.get_color(name, fallback)
            return get_color_from_hex(hex_color)
        except Exception as e:
            logger.error(f"Error getting RGBA color {name}: {e}")
            return [1, 1, 1, 1]

    def get_param(self, name, fallback=None):
        """Получить параметр темы (например, menu_height, button_width)."""
        try:
            # Сначала ищем в menu секции
            menu_params = self.theme_data.get("menu", {})
            if name in menu_params:
                return menu_params[name]
            
            # Потом в colors секции
            colors = self.theme_data.get("colors", {})
            if name in colors:
                return colors[name]
            
            # Потом в корне theme_data
            if name in self.theme_data:
                return self.theme_data[name]
            
            # Fallback к default_theme
            default_menu = self.default_theme.get("menu", {})
            if name in default_menu:
                return default_menu[name]
            
            default_colors = self.default_theme.get("colors", {})
            if name in default_colors:
                return default_colors[name]
            
            return fallback
        except Exception as e:
            logger.error(f"Error getting param {name}: {e}")
            return fallback

    def get_font(self, name):
        """Вернуть путь к шрифту по имени."""
        try:
            # Получаем имя файла шрифта из конфигурации темы
            font_file = self.theme_data.get("fonts", {}).get(name)
            if not font_file:
                # Фолбэк на дефолт
                font_file = self.default_theme["fonts"].get(name, "Minecraftia-Regular.ttf")
            
            if not self.theme_name:
                logger.warning("Theme not loaded, using default font")
                return ""
            
            # ИСПРАВЛЕНИЕ: Проверяем, не является ли font_file уже полным путем
            if os.path.sep in font_file or '/' in font_file:
                # Если в font_file уже есть путь, используем его как есть
                path = font_file
            else:
                # Если это просто имя файла, формируем полный путь
                path = os.path.join(
                    self.themes_dir, self.theme_name, "fonts", font_file
                )
            
            # Нормализуем путь для корректного отображения
            path = os.path.normpath(path)
            
            if not os.path.isfile(path):
                logger.warning(f"Font not found: {path}, trying fallback")
                # Пробуем fallback путь
                fallback_path = os.path.join(self.themes_dir, self.theme_name, "fonts", "Minecraftia-Regular.ttf")
                fallback_path = os.path.normpath(fallback_path)
                if os.path.isfile(fallback_path):
                    return fallback_path
                else:
                    logger.warning(f"Fallback font also not found: {fallback_path}")
                    return ""
            
            return path
        except Exception as e:
            logger.error(f"Error getting font {name}: {e}")
            return ""

    def get_image(self, name):
        """Вернуть путь к изображению по имени (например, 'background' или 'btn_bg')."""
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
        """Вернуть путь к звуковому файлу по имени (например, 'click')."""
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
                # Если это просто имя файла, формируем полный путь
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

# Глобальный singleton
theme_manager = ThemeManager()