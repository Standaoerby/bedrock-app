# main.py - ИСПРАВЛЕННАЯ версия с оптимизированной инициализацией
"""
ИСПРАВЛЕНИЯ:
✅ KV файлы загружаются в build() вместо уровня модуля
✅ Убраны дублирования в инициализации
✅ Оптимизирована последовательность загрузки
✅ Улучшена обработка ошибок
✅ Консистентность с остальными файлами
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
    logger.warning(f"AlarmClock unavailable: {e}")
    AlarmClock = None
    ALARM_CLOCK_AVAILABLE = False

logger.info("=== Bedrock 2.1 Started ===")


class BedrockApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Основные менеджеры
        self.theme_manager = ThemeManager()
        self.localizer = localizer
        self.user_config = user_config
        
        # Все сервисы (инициализируются в _initialize_services)
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
        
        try:
            # 1. Загружаем KV файлы (ИСПРАВЛЕНО: в build() вместо уровня модуля)
            self._load_kv_files()
            
            # 2. Загружаем пользовательские настройки
            self._load_user_settings()
            
            # 3. Инициализируем сервисы
            self._initialize_services()
            
            # 4. Создаем корневой виджет
            root = RootWidget()
            
            # 5. Подключаем события
            self._setup_events()
            
            # 6. Отложенная финализация
            Clock.schedule_once(lambda dt: self._finalize_initialization(), 1.0)
            
            logger.info("Application built successfully")
            return root
            
        except Exception as e:
            logger.error(f"Critical error in build(): {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _load_kv_files(self):
        """ИСПРАВЛЕНО: Загрузка KV файлов в правильном порядке"""
        try:
            kv_files = [
                'widgets/root_widget.kv',
                'widgets/top_menu.kv',
                'widgets/overlay_card.kv',
                'pages/home.kv',
                'pages/alarm.kv',
                'pages/schedule.kv',
                'pages/weather.kv',
                'pages/pigs.kv',
                'pages/settings.kv'
            ]
            
            for kv_file in kv_files:
                Builder.load_file(kv_file)
                logger.debug(f"Loaded KV file: {kv_file}")
                
            logger.info("All KV files loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading KV files: {e}")
            raise
    
    def _load_user_settings(self):
        """Загрузка пользовательских настроек"""
        try:
            # Применяем тему из конфига
            theme = self.user_config.get("theme", "minecraft")
            variant = self.user_config.get("variant", "light") 
            language = self.user_config.get("language", "en")
            
            # Загружаем тему
            if not self.theme_manager.load_theme(theme, variant):
                logger.warning(f"Failed to load theme {theme}/{variant}, using default")
                self.theme_manager.load_theme("minecraft", "light")
            
            # Загружаем язык
            self.localizer.load(language)
            logger.info(f"Settings loaded: theme={theme}/{variant}, language={language}")
            
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")

    def _initialize_services(self):
        """ОПТИМИЗИРОВАННАЯ инициализация сервисов"""
        try:
            logger.info("Initializing services...")
            
            # ===== КРИТИЧЕСКИЕ СЕРВИСЫ (сразу) =====
            
            # Audio Service (критически важен)
            try:
                self.audio_service = AudioService()
                logger.info("✅ audio_service initialized")
            except Exception as e:
                logger.error(f"❌ audio_service failed: {e}")
                self.audio_service = None
            
            # Alarm Service (важен для интерфейса)
            try:
                self.alarm_service = AlarmService()
                logger.info("✅ alarm_service initialized")
            except Exception as e:
                logger.error(f"❌ alarm_service failed: {e}")
                self.alarm_service = None
            
            # Notification Service (для уведомлений)
            try:
                self.notification_service = NotificationService()
                logger.info("✅ notification_service initialized")
            except Exception as e:
                logger.error(f"❌ notification_service failed: {e}")
                self.notification_service = None
            
            # Schedule Service (быстро загружается)
            try:
                self.schedule_service = ScheduleService()
                logger.info("✅ schedule_service initialized")
            except Exception as e:
                logger.error(f"❌ schedule_service failed: {e}")
                self.schedule_service = None
            
            # ===== ОТЛОЖЕННАЯ ИНИЦИАЛИЗАЦИЯ =====
            # Остальные сервисы инициализируем в фоне
            Clock.schedule_once(lambda dt: self._initialize_deferred_services(), 2.0)
            
            logger.info("Critical services initialized, deferred services scheduled")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")

    def _initialize_deferred_services(self):
        """Отложенная инициализация некритических сервисов"""
        try:
            logger.info("🔄 Starting deferred service initialization...")
            
            # Weather Service
            try:
                self.weather_service = WeatherService()
                logger.info("✅ weather_service initialized")
            except Exception as e:
                logger.warning(f"⚠️ weather_service not available: {e}")
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
            
            # Finalize dependencies
            Clock.schedule_once(lambda dt: self._finalize_service_dependencies(), 1.0)
            
        except Exception as e:
            logger.error(f"Error in deferred service initialization: {e}")

    def _finalize_service_dependencies(self):
        """Финализация зависимостей между сервисами"""
        try:
            logger.info("🔄 Finalizing service dependencies...")
            
            # Auto Theme Service (зависит от sensor_service)
            try:
                if self.sensor_service:
                    self.auto_theme_service = AutoThemeService()
                    if hasattr(self.auto_theme_service, 'start'):
                        self.auto_theme_service.start()
                    logger.info("✅ auto_theme_service initialized")
                else:
                    logger.warning("⚠️ auto_theme_service not available (no sensor service)")
            except Exception as e:
                logger.warning(f"⚠️ auto_theme_service not available: {e}")
            
            # Alarm Clock (зависит от audio_service и alarm_service)
            try:
                if ALARM_CLOCK_AVAILABLE and self.audio_service:
                    self.alarm_clock = AlarmClock()
                    if hasattr(self.alarm_clock, 'start'):
                        self.alarm_clock.start()
                    logger.info("✅ alarm_clock initialized")
                else:
                    logger.warning("⚠️ alarm_clock not available")
            except Exception as e:
                logger.warning(f"⚠️ alarm_clock not available: {e}")
            
            # Setup auto-theme
            self._setup_auto_theme()
            
            # Setup volume
            self._setup_volume_service()
            
            logger.info("✅ All services initialized and configured")
            
        except Exception as e:
            logger.error(f"Error finalizing service dependencies: {e}")

    def _setup_auto_theme(self):
        """Настройка автотемы"""
        try:
            if hasattr(self, 'auto_theme_service') and self.auto_theme_service:
                auto_theme_enabled = self.user_config.get("auto_theme", False)
                threshold = self.user_config.get("light_threshold", 3)
                
                if auto_theme_enabled:
                    self.auto_theme_service.enable()
                    logger.info(f"[Auto-theme setup] enabled=True, threshold={threshold}s")
                    
                    # Первичная проверка автотемы через 3 секунды
                    Clock.schedule_once(lambda dt: self._initial_auto_theme_check(), 3.0)
                    
        except Exception as e:
            logger.error(f"Error setting up auto-theme: {e}")

    def _initial_auto_theme_check(self):
        """Первичная проверка автотемы"""
        try:
            if hasattr(self, 'auto_theme_service') and self.auto_theme_service:
                self.auto_theme_service.check_and_update_theme()
                logger.info("Initial auto-theme check completed")
        except Exception as e:
            logger.error(f"Error in initial auto-theme check: {e}")

    def _setup_volume_service(self):
        """Настройка сервиса громкости"""
        try:
            if hasattr(self, 'volume_service') and self.volume_service:
                # Устанавливаем громкость из конфига
                saved_volume = self.user_config.get("volume", 50)
                self.volume_service.set_volume(saved_volume)
                
                status = self.volume_service.get_status()
                logger.info(f"Volume service setup complete, volume: {saved_volume}%")
                
        except Exception as e:
            logger.error(f"Error setting up volume service: {e}")

    def _setup_events(self):
        """Настройка обработчиков событий"""
        try:
            from app.event_bus import event_bus
            
            # Подписываемся на события приложения
            event_bus.subscribe("auto_theme_trigger", self._on_auto_theme_trigger)
            event_bus.subscribe("volume_changed", self._on_volume_changed)
            
            logger.info("Event handlers setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up events: {e}")

    def _finalize_initialization(self):
        """Финальная инициализация приложения"""
        try:
            logger.info("Finalizing application initialization...")
            self._running = True
            
            # Любые дополнительные настройки после полной загрузки
            logger.info("Application initialization completed")
            
        except Exception as e:
            logger.error(f"Error in finalization: {e}")

    # ======================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ======================================

    def _on_auto_theme_trigger(self, event_data):
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
        """Корректное завершение работы приложения"""
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