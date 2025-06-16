# pages/home.py - ПОЛНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
ИСПРАВЛЕНИЯ:
✅ Полная миграция на BaseScreen  
✅ Правильное применение темы
✅ Убраны все дублирования
✅ Исправлена инициализация
✅ Добавлены отладочные методы
✅ Проверен синтаксис
"""

from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.app import App
import time
import datetime
from app.event_bus import event_bus
from app.logger import app_logger as logger
from widgets.base_screen import BaseScreen


class HomeScreen(BaseScreen):
    """Главный экран с часами, датой, погодой и уведомлениями"""
    
    # Основные свойства для отображения (названия соответствуют home.kv)
    clock_time = StringProperty("--:--")
    current_date = StringProperty("")
    current_alarm_time = StringProperty("--:--")
    alarm_status_text = StringProperty("OFF")
    
    # Разделенная погода для правильного окрашивания
    # Текущая погода
    weather_now_temp = StringProperty("--°C")
    weather_now_condition = StringProperty("Loading...")
    
    # Прогноз на 5 часов
    weather_5h_temp = StringProperty("--°C")
    weather_5h_condition = StringProperty("Unknown")
    weather_5h_in_text = StringProperty("in 5h")
    
    # Стрелка тренда
    weather_trend_arrow = StringProperty("→")
    
    # Температуры для цветовой логики
    current_temp_value = NumericProperty(20)
    forecast_temp_value = NumericProperty(20)
    temp_trend = NumericProperty(0)  # -1, 0, 1 для падения, стабильно, рост
    
    # Уведомления - бегущая строка
    notification_text = StringProperty("Welcome to Bedrock 2.0!")
    notification_scroll_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # BaseScreen автоматически подписывается на события
        
        # События для обновлений
        self._update_events = []
        
        # Переменные для оптимизации обновлений
        self._last_alarm_update = 0
        self._alarm_update_delay = 0.5  # Минимум 500ms между обновлениями
        self._cached_alarm_data = None
        
        # Подписка на специфичные события приложения
        event_bus.subscribe("alarm_settings_changed", self._on_alarm_settings_changed)
        
        logger.info("HomeScreen initialized with BaseScreen")

    # ========================================
    # ИНИЦИАЛИЗАЦИЯ И ЖИЗНЕННЫЙ ЦИКЛ
    # ========================================

    def on_screen_initialized(self):
        """Переопределяем метод BaseScreen для специфичной инициализации"""
        try:
            logger.info("🏠 HomeScreen initializing...")
            
            # Выполняем первичную инициализацию данных
            self.update_all_data()
            
            # ИСПРАВЛЕНО: Принудительно обновляем тему
            Clock.schedule_once(lambda dt: self._force_initial_theme_refresh(), 0.1)
            
            logger.info("✅ HomeScreen initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Error in HomeScreen initialization: {e}")

    def _force_initial_theme_refresh(self):
        """НОВОЕ: Принудительное обновление темы при инициализации"""
        try:
            logger.info("🎨 HomeScreen: forcing initial theme refresh...")
            
            # Проверяем наличие theme_manager
            tm = self.get_theme_manager()
            if not tm:
                logger.warning("❌ HomeScreen: ThemeManager not available")
                # Пробуем получить через Clock с задержкой
                Clock.schedule_once(lambda dt: self._force_initial_theme_refresh(), 0.5)
                return
            
            if not tm.is_loaded():
                logger.warning("❌ HomeScreen: Theme not loaded yet")
                # Пробуем снова через некоторое время
                Clock.schedule_once(lambda dt: self._force_initial_theme_refresh(), 0.5)
                return
            
            # Тема доступна - обновляем
            self.refresh_theme()
            logger.info("✅ HomeScreen: initial theme refresh completed")
            
        except Exception as e:
            logger.error(f"❌ Error in HomeScreen force theme refresh: {e}")

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering HomeScreen")
        self.update_all_data()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    # ========================================
    # ПЕРИОДИЧЕСКИЕ ОБНОВЛЕНИЯ
    # ========================================

    def start_updates(self):
        """Запуск периодических обновлений"""
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_time(), 1),           # Время каждую секунду
            Clock.schedule_interval(lambda dt: self.update_weather(), 300),      # Погода каждые 5 минут
            Clock.schedule_interval(lambda dt: self.update_alarm_status(), 60),  # Будильник каждую минуту
            Clock.schedule_interval(lambda dt: self.update_notifications(), 30), # Уведомления каждые 30 сек
            Clock.schedule_interval(lambda dt: self.scroll_notification(), 0.1), # Прокрутка уведомлений
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        for event in self._update_events:
            if event:
                event.cancel()
        self._update_events = []

    def update_all_data(self):
        """Обновление всех данных на экране"""
        try:
            self.update_time()
            self.update_weather()
            self.update_alarm_status()
            self.update_notifications()
            logger.debug("All HomeScreen data updated")
        except Exception as e:
            logger.error(f"Error updating HomeScreen data: {e}")

    # ========================================
    # ОБНОВЛЕНИЕ ВРЕМЕНИ И ДАТЫ
    # ========================================

    def update_time(self):
        """Обновление времени и даты"""
        try:
            now = datetime.datetime.now()
            self.clock_time = now.strftime("%H:%M")
            self.current_date = now.strftime("%A, %B %d")
        except Exception as e:
            logger.error(f"Error updating time: {e}")

    # ========================================
    # ОБНОВЛЕНИЕ ПОГОДЫ
    # ========================================

    def update_weather(self):
        """Обновление данных о погоде"""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'weather_service') or not app.weather_service:
                logger.warning("Weather service not available")
                return

            weather_service = app.weather_service
            
            # Проверяем, нужно ли обновить данные
            if weather_service.needs_update():
                logger.info("Fetching fresh weather data...")
                weather_service.fetch_weather()
            
            # Получаем данные о погоде
            weather_data = weather_service.weather
            
            # Текущая погода
            current = weather_data.get("current", {})
            self.weather_now_temp = f"{current.get('temperature', '--')}°C"
            self.weather_now_condition = current.get("condition", "Unknown")
            self.current_temp_value = current.get("temperature", 20)
            
            # Прогноз на 5 часов
            forecast_5h = weather_data.get("forecast_5h", {})
            self.weather_5h_temp = f"{forecast_5h.get('temperature', '--')}°C"
            self.weather_5h_condition = forecast_5h.get("condition", "Unknown")
            self.forecast_temp_value = forecast_5h.get("temperature", 20)
            
            # Тренд температуры
            current_temp = current.get("temperature", 20)
            forecast_temp = forecast_5h.get("temperature", 20)
            
            if forecast_temp > current_temp + 1:
                self.temp_trend = 1
                self.weather_trend_arrow = "↗"
            elif forecast_temp < current_temp - 1:
                self.temp_trend = -1
                self.weather_trend_arrow = "↘"
            else:
                self.temp_trend = 0
                self.weather_trend_arrow = "→"
            
            logger.debug("Weather data updated")
            
        except Exception as e:
            logger.error(f"Error updating weather: {e}")

    # ========================================
    # ОБНОВЛЕНИЕ БУДИЛЬНИКА
    # ========================================
    def update_alarm_status(self):
        """Обновление статуса будильника с кэшированием"""
        try:
            current_time = time.time()
            
            # Проверяем, не слишком ли часто обновляем
            if current_time - self._last_alarm_update < self._alarm_update_delay:
                return
            
            app = App.get_running_app()
            
            # ИСПРАВЛЕНО: Используем alarm_service вместо user_config
            if not hasattr(app, 'alarm_service') or not app.alarm_service:
                logger.warning("Alarm service not available")
                # Устанавливаем дефолтные значения
                self.current_alarm_time = "--:--"
                self.alarm_status_text = "OFF"
                return
            
            # Получаем данные из alarm_service
            alarm_data = app.alarm_service.get_alarm()
            if not alarm_data:
                self.current_alarm_time = "--:--"
                self.alarm_status_text = "OFF"
                return
            
            # Проверяем, изменились ли данные
            if self._cached_alarm_data == alarm_data:
                return
            
            self._cached_alarm_data = alarm_data.copy()
            self._last_alarm_update = current_time
            
            # Обновляем данные будильника
            if alarm_data.get("enabled", False):
                alarm_time = alarm_data.get("time", "07:00")
                self.current_alarm_time = alarm_time
                self.alarm_status_text = "ON"
            else:
                self.current_alarm_time = "--:--"
                self.alarm_status_text = "OFF"
            
            logger.debug(f"Alarm status updated: {self.current_alarm_time} ({self.alarm_status_text})")
            
        except Exception as e:
            logger.error(f"Error updating alarm status: {e}")

    def is_alarm_enabled(self):
        """Проверить, включен ли будильник"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm_data = app.alarm_service.get_alarm()
                return alarm_data.get("enabled", False) if alarm_data else False
        except Exception as e:
            logger.error(f"Error checking alarm status: {e}")
        return False

    def _on_alarm_settings_changed(self, *args):
        """Обработчик изменения настроек будильника"""
        self._cached_alarm_data = None
        self.update_alarm_status()

    # ========================================
    # ОБНОВЛЕНИЕ УВЕДОМЛЕНИЙ
    # ========================================

    def update_notifications(self):
        """Обновление уведомлений"""
        try:
            app = App.get_running_app()
            
            # Проверяем сервис уведомлений
            if hasattr(app, 'notification_service') and app.notification_service:
                try:
                    last_notification = app.notification_service.get_last_notification()
                
                    if last_notification and last_notification.get("text"):
                        self.notification_text = last_notification.get("text")
                    else:
                        self._set_welcome_notification()
                except Exception as e:
                    logger.error(f"Error getting notifications: {e}")
                    self._set_welcome_notification()
            else:
                self._set_welcome_notification()
                
        except Exception as e:
            logger.error(f"Error updating notifications: {e}")

    def _set_welcome_notification(self):
        """Установить приветственное уведомление"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'user_config'):
                username = app.user_config.get("username", "User")
                self.notification_text = f"Welcome back, {username}! Have a great day!"
            else:
                self.notification_text = "Welcome to Bedrock 2.0!"
        except Exception as e:
            logger.error(f"Error setting welcome notification: {e}")
            self.notification_text = "Welcome to Bedrock 2.0!"

    # ЗАМЕНИТЬ метод scroll_notification в pages/home.py:

    def scroll_notification(self):
        """УЛУЧШЕННАЯ прокрутка текста уведомлений"""
        try:
            if not hasattr(self, 'ids') or 'notification_text_label' not in self.ids:
                return
                
            label = self.ids.notification_text_label
            container = self.ids.get('notification_container')
            
            if not label or not container:
                return
                
            # Получаем реальные размеры
            text_width = label.texture_size[0] if label.texture_size[0] > 0 else 100
            container_width = container.width if container.width > 0 else 400
            
            if text_width <= container_width:
                # Текст помещается - центрируем
                self.notification_scroll_x = (container_width - text_width) / 2
            else:
                # Текст не помещается - плавная прокрутка
                scroll_speed = 50  # пикселей в секунду
                
                # Обновляем позицию
                self.notification_scroll_x -= scroll_speed * 0.1  # 0.1 - интервал Clock
                
                # Сброс в начало при полной прокрутке
                if self.notification_scroll_x < -(text_width + 50):  # +50 для паузы
                    self.notification_scroll_x = container_width + 20  # +20 для появления
                    
        except Exception as e:
            logger.error(f"Error scrolling notification: {e}")
            # Простой fallback
            self.notification_scroll_x += 1
            if self.notification_scroll_x > 200:
                self.notification_scroll_x = -100

    # ========================================
    # ЦВЕТОВАЯ ЛОГИКА
    # ========================================

    def get_temperature_color(self, temp_value):
        """Получить цвет для температуры в зависимости от значения"""
        if temp_value > 23:
            return [1, 0.6, 0, 1]  # Оранжевый для жаркой погоды
        elif temp_value < 18:
            return [0.2, 0.6, 1, 1]  # Синий для холодной погоды
        else:
            tm = self.get_theme_manager()
            return tm.get_rgba("primary") if tm else [1, 1, 1, 1]

    def get_trend_arrow_color(self):
        """Получить цвет стрелки тренда"""
        if self.temp_trend > 0:
            return [1, 0.6, 0, 1]  # Оранжевый для роста
        elif self.temp_trend < 0:
            return [0.2, 0.6, 1, 1]  # Синий для падения
        else:
            tm = self.get_theme_manager()
            return tm.get_rgba("text") if tm else [1, 1, 1, 1]

    # ========================================
    # ПЕРЕОПРЕДЕЛЕННЫЕ МЕТОДЫ BaseScreen
    # ========================================

    def refresh_theme(self):
        """
        Основной метод обновления темы.
        Автоматически обновляет все виджеты с учетом текущей темы.
        """
        try:
            logger.debug("🎨 HomeScreen: refreshing theme...")
            
            tm = self.get_theme_manager()
            if not tm or not tm.is_loaded():
                logger.warning(f"❌ HomeScreen: Theme manager not available or not loaded")
                return

            # ИСПРАВЛЕНО: Сначала вызываем базовый метод
            super().refresh_theme()

            # Затем применяем специфичные стили для HomeScreen
            self._apply_home_specific_styles(tm)
            
            logger.debug("✅ HomeScreen: theme refresh completed")
            
        except Exception as e:
            logger.error(f"❌ Error refreshing theme in HomeScreen: {e}")

    def _apply_home_specific_styles(self, tm):
        """НОВОЕ: Применение специфичных стилей HomeScreen"""
        try:
            if not hasattr(self, 'ids'):
                logger.warning("❌ HomeScreen: ids not available")
                return
                
            # Проверяем, что все нужные виджеты существуют
            required_widgets = [
                'clock_label', 'date_label', 'weather_now_temp_label',
                'weather_now_condition_label', 'alarm_time_label'
            ]
            
            missing_widgets = [w for w in required_widgets if w not in self.ids]
            if missing_widgets:
                logger.warning(f"❌ HomeScreen: missing widgets: {missing_widgets}")
            
            # Применяем стили для существующих виджетов
            self._update_clock_styles(tm)
            self._update_weather_styles(tm)
            self._update_alarm_styles(tm)
            self._update_notification_styles(tm)
            
            logger.debug("✅ HomeScreen: specific styles applied")
            
        except Exception as e:
            logger.error(f"❌ Error applying HomeScreen specific styles: {e}")

    def _update_clock_styles(self, tm):
        """Обновление стилей часов"""
        try:
            # Основные часы
            if 'clock_label' in self.ids:
                self.ids.clock_label.font_name = tm.get_font("clock")
                self.ids.clock_label.color = tm.get_rgba("primary")
            
            # Тени часов
            shadow_color = tm.get_rgba("clock_shadow")
            for i in range(1, 4):  # clock_shadow1, clock_shadow2, clock_shadow3
                shadow_id = f"clock_shadow{i}"
                if shadow_id in self.ids:
                    self.ids[shadow_id].font_name = tm.get_font("clock")
                    self.ids[shadow_id].color = shadow_color
            
            # Дата
            if 'date_label' in self.ids:
                self.ids.date_label.font_name = tm.get_font("main")
                self.ids.date_label.color = tm.get_rgba("text_secondary")
                
            logger.debug("✅ Clock styles updated")
            
        except Exception as e:
            logger.error(f"❌ Error updating clock styles: {e}")

    def _update_weather_styles(self, tm):
        """Обновление стилей погоды"""
        try:
            # Текущая погода
            if 'weather_now_temp_label' in self.ids:
                self.ids.weather_now_temp_label.font_name = tm.get_font("main")
                self.ids.weather_now_temp_label.color = self.get_temperature_color(self.current_temp_value)
            
            if 'weather_now_condition_label' in self.ids:
                self.ids.weather_now_condition_label.font_name = tm.get_font("main")
                self.ids.weather_now_condition_label.color = tm.get_rgba("text")
            
            # Прогноз на 5 часов
            if 'weather_5h_temp_label' in self.ids:
                self.ids.weather_5h_temp_label.font_name = tm.get_font("main")
                self.ids.weather_5h_temp_label.color = self.get_temperature_color(self.forecast_temp_value)
            
            if 'weather_5h_condition_label' in self.ids:
                self.ids.weather_5h_condition_label.font_name = tm.get_font("main")
                self.ids.weather_5h_condition_label.color = tm.get_rgba("text")
            
            if 'weather_5h_in_label' in self.ids:
                self.ids.weather_5h_in_label.font_name = tm.get_font("main")
                self.ids.weather_5h_in_label.color = tm.get_rgba("text_secondary")
            
            # Стрелка тренда
            if 'weather_trend_label' in self.ids:
                self.ids.weather_trend_label.font_name = tm.get_font("main")
                self.ids.weather_trend_label.color = self.get_trend_arrow_color()
                
            logger.debug("✅ Weather styles updated")
            
        except Exception as e:
            logger.error(f"❌ Error updating weather styles: {e}")

    def _update_alarm_styles(self, tm):
        """Обновление стилей будильника"""
        try:
            if 'alarm_time_label' in self.ids:
                self.ids.alarm_time_label.font_name = tm.get_font("main")
                self.ids.alarm_time_label.color = tm.get_rgba("text")
            
            if 'alarm_toggle_btn' in self.ids:
                color = tm.get_rgba("text_accent") if self.is_alarm_enabled() else tm.get_rgba("text_inactive")
                self.ids.alarm_toggle_btn.color = color
                
            logger.debug("✅ Alarm styles updated")
            
        except Exception as e:
            logger.error(f"❌ Error updating alarm styles: {e}")

    def _update_notification_styles(self, tm):
        """Обновление стилей уведомлений"""
        try:
            if 'notification_text_label' in self.ids:
                self.ids.notification_text_label.font_name = tm.get_font("main")
                self.ids.notification_text_label.color = tm.get_rgba("text")
                
            logger.debug("✅ Notification styles updated")
            
        except Exception as e:
            logger.error(f"❌ Error updating notification styles: {e}")

    def get_theme_manager(self):
        """ИСПРАВЛЕНО: Более надежное получение theme_manager"""
        try:
            app = App.get_running_app()
            if app and hasattr(app, 'theme_manager') and app.theme_manager:
                return app.theme_manager
            
            # Альтернативный способ через глобальный экземпляр
            from app.theme_manager import get_theme_manager
            tm = get_theme_manager()
            if tm and tm.is_loaded():
                return tm
                
            logger.warning("❌ HomeScreen: ThemeManager not available")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting theme manager in HomeScreen: {e}")
            return None

    def refresh_text(self):
        """Обновление локализованных текстов"""
        try:
            # Обновляем текст "in 5h"
            self.weather_5h_in_text = self._get_localized_text("in_5h", "in 5h")
            
            # Обновляем приветственное сообщение если оно активно
            if "Welcome" in self.notification_text or "Bedrock" in self.notification_text:
                self._set_welcome_notification()
                
            logger.debug("HomeScreen text refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing HomeScreen text: {e}")

    def _get_localized_text(self, key, default):
        """Получить локализованный текст"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'localizer'):
                return app.localizer.get(key, default)
        except Exception as e:
            logger.error(f"Error getting localized text: {e}")
        return default

    def toggle_alarm(self):
        """Переключение состояния будильника через сервис"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'alarm_service') and app.alarm_service:
                # Используем метод toggle из alarm_service
                success = app.alarm_service.toggle()
                if success:
                    if hasattr(app, 'audio_service') and app.audio_service:
                        app.audio_service.play_sound("confirm")
                    # Принудительно обновляем отображение
                    self._cached_alarm_data = None  # Сбрасываем кэш
                    self.update_alarm_status()
                    logger.info("Alarm toggled successfully")
                else:
                    logger.warning("Failed to toggle alarm")
            else:
                logger.warning("Alarm service not available")
                
        except Exception as e:
            logger.error(f"Error toggling alarm: {e}")

    # ========================================
    # ОТЛАДОЧНЫЕ МЕТОДЫ
    # ========================================

    def diagnose_theme_state(self):
        """НОВОЕ: Диагностика состояния темы для отладки"""
        try:
            tm = self.get_theme_manager()
            
            info = {
                "theme_manager_available": tm is not None,
                "theme_loaded": tm.is_loaded() if tm else False,
                "current_theme": tm.current_theme if tm else None,
                "current_variant": tm.current_variant if tm else None,
                "ids_count": len(self.ids) if hasattr(self, 'ids') else 0,
                "widgets_in_ids": list(self.ids.keys()) if hasattr(self, 'ids') else []
            }
            
            logger.info(f"🔍 HomeScreen theme state: {info}")
            return info
            
        except Exception as e:
            logger.error(f"❌ Error in theme state diagnosis: {e}")
            return {"error": str(e)}

    def force_theme_refresh_debug(self):
        """НОВОЕ: Принудительное обновление темы с отладкой"""
        try:
            logger.info("🐛 HomeScreen: DEBUG theme refresh started")
            
            # Диагностика
            self.diagnose_theme_state()
            
            # Попытка обновления
            self.refresh_theme()
            
            logger.info("✅ HomeScreen: DEBUG theme refresh completed")
            
        except Exception as e:
            logger.error(f"❌ HomeScreen: DEBUG theme refresh failed: {e}")

    def force_alarm_status_refresh(self):
        """Принудительное обновление статуса будильника"""
        self._cached_alarm_data = None
        self._last_alarm_update = 0
        self.update_alarm_status()
        logger.info("Forced alarm status refresh")

# ВЫЗОВ ИЗ КОНСОЛИ ДЛЯ ОТЛАДКИ:
# App.get_running_app().root.screen_manager.current_screen.diagnose_theme_state()
# App.get_running_app().root.screen_manager.current_screen.force_theme_refresh_debug()