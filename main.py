from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'show_cursor', '1') # Убрать тут курсор
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder

from pages.home import HomeScreen
from pages.alarm import AlarmScreen
from pages.schedule import ScheduleScreen
from pages.weather import WeatherScreen
from pages.pigs import PigsScreen
from pages.settings import SettingsScreen

Builder.load_file("root_widget.kv")
Builder.load_file("top_menu.kv")
Builder.load_file("pages/home.kv")
Builder.load_file("pages/alarm.kv")
Builder.load_file("pages/schedule.kv")
Builder.load_file("pages/weather.kv")
Builder.load_file("pages/pigs.kv")
Builder.load_file("pages/settings.kv")


from root_widget import RootWidget
from theme_manager import theme_manager
from pages.home import HomeScreen
from top_menu import TopMenu

class BedrockApp(App):
    theme_manager = theme_manager

    def build(self):
        Window.fullscreen = 'auto'
        Window.borderless = True
        Window.show_cursor = True  # Убрать тут курсор

        return RootWidget()

if __name__ == "__main__":
    BedrockApp().run()
