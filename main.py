# main.py — версия с автотемой по датчику освещенности и управлением громкости
# ИСПРАВЛЕНО: Устранено дублирование AlarmClock, улучшена диагностика

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
from kivy.clock import Clock

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

# ИСПРАВЛЕНО: Импортируем классы сервисов, а не экземпляры
from services.audio_service import AudioService
from services.alarm_service import AlarmService
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from services.sensor_service import SensorService
from services.pigs_service import PigsService
from services.schedule_service import ScheduleService
from services.auto_theme_service import AutoThemeService
from services.volume_service import VolumeControlService

# ИСПРАВЛЕНО: AlarmClock импорт с защитой и диагностикой
try:
    from services.alarm_clock import AlarmClock
    ALARM_CLOCK_AVAILABLE = True
    logger.info("✅ AlarmClock class imported successfully")
except ImportError as e:
    logger.warning(f"❌ AlarmClock unavailable: {e}")
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

logger.info("=== Bedrock 2.1 Started ===")


class BedrockApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Инициализируем theme_manager как экземпляр класса
        self.theme_manager = ThemeManager()
        
        # Остальные менеджеры
        self.localizer = localizer
        self.user_config = user_config
        
        # ИСПРАВЛЕНО: Все сервисы инициализируются в _initialize_services
        self.audio_service = None
        self.alarm_service = None
        self.notification_service = None
        self.weather_service = None
        self.sensor_service = None
        self.pigs_service = None
        self.schedule_service = None
        self.alarm_clock = None  # ИСПРАВЛЕНО: Один раз объявляем
        self.auto_theme_service = None
        self.volume_service = None
        
        # Переменные состояния приложения
        self._running = False

    def build(self):
        """Основной метод приложения - строим интерфейс"""
        logger.info("Building application...")
        
        # Загружаем пользовательские настройки
        self._load_user_settings()
        
        # Инициализируем сервисы
        self._initialize_services()
        
        # Создаем корневой виджет
        root = RootWidget()
        
        # Подключаем события
        self._setup_events()
        
        # ИСПРАВЛЕНО: Отложенная инициализация тем и автотемы
        Clock.schedule_once(lambda dt: self._finalize_initialization(), 1.0)
        
        logger.info("Application built successfully")
        return root
    
    def _load_user_settings(self):
        """ИСПРАВЛЕНО: Загрузка пользовательских настроек с обработкой ошибок"""
        try:
            # Применяем тему из конфига
            theme = self.user_config.get("theme", "minecraft")
            variant = self.user_config.get("variant", "light") 
            language = self.user_config.get("language", "en")
            
            # ИСПРАВЛЕНО: Проверяем что theme_manager инициализирован правильно
            if hasattr(self, 'theme_manager') and self.theme_manager:
                if not self.theme_manager.load_theme(theme, variant):
                    logger.warning(f"Failed to load theme {theme}/{variant}, using default")
                    self.theme_manager.load_theme("minecraft", "light")
            else:
                logger.error("ThemeManager not initialized properly!")
            
            # ИСПРАВЛЕНО: Проверяем что localizer инициализирован
            if hasattr(self, 'localizer') and self.localizer:
                self.localizer.load(language)
                logger.info(f"Language loaded: {language}")
            else:
                logger.error("Localizer not initialized properly!")
            
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")

    def _initialize_services(self):
        """ИСПРАВЛЕНО: Инициализация всех сервисов с правильным порядком"""
        try:
            logger.info("Initializing services...")
            
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Инициализируем AudioService первым
            try:
                logger.info("Initializing AudioService...")
                self.audio_service = AudioService()
                
                # Проверяем что сервис корректно инициализирован
                if hasattr(self.audio_service, 'diagnose_state'):
                    logger.info("✅ AudioService initialized with diagnose_state method")
                    # Выполняем диагностику для проверки
                    diagnosis = self.audio_service.diagnose_state()
                    logger.info(f"AudioService diagnosis: {diagnosis}")
                else:
                    logger.error("❌ AudioService missing diagnose_state method")
                    
            except Exception as e:
                logger.error(f"CRITICAL: AudioService initialization failed: {e}")
                self.audio_service = None
            
            # Конфигурация остальных сервисов (порядок КРИТИЧЕСКИ ВАЖЕН!)
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
                ('volume_service', VolumeControlService, {}),
            ]
            
            # Инициализируем сервисы последовательно
            for service_name, service_class, kwargs in services_config:
                try:
                    logger.info(f"Initializing {service_name}...")
                    service_instance = service_class(**kwargs)
                    setattr(self, service_name, service_instance)
                    
                    # Запускаем сервис если у него есть метод start
                    if hasattr(service_instance, 'start'):
                        service_instance.start()
                    
                    logger.info(f"✅ Service initialized: {service_name}")
                    
                except Exception as ex:
                    logger.error(f"❌ Failed to initialize {service_name}: {ex}")
                    setattr(self, service_name, None)

            # 🚨 ИСПРАВЛЕНО: ЕДИНАЯ инициализация AlarmClock (убрано дублирование)
            try:
                if ALARM_CLOCK_AVAILABLE and self.alarm_service:
                    logger.info("Initializing AlarmClock service...")
                    self.alarm_clock = AlarmClock()
                    
                    # Запускаем alarm_clock
                    self.alarm_clock.start()
                    
                    logger.info("✅ AlarmClock initialized and started successfully")
                    
                    # Дополнительная проверка состояния
                    if hasattr(self.alarm_clock, 'running') and self.alarm_clock.running:
                        logger.info("✅ AlarmClock is running correctly")
                    else:
                        logger.warning("⚠️ AlarmClock created but not running")
                        
                else:
                    if not ALARM_CLOCK_AVAILABLE:
                        logger.warning("❌ AlarmClock not available (import error)")
                    if not self.alarm_service:
                        logger.warning("❌ AlarmClock not initialized - AlarmService missing")
                    self.alarm_clock = None
                    
            except Exception as e:
                logger.error(f"❌ Failed to initialize AlarmClock: {e}")
                import traceback
                logger.error(f"AlarmClock traceback: {traceback.format_exc()}")
                self.alarm_clock = None

            # 🚨 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: AutoThemeService инициализируется ПОСЛЕ sensor_service и theme_manager
            try:
                logger.info("Initializing auto_theme_service...")
                if self.sensor_service and self.theme_manager:
                    self.auto_theme_service = AutoThemeService(
                        sensor_service=self.sensor_service,
                        theme_manager=self.theme_manager
                    )
                    
                    # Запускаем сервис
                    if hasattr(self.auto_theme_service, 'start'):
                        self.auto_theme_service.start()
                    
                    logger.info("✅ Service initialized: auto_theme_service")
                else:
                    logger.error("❌ Cannot initialize auto_theme_service: missing dependencies")
                    logger.error(f"sensor_service available: {self.sensor_service is not None}")
                    logger.error(f"theme_manager available: {self.theme_manager is not None}")
                    self.auto_theme_service = None
                    
            except Exception as ex:
                logger.error(f"❌ Failed to initialize auto_theme_service: {ex}")
                self.auto_theme_service = None

            # Дополнительная настройка сервисов
            self._setup_auto_theme()
            self._setup_volume_service()
            
            # НОВОЕ: Диагностика финального состояния сервисов
            self._diagnose_services_state()
            
            logger.info("✅ All services initialized")
            
        except Exception as e:
            logger.error(f"Critical error initializing services: {e}")
            import traceback
            logger.error(f"Services initialization traceback: {traceback.format_exc()}")

    def _diagnose_services_state(self):
        """НОВОЕ: Диагностика состояния всех сервисов после инициализации"""
        logger.info("🔧 === SERVICES DIAGNOSTIC ===")
        
        services_to_check = [
            'audio_service', 'alarm_service', 'alarm_clock', 'notification_service',
            'weather_service', 'sensor_service', 'auto_theme_service', 'volume_service'
        ]
        
        for service_name in services_to_check:
            service = getattr(self, service_name, None)
            if service:
                status = "✅ Available"
                if hasattr(service, 'running'):
                    status += f" (running: {service.running})"
                logger.info(f"[{service_name:20}] {status}")
            else:
                logger.warning(f"[{service_name:20}] ❌ Not available")

    def _setup_auto_theme(self):
        """🚨 ИСПРАВЛЕНО: Настройка автоматической темы БЕЗ дублирования"""
        try:
            if self.auto_theme_service and hasattr(self.auto_theme_service, 'start'):
                # Сервис уже запущен в _initialize_services
                logger.debug("AutoTheme service already started")
            else:
                logger.warning("AutoTheme service not available or missing start method")
        except Exception as e:
            logger.error(f"Error setting up auto theme: {e}")

    def _setup_volume_service(self):
        """Настройка сервиса управления громкостью"""
        try:
            if self.volume_service:
                logger.debug("Volume service initialized")
            else:
                logger.warning("Volume service not available")
        except Exception as e:
            logger.error(f"Error setting up volume service: {e}")

    def _setup_events(self):
        """ИСПРАВЛЕНО: Настройка событий приложения"""
        try:
            from app.event_bus import event_bus
            
            # Подписываемся на события темы
            event_bus.subscribe("theme_changed", self._on_theme_changed)
            event_bus.subscribe("variant_changed", self._on_variant_changed)
            event_bus.subscribe("language_changed", self._on_language_changed)
            
            # Подписываемся на события автотемы
            event_bus.subscribe("auto_theme_triggered", self._on_auto_theme_triggered)
            
            # Подписываемся на события громкости
            event_bus.subscribe("volume_changed", self._on_volume_changed)
            
            logger.info("Event handlers setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up events: {e}")

    def _finalize_initialization(self):
        """ИСПРАВЛЕНО: Финальная инициализация после построения UI"""
        try:
            self._running = True
            
            # Проверяем состояние всех сервисов
            self._verify_services()
            
            # Выполняем начальную диагностику
            self._perform_initial_diagnostics()
            
            logger.info("Application initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Error in finalization: {e}")

    def _verify_services(self):
        """НОВОЕ: Проверка состояния всех сервисов"""
        logger.info("🔧 === SERVICES VERIFICATION ===")
        
        critical_services = ['audio_service', 'alarm_service']
        important_services = ['alarm_clock', 'auto_theme_service', 'volume_service']
        
        for service_name in critical_services:
            service = getattr(self, service_name, None)
            if not service:
                logger.error(f"❌ CRITICAL: {service_name} is missing!")
            else:
                logger.info(f"✅ {service_name} is available")
                
        for service_name in important_services:
            service = getattr(self, service_name, None)
            if not service:
                logger.warning(f"⚠️ {service_name} is missing")
            else:
                logger.info(f"✅ {service_name} is available")

    def _perform_initial_diagnostics(self):
        """НОВОЕ: Выполнение начальной диагностики"""
        try:
            # Диагностика audio_service
            if self.audio_service and hasattr(self.audio_service, 'diagnose_state'):
                self.audio_service.diagnose_state()
            
            # Диагностика alarm_clock
            if self.alarm_clock:
                logger.info(f"AlarmClock status: running={getattr(self.alarm_clock, 'running', 'unknown')}")
                if hasattr(self.alarm_clock, '_alarm_active'):
                    logger.info(f"AlarmClock alarm_active: {self.alarm_clock._alarm_active}")
            
        except Exception as e:
            logger.error(f"Error in initial diagnostics: {e}")

    # ========================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ========================================

    def _on_theme_changed(self, event_data):
        """Обработчик изменения темы"""
        try:
            theme = event_data.get("theme")
            variant = event_data.get("variant")
            if theme and variant:
                self.user_config.set("theme", theme)
                self.user_config.set("variant", variant)
                logger.debug(f"Theme saved to config: {theme}/{variant}")
        except Exception as e:
            logger.error(f"Error handling theme change: {e}")

    def _on_variant_changed(self, event_data):
        """Обработчик изменения варианта темы"""
        try:
            variant = event_data.get("variant")
            if variant:
                self.user_config.set("variant", variant)
                logger.debug(f"Variant saved to config: {variant}")
        except Exception as e:
            logger.error(f"Error handling variant change: {e}")

    def _on_language_changed(self, event_data):
        """Обработчик изменения языка"""
        try:
            language = event_data.get("language")
            if language and hasattr(self, 'localizer'):
                self.user_config.set("language", language)
                self.localizer.load(language)
                logger.debug(f"Language saved to config: {language}")
        except Exception as e:
            logger.error(f"Error handling language change: {e}")

    def _on_auto_theme_triggered(self, event_data):
        """Обработчик автоматической смены темы"""
        try:
            new_variant = event_data.get("variant")
            if new_variant and hasattr(self, 'theme_manager'):
                current_theme = self.user_config.get("theme", "minecraft")
                self.theme_manager.set_variant(new_variant)
                logger.debug(f"Auto-theme triggered: {current_theme}/{new_variant}")
        except Exception as e:
            logger.error(f"Error handling auto-theme trigger: {e}")

    def _on_volume_changed(self, event_data):
        """Обработчик изменения громкости"""
        try:
            volume = event_data.get("volume")
            if volume is not None:
                self.user_config.set("volume", volume)
                logger.debug(f"Volume saved to config: {volume}")
        except Exception as e:
            logger.error(f"Error handling volume change: {e}")

    def on_stop(self):
        """Корректная остановка всех сервисов при закрытии приложения"""
        try:
            logger.info("Stopping application services...")
            
            # Останавливаем AlarmClock первым чтобы избежать popup при закрытии
            if hasattr(self, 'alarm_clock') and self.alarm_clock:
                try:
                    self.alarm_clock.stop()
                    logger.info("✅ AlarmClock stopped")
                except Exception as e:
                    logger.error(f"Error stopping AlarmClock: {e}")
            
            # Останавливаем остальные сервисы
            services_to_stop = [
                'auto_theme_service', 'volume_service', 'schedule_service',
                'pigs_service', 'sensor_service', 'weather_service',
                'notification_service', 'audio_service'
            ]
            
            for service_name in services_to_stop:
                if hasattr(self, service_name):
                    service = getattr(self, service_name)
                    if service and hasattr(service, 'stop'):
                        try:
                            service.stop()
                            logger.info(f"✅ {service_name} stopped")
                        except Exception as e:
                            logger.error(f"Error stopping {service_name}: {e}")
            
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
        
        return True

if __name__ == "__main__":
    try:
        app = BedrockApp()
        app.run()
    except Exception as e:
        logger.error(f"Critical application error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Application terminated")