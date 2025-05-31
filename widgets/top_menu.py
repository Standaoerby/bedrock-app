from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.app import App

class TopMenu(BoxLayout):
    current_page = StringProperty("home")

    def select(self, page_name):
        app = App.get_running_app()
        if hasattr(app.root, "switch_screen"):
            app.root.switch_screen(page_name)

    def refresh_theme(self):
        app = App.get_running_app()
        self.canvas.ask_update()
        for btn in self.children:
            if hasattr(btn, 'background_normal'):
                btn.background_normal = app.theme_manager.get_image("menu_button_bg")
                btn.background_down = app.theme_manager.get_image("menu_button_bg_active")
                btn.color = app.theme_manager.get_rgba("menu_button_text")
