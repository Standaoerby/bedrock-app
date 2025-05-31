from kivy.uix.screenmanager import Screen
from kivy.app import App
from app.event_bus import event_bus  # импортируй event_bus
from app.localizer import localizer  # если нужен прямой доступ

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        event_bus.subscribe("language_changed", self.refresh_text)  # подписка

    def on_pre_enter(self, *args):
        self.refresh_theme()
        self.refresh_text()  # обновим текст сразу

    def refresh_theme(self):
        app = App.get_running_app()
        theme_manager = app.theme_manager
        if "title_label" in self.ids:
            self.ids.title_label.color = theme_manager.get_color("primary")
        if "form_label" in self.ids:
            self.ids.form_label.color = theme_manager.get_color("text")
        if "input_box" in self.ids:
            self.ids.input_box.background_color = theme_manager.get_color("background")

    def refresh_text(self, *args):
        app = App.get_running_app()
        if "title_label" in self.ids:
            self.ids.title_label.text = app.localizer.t("menu_home")
        if "form_label" in self.ids:
            self.ids.form_label.text = app.localizer.t("example_form")
        if "input_box" in self.ids:
            self.ids.input_box.hint_text = app.localizer.t("hint_input")
