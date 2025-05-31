from kivy.uix.screenmanager import Screen
from kivy.app import App

class HomeScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh_theme()

    def refresh_theme(self):
        app = App.get_running_app()
        theme_manager = app.theme_manager
        if "title_label" in self.ids:
            self.ids.title_label.color = theme_manager.get_color("primary")
        if "form_label" in self.ids:
            self.ids.form_label.color = theme_manager.get_color("text")
        if "input_box" in self.ids:
            self.ids.input_box.background_color = theme_manager.get_color("background")
