from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.app import App
from app.event_bus import event_bus
from app.logger import app_logger as logger
from datetime import datetime


class HomeScreen(Screen):
    """Главный экран с часами, датой, погодой и уведомлениями"""
    
    # Основные свойства для отображения
    clock_time = StringProperty("--:--")
    current_date = StringProperty("")
    current_alarm_time = StringProperty("--:--")
    alarm_status_text = StringProperty("OFF")
    
    # ИСПРАВЛЕНО: Разделенная погода для правильного окрашивания
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
        super().__init__(**kwargs)
        
        # События для обновлений
        self._update_events = []
        
        # Инициализируем все свойства значениями по умолчанию
        self.clock_time = "--:--"
        self.current_date = ""
        self.current_alarm_time = "--:--"
        self.alarm_status_text = "OFF"
        
        # ИСПРАВЛЕНО: Инициализация разделенных полей погоды
        self.weather_now_temp = "--°C"
        self.weather_now_condition = "Loading..."
        self.weather_5h_temp = "--°C"
        self.weather_5h_condition = "Unknown"
        self.weather_5h_in_text = "in 5h"
        self.weather_trend_arrow = "→"
        
        self.current_temp_value = 20
        self.forecast_temp_value = 20
        self.temp_trend = 0
        self.notification_text = "Welcome to Bedrock 2.0!"
        self.notification_scroll_x = 0
        
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme)
        event_bus.subscribe("language_changed", self.refresh_text)
        
    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering HomeScreen")
        self.refresh_theme()
        self.refresh_text()
        self.update_all_data()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in HomeScreen")
        return None

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
        """Полное обновление всех данных"""
        self.update_time()
        self.update_weather()
        self.update_alarm_status()
        self.update_notifications()

    def update_time(self, *args):
        """Обновление времени и даты"""
        try:
            now = datetime.now()
            self.clock_time = now.strftime("%H:%M")
            
            # Формат: число месяц, день недели
            app = App.get_running_app()
            if hasattr(app, 'localizer') and app.localizer:
                day_names = {
                    0: "Monday", 1: "Tuesday", 2: "Wednesday", 
                    3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
                }
                month_names = {
                    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
                }
                
                day_name = day_names.get(now.weekday(), now.strftime("%A"))
                month_name = month_names.get(now.month, now.strftime("%B"))
                
                # Формат: число месяц, день недели
                self.current_date = f"{now.day} {month_name}, {day_name}"
            else:
                # Fallback
                self.current_date = now.strftime("%d %B, %A")
                
        except Exception as e:
            logger.error(f"Error updating time: {e}")
            self.clock_time = "--:--"
            self.current_date = "Error"

    def update_weather(self, *args):
        """Обновление данных о погоде"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'weather_service') and app.weather_service:
                weather = app.weather_service.get_weather()
                
                # ИСПРАВЛЕНО: Обработка текущей погоды
                current = weather.get("current", {})
                if current:
                    temp_now = current.get('temperature', 0)
                    self.current_temp_value = temp_now
                    condition_now = current.get('condition', 'Unknown')
                    
                    # Разделяем температуру и условие
                    self.weather_now_temp = f"{temp_now:.1f}°"
                    self.weather_now_condition = condition_now
                else:
                    self.weather_now_temp = "--°"
                    self.weather_now_condition = "No data"
                    self.current_temp_value = 20
                
                # ИСПРАВЛЕНО: Обработка прогноза на 5 часов
                forecast_5h = weather.get("forecast_5h", {})
                if forecast_5h and forecast_5h.get('temperature') is not None:
                    temp_5h = forecast_5h.get('temperature', 0)
                    condition_5h = forecast_5h.get('condition', 'Unknown')
                    self.forecast_temp_value = temp_5h
                    
                    # Разделяем температуру, условие и текст "in 5h"
                    self.weather_5h_temp = f"{temp_5h:.1f}°"
                    self.weather_5h_condition = condition_5h
                    
                    # Получаем локализованный текст "in 5h"
                    if hasattr(app, 'localizer') and app.localizer:
                        self.weather_5h_in_text = app.localizer.tr("in_5h", "in 5h")
                    else:
                        self.weather_5h_in_text = "in 5h"
                    
                    # Тренд температуры
                    temp_diff = temp_5h - temp_now
                    if temp_diff > 1:
                        self.weather_trend_arrow = "↗"  # Растет
                        self.temp_trend = 1
                    elif temp_diff < -1:
                        self.weather_trend_arrow = "↘"  # Падает
                        self.temp_trend = -1
                    else:
                        self.weather_trend_arrow = "→"  # Стабильно
                        self.temp_trend = 0
                else:
                    self.weather_5h_temp = "--°"
                    self.weather_5h_condition = "No forecast"
                    self.weather_5h_in_text = ""
                    self.weather_trend_arrow = "→"
                    self.forecast_temp_value = 20
                    self.temp_trend = 0
            else:
                # Сервис недоступен
                self.weather_now_temp = "--°"
                self.weather_now_condition = "Service offline"
                self.weather_5h_temp = "--°"
                self.weather_5h_condition = "Service offline"
                self.weather_5h_in_text = ""
                self.weather_trend_arrow = "→"
                self.current_temp_value = 20
                self.forecast_temp_value = 20
                self.temp_trend = 0
                
            # Обновляем цвета после изменения данных
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
                
        except Exception as e:
            logger.error(f"Error updating weather: {e}")
            self.weather_now_temp = "--°"
            self.weather_now_condition = "Error"
            self.weather_5h_temp = "--°"
            self.weather_5h_condition = "Error"
            self.weather_5h_in_text = ""
            self.weather_trend_arrow = "→"
            self.current_temp_value = 20
            self.forecast_temp_value = 20
            self.temp_trend = 0

    def update_alarm_status(self, *args):
        """Обновление статуса будильника"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    # Время будильника всегда показываем
                    self.current_alarm_time = alarm.get("time", "07:30")
                    
                    # Статус зависит от enabled
                    if alarm.get("enabled", False):
                        if hasattr(app, 'localizer') and app.localizer:
                            self.alarm_status_text = app.localizer.tr("alarm_on", "ON")
                        else:
                            self.alarm_status_text = "ON"
                    else:
                        if hasattr(app, 'localizer') and app.localizer:
                            self.alarm_status_text = app.localizer.tr("alarm_off", "OFF")
                        else:
                            self.alarm_status_text = "OFF"
                else:
                    self.current_alarm_time = "07:30"
                    self.alarm_status_text = "OFF"
            else:
                self.current_alarm_time = "07:30"
                self.alarm_status_text = "SERVICE OFFLINE"
                
            # Обновляем цвета будильника после изменения статуса
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
                
        except Exception as e:
            logger.error(f"Error updating alarm status: {e}")
            self.current_alarm_time = "07:30"
            self.alarm_status_text = "ERROR"

    def update_notifications(self, *args):
        """Обновление уведомлений - показываем только последнее"""
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'notification_service') and app.notification_service:
                notifications = app.notification_service.list_unread()
                if notifications:
                    # Берём только последнее уведомление вместо объединения всех
                    last_notification = notifications[-1]
                    text = last_notification.get("text", "").strip()
                    if text:
                        self.notification_text = text
                    else:
                        self.notification_text = "No new notifications"
                else:
                    if hasattr(app, 'user_config') and app.user_config:
                        username = app.user_config.get("username", "User")
                        if hasattr(app, 'localizer') and app.localizer:
                            welcome_text = app.localizer.tr("hello_user", "Hello, {username}!").format(username=username)
                            self.notification_text = welcome_text
                        else:
                            self.notification_text = f"Hello, {username}!"
                    else:
                        self.notification_text = "Welcome to Bedrock 2.0!"
            else:
                self.notification_text = "Notification service offline"
                
        except Exception as e:
            logger.error(f"Error updating notifications: {e}")
            self.notification_text = "Error loading notifications"

    def scroll_notification(self, *args):
        """Прокрутка уведомлений (бегущая строка)"""
        try:
            if not hasattr(self, 'ids') or 'notification_container' not in self.ids:
                return
                
            container = self.ids.notification_container
            if not hasattr(self, 'ids') or 'notification_text_label' not in self.ids:
                return
                
            label = self.ids.notification_text_label
            
            # Проверяем, что label и container корректно инициализированы
            if not container.width or not label.texture_size:
                return
            
            # Если текст помещается в контейнер, не прокручиваем
            if label.texture_size[0] <= container.width:
                self.notification_scroll_x = 0
                return
            
            # Прокрутка справа налево
            scroll_speed = 1  # пикселей за кадр
            max_scroll = label.texture_size[0] + 50  # добавляем отступ
            
            self.notification_scroll_x -= scroll_speed
            if self.notification_scroll_x < -max_scroll:
                self.notification_scroll_x = container.width
                
        except Exception as e:
            logger.error(f"Error scrolling notification: {e}")

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

    def is_alarm_enabled(self):
        """Проверка включен ли будильник"""
        return self.alarm_status_text == "ON"

    def toggle_alarm(self, *args):
        """Переключение состояния будильника"""
        try:
            app = App.get_running_app()
            
            # Воспроизводим звук
            tm = self.get_theme_manager()
            if hasattr(app, 'audio_service') and app.audio_service and tm:
                sound_file = tm.get_sound("click")
                if sound_file:
                    app.audio_service.play(sound_file)
            
            # Переключаем состояние будильника
            if hasattr(app, 'alarm_service') and app.alarm_service:
                alarm = app.alarm_service.get_alarm()
                if alarm:
                    new_enabled = not alarm.get("enabled", False)
                    alarm["enabled"] = new_enabled
                    app.alarm_service.set_alarm(alarm)
                    
                    # Немедленно обновляем отображение
                    self.update_alarm_status()
                    
                    logger.info(f"Alarm toggled: {'ON' if new_enabled else 'OFF'}")
                else:
                    logger.error("No alarm configuration found")
            else:
                logger.error("Alarm service not available")
                
        except Exception as e:
            logger.error(f"Error toggling alarm: {e}")

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            logger.warning("ThemeManager not loaded in HomeScreen.refresh_theme")
            return

        # ИСПРАВЛЕНО: Обновленный список виджетов с разделенными элементами погоды
        widgets_to_update = [
            "date_label", "alarm_time_label", "alarm_toggle_btn", 
            "clock_label", "clock_shadow1", "clock_shadow2", "clock_shadow3",
            # Разделенные элементы погоды
            "weather_now_temp_label", "weather_now_condition_label",
            "weather_5h_temp_label", "weather_5h_condition_label", "weather_5h_in_label",
            "weather_trend_label",
            "notification_text_label"
        ]
        
        # Получаем путь к шрифту один раз
        font_path = tm.get_font("main")
        
        for widget_id in widgets_to_update:
            if hasattr(self, 'ids') and widget_id in self.ids:
                widget = self.ids[widget_id]
                
                # Обновляем шрифт только если путь корректный
                if hasattr(widget, 'font_name') and font_path:
                    try:
                        widget.font_name = font_path
                    except Exception as e:
                        logger.warning(f"Failed to set font for {widget_id}: {e}")
                    
                # ИСПРАВЛЕНО: Правильная логика цветов
                if hasattr(widget, 'color'):
                    if widget_id == "clock_label":
                        # Часы меняют цвет по теме
                        widget.color = tm.get_rgba("clock_main")
                    elif widget_id in ["clock_shadow1", "clock_shadow2", "clock_shadow3"]:
                        # Тени остаются черными с разной прозрачностью
                        pass
                    elif widget_id == "alarm_time_label":
                        # Цвет времени будильника зависит от статуса
                        if self.is_alarm_enabled():
                            widget.color = tm.get_rgba("primary")
                        else:
                            widget.color = tm.get_rgba("text_secondary")
                    elif widget_id == "alarm_toggle_btn":
                        # Цвет кнопки будильника зависит от статуса
                        if self.is_alarm_enabled():
                            widget.color = tm.get_rgba("primary")
                        else:
                            widget.color = tm.get_rgba("text_secondary")
                    # ИСПРАВЛЕНО: Правильные цвета для элементов погоды
                    elif widget_id == "weather_now_temp_label":
                        # Температура сейчас - цвет по условию
                        widget.color = self.get_temperature_color(self.current_temp_value)
                    elif widget_id == "weather_now_condition_label":
                        # Условие сейчас - основной цвет темы
                        widget.color = tm.get_rgba("primary")
                    elif widget_id == "weather_5h_temp_label":
                        # Температура прогноза - цвет по условию
                        widget.color = self.get_temperature_color(self.forecast_temp_value)
                    elif widget_id == "weather_5h_condition_label":
                        # Условие прогноза - основной цвет темы
                        widget.color = tm.get_rgba("primary")
                    elif widget_id == "weather_5h_in_label":
                        # Текст "in 5h" - вторичный цвет
                        widget.color = tm.get_rgba("text_secondary")
                    elif widget_id == "weather_trend_label":
                        # Цвет стрелки тренда по динамике
                        widget.color = self.get_trend_arrow_color()
                    elif widget_id in ["date_label", "notification_text_label"]:
                        widget.color = tm.get_rgba("text")
                
                # Обновляем фон кнопок
                if hasattr(widget, 'background_normal'):
                    bg_normal = tm.get_image("button_bg")
                    bg_active = tm.get_image("button_bg_active")
                    if bg_normal:
                        widget.background_normal = bg_normal
                    if bg_active:
                        widget.background_down = bg_active

        logger.debug("HomeScreen theme refreshed")

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        # Обновляем дату, будильник и уведомления
        self.update_time()
        self.update_alarm_status() 
        self.update_notifications()
        # Также обновляем текст "in 5h" при смене языка
        self.update_weather()

    def on_kv_post(self, base_widget):
        """Вызывается после загрузки KV файла"""
        try:
            # Применяем тему после загрузки KV
            Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)
        except Exception as e:
            logger.error(f"Error in HomeScreen on_kv_post: {e}")