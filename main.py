from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'show_cursor', '0')
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')

from kivy.app import App
from kivy.core.window import Window
from app_state import app_state
from event_bus import event_bus
from theme_manager import theme_manager
from audio_service import audio_service

from kivy.uix.screenmanager import ScreenManager
from pages.home import HomeScreen

class BedrockApp(App):
    theme_manager = theme_manager
    def build(self):        
        Window.fullscreen = 'auto'
        Window.borderless = True
        Window.show_cursor = False

        # Менеджер экранов
        self.sm = ScreenManager()
        self.sm.add_widget(HomeScreen(name='home'))

        # Подписка на события
        event_bus.subscribe("theme_changed", self.on_theme_changed)
        event_bus.subscribe("audio_play", lambda file: audio_service.play(file))
        return self.sm

    def on_theme_changed(self, new_theme, **kwargs):
        theme_manager.load_theme(new_theme)
        if hasattr(self.sm.current_screen, 'refresh_theme'):
            self.sm.current_screen.refresh_theme()

if __name__ == "__main__":
    BedrockApp().run()