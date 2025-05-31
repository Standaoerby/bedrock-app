from kivy.uix.screenmanager import Screen
from kivy.app import App
from app.app_state import app_state

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
        app_state.theme = theme
        app = App.get_running_app()
        app.theme_manager.load_theme(theme, app.theme_manager.variant)
        # Не вызываем refresh_theme — всё обновится по событию!

    def on_variant_select(self, variant):
        app_state.variant = variant
        app = App.get_running_app()
        app.theme_manager.load_theme(app.theme_manager.current_theme, variant)
        # Не вызываем refresh_theme — всё обновится по событию!
