# main.py — версия с автотемой по датчику освещенности и управлением громкости
# ИСПРАВЛЕНО: Устранены глобальные импорты сервисов, улучшена архитектура

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
        self.alarm_clock = None
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
        
        # ИСПРАВЛЕНО: Убираем _setup_screens так как экраны уже в KV файле
        # KV файл root_widget.kv уже содержит ScreenManager с экранами
        
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
                    # ✅ Убрали дублирующее логирование - ThemeManager сам логирует результат
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

            # Инициализируем alarm_clock если доступен
            if ALARM_CLOCK_AVAILABLE:
                try:
                    logger.info("Initializing AlarmClock...")
                    self.alarm_clock = AlarmClock()
                    self.alarm_clock.start()
                    logger.info("✅ AlarmClock initialized and started")
                except Exception as ex:
                    logger.error(f"❌ AlarmClock initialization failed: {ex}")
                    self.alarm_clock = None
            
            # Дополнительная настройка сервисов
            self._setup_auto_theme()
            self._setup_volume_service()
            
            logger.info("✅ All services initialized")
            
        except Exception as e:
            logger.error(f"Critical error initializing services: {e}")

    def _setup_auto_theme(self):
        """ИСПРАВЛЕНО: Настройка автоматической темы"""
        try:
            if hasattr(self, 'auto_theme_service') and self.auto_theme_service:
                # Получаем настройки из конфига
                threshold = self.user_config.get("light_sensor_threshold", 3)
                auto_enabled = self.user_config.get("auto_theme_enabled", False)
                
                logger.info(f"Auto-theme setup: enabled={auto_enabled}, threshold={threshold}s")
                
                # 🚨 ИСПРАВЛЕНО: Используем правильный метод calibrate_sensor с параметром
                if hasattr(self, 'sensor_service') and self.sensor_service:
                    self.auto_theme_service.calibrate_sensor(threshold)
                    logger.info(f"Auto-theme sensor calibrated: {threshold}s threshold")
                
                # Включаем автотему если настроено
                if auto_enabled:
                    self.auto_theme_service.set_enabled(True)
                    # Если включена, делаем первичную проверку через 3 секунды
                    Clock.schedule_once(lambda dt: self._initial_auto_theme_check(), 3.0)
                    
        except Exception as e:
            logger.error(f"Error setting up auto-theme: {e}")

    def _initial_auto_theme_check(self):
        """ИСПРАВЛЕНО: Первичная проверка автотемы"""
        try:
            if hasattr(self, 'auto_theme_service') and self.auto_theme_service:
                # 🚨 ИСПРАВЛЕНО: Используем правильный метод check_and_update_theme
                self.auto_theme_service.check_and_update_theme()
                logger.info("Initial auto-theme check completed")
        except Exception as e:
            logger.error(f"Error in initial auto-theme check: {e}")

    def _setup_volume_service(self):
        """ИСПРАВЛЕНО: Настройка сервиса громкости"""
        try:
            if hasattr(self, 'volume_service') and self.volume_service:
                # Проверяем доступность GPIO
                status = self.volume_service.get_status()
                logger.info(f"Volume service status: {status}")
                
                # Устанавливаем громкость из конфига
                saved_volume = self.user_config.get("volume", 50)
                self.volume_service.set_volume(saved_volume)
                logger.info(f"Volume service setup complete, volume: {saved_volume}%")
                
        except Exception as e:
            logger.error(f"Error setting up volume service: {e}")
    def _setup_screens(self, root):
        """Настройка экранов приложения"""
        try:
            # Создаем и добавляем экраны
            screens = [
                ("home", HomeScreen(name="home")),
                ("alarm", AlarmScreen(name="alarm")),
                ("schedule", ScheduleScreen(name="schedule")),
                ("weather", WeatherScreen(name="weather")),
                ("pigs", PigsScreen(name="pigs")),
                ("settings", SettingsScreen(name="settings")),
            ]
            
            for screen_name, screen in screens:
                root.screen_manager.add_widget(screen)
                logger.debug(f"Added screen: {screen_name}")
            
            # Устанавливаем начальный экран
            root.screen_manager.current = "home"
            logger.info("Screens setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up screens: {e}")

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
        services_to_check = [
            'audio_service', 'alarm_service', 'notification_service',
            'weather_service', 'sensor_service', 'pigs_service',
            'schedule_service', 'auto_theme_service', 'volume_service'
        ]
        
        for service_name in services_to_check:
            service = getattr(self, service_name, None)
            if service:
                logger.info(f"✅ {service_name}: Available")
                
                # Специальная проверка для AudioService
                if service_name == 'audio_service':
                    if hasattr(service, 'diagnose_state'):
                        logger.info(f"✅ {service_name}: diagnose_state method available")
                    else:
                        logger.error(f"❌ {service_name}: diagnose_state method MISSING")
            else:
                logger.warning(f"⚠️ {service_name}: Not available")

    def _perform_initial_diagnostics(self):
        """НОВОЕ: Выполнение начальной диагностики"""
        try:
            # Диагностика AudioService
            if self.audio_service and hasattr(self.audio_service, 'diagnose_state'):
                logger.info("🔧 === INITIAL AUDIO DIAGNOSTICS ===")
                diagnosis = self.audio_service.diagnose_state()
                for key, value in diagnosis.items():
                    logger.info(f"Audio {key}: {value}")
            
            # Диагностика VolumeService
            if self.volume_service and hasattr(self.volume_service, 'get_status'):
                logger.info("🔧 === INITIAL VOLUME DIAGNOSTICS ===")
                status = self.volume_service.get_status()
                for key, value in status.items():
                    logger.info(f"Volume {key}: {value}")
                    
        except Exception as e:
            logger.error(f"Error in initial diagnostics: {e}")

    def debug_audio_service(self):
        """НОВОЕ: Метод отладки для AudioService"""
        logger.info("=== AUDIO SERVICE DEBUG ===")
        
        if self.audio_service:
            logger.info(f"AudioService instance: {type(self.audio_service)}")
            logger.info(f"AudioService ID: {id(self.audio_service)}")
            logger.info(f"Has diagnose_state: {hasattr(self.audio_service, 'diagnose_state')}")
            
            methods = [method for method in dir(self.audio_service) if not method.startswith('_')]
            logger.info(f"AudioService methods: {methods}")
            
            if hasattr(self.audio_service, 'diagnose_state'):
                try:
                    diagnosis = self.audio_service.diagnose_state()
                    logger.info(f"Diagnosis result: {diagnosis}")
                except Exception as e:
                    logger.error(f"Diagnosis failed: {e}")
        else:
            logger.error("AudioService is None")

    # ================================
    # EVENT HANDLERS
    # ================================

    def _on_theme_changed(self, event_data):
        """Обработчик смены темы"""
        try:
            theme = event_data.get("theme")
            if theme and self.theme_manager:
                current_variant = self.theme_manager.current_variant
                self.theme_manager.load_theme(theme, current_variant)
                self.user_config.set("theme", theme)
                logger.info(f"Theme changed to: {theme}")
        except Exception as e:
            logger.error(f"Error handling theme change: {e}")

    def _on_variant_changed(self, event_data):
        """Обработчик смены варианта темы"""
        try:
            variant = event_data.get("variant")
            if variant and self.theme_manager:
                current_theme = self.theme_manager.current_theme
                self.theme_manager.load_theme(current_theme, variant)
                self.user_config.set("variant", variant)
                logger.info(f"Variant changed to: {variant}")
        except Exception as e:
            logger.error(f"Error handling variant change: {e}")

    def _on_language_changed(self, event_data):
        """Обработчик смены языка"""
        try:
            language = event_data.get("language")
            if language:
                self.user_config.set("language", language)
                logger.info(f"Language changed to: {language}")
        except Exception as e:
            logger.error(f"Error handling language change: {e}")

    def _on_auto_theme_triggered(self, event_data):
        """Обработчик срабатывания автотемы"""
        try:
            action = event_data.get("action")
            logger.info(f"Auto-theme triggered: {action}")
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
        """ИСПРАВЛЕНО: Корректное завершение работы приложения"""
        logger.info("Application stopping...")
        self._running = False
        
        # Останавливаем все сервисы
        services_to_stop = [
            'alarm_clock', 'auto_theme_service', 'volume_service', 
            'sensor_service', 'weather_service', 'pigs_service'
        ]
        
        for service_name in services_to_stop:
            service = getattr(self, service_name, None)
            if service and hasattr(service, 'stop'):
                try:
                    service.stop()
                    logger.info(f"Stopped {service_name}")
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")
        
        # Останавливаем аудио
        if self.audio_service and hasattr(self.audio_service, 'stop'):
            try:
                self.audio_service.stop()
                logger.info("Stopped audio_service")
            except Exception as e:
                logger.error(f"Error stopping audio_service: {e}")
        
        # Сохраняем конфигурацию
        try:
            self.user_config.save()
            logger.info("User config saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
        
        logger.info("Application stopped")
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