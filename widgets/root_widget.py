from kivy.properties import StringProperty
from kivy.uix.floatlayout import FloatLayout
from app.event_bus import event_bus
from kivy.app import App



class RootWidget(FloatLayout):
    current_page = StringProperty("home")
    def switch_screen(self, page_name):
        self.ids.sm.current = page_name
        self.current_page = page_name


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        event_bus.subscribe("theme_changed", self.refresh_theme_everywhere)

    def refresh_theme_everywhere(self, **kwargs):
        app = App.get_running_app()
        self.ids.background_image.source = app.theme_manager.get_image("background")
        self.ids.overlay_image.source = app.theme_manager.get_image("overlay_" + self.current_page)
        self.ids.topmenu.refresh_theme()
