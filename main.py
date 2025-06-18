# main.py — полная версия с автотемой по датчику освещенности и управлением громкости
# ИСПРАВЛЕНО: Только методы ThemeManager, остальная функциональность сохранена

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

# Импортируем классы сервисов, а не экземпляры
from services.audio_service import AudioService
from services.alarm_service import AlarmService
from services.notifications_service import NotificationService
from services.weather_service import WeatherService
from services.sensor_service import SensorService
from services.pigs_service import PigsService
from services.schedule_service import ScheduleService
from services.auto_theme_service import AutoThemeService
from services.volume_service import VolumeControlService

# AlarmClock импорт с защитой и диагностикой
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
        
        # Все сервисы инициализируются в _initialize_services
        self.audio_service = None
        self.alarm_service = None
        self.notification_service = None
        self.weather_service = None
        self.sensor_service = None
        self.pigs_service = None
        self.schedule_service = None
        self.alarm_clock = None
        self.auto_theme_service = None
        self.volume_service = None
        
        # Переменные состояния
        self._running = False
        self._setup_complete = False
        
        logger.info("BedrockApp instance created")

    def build(self):
        """Основной билдер приложения"""
        logger.info("Building application...")
        
        # Загружаем конфигурацию пользователя
        self._load_user_settings()
        
        # Инициализируем все сервисы
        self._initialize_services()
        
        # Создаем корневой виджет
        root = RootWidget()
        
        # Настраиваем события
        self._setup_events()
        
        # Отложенная финализация после построения UI
        Clock.schedule_once(lambda dt: self._finalize_initialization(), 1.0)
        
        logger.info("Application built successfully")
        return root

    def _load_user_settings(self):
        """ИСПРАВЛЕНО: Загрузка пользовательских настроек с правильными методами"""
        try:
            # Применяем тему из конфига
            theme = self.user_config.get("theme", "minecraft")
            variant = self.user_config.get("variant", "light")
            language = self.user_config.get("language", "en")
            
            # ИСПРАВЛЕНО: Используем только load() метод
            if not self.theme_manager.load(theme, variant):
                logger.warning(f"Failed to load theme {theme}/{variant}, using default")
                self.theme_manager.load("minecraft", "light")
            
            # Применяем язык
            self.localizer.load(language)
            
            # Загружаем конфиг автотемы
            self._auto_theme_config = {
                'enabled': self.user_config.get("auto_theme_enabled", False),
                'threshold': self.user_config.get("light_sensor_threshold", 3)
            }
            
            logger.info("User settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")

 

    def _initialize_services(self):
        """ИСПРАВЛЕНО: Инициализация всех сервисов с правильным AudioService"""
        try:
            logger.info("Initializing services...")
            
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Правильная инициализация AudioService
            try:
                logger.info("Initializing AudioService...")
                self.audio_service = AudioService()
                
                # ИСПРАВЛЕНО: AudioService НЕ имеет метода start()! 
                # Он инициализируется в конструкторе
                
                # Проверяем что сервис корректно инициализирован
                if hasattr(self.audio_service, 'diagnose_state'):
                    logger.info("✅ AudioService initialized with diagnose_state method")
                    # Выполняем диагностику для проверки
                    diagnosis = self.audio_service.diagnose_state()
                    logger.debug(f"AudioService diagnosis: {diagnosis}")
                else:
                    logger.error("❌ AudioService missing diagnose_state method")
                    
            except Exception as e:
                logger.error(f"CRITICAL: AudioService initialization failed: {e}")
                import traceback
                logger.error(f"AudioService traceback: {traceback.format_exc()}")
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
                    
                    # ИСПРАВЛЕНО: Запускаем сервис если у него есть метод start
                    if hasattr(service_instance, 'start'):
                        service_instance.start()
                        logger.debug(f"✅ {service_name} started")
                    else:
                        logger.debug(f"✅ {service_name} initialized (no start method)")
                    
                    logger.info(f"✅ Service initialized: {service_name}")
                    
                except Exception as ex:
                    logger.error(f"❌ Failed to initialize {service_name}: {ex}")
                    import traceback
                    logger.error(f"{service_name} traceback: {traceback.format_exc()}")
                    setattr(self, service_name, None)

            # ЕДИНАЯ инициализация AlarmClock
            try:
                if ALARM_CLOCK_AVAILABLE and self.alarm_service:
                    logger.info("Initializing AlarmClock service...")
                    self.alarm_clock = AlarmClock()
                    
                    # Запускаем alarm_clock
                    if hasattr(self.alarm_clock, 'start'):
                        self.alarm_clock.start()
                        logger.info("✅ AlarmClock initialized and started successfully")
                    else:
                        logger.warning("⚠️ AlarmClock has no start method")
                    
                    # Дополнительная диагностика
                    if hasattr(self.alarm_clock, '_version'):
                        logger.info(f"AlarmClock version: {self.alarm_clock._version}")
                else:
                    logger.warning("❌ AlarmClock not available or AlarmService missing")
                    self.alarm_clock = None
                    
            except Exception as ex:
                logger.error(f"❌ Failed to initialize AlarmClock: {ex}")
                import traceback
                logger.error(f"AlarmClock traceback: {traceback.format_exc()}")
                self.alarm_clock = None

            # Инициализация AutoThemeService
            try:
                if self.sensor_service and self.theme_manager:
                    logger.info("Initializing AutoThemeService...")
                    self.auto_theme_service = AutoThemeService(self.sensor_service, self.theme_manager)
                    
                    # AutoThemeService ИМЕЕТ метод start()
                    if hasattr(self.auto_theme_service, 'start'):
                        self.auto_theme_service.start()
                        logger.info("✅ AutoThemeService initialized and started")
                    else:
                        logger.warning("⚠️ AutoThemeService has no start method")
                else:
                    logger.warning("❌ AutoThemeService dependencies missing")
                    self.auto_theme_service = None
                    
            except Exception as ex:
                logger.error(f"❌ Failed to initialize auto_theme_service: {ex}")
                import traceback
                logger.error(f"AutoThemeService traceback: {traceback.format_exc()}")
                self.auto_theme_service = None

            # Дополнительная настройка сервисов
            self._setup_auto_theme()
            self._setup_volume_service()
            
            # Диагностика финального состояния сервисов
            self._diagnose_services_state()
            
            logger.info("✅ All services initialized")
            
        except Exception as e:
            logger.error(f"Critical error initializing services: {e}")
            import traceback
            logger.error(f"Services initialization traceback: {traceback.format_exc()}")
    def _diagnose_services_state(self):
        """Диагностика состояния всех сервисов после инициализации"""
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
        """Настройка автоматической темы БЕЗ дублирования"""
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
        """Настройка событий приложения"""
        try:
            from app.event_bus import event_bus
            
            # Подписываемся на события темы
            event_bus.subscribe("theme_changed", self._on_theme_changed)
            event_bus.subscribe("variant_changed", self._on_variant_changed)
            event_bus.subscribe("language_changed", self._on_language_changed)
            
            # ИСПРАВЛЕНО: Убираем конфликтующую подписку на auto_theme_triggered
            # event_bus.subscribe("auto_theme_triggered", self._on_auto_theme_triggered)
            
            # Подписываемся на события громкости
            event_bus.subscribe("volume_changed", self._on_volume_changed)
            
            logger.info("Event handlers setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up events: {e}")

    def _finalize_initialization(self):
        """Финальная инициализация после построения UI"""
        try:
            self._running = True
            
            # Проверяем состояние всех сервисов
            self._verify_services()

            self._apply_auto_theme_settings()
            
            # Выполняем начальную диагностику
            self._perform_initial_diagnostics()
            
            logger.info("Application initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Error in finalization: {e}")

    def _apply_auto_theme_settings(self):
        """Применение настроек auto_theme из конфига пользователя"""
        try:
            if not hasattr(self, '_auto_theme_config'):
                logger.warning("Auto theme config not loaded, skipping")
                return
                
            auto_theme_enabled = self._auto_theme_config.get('enabled', False)
            threshold = self._auto_theme_config.get('threshold', 3)
            
            logger.info(f"Applying auto theme settings: enabled={auto_theme_enabled}, threshold={threshold}")
            
            if hasattr(self, 'auto_theme_service') and self.auto_theme_service:
                # Применяем настройки
                if auto_theme_enabled:
                    # Калибруем датчик с настройками из конфига
                    self.auto_theme_service.calibrate_sensor(int(threshold))
                    
                    # Активируем сервис
                    self.auto_theme_service.set_enabled(True)

                    
                    logger.info(f"✅ Auto-theme activated from config: threshold={threshold}s")
                else:
                    logger.info("Auto-theme disabled in config")
            else:
                logger.warning("auto_theme_service not available, cannot apply settings")
                
        except Exception as e:
            logger.error(f"Error applying auto theme settings: {e}")

    def _verify_services(self):
        """Проверка состояния всех сервисов"""
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
        """Выполнение начальной диагностики"""
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

    # УДАЛЕНО: Конфликтующий метод _on_auto_theme_triggered
    # def _on_auto_theme_triggered(self, event_data):
    #     """Обработчик автоматической смены темы"""
    #     try:
    #         new_variant = event_data.get("variant")
    #         if new_variant and hasattr(self, 'theme_manager'):
    #             current_theme = self.user_config.get("theme", "minecraft")
    #             self.theme_manager.set_variant(new_variant)  # ← ЭТОГО МЕТОДА НЕТ!
    #             logger.debug(f"Auto-theme triggered: {current_theme}/{new_variant}")
    #     except Exception as e:
    #         logger.error(f"Error handling auto-theme trigger: {e}")

    def _on_volume_changed(self, event_data):
        """Обработчик изменения громкости"""
        try:
            volume = event_data.get("volume")
            if volume is not None:
                self.user_config.set("volume", volume)
                logger.debug(f"Volume saved to config: {volume}")
        except Exception as e:
            logger.error(f"Error handling volume change: {e}")

    def on_start(self):
        """Вызывается при старте приложения"""
        logger.info("Application started")

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