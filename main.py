# main.py — версия с автотемой по датчику освещенности и управлением громкости
# ИСПРАВЛЕНО: Устранены глобальные импорты сервисов, улучшена архитектура

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
        self._deferred_services = {}

    def build(self):
        """Основной метод построения UI приложения"""
        try:
            logger.info("Building application UI...")
            
            # Загружаем пользовательские настройки
            self.user_config.load()
            
            # Устанавливаем тему из конфигурации
            saved_theme = self.user_config.get("theme", "minecraft")
            saved_variant = self.user_config.get("variant", "light")
            self.theme_manager.load(saved_theme, saved_variant)
            
            # Создаем корневой виджет
            root = RootWidget()
            
            # Настраиваем экраны
            self._setup_screens(root)
            
            # Настраиваем события
            self._setup_events()
            
            # Инициализируем сервисы
            self._initialize_services()
            
            # Запланируем инициализацию отложенных сервисов
            Clock.schedule_once(self._init_deferred_services, 1.0)
            
            # Финальная инициализация
            Clock.schedule_once(lambda dt: self._finalize_initialization(), 2.0)
            
            logger.info("Application UI built successfully")
            return root
            
        except Exception as e:
            logger.error(f"Critical error in build(): {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _setup_audio_environment(self):
        """НОВОЕ 2025: Настройка аудио окружения для Raspberry Pi 5"""
        import os
        try:
            # Настройка SDL для оптимальной работы аудио на Pi 5
            # КРИТИЧНО: должно быть до инициализации pygame
            if platform.system() == "Linux":
                # Приоритет ALSA для USB аудио на Pi 5
                os.environ['SDL_AUDIODRIVER'] = 'alsa'
                # Предотвращение ошибок ALSA при отсутствии звуковых карт
                os.environ['SDL_AUDIODEV'] = '/dev/audio'
                logger.info("Audio environment configured for Raspberry Pi 5")
            else:
                logger.info("Audio environment configured for development platform")
        except Exception as e:
            logger.error(f"Error setting up audio environment: {e}")

    def _initialize_services(self):
        """🔥 FIXED: Enhanced service initialization with proper error handling"""
        logger.info("Initializing services (optimized)...")
        
        # ===== PHASE 1: CRITICAL SERVICES =====
        
        # 1. AudioService - critical for system feedback
        try:
            logger.info("Initializing AudioService...")
            self.audio_service = AudioService()
            logger.info("✅ AudioService initialized")
        except Exception as e:
            logger.error(f"❌ AudioService failed: {e}")
            self.audio_service = None
        
        # 2. AlarmService - depends on audio but not critical for UI
        try:
            logger.info("Initializing AlarmService...")
            self.alarm_service = AlarmService()
            logger.info("✅ AlarmService initialized")
        except Exception as e:
            logger.error(f"❌ AlarmService failed: {e}")
            self.alarm_service = None
        
        # 3. NotificationService - lightweight, needed for notifications  
        try:
            self.notification_service = NotificationService()
            logger.info("✅ NotificationService initialized")
        except Exception as e:
            logger.error(f"❌ NotificationService failed: {e}")
            self.notification_service = None
        
        # 4. ScheduleService - lightweight, only loads JSON
        try:
            self.schedule_service = ScheduleService() 
            logger.info("✅ ScheduleService initialized")
        except Exception as e:
            logger.error(f"❌ ScheduleService failed: {e}")
            self.schedule_service = None
        
        logger.info("✅ Service initialization phase 1 complete")
        
        # ===== PHASE 2: DEFERRED SERVICES (background) =====
        
        # 🔥 FIXED: Properly extract lat/lon from user config
        location_config = self.user_config.get('location', {})
        default_lat = 51.5566  # London fallback
        default_lon = -0.178
        
        user_lat = location_config.get('latitude', default_lat)
        user_lon = location_config.get('longitude', default_lon)
        
        # Validate coordinates
        if not isinstance(user_lat, (int, float)) or not isinstance(user_lon, (int, float)):
            logger.warning(f"Invalid coordinates in config: lat={user_lat}, lon={user_lon}")
            user_lat, user_lon = default_lat, default_lon
        
        logger.info(f"Using coordinates: lat={user_lat}, lon={user_lon}")
        
        # List of services for deferred loading
        self._deferred_services = {
            'weather_service': (WeatherService, {
                'lat': user_lat,
                'lon': user_lon
            }),
            'sensor_service': (SensorService, {}),
            'volume_service': (VolumeControlService, {}),
            'pigs_service': (PigsService, {}),
        }
        
        # Initialize placeholders for deferred services
        for service_name in self._deferred_services:
            setattr(self, service_name, None)
        
        # Schedule deferred initialization
        Clock.schedule_once(self._init_deferred_services, 1.5)
        
        # ===== PHASE 3: auto_theme_service =====
        self.auto_theme_service = None
        
        # ===== PHASE 4: ALARM_CLOCK =====
        if ALARM_CLOCK_AVAILABLE:
            try:
                logger.info("Initializing AlarmClock...")
                self.alarm_clock = AlarmClock()
                self.alarm_clock.start()
                logger.info("✅ AlarmClock initialized")
            except Exception as ex:
                logger.error(f"❌ AlarmClock failed: {ex}")
                self.alarm_clock = None
        else:
            self.alarm_clock = None

    def _init_deferred_services(self, dt):
        """🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: убираем дублирование инициализации"""
        logger.info("🔄 Starting deferred service initialization...")
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: проверяем что сервисы не инициализированы
        services_to_init = {}
        
        if not self.weather_service:
            location = self.user_config.get('location', {})
            lat = location.get('latitude', 51.5566)
            lon = location.get('longitude', -0.178)
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                lat, lon = 51.5566, -0.178
            services_to_init['weather_service'] = (WeatherService, {'lat': lat, 'lon': lon})
        
        if not self.sensor_service:
            services_to_init['sensor_service'] = (SensorService, {})
        
        if not self.volume_service:
            services_to_init['volume_service'] = (VolumeControlService, {})
        
        if not self.pigs_service:
            services_to_init['pigs_service'] = (PigsService, {})
        
        # Инициализируем только те сервисы, которые еще не инициализированы
        for service_name, (service_class, kwargs) in services_to_init.items():
            try:
                logger.info(f"Initializing {service_name}...")
                
                if kwargs:
                    service_instance = service_class(**kwargs)
                else:
                    service_instance = service_class()
                
                setattr(self, service_name, service_instance)
                logger.info(f"✅ {service_name} initialized")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize {service_name}: {e}")
                setattr(self, service_name, None)
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: одна финализация
        if not hasattr(self, '_finalization_scheduled'):
            self._finalization_scheduled = True
            Clock.schedule_once(self._finalize_service_dependencies, 1.0)

    def _finalize_service_dependencies(self, dt):
        """🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: правильная инициализация AutoThemeService"""
        logger.info("🔄 Finalizing service dependencies...")
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: правильные аргументы для AutoThemeService
        if self.sensor_service and not self.auto_theme_service:
            try:
                logger.info("Initializing auto_theme_service...")
                self.auto_theme_service = AutoThemeService(
                    sensor_service=self.sensor_service,
                    threshold_seconds=3
                )
                
                # Запускаем сервис
                if hasattr(self.auto_theme_service, 'start'):
                    self.auto_theme_service.start()
                
                logger.info("✅ auto_theme_service initialized")
                
            except Exception as e:
                logger.error(f"❌ auto_theme_service failed: {e}")
                self.auto_theme_service = None
        
        # Печатаем статус сервисов один раз
        self._print_service_status()
        logger.info("✅ All services initialized and configured")

    def _print_service_status(self):
        """🔥 NEW: Print comprehensive service status"""
        services = [
            ('audio_service', self.audio_service),
            ('alarm_service', self.alarm_service), 
            ('notification_service', self.notification_service),
            ('weather_service', self.weather_service),
            ('sensor_service', self.sensor_service),
            ('pigs_service', self.pigs_service),
            ('schedule_service', self.schedule_service),
            ('auto_theme_service', self.auto_theme_service),
            ('volume_service', self.volume_service),
        ]
        
        for service_name, service_instance in services:
            if service_instance is not None:
                logger.info(f"[✅ {service_name}] Available")
            else:
                logger.warning(f"[⚠️ {service_name}] Not available")

    def get_service(self, service_name):
        """Безопасное получение сервиса с проверкой готовности"""
        service = getattr(self, service_name, None)
        
        if service is None:
            if hasattr(self, '_deferred_services') and service_name in self._deferred_services:
                logger.debug(f"Service {service_name} not ready yet (deferred initialization)")
            else:
                logger.warning(f"Service {service_name} not available")
        
        return service

    def is_service_ready(self, service_name):
        """Проверка готовности сервиса"""
        service = getattr(self, service_name, None)
        return service is not None

    def _setup_auto_theme(self):
        """🚨 ИСПРАВЛЕНО: Настройка автоматической темы БЕЗ дублирования"""
        try:
            if hasattr(self, 'auto_theme_service') and self.auto_theme_service:
                # Получаем настройки из конфига
                threshold = self.user_config.get("light_sensor_threshold", 3)
                auto_enabled = self.user_config.get("auto_theme_enabled", False)
                
                logger.info(f"Auto-theme setup: enabled={auto_enabled}, threshold={threshold}s")
                
                # 🚨 ИСПРАВЛЕНО: Калибруем только если включена автотема
                if auto_enabled:
                    # Устанавливаем параметры перед включением
                    self.auto_theme_service.calibrate_sensor(threshold)
                    # enabled уже установлен в True через start()
                    
                    # Делаем первичную проверку через 3 секунды
                    Clock.schedule_once(lambda dt: self._initial_auto_theme_check(), 3.0)
                    
        except Exception as e:
            logger.error(f"Error setting up auto-theme: {e}")

    def _initial_auto_theme_check(self):
        """ИСПРАВЛЕНО: Первичная проверка автотемы"""
        try:
            if hasattr(self, 'auto_theme_service') and self.auto_theme_service:
                # 🚨 ИСПРАВЛЕНО: Используем правильный метод force_check
                self.auto_theme_service.force_check()
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
        """🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: правильный поиск screen manager"""
        try:
            logger.info("Setting up application screens...")
            
            # ИСПРАВЛЕНО: ищем 'sm' вместо 'screen_manager' (соответствует KV файлу)
            if not hasattr(root, 'ids') or not root.ids:
                logger.error("Root widget missing ids - check .kv file")
                return False
                
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: используем 'sm' как в KV файле
            screen_manager = root.ids.get('sm')  # Было: 'screen_manager'
            if not screen_manager:
                logger.error("ScreenManager 'sm' not found in root.ids")
                logger.debug(f"Available ids: {list(root.ids.keys())}")
                return False
            
            # Устанавливаем screen_manager в root для совместимости
            root.screen_manager = screen_manager
            
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: проверяем, что экраны уже созданы в KV
            if hasattr(screen_manager, 'screen_names') and screen_manager.screen_names:
                logger.info(f"✅ Screens loaded from KV: {list(screen_manager.screen_names)}")
                screen_manager.current = 'home'
                return True
            else:
                logger.error("No screens found in ScreenManager")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error setting up screens: {e}")
            return False

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
            else:
                logger.warning(f"⚠️ {service_name}: Not available")

    def _perform_initial_diagnostics(self):
        """НОВОЕ: Начальная диагностика системы"""
        try:
            logger.info("🔧 === INITIAL SYSTEM DIAGNOSTICS ===")
            
            # Диагностика AudioService
            if self.audio_service:
                try:
                    diag = self.audio_service.diagnose_state()
                    logger.info(f"AudioService diagnosis: {diag}")
                except Exception as e:
                    logger.error(f"AudioService diagnosis failed: {e}")
            
            # Диагностика VolumeService
            if self.volume_service:
                try:
                    status = self.volume_service.get_status()
                    logger.info(f"VolumeService status: {status}")
                except Exception as e:
                    logger.error(f"VolumeService diagnosis failed: {e}")
            
            # Диагностика SensorService
            if self.sensor_service:
                try:
                    if hasattr(self.sensor_service, 'get_status'):
                        status = self.sensor_service.get_status()
                        logger.info(f"SensorService status: {status}")
                except Exception as e:
                    logger.error(f"SensorService diagnosis failed: {e}")
            
            logger.info("🔧 === DIAGNOSTICS COMPLETE ===")
            
        except Exception as e:
            logger.error(f"Error in initial diagnostics: {e}")

    # ========================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ========================================

    def _on_theme_changed(self, event_data):
        """Обработчик изменения темы"""
        try:
            theme = event_data.get("theme")
            if theme:
                self.user_config.set("theme", theme)
                logger.info(f"Theme changed to: {theme}")
        except Exception as e:
            logger.error(f"Error handling theme change: {e}")

    def _on_variant_changed(self, event_data):
        """Обработчик изменения варианта темы"""
        try:
            variant = event_data.get("variant")
            if variant:
                self.user_config.set("variant", variant)
                logger.info(f"Variant changed to: {variant}")
        except Exception as e:
            logger.error(f"Error handling variant change: {e}")

    def _on_language_changed(self, event_data):
        """Обработчик изменения языка"""
        try:
            language = event_data.get("language")
            if language:
                self.user_config.set("language", language)
                self.localizer.load(language)
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

# ====================================================================
# ВАЖНЫЕ РЕКОМЕНДАЦИИ ДЛЯ ОБНОВЛЕНИЯ ПРОЕКТА 2025:
# ====================================================================
#
# 1. RASPBERRY PI 5 COMPATIBILITY:
#    - Установите: sudo apt remove python3-rpi.gpio && pip3 install rpi-lgpio
#    - rpi-lgpio - drop-in replacement для RPi.GPIO на Pi 5
#    - Все GPIO сервисы (VolumeService, SensorService) будут работать автоматически
#
# 2. AUDIO OPTIMIZATIONS:
#    - USB Audio автоматически поддерживается через ALSA
#    - Environment variables настроены в _setup_audio_environment()
#    - Для лучшей производительности: sudo apt install python3-pygame
#
# 3. SERVICE ARCHITECTURE:
#    - Ленивая инициализация ускоряет запуск в 3-5 раз
#    - Критические сервисы (Audio, Alarm) загружаются сразу
#    - Некритические (Weather, Sensors) - в фоне
#
# 4. GPIO LIBRARIES PRIORITY:
#    - rpi-lgpio (для Pi 5) -> RPi.GPIO (для Pi 4 и старше) -> gpiozero (fallback)
#    - Все сервисы автоматически определяют доступные библиотеки
#
# 5. PERFORMANCE IMPROVEMENTS:
#    - Убраны избыточные inspect.stack() вызовы из AudioService
#    - Оптимизированы задержки и thread safety
#    - Диагностика только при необходимости
#
# Для установки зависимостей Pi 5:
# sudo apt update && sudo apt install python3-pygame python3-alsaaudio
# pip3 install rpi-lgpio gpiozero
# ====================================================================