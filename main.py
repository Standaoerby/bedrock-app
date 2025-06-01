# main.py — исправленная версия с правильной архитектурой

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

# Импорты страниц
from pages.home import HomeScreen
from pages.alarm import AlarmScreen
from pages.schedule import ScheduleScreen
from pages.weather import WeatherScreen
from pages.pigs import PigsScreen
from pages.settings import SettingsScreen

# Импорты архитектуры приложения
from app.localizer import localizer
from app.user_config import user_config
from app.logger import app_logger as logger

# Импорты виджетов
from widgets.root_widget import RootWidget
from widgets.top_menu import TopMenu

# Импорты сервисов
from services.audio_service import audio_service
from services.alarm_service import AlarmService
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from services.sensor_service import SensorService
from services.pigs_service import PigsService
from services.schedule_service import ScheduleService

# AlarmClock может отсутствовать — защищаем импорт
try:
    from services.alarm_clock import AlarmClock
    ALARM_CLOCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AlarmClock unavailable: {e}")
    AlarmClock = None
    ALARM_CLOCK_AVAILABLE = False

# Импортируем theme_manager отдельно ПОСЛЕ настройки Kivy
from app.theme_manager import ThemeManager

# Загружаем KV файлы
Builder.load_file('widgets/root_widget.kv')
Builder.load_file('widgets/top_menu.kv')
Builder.load_file('widgets/overlay_card.kv')
Builder.load_file('pages/home.kv')
Builder.load_file('pages/alarm.kv')
Builder.load_file('pages/schedule.kv')
Builder.load_file('pages/weather.kv')
Builder.load_file('pages/pigs.kv')
Builder.load_file('pages/settings.kv')

logger.info("=== Bedrock 2.0 Started ===")


class BedrockApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Инициализируем theme_manager как экземпляр класса
        self.theme_manager = ThemeManager()
        
        # Остальные менеджеры
        self.localizer = localizer
        self.user_config = user_config
        self.audio_service = audio_service
        
        # Сервисы приложения
        self.alarm_service = None
        self.notification_service = None
        self.weather_service = None
        self.sensor_service = None
        self.pigs_service = None
        self.schedule_service = None
        self.alarm_clock = None
        
        self._services_stopped = False

    def build(self):
        """Построение приложения"""
        try:
            # Загружаем пользовательские настройки
            self._load_user_settings()
            
            # Инициализируем сервисы
            self._initialize_services()
            
            # Создаем корневой виджет
            return RootWidget()
            
        except Exception as e:
            logger.exception(f"Critical error in build(): {e}")
            return None

    def _load_user_settings(self):
        """Загрузка пользовательских настроек"""
        try:
            # Загружаем язык
            lang = self.user_config.get("language", "en")
            self.localizer.load(lang)
            logger.info(f"Language loaded: {lang}")

            # Загружаем тему
            theme_name = self.user_config.get("theme", "minecraft")
            theme_variant = self.user_config.get("variant", "light")
            
            # Проверяем что theme_manager инициализирован
            if hasattr(self, 'theme_manager') and self.theme_manager:
                self.theme_manager.load(theme_name, theme_variant)
                logger.info(f"Theme loaded: {theme_name}/{theme_variant}")
            else:
                logger.error("ThemeManager not initialized!")
            
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")

    def _initialize_services(self):
        """Инициализация всех сервисов"""
        try:
            # Инициализируем сервисы с обработкой ошибок
            services_config = [
                ('alarm_service', AlarmService, {}),
                ('notification_service', NotificationService, {}),
                ('weather_service', WeatherService, {
                    'lat': self.user_config.get('location', {}).get('latitude', 51.5566),
                    'lon': self.user_config.get('location', {}).get('longitude', -0.178)
                }),
                ('sensor_service', SensorService, {}),
                ('pigs_service', PigsService, {}),
                ('schedule_service', ScheduleService, {}),
            ]
            
            for service_name, service_class, kwargs in services_config:
                try:
                    service_instance = service_class(**kwargs)
                    setattr(self, service_name, service_instance)
                    
                    # Запускаем сервис если у него есть метод start
                    if hasattr(service_instance, 'start'):
                        service_instance.start()
                    
                    logger.info(f"Service initialized: {service_name}")
                    
                except Exception as ex:
                    logger.error(f"Failed to initialize {service_name}: {ex}")
                    setattr(self, service_name, None)

            # Инициализируем alarm_clock если доступен
            if ALARM_CLOCK_AVAILABLE:
                try:
                    self.alarm_clock = AlarmClock()
                    self.alarm_clock.start()
                    logger.info("AlarmClock initialized and started")
                except Exception as ex:
                    logger.error(f"AlarmClock initialization failed: {ex}")
                    self.alarm_clock = None
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")

    def on_stop(self):
        """Остановка приложения"""
        if self._services_stopped:
            return
        self._services_stopped = True

        logger.info("Stopping application...")

        # Остановка всех сервисов
        services = [
            'alarm_service', 'notification_service', 'weather_service',
            'sensor_service', 'pigs_service', 'schedule_service'
        ]
        
        for service_name in services:
            service = getattr(self, service_name, None)
            if service:
                try:
                    if hasattr(service, 'stop'):
                        service.stop()
                    logger.info(f"Stopped service: {service_name}")
                except Exception as ex:
                    logger.warning(f"Failed to stop {service_name}: {ex}")

        # Остановка alarm_clock
        if self.alarm_clock:
            try:
                self.alarm_clock.stop()
                logger.info("AlarmClock stopped")
            except Exception as ex:
                logger.warning(f"Failed to stop AlarmClock: {ex}")

        logger.info("=== Bedrock 2.0 Stopped ===")

    def switch_theme(self, theme, variant):
        """Глобальная смена темы"""
        try:
            if hasattr(self, 'theme_manager') and self.theme_manager:
                self.theme_manager.load(theme, variant)
                logger.info(f"Theme switched to {theme}/{variant}")
            else:
                logger.error("ThemeManager not available for theme switch")
        except Exception as e:
            logger.error(f"Error switching theme: {e}")

    def switch_language(self, lang):
        """Глобальная смена языка"""
        try:
            if hasattr(self, 'localizer') and self.localizer:
                self.localizer.load(lang)
                logger.info(f"Language switched to {lang}")
            else:
                logger.error("Localizer not available for language switch")
        except Exception as e:
            logger.error(f"Error switching language: {e}")

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        if hasattr(self, 'theme_manager') and self.theme_manager:
            return self.theme_manager
        else:
            logger.warning("ThemeManager not available, creating fallback")
            # Создаем fallback theme_manager
            fallback_tm = ThemeManager()
            fallback_tm.load("minecraft", "light")
            return fallback_tm


if __name__ == '__main__':
    try:
        BedrockApp().run()
    except Exception as e:
        logger.exception(f"Critical application error: {e}")
        sys.exit(1)