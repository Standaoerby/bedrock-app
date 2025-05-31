import json
import os

def hex_to_rgba(hex_str, alpha=1.0):
    hex_str = hex_str.lstrip('#')
    lv = len(hex_str)
    rgb = tuple(int(hex_str[i:i + lv // 3], 16) / 255 for i in range(0, lv, lv // 3))
    return (*rgb, alpha)

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
        print("LOADING THEME FROM:", path)
        with open(path, "r") as f:
            self.theme_data = json.load(f)
        print("theme_data images:", self.theme_data.get("images"))


    def get_font(self, key):
        return self.theme_data.get("fonts", {}).get(key, "Roboto")

    def get_color(self, key):
        return self.theme_data.get("colors", {}).get(key, "#FFFFFF")

    def get_rgba(self, key, alpha=1.0):
        color = self.get_color(key)
        if isinstance(color, str) and color.startswith('#'):
            return hex_to_rgba(color, alpha)
        elif isinstance(color, (list, tuple)):
            return tuple(color)
        else:
            return (1, 1, 1, alpha)

    def get_image(self, key):
        images = self.theme_data.get("images", {})
        rel_path = images.get(key) or images.get("overlay_default") or ""
        if rel_path and not os.path.isabs(rel_path):
            # Собери полный путь до файла
            base_dir = os.path.join(self.themes_dir, self.current_theme, self.variant)
            return os.path.join(base_dir, rel_path)
        return rel_path
    def get_sound(self, key):
        sfx = self.theme_data.get("sounds", {})
        path = sfx.get(key, "")
        if path and not os.path.isabs(path):
            # Абсолютный путь относительно main.py
            return os.path.join(os.getcwd(), path)
        return path

theme_manager = ThemeManager()
