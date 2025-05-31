from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from app.event_bus import event_bus

class RootWidget(BoxLayout):
    current_page = StringProperty("home")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        event_bus.subscribe("screen_changed", self.on_screen_changed)

    def switch_screen(self, screen_name):
        self.current_page = screen_name
        self.ids.sm.current = screen_name
        event_bus.emit("screen_changed", page=screen_name)

    def on_screen_changed(self, page, **kwargs):
        self.current_page = page
        print("current_page:", self.current_page)

