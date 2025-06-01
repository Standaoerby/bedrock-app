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
                "accent": "#277da1"
            },
            "fonts": {
                "main": "Minecraftia-Regular.ttf"
            },
            "images": {
                "background": "background.png"
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
        from kivy.utils import get_color_from_hex
        hex_color = self.get_color(name, fallback)
        return get_color_from_hex(hex_color)

    def get_font(self, name):
        """Вернуть путь к шрифту по имени."""
        font_file = self.theme_data.get("fonts", {}).get(name)
        if not font_file:
            # Фолбэк на дефолт
            font_file = self.default_theme["fonts"].get(name, "Minecraftia-Regular.ttf")
        path = os.path.join(
            self.themes_dir, self.theme_name, "fonts", font_file
        )
        if not os.path.isfile(path):
            logger.warning(f"Font not found: {path}, using default")
            return os.path.join(self.themes_dir, self.theme_name, "fonts", "Minecraftia-Regular.ttf")
        return path

    def get_image(self, name):
        """Вернуть путь к изображению по имени (например, 'background' или 'btn_bg')."""
        img_file = self.theme_data.get("images", {}).get(name)
        if not img_file:
            # Фолбэк: совпадает с именем файла
            img_file = f"{name}.png"
        path = os.path.join(
            self.themes_dir, self.theme_name, self.variant, img_file
        )
        if not os.path.isfile(path):
            logger.warning(f"Image not found: {path}, using fallback")
            # Можно фолбэк на дефолтный фон или прозрачку
            fallback_path = os.path.join(
                self.themes_dir, self.theme_name, self.variant, "background.png"
            )
            return fallback_path if os.path.isfile(fallback_path) else ""
        return path

    def get_overlay(self, page_name):
        """Вернуть путь к overlay-файлу для страницы."""
        overlay_name = f"overlay_{page_name}.png"
        path = os.path.join(
            self.themes_dir, self.theme_name, self.variant, overlay_name
        )
        if os.path.isfile(path):
            return path
        # fallback: overlay_default.png
        fallback = os.path.join(
            self.themes_dir, self.theme_name, self.variant, "overlay_default.png"
        )
        if os.path.isfile(fallback):
            return fallback
        return ""

    def get_sound(self, name):
        """Вернуть путь к звуковому файлу по имени (например, 'click')."""
        sound_file = f"{name}.ogg"
        path = os.path.join(
            self.themes_dir, self.theme_name, "sounds", sound_file
        )
        if not os.path.isfile(path):
            logger.warning(f"Sound not found: {path}")
            return ""
        return path

# Глобальный singleton
theme_manager = ThemeManager()
