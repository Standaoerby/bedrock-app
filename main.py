from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'borderless', '0')
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
from widgets.top_menu import TopMenu
from services.audio_service import audio_service
from services.alarm_service import AlarmService
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from services.sensor_service import SensorService
from app.logger import app_logger as logger
logger.info("=== App Started ===")

# Window.fullscreen = 'auto' Это отключил на винде, может пригодиться на Пи
# Window.borderless = True
# Window.show_cursor = True # Убрать тут курсор
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
        location = user_config.get("location", {})
        lat = location.get("latitude", 55.7522)  # Москва, пример
        lon = location.get("longitude", 37.6156)
        self.weather_service = WeatherService(lat, lon)
        
        # Инициализация сервиса датчиков
        self.sensor_service = SensorService()
        try:
            self.sensor_service.start()
            logger.info("SensorService started successfully")
        except Exception as e:
            logger.error(f"Failed to start SensorService: {e}")
            # Сервис датчиков не критичен, продолжаем работу
            self.sensor_service = None

        Builder.load_file("widgets/root_widget.kv")
        Builder.load_file("widgets/top_menu.kv")
        Builder.load_file("pages/home.kv")
        Builder.load_file("pages/alarm.kv")
        Builder.load_file("pages/schedule.kv")
        Builder.load_file("pages/weather.kv")
        Builder.load_file("pages/pigs.kv")
        Builder.load_file("pages/settings.kv")
        Builder.load_file("widgets/overlay_card.kv")
        
        # Воспроизведение звука запуска
        startup_sound = self.theme_manager.get_sound("startup")
        if startup_sound:
            audio_service.play(startup_sound)
        
        return RootWidget()
    
    def on_stop(self):
        """Закрытие приложения - остановка сервисов"""
        logger.info("=== App Stopping ===")
        
        # Останавливаем все сервисы
        try:
            if hasattr(self, 'sensor_service') and self.sensor_service:
                self.sensor_service.stop()
                logger.info("SensorService stopped")
        except Exception as e:
            logger.error(f"Error stopping SensorService: {e}")
            
        try:
            if hasattr(self, 'alarm_service') and self.alarm_service:
                self.alarm_service.stop()
                logger.info("AlarmService stopped")
        except Exception as e:
            logger.error(f"Error stopping AlarmService: {e}")
            
        try:
            if hasattr(self, 'audio_service') and self.audio_service:
                self.audio_service.stop()
                logger.info("AudioService stopped")
        except Exception as e:
            logger.error(f"Error stopping AudioService: {e}")
        
        logger.info("=== App Stopped ===")

if __name__ == "__main__":
    BedrockApp().run()