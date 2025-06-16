# main.py - ИСПРАВЛЕННАЯ версия с правильной инициализацией сервисов
"""
ИСПРАВЛЕНИЯ:
✅ WeatherService получает координаты из user_config
✅ AutoThemeService получает правильные зависимости
✅ Правильная последовательность инициализации сервисов
✅ Гарантированная загрузка темы перед UI
✅ Улучшенная обработка ошибок
"""

from kivy.config import Config
import sys
import threading
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
from kivy.clock import Clock

# Импорты архитектуры приложения
from app.localizer import localizer
from app.user_config import user_config
from app.logger import app_logger as logger
from app.theme_manager import ThemeManager

# Импорты виджетов
from widgets.root_widget import RootWidget
from widgets.top_menu import TopMenu

# Импорты страниц
from pages.home import HomeScreen
from pages.alarm import AlarmScreen
from pages.schedule import ScheduleScreen
from pages.weather import WeatherScreen
from pages.pigs import PigsScreen
from pages.settings import SettingsScreen

# Импорты сервисов
from services.audio_service import AudioService
from services.alarm_service import AlarmService
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from services.sensor_service import SensorService
from services.pigs_service import PigsService
from services.schedule_service import ScheduleService
from services.auto_theme_service import AutoThemeService
from services.volume_service import VolumeControlService

# AlarmClock с защищенным импортом
try:
    from services.alarm_clock import AlarmClock
    ALARM_CLOCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AlarmClock not available: {e}")
    ALARM_CLOCK_AVAILABLE = False


class BedrockApp(App):
    """Основное приложение Bedrock 2.0"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Архитектура приложения
        self.user_config = user_config
        self.localizer = localizer
        self.theme_manager = None
        
        # Сервисы (будут инициализированы позже)
        self.audio_service = None
        self.alarm_service = None
        self.notification_service = None
        self.weather_service = None
        self.sensor_service = None
        self.pigs_service = None
        self.schedule_service = None
        self.auto_theme_service = None
        self.volume_service = None
        self.alarm_clock = None
        
        logger.info("BedrockApp instance created")

    def build_config(self, config):
        """Настройка конфигурации Kivy"""
        pass

    def build(self):
        """Построение интерфейса приложения"""
        try:
            logger.info("🚀 Starting Bedrock 2.0...")
            
            # 1. Инициализация theme_manager и загрузка темы
            self._initialize_theme_manager()
            
            # 2. Загрузка KV файлов
            self._load_kv_files()
            
            # 3. Создание корневого виджета
            root = RootWidget()
            
            # 4. Инициализация сервисов (отложенная)
            self._initialize_services()
            
            logger.info("✅ Bedrock 2.0 initialized successfully")
            return root
            
        except Exception as e:
            logger.error(f"❌ Critical error during build: {e}")
            raise

    def _initialize_theme_manager(self):
        """Инициализация и загрузка темы"""
        try:
            logger.info("🎨 Initializing theme manager...")
            
            # Создаем theme_manager
            self.theme_manager = ThemeManager()
            
            # Получаем тему и вариант из конфигурации
            theme_name = self.user_config.get("theme", "minecraft")
            theme_variant = self.user_config.get("variant", "light")
            
            # Загружаем тему
            if self.theme_manager.load(theme_name, theme_variant):
                logger.info(f"✅ Theme loaded: {theme_name}/{theme_variant}")
            else:
                logger.warning(f"⚠️ Failed to load theme, using default")
                
        except Exception as e:
            logger.error(f"❌ Error initializing theme manager: {e}")
            # Создаем дефолтный theme_manager
            self.theme_manager = ThemeManager()

    def _load_kv_files(self):
        """Загрузка KV файлов"""
        try:
            logger.info("📁 Loading KV files...")
            
            kv_files = [
                "widgets/root_widget.kv",
                "widgets/top_menu.kv", 
                "widgets/overlay_card.kv",  # Ваш существующий OverlayCard
                "pages/home.kv",
                "pages/alarm.kv",
                "pages/schedule.kv",
                "pages/weather.kv",
                "pages/pigs.kv",
                "pages/settings.kv"
            ]
            
            for kv_file in kv_files:
                try:
                    Builder.load_file(kv_file)
                    logger.debug(f"✅ Loaded KV: {kv_file}")
                except Exception as e:
                    logger.error(f"❌ Failed to load KV file {kv_file}: {e}")
                    # Не останавливаем загрузку из-за одного файла
                    
        except Exception as e:
            logger.error(f"❌ Error loading KV files: {e}")
            raise

    def _initialize_services(self):
        """Инициализация всех сервисов"""
        try:
            logger.info("🔧 Initializing services...")
            
            # Основные сервисы
            self._initialize_core_services()
            
            # Сервис с зависимостями
            self._initialize_dependent_services()
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")

    def _initialize_core_services(self):
        """Инициализация основных сервисов"""
        try:
            # Audio Service
            try:
                self.audio_service = AudioService()
                logger.info("✅ audio_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ audio_service not available: {e}")
                self.audio_service = None
            
            # Alarm Service
            try:
                self.alarm_service = AlarmService()
                logger.info("✅ alarm_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ alarm_service not available: {e}")
                self.alarm_service = None
            
            # Notification Service
            try:
                self.notification_service = NotificationService()
                logger.info("✅ notification_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ notification_service not available: {e}")
                self.notification_service = None
            
            # Weather Service с координатами из user_config -- ПОПРАВИТЬ НА РЕФАКТОРЕ
            try:
                location = self.user_config.get("location", {})
                lat = location.get("latitude", 51.5566)
                lon = location.get("longitude", -0.178)
                
                # Убеждаемся что координаты корректные числа
                lat = float(lat) if lat is not None else 51.5566
                lon = float(lon) if lon is not None else -0.178
                
                self.weather_service = WeatherService(lat=lat, lon=lon)
                logger.info("✅ weather_service initialized")
                
            except Exception as e:
                logger.error(f"❌ weather_service failed: {e}")
                logger.info("🔧 Continuing without weather service...")
                self.weather_service = None
            
            # Sensor Service
            try:
                self.sensor_service = SensorService()
                if hasattr(self.sensor_service, 'start'):
                    self.sensor_service.start()
                logger.info("✅ sensor_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ sensor_service not available: {e}")
                self.sensor_service = None
            
            # Volume Service
            try:
                self.volume_service = VolumeControlService()
                if hasattr(self.volume_service, 'start'):
                    self.volume_service.start()
                logger.info("✅ volume_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ volume_service not available: {e}")
                self.volume_service = None
            
            # Pigs Service
            try:
                self.pigs_service = PigsService()
                logger.info("✅ pigs_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ pigs_service not available: {e}")
                self.pigs_service = None
            
            # Schedule Service
            try:
                self.schedule_service = ScheduleService()
                logger.info("✅ schedule_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ schedule_service not available: {e}")
                self.schedule_service = None
                
        except Exception as e:
            logger.error(f"Error in core services initialization: {e}")

    def _initialize_dependent_services(self):
        """Инициализация сервисов с зависимостями"""
        try:
            logger.info("🔄 Initializing dependent services...")
            
            # ИСПРАВЛЕНО: Auto Theme Service с правильными зависимостями
            try:
                if self.sensor_service is not None and self.theme_manager is not None:
                    self.auto_theme_service = AutoThemeService(
                        sensor_service=self.sensor_service,
                        theme_manager=self.theme_manager
                    )
                    if hasattr(self.auto_theme_service, 'start'):
                        self.auto_theme_service.start()
                    logger.info("✅ auto_theme_service initialized")
                else:
                    logger.warning("⚠️ auto_theme_service not available (missing dependencies)")
                    
            except Exception as e:
                logger.warning(f"⚠️ auto_theme_service not available: {e}")
                self.auto_theme_service = None
            
            # Alarm Clock (зависит от audio_service)
            try:
                if ALARM_CLOCK_AVAILABLE and self.audio_service is not None:
                    self.alarm_clock = AlarmClock()
                    if hasattr(self.alarm_clock, 'start'):
                        self.alarm_clock.start()
                    logger.info("✅ alarm_clock initialized")
                else:
                    logger.warning("⚠️ alarm_clock not available")
                    
            except Exception as e:
                logger.warning(f"⚠️ alarm_clock not available: {e}")
                self.alarm_clock = None
            
            # Настройка auto-theme
            self._setup_auto_theme()
            
            # Настройка volume service
            self._setup_volume_service()
            
            # ИСПРАВЛЕНО: Принудительное обновление темы для всех экранов
            self._force_theme_refresh()
            
            logger.info("✅ All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error finalizing dependent services: {e}")

    def _setup_auto_theme(self):
        """Настройка автотемы"""
        try:
            if self.auto_theme_service is not None:
                auto_theme_enabled = self.user_config.get("auto_theme_enabled", False)
                threshold = self.user_config.get("light_sensor_threshold", 3)
                
                if auto_theme_enabled:
                    self.auto_theme_service.set_enabled(True)
                    logger.info(f"Auto-theme enabled with threshold: {threshold}s")
                    
                    # Первичная проверка автотемы через 3 секунды
                    Clock.schedule_once(lambda dt: self._initial_auto_theme_check(), 3.0)
                    
        except Exception as e:
            logger.error(f"Error setting up auto-theme: {e}")

    def _initial_auto_theme_check(self):
        """Первичная проверка автотемы"""
        try:
            if self.auto_theme_service is not None:
                self.auto_theme_service.check_and_update_theme()
                logger.info("Initial auto-theme check completed")
        except Exception as e:
            logger.error(f"Error in initial auto-theme check: {e}")

    def _setup_volume_service(self):
        """Настройка volume service"""
        try:
            if self.volume_service is not None:
                # Устанавливаем начальную громкость из конфигурации
                initial_volume = self.user_config.get("volume", 0.7)
                self.volume_service.set_volume(initial_volume)
                logger.info(f"Volume service configured with initial volume: {initial_volume}")
        except Exception as e:
            logger.error(f"Error setting up volume service: {e}")

    def _force_theme_refresh(self):
        """НОВОЕ: Принудительное обновление темы для всех экранов"""
        try:
            logger.info("🎨 Forcing theme refresh for all screens...")
            
            # Обновляем root widget
            if self.root and hasattr(self.root, 'refresh_theme'):
                Clock.schedule_once(lambda dt: self.root.refresh_theme(), 0.2)
            
            # Обновляем все экраны через screen_manager
            if self.root and hasattr(self.root, 'screen_manager'):
                sm = self.root.screen_manager
                if sm and hasattr(sm, 'screens'):
                    for screen in sm.screens:
                        if hasattr(screen, 'refresh_theme'):
                            Clock.schedule_once(lambda dt, s=screen: s.refresh_theme(), 0.3)
                            
            logger.info("✅ Theme refresh scheduled for all screens")
            
        except Exception as e:
            logger.error(f"Error forcing theme refresh: {e}")

    def on_start(self):
        """Вызывается после полного запуска приложения"""
        try:
            logger.info("🎉 Bedrock 2.0 started successfully!")
            
            # Финальная проверка и диагностика
            self._final_diagnostics()
            
        except Exception as e:
            logger.error(f"Error in on_start: {e}")

    def _final_diagnostics(self):
        """Финальная диагностика состояния приложения"""
        try:
            logger.info("📊 Running final diagnostics...")
            
            # Проверяем theme_manager
            if self.theme_manager:
                logger.info(f"Theme Manager: {self.theme_manager.current_theme}/{self.theme_manager.current_variant}")
                logger.info(f"Theme loaded: {self.theme_manager.is_loaded()}")
            
            # Считаем инициализированные сервисы
            services = [
                'audio_service', 'alarm_service', 'notification_service',
                'weather_service', 'sensor_service', 'volume_service',
                'pigs_service', 'schedule_service', 'auto_theme_service',
                'alarm_clock'
            ]
            
            initialized_count = sum(1 for service in services if getattr(self, service, None) is not None)
            logger.info(f"Services initialized: {initialized_count}/{len(services)}")
            
            # Проверяем root widget
            if self.root:
                logger.info("Root widget created successfully")
                if hasattr(self.root, 'screen_manager') and self.root.screen_manager:
                    screens_count = len(self.root.screen_manager.screens)
                    logger.info(f"Screens loaded: {screens_count}")
            
            logger.info("✅ Diagnostics completed")
            
        except Exception as e:
            logger.error(f"Error in diagnostics: {e}")

    def on_stop(self):
        """Корректное завершение приложения"""
        try:
            logger.info("🛑 Shutting down Bedrock 2.0...")
            
            # Останавливаем сервисы
            services_to_stop = [
                'auto_theme_service', 'alarm_clock', 'volume_service',
                'sensor_service', 'audio_service'
            ]
            
            for service_name in services_to_stop:
                service = getattr(self, service_name, None)
                if service and hasattr(service, 'stop'):
                    try:
                        service.stop()
                        logger.info(f"Stopped {service_name}")
                    except Exception as e:
                        logger.error(f"Error stopping {service_name}: {e}")
            
            logger.info("✅ Bedrock 2.0 shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    try:
        app = BedrockApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Critical application error: {e}")
        sys.exit(1)