from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty

class TopMenu(BoxLayout):
    current_page = StringProperty("home")
    def select(self, page_name):
        if self.parent:
            self.parent.switch_screen(page_name)
