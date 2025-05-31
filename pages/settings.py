from kivy.uix.screenmanager import Screen
from kivy.app import App
from app.app_state import app_state
from app.user_config import user_config
from app.localizer import localizer
from app.event_bus import event_bus

class SettingsScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh_theme()

    def refresh_theme(self):
        app = App.get_running_app()
        tm = app.theme_manager
        if "theme_label" in self.ids:
            self.ids.theme_label.color = tm.get_color("primary")

    def on_theme_select(self, theme):
        app_state.theme = theme
        app = App.get_running_app()
        app.theme_manager.load_theme(theme, app.theme_manager.variant)

    def on_variant_select(self, variant):
        app_state.variant = variant
        app = App.get_running_app()
        app.theme_manager.load_theme(app.theme_manager.current_theme, variant)

    def on_language_select(self, lang):
        user_config.set("language", lang)
        App.get_running_app().localizer.load(lang)
        event_bus.emit("language_changed")
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        event_bus.subscribe("language_changed", self.refresh_text)

    def refresh_text(self, *args):
        self.ids.theme_label.text = App.get_running_app().localizer.t("settings_theme")
        self.ids.lang_label.text = App.get_running_app().localizer.t("settings_language")
        # и другие надписи по месту

