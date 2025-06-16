# main.py - ИСПРАВЛЕННАЯ версия с оптимизированной инициализацией
"""
КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
✅ Правильный порядок инициализации сервисов (независимые → зависимые)
✅ Устранение WARNING'ов "service not available" 
✅ Отложенная инициализация зависимых сервисов
✅ Улучшенная обработка ошибок
✅ Оптимизация загрузки темы
✅ Защита от повторной инициализации
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
    """Основное приложение Bedrock 2.0 с оптимизированной инициализацией"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Архитектура приложения
        self.user_config = user_config
        self.localizer = localizer
        self.theme_manager = None
        
        # ✅ НОВОЕ: Флаги состояния инициализации
        self._core_services_initialized = False
        self._dependent_services_initialized = False
        self._initialization_in_progress = False
        
        # Сервисы (будут инициализированы в правильном порядке)
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
            
            # Защита от повторного запуска
            if self._initialization_in_progress:
                logger.warning("Initialization already in progress")
                return
                
            self._initialization_in_progress = True
            
            # 1. ✅ Инициализация theme_manager и загрузка темы (ПРИОРИТЕТ!)
            self._initialize_theme_manager()
            
            # 2. ✅ Загрузка KV файлов после загрузки темы
            self._load_kv_files()
            
            # 3. ✅ Создание корневого виджета
            root = RootWidget()
            
            # 4. ✅ Отложенная инициализация сервисов (избегаем блокировку UI)
            Clock.schedule_once(lambda dt: self._initialize_services_staged(), 0.1)
            
            logger.info("✅ Bedrock 2.0 UI initialized successfully")
            return root
            
        except Exception as e:
            logger.error(f"❌ Critical error during build: {e}")
            raise
        finally:
            self._initialization_in_progress = False

    def _initialize_theme_manager(self):
        """✅ Оптимизированная инициализация и загрузка темы"""
        try:
            logger.info("🎨 Initializing theme manager...")
            
            # Создаем оптимизированный theme_manager
            self.theme_manager = ThemeManager()
            
            # Получаем тему и вариант из конфигурации
            theme_name = self.user_config.get("theme", "minecraft")
            theme_variant = self.user_config.get("variant", "light")
            
            # Загружаем тему с проверкой
            if self.theme_manager.load(theme_name, theme_variant):
                logger.info(f"✅ Theme loaded: {theme_name}/{theme_variant}")
                
                # Получаем статистику кэша для отладки (только в debug режиме)
                if logger.level <= 10:  # DEBUG level
                    stats = self.theme_manager.get_cache_stats()
                    logger.debug(f"Theme cache initialized: {stats['cached_fonts']} fonts, {stats['cached_colors']} colors")
            else:
                logger.warning(f"⚠️ Failed to load theme, using default")
                
        except Exception as e:
            logger.error(f"❌ Error initializing theme manager: {e}")
            # Создаем дефолтный theme_manager
            self.theme_manager = ThemeManager()

    def _load_kv_files(self):
        """✅ Оптимизированная загрузка KV файлов"""
        try:
            logger.info("📁 Loading KV files...")
            
            kv_files = [
                "widgets/root_widget.kv",
                "widgets/top_menu.kv", 
                "widgets/overlay_card.kv",
                "pages/home.kv",
                "pages/alarm.kv",
                "pages/schedule.kv",
                "pages/weather.kv",
                "pages/pigs.kv",
                "pages/settings.kv"
            ]
            
            loaded_count = 0
            for kv_file in kv_files:
                try:
                    Builder.load_file(kv_file)
                    loaded_count += 1
                    logger.debug(f"✅ Loaded KV: {kv_file}")
                except Exception as e:
                    logger.error(f"❌ Failed to load KV file {kv_file}: {e}")
                    # Не останавливаем загрузку из-за одного файла
                    
            logger.info(f"✅ Loaded {loaded_count}/{len(kv_files)} KV files")
                    
        except Exception as e:
            logger.error(f"❌ Error loading KV files: {e}")

    def _initialize_services_staged(self):
        """✅ НОВОЕ: Поэтапная инициализация сервисов"""
        try:
            logger.info("🔧 Initializing services (staged)...")
            
            # Этап 1: Независимые сервисы
            self._initialize_independent_services()
            
            # Этап 2: Сервисы с зависимостями (через небольшую задержку)
            Clock.schedule_once(lambda dt: self._initialize_dependent_services(), 0.5)
            
        except Exception as e:
            logger.error(f"Error in staged services initialization: {e}")

    def _initialize_independent_services(self):
        """✅ Инициализация независимых сервисов (БЕЗ WARNING'ов)"""
        try:
            logger.info("🔧 Initializing independent services...")
            
            # Список сервисов без зависимостей
            independent_services = [
                ('audio_service', AudioService, 'Audio system'),
                ('notification_service', NotificationService, 'Notifications'),
                ('alarm_service', AlarmService, 'Alarm management'),
                ('pigs_service', PigsService, 'Pigs management'),
                ('schedule_service', ScheduleService, 'Schedule management'),
            ]
            
            initialized_count = 0
            
            for service_name, service_class, description in independent_services:
                try:
                    service_instance = service_class()
                    setattr(self, service_name, service_instance)
                    logger.info(f"✅ {service_name} initialized ({description})")
                    initialized_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ {service_name} not available: {e}")
                    setattr(self, service_name, None)
            
            # Специальная инициализация WeatherService с координатами
            self._initialize_weather_service()
            if self.weather_service:
                initialized_count += 1
            
            # Специальная инициализация SensorService
            self._initialize_sensor_service()
            if self.sensor_service:
                initialized_count += 1
                
            # Специальная инициализация VolumeService
            self._initialize_volume_service()
            if self.volume_service:
                initialized_count += 1
            
            self._core_services_initialized = True
            logger.info(f"✅ Independent services initialized: {initialized_count}/8")
            
        except Exception as e:
            logger.error(f"Error initializing independent services: {e}")

    def _initialize_weather_service(self):
        """✅ Специальная инициализация WeatherService с координатами"""
        try:
            location = self.user_config.get("location", {})
            lat = location.get("latitude", 51.5566)
            lon = location.get("longitude", -0.178)
            
            # Убеждаемся что координаты корректные числа
            lat = float(lat) if lat is not None else 51.5566
            lon = float(lon) if lon is not None else -0.178
            
            self.weather_service = WeatherService(lat=lat, lon=lon)
            logger.info(f"✅ weather_service initialized (lat: {lat}, lon: {lon})")
            
        except Exception as e:
            logger.warning(f"⚠️ weather_service not available: {e}")
            self.weather_service = None

    def _initialize_sensor_service(self):
        """✅ Специальная инициализация SensorService"""
        try:
            self.sensor_service = SensorService()
            
            # Запускаем сервис если есть метод start
            if hasattr(self.sensor_service, 'start'):
                self.sensor_service.start()
                
            logger.info("✅ sensor_service initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ sensor_service not available: {e}")
            self.sensor_service = None

    def _initialize_volume_service(self):
        """✅ Специальная инициализация VolumeService"""
        try:
            self.volume_service = VolumeControlService()
            
            # Запускаем сервис если есть метод start
            if hasattr(self.volume_service, 'start'):
                self.volume_service.start()
                
            logger.info("✅ volume_service initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ volume_service not available: {e}")
            self.volume_service = None

    def _initialize_dependent_services(self):
        """✅ Инициализация сервисов с зависимостями"""
        try:
            logger.info("🔄 Initializing dependent services...")
            
            # AutoThemeService требует sensor_service и theme_manager
            self._initialize_auto_theme_service()
            
            # AlarmClock требует alarm_service и audio_service  
            self._initialize_alarm_clock()
            
            # Финальная настройка сервисов
            self._setup_service_configurations()
            
            # Принудительное обновление темы для всех экранов
            Clock.schedule_once(lambda dt: self._force_theme_refresh(), 0.5)
            
            self._dependent_services_initialized = True
            logger.info("✅ Dependent services initialized")
            
        except Exception as e:
            logger.error(f"Error initializing dependent services: {e}")

    def _initialize_auto_theme_service(self):
        """✅ Инициализация AutoThemeService с зависимостями"""
        try:
            if self.sensor_service is not None and self.theme_manager is not None:
                self.auto_theme_service = AutoThemeService(
                    sensor_service=self.sensor_service,
                    theme_manager=self.theme_manager
                )
                
                # Запускаем сервис
                if hasattr(self.auto_theme_service, 'start'):
                    self.auto_theme_service.start()
                    
                logger.info("✅ auto_theme_service initialized")
                
                # Планируем первичную проверку автотемы
                Clock.schedule_once(lambda dt: self._initial_auto_theme_check(), 2.0)
            else:
                logger.warning("⚠️ auto_theme_service dependencies not available")
                self.auto_theme_service = None
                
        except Exception as e:
            logger.warning(f"⚠️ auto_theme_service not available: {e}")
            self.auto_theme_service = None

    def _initialize_alarm_clock(self):
        """✅ Инициализация AlarmClock с зависимостями"""
        try:
            # ИСПРАВЛЕНО: AlarmClock создается БЕЗ параметров (конструктор не принимает аргументы)
            if ALARM_CLOCK_AVAILABLE:
                self.alarm_clock = AlarmClock()
                
                # Запускаем alarm clock
                if hasattr(self.alarm_clock, 'start'):
                    self.alarm_clock.start()
                    
                logger.info("✅ alarm_clock initialized")
            else:
                logger.warning("⚠️ alarm_clock not available (module not found)")
                self.alarm_clock = None
                
        except Exception as e:
            logger.warning(f"⚠️ alarm_clock not available: {e}")
            self.alarm_clock = None

    def _setup_service_configurations(self):
        """✅ Настройка конфигураций сервисов"""
        try:
            # Настройка volume service
            if self.volume_service is not None:
                initial_volume = self.user_config.get("volume", 65)  # В процентах
                try:
                    # Конвертируем в 0.0-1.0 если нужно
                    if initial_volume > 1:
                        volume_float = initial_volume / 100.0
                    else:
                        volume_float = initial_volume
                    self.volume_service.set_volume(volume_float)
                    logger.info(f"[Volume service configured with initial volume] {initial_volume}%")
                except Exception as e:
                    logger.error(f"Error setting initial volume: {e}")
            
            # Настройка auto-theme (ИСПРАВЛЕНО: правильные методы API)
            if self.auto_theme_service is not None:
                auto_enabled = self.user_config.get("auto_theme", False)
                threshold = self.user_config.get("light_threshold", 3.0)
                
                try:
                    # ИСПРАВЛЕНО: используем set_enabled и calibrate_sensor
                    if auto_enabled:
                        self.auto_theme_service.set_enabled(True)
                        logger.info("Auto-theme enabled")
                    
                    # Устанавливаем порог через калибровку
                    self.auto_theme_service.calibrate_sensor(threshold)
                    logger.info(f"[Auto-theme threshold set] {threshold}s")
                    
                except Exception as e:
                    logger.error(f"Error configuring auto-theme: {e}")
                    
        except Exception as e:
            logger.error(f"Error setting up service configurations: {e}")

    def _initial_auto_theme_check(self):
        """Первичная проверка автотемы"""
        try:
            if self.auto_theme_service is not None:
                self.auto_theme_service.check_and_update_theme()
                logger.info("Initial auto-theme check completed")
        except Exception as e:
            logger.error(f"Error in initial auto-theme check: {e}")

    def _force_theme_refresh(self):
        """✅ Принудительное обновление темы для всех экранов"""
        try:
            logger.info("🎨 Forcing theme refresh for all screens...")
            
            # Обновляем root widget
            if self.root and hasattr(self.root, 'refresh_theme'):
                Clock.schedule_once(lambda dt: self.root.refresh_theme(), 0.1)
            
            # Обновляем все экраны через screen_manager
            if self.root and hasattr(self.root, 'screen_manager'):
                sm = self.root.screen_manager
                if sm and hasattr(sm, 'screens'):
                    for i, screen in enumerate(sm.screens):
                        if hasattr(screen, 'refresh_theme'):
                            # Распределяем обновления по времени для плавности
                            delay = 0.2 + (i * 0.1)
                            Clock.schedule_once(lambda dt, s=screen: s.refresh_theme(), delay)
                            
            logger.info("✅ Theme refresh scheduled for all screens")
            
        except Exception as e:
            logger.error(f"Error forcing theme refresh: {e}")

    def on_start(self):
        """Вызывается после полного запуска приложения"""
        try:
            # Ждем завершения инициализации сервисов
            Clock.schedule_once(lambda dt: self._finalize_startup(), 1.0)
            
        except Exception as e:
            logger.error(f"Error in on_start: {e}")

    def _finalize_startup(self):
        """✅ Финализация запуска приложения"""
        try:
            logger.info("🎉 Bedrock 2.0 started successfully!")
            
            # Финальная диагностика
            self._final_diagnostics()
            
            # Показываем уведомление о успешном запуске (ИСПРАВЛЕНО: используем add)
            if self.notification_service:
                username = self.user_config.get("username", "User")
                self.notification_service.add(
                    f"Welcome back, {username}! Bedrock 2.0 is ready.", 
                    "system"
                )
                
        except Exception as e:
            logger.error(f"Error in startup finalization: {e}")

    def _final_diagnostics(self):
        """✅ Финальная диагностика состояния приложения"""
        try:
            logger.info("📊 Running final diagnostics...")
            
            # Проверяем theme_manager
            if self.theme_manager:
                logger.info(f"[Theme Manager] {self.theme_manager.current_theme}/{self.theme_manager.current_variant}")
                logger.info(f"[Theme loaded] {self.theme_manager.is_loaded()}")
                
                # Показываем статистику кэша
                if logger.level <= 10:  # DEBUG level
                    stats = self.theme_manager.get_cache_stats()
                    logger.debug(f"[Theme cache stats] {stats['hit_rate']} hit rate, {stats['cached_fonts']} fonts cached")
            
            # Считаем инициализированные сервисы
            services = [
                'audio_service', 'alarm_service', 'notification_service',
                'weather_service', 'sensor_service', 'volume_service',
                'pigs_service', 'schedule_service', 'auto_theme_service',
                'alarm_clock'
            ]
            
            initialized_count = sum(1 for service in services if getattr(self, service, None) is not None)
            logger.info(f"[Services initialized] {initialized_count}/{len(services)}")
            
            # Проверяем root widget
            if self.root:
                logger.info("Root widget created successfully")
                if hasattr(self.root, 'screen_manager') and self.root.screen_manager:
                    screens_count = len(self.root.screen_manager.screens)
                    logger.info(f"[Screens loaded] {screens_count}")
            
            logger.info("✅ Diagnostics completed")
            
        except Exception as e:
            logger.error(f"Error in diagnostics: {e}")

    def on_stop(self):
        """✅ Корректное завершение приложения"""
        try:
            logger.info("🛑 Shutting down Bedrock 2.0...")
            
            # Останавливаем сервисы в обратном порядке
            services_to_stop = [
                'auto_theme_service', 'alarm_clock', 'volume_service',
                'sensor_service', 'audio_service'
            ]
            
            stopped_count = 0
            for service_name in services_to_stop:
                service = getattr(self, service_name, None)
                if service and hasattr(service, 'stop'):
                    try:
                        service.stop()
                        logger.info(f"Stopped {service_name}")
                        stopped_count += 1
                    except Exception as e:
                        logger.error(f"Error stopping {service_name}: {e}")
            
            logger.info(f"✅ Bedrock 2.0 shutdown complete ({stopped_count} services stopped)")
            
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