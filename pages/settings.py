from kivy.uix.screenmanager import Screen
from kivy.app import App

class SettingsScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh_theme()

    def refresh_theme(self):
        app = App.get_running_app()
        tm = app.theme_manager
        # Пример смены цвета label, если надо
        if "theme_label" in self.ids:
            self.ids.theme_label.color = tm.get_color("primary")

    def on_theme_select(self, theme):
        app = App.get_running_app()
        app.theme_manager.load_theme(theme, app.theme_manager.variant)
        # Можно сделать: event_bus.emit("theme_changed", theme=theme)
        self.refresh_theme()

    def on_variant_select(self, variant):
        app = App.get_running_app()
        app.theme_manager.load_theme(app.theme_manager.current_theme, variant)
        # Можно сделать: event_bus.emit("theme_changed", variant=variant)
        self.refresh_theme()
