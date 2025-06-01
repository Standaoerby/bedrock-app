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
from services.alarm_clock import AlarmClock
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from services.sensor_service import SensorService
from services.pigs_service import PigsService
from app.logger import app_logger as logger
logger.info("=== App Started ===")

# Window.fullscreen = 'auto' Это отключил на винде, может пригодиться на Пи
# Window.borderless = True
# Window.show_cursor = True # Убрать тут курсор
class BedrockApp(App):
    theme_manager = theme_manager
    audio_service = audio_service

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Флаги для предотвращения двойной остановки сервисов
        self._services_stopped = False
        self._stopping_in_progress = False

    def build(self):

        # Локализация
        localizer.load(user_config.get("language", "en"))
        self.localizer = localizer
        self.pigs_service = PigsService()
        theme_manager.load_theme(user_config.get("theme"), user_config.get("variant"))

        # Инициализация сервисов
        self.alarm_service = AlarmService()
        self.alarm_clock = AlarmClock()
        try:
            self.alarm_clock.start()
            logger.info("AlarmClock started successfully")
        except Exception as e:
            logger.error(f"Failed to start AlarmClock: {e}")
            # AlarmClock не критичен, продолжаем работу
            self.alarm_clock = None
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
        Builder.load_file("pages/pigs.kv")
        
        # Воспроизведение звука запуска
        startup_sound = self.theme_manager.get_sound("startup")
        if startup_sound:
            audio_service.play(startup_sound)
        
        return RootWidget()
    
    def stop_services_safely(self):
        """Безопасная остановка всех сервисов с защитой от повторного вызова"""
        if self._services_stopped or self._stopping_in_progress:
            logger.debug("Services already stopped or stopping in progress, skipping")
            return
        
        self._stopping_in_progress = True
        logger.info("=== Starting Services Shutdown ===")
        
        # Список сервисов для остановки в правильном порядке
        services_to_stop = [
            ('alarm_clock', 'AlarmClock'),
            ('sensor_service', 'SensorService'),
            ('alarm_service', 'AlarmService'),
            ('audio_service', 'AudioService'),
            ('weather_service', 'WeatherService'),
            ('pigs_service', 'PigsService'),
            ('notification_service', 'NotificationService')
        ]
        
        for service_attr, service_name in services_to_stop:
            try:
                if hasattr(self, service_attr):
                    service = getattr(self, service_attr)
                    if service and hasattr(service, 'stop'):
                        logger.info(f"Stopping {service_name}...")
                        service.stop()
                        logger.info(f"{service_name} stopped successfully")
                    else:
                        logger.debug(f"{service_name} has no stop method or is None")
                else:
                    logger.debug(f"{service_name} attribute not found")
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        self._services_stopped = True
        self._stopping_in_progress = False
        logger.info("=== Services Shutdown Complete ===")
    
    def on_stop(self):
        """Закрытие приложения - остановка сервисов"""
        logger.info("=== App Stopping ===")
        
        # Безопасная остановка всех сервисов
        self.stop_services_safely()
        
        logger.info("=== App Stopped ===")

if __name__ == "__main__":
    BedrockApp().run()