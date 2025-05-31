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
from app.user_config import user_config
from app.localizer import localizer
from widgets.root_widget import RootWidget
from app.theme_manager import theme_manager
from pages.home import HomeScreen
from widgets.top_menu import TopMenu
from services.audio_service import audio_service
from services.alarm_service import AlarmService
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from app.logger import app_logger as logger
logger.info("=== App Started ===")

Window.fullscreen = 'auto'
Window.borderless = True
Window.show_cursor = True # Убрать тут курсор
class BedrockApp(App):
    theme_manager = theme_manager
    audio_service = audio_service

    def build(self):

        # Локализация
        localizer.load(user_config.get("language", "en"))
        self.localizer = localizer
        theme_manager.load_theme(user_config.get("theme"), user_config.get("variant"))

        # Инициализация сервисов
        self.alarm_service = AlarmService()
        self.notification_service = NotificationService()
        # Координаты для погоды — лучше взять из user_config, а если нет, использовать дефолтные:
        lat = user_config.get("lat", 55.7522)  # Москва, пример
        lon = user_config.get("lon", 37.6156)
        self.weather_service = WeatherService(lat, lon)

        Builder.load_file("widgets/root_widget.kv")
        Builder.load_file("widgets/top_menu.kv")
        Builder.load_file("pages/home.kv")
        Builder.load_file("pages/alarm.kv")
        Builder.load_file("pages/schedule.kv")
        Builder.load_file("pages/weather.kv")
        Builder.load_file("pages/pigs.kv")
        Builder.load_file("pages/settings.kv")
        Builder.load_file("widgets/overlay_card.kv")
        audio_service.play(self.theme_manager.get_sound("startup"))
        return RootWidget()

if __name__ == "__main__":
    BedrockApp().run()
