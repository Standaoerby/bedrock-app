import json
import os

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

    def get_color(self, key):
        return self.theme_data.get("colors", {}).get(key, "#FFFFFF")

    def get_image(self, key):
        return self.theme_data.get("images", {}).get(key, "")

theme_manager = ThemeManager()