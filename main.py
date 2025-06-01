# main.py — оптимизированная версия

from kivy.config import Config
import sys
import platform

# Настройки Kivy для разных платформ
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '600')
if platform.system() == "Linux":
    Config.set('graphics', 'fullscreen', 'auto')
    Config.set('graphics', 'borderless', '1')
    Config.set('graphics', 'show_cursor', '0')
else:
    Config.set('graphics', 'fullscreen', '0')
    Config.set('graphics', 'borderless', '0')
    Config.set('graphics', 'show_cursor', '1')

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window

from pages.home import HomeScreen
from pages.alarm import AlarmScreen
from pages.schedule import ScheduleScreen
from pages.weather import WeatherScreen
from pages.pigs import PigsScreen
from pages.settings import SettingsScreen

from app.theme_manager import theme_manager
from app.localizer import localizer
from app.user_config import user_config
from app.logger import app_logger as logger

from widgets.root_widget import RootWidget
from widgets.top_menu import TopMenu

from services.audio_service import audio_service
from services.alarm_service import AlarmService
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from services.sensor_service import SensorService
from services.pigs_service import PigsService

# AlarmClock может отсутствовать — защищаем импорт
try:
    from services.alarm_clock import AlarmClock
    ALARM_CLOCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AlarmClock unavailable: {e}")
    AlarmClock = None
    ALARM_CLOCK_AVAILABLE = False

logger.info("=== App Started ===")

class BedrockApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_manager = theme_manager
        self.localizer = localizer
        self.user_config = user_config
        self.audio_service = audio_service
        self.services = []
        self._services_stopped = False

    def build(self):
        # Загружаем язык
        lang = self.user_config.get("language", "en")
        self.localizer.load(lang)

        # Загружаем тему
        theme_name = self.user_config.get("theme", "minecraft")
        theme_variant = self.user_config.get("variant", "light")
        self.theme_manager.load(theme_name, theme_variant)

        # Инициализация сервисов (могут быть синглтоны, но список для единого контроля)
        self.services = [
            AlarmService(),
            NotificationService(),
            WeatherService(),
            SensorService(),
            PigsService(),
            # Можно добавить еще сервисы по необходимости
        ]
        for service in self.services:
            try:
                service.start()
                logger.info(f"Started service: {service.__class__.__name__}")
            except Exception as ex:
                logger.error(f"Service start failed: {service.__class__.__name__}: {ex}")

        # Встроить alarm_clock если доступен
        self.alarm_clock = AlarmClock() if ALARM_CLOCK_AVAILABLE else None
        if self.alarm_clock:
            try:
                self.alarm_clock.start()
                logger.info("AlarmClock started")
            except Exception as ex:
                logger.error(f"AlarmClock start failed: {ex}")

        # Root layout: menu + экран
        return RootWidget()

    def on_stop(self):
        if self._services_stopped:
            return
        self._services_stopped = True

        # Остановка сервисов
        for service in self.services:
            try:
                service.stop()
                logger.info(f"Stopped service: {service.__class__.__name__}")
            except Exception as ex:
                logger.warning(f"Failed to stop service: {service.__class__.__name__}: {ex}")
        if self.alarm_clock:
            try:
                self.alarm_clock.stop()
            except Exception as ex:
                logger.warning(f"Failed to stop AlarmClock: {ex}")

        logger.info("=== App Stopped ===")

    # Глобальная смена темы (для всех экранов)
    def switch_theme(self, theme, variant):
        self.theme_manager.load(theme, variant)
        # Инвалидировать все экраны
        if self.root:
            self.root.invalidate_theme()

    # Глобальная смена языка
    def switch_language(self, lang):
        self.localizer.load(lang)
        if self.root:
            self.root.invalidate_language()

if __name__ == '__main__':
    try:
        BedrockApp().run()
    except Exception as e:
        logger.exception(f"Critical error: {e}")
