import json
import os
from kivy.app import App
from app.event_bus import event_bus

def hex_to_rgba(hex_str, alpha=1.0):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 8:  # #RRGGBBAA
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        a = int(hex_str[6:8], 16) / 255.0
        return (r, g, b, a)
    elif len(hex_str) == 6:  # #RRGGBB
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, alpha)
    else:
        # fallback: почти прозрачный чёрный
        return (0, 0, 0, alpha)


class ThemeManager:
    def __init__(self, themes_dir="themes"):
        self.themes_dir = themes_dir
        self.current_theme = "minecraft"
        self.variant = "light"
        self.theme_data = {}

    def load_theme(self, name=None, variant=None):
        if name:
            self.current_theme = name
        if variant:
            self.variant = variant
        path = os.path.join(self.themes_dir, self.current_theme, self.variant, "theme.json")
        with open(path, "r") as f:
            self.theme_data = json.load(f)
        # Оповещаем всех об изменении темы!
        event_bus.emit("theme_changed")

    def get_font(self, key):
        return self.theme_data.get("fonts", {}).get(key, "Roboto")

    def get_color(self, key):
        return self.theme_data.get("colors", {}).get(key, "#FFFFFF")

    def get_rgba(self, key, alpha=1.0):
        color = self.get_color(key)
        if isinstance(color, str) and color.startswith('#'):
            return hex_to_rgba(color, alpha)
        elif isinstance(color, (list, tuple)) and len(color) == 4:
            return tuple(color)
        else:
            return (0, 0, 0, alpha)

    def get_image(self, key):
        images = self.theme_data.get("images", {})
        rel_path = images.get(key) or images.get("overlay_default") or ""
        if rel_path and not os.path.isabs(rel_path):
            base_dir = os.path.join(self.themes_dir, self.current_theme, self.variant)
            return os.path.join(base_dir, rel_path)
        return rel_path

    def get_sound(self, key):
        sfx = self.theme_data.get("sounds", {})
        path = sfx.get(key, "")
        if path and not os.path.isabs(path):
            return os.path.join(os.getcwd(), path)
        return path

    def get_param(self, key, default=None):
        for section in ("colors", "fonts", "images", "sounds", "menu", None):
            if section:
                val = self.theme_data.get(section, {}).get(key)
                if val is not None:
                    return val
            else:
                val = self.theme_data.get(key)
                if val is not None:
                    return val
        return default

theme_manager = ThemeManager()

def get_rgba(key, alpha=1.0):
    return theme_manager.get_rgba(key, alpha)

def get_font(key):
    return theme_manager.get_font(key)

def get_image(key):
    return theme_manager.get_image(key)
