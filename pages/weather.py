from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.app import App
from kivy.metrics import dp
from app.event_bus import event_bus
from app.logger import app_logger as logger


class DayForecastItem(BoxLayout):
    """Виджет для отображения прогноза на один день - ОБНОВЛЕНО"""
    
    def __init__(self, day_data, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(32)
        self.spacing = dp(8)
        self.padding = [dp(8), dp(2)]
        
        app = App.get_running_app()
        tm = app.theme_manager if hasattr(app, 'theme_manager') else None
        
        # День недели
        day_name = day_data.get("day", "")
        is_weekend = day_name in ["Sat", "Sun"]
        day_color = tm.get_rgba("primary") if (tm and is_weekend) else (tm.get_rgba("text") if tm else [1, 1, 1, 1])
        
        day_label = Label(
            text=day_name,
            font_name=tm.get_font("main") if tm else "",
            font_size="16sp",
            halign="left",
            valign="middle",
            size_hint_x=0.05,
            color=day_color,
            text_size=(None, None)
        )
        day_label.bind(size=day_label.setter('text_size'))
        
        # Температура
        temp_max = day_data.get("temp_max", 0)
        temp_label = Label(
            text=f"{temp_max:.1f}°C",
            font_name=tm.get_font("main") if tm else "",
            font_size="16sp",
            halign="center",
            valign="middle",
            size_hint_x=0.15,
            color=tm.get_rgba("primary") if tm else [1, 1, 1, 1],
            text_size=(None, None)
        )
        temp_label.bind(size=temp_label.setter('text_size'))
        
        # ИЗМЕНЕНО: Условие погоды с Min/Max температурами
        condition = day_data.get("condition", "")
        temp_min = day_data.get("temp_min", 0)
        temp_max = day_data.get("temp_max", 0)
        
        # Формируем строку с Min/Max перед условием
        condition_text = f"Min: {temp_min:.1f}°, Max: {temp_max:.1f}° - {condition}"
        if len(condition_text) > 50:
            condition_text = condition_text[:45] + "..."
        
        condition_label = Label(
            text=condition_text,
            font_name=tm.get_font("main") if tm else "",
            font_size="16sp",
            halign="left",
            valign="middle",
            size_hint_x=0.55,
            color=tm.get_rgba("text") if tm else [1, 1, 1, 1],
            text_size=(None, None)
        )
        condition_label.bind(size=condition_label.setter('text_size'))
        
        # Вероятность осадков
        precip = day_data.get("precipitation_probability", 0)
        precip_label = Label(
            text=f"{precip}%",
            font_name=tm.get_font("main") if tm else "",
            font_size="16sp",
            halign="center",
            valign="middle",
            size_hint_x=0.25,
            color=tm.get_rgba("text_secondary") if tm else [0.7, 0.7, 0.7, 1],
            text_size=(None, None)
        )
        precip_label.bind(size=precip_label.setter('text_size'))
        
        # Добавляем все виджеты
        self.add_widget(day_label)
        self.add_widget(temp_label)
        self.add_widget(condition_label)
        self.add_widget(precip_label)


class WeatherScreen(Screen):
    """Экран погоды с данными датчиков и прогнозом"""
    
    # Текущая погода
    current_temp = StringProperty("--°C")
    current_condition = StringProperty("Loading...")
    current_precipitation = StringProperty("Rain: --%")
    
    # Показания датчиков - ИЗМЕНЕНО
    sensor_temp_humidity = StringProperty("Room: --°C, Humidity: --%")
    sensor_co2_tvoc = StringProperty("CO2: -- ppm, TVOC: -- ppb")
    sensor_air_quality = StringProperty("Air Quality: Unknown")
    
    # Статус датчиков
    sensor_available = BooleanProperty(False)
    using_mock_sensors = BooleanProperty(True)
    
    # Недельный прогноз
    weekly_forecast = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme)
        event_bus.subscribe("language_changed", self.refresh_text)
        
        # События для обновлений
        self._update_events = []

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering WeatherScreen")
        self.refresh_theme()
        self.refresh_text()
        self.update_all()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in WeatherScreen")
        return None

    def start_updates(self):
        """Запуск периодических обновлений"""
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_weather(), 600),   # Погода каждые 10 минут
            Clock.schedule_interval(lambda dt: self.update_sensors(), 30),    # Датчики каждые 30 секунд
            Clock.schedule_interval(lambda dt: self.update_display(), 5),     # Отображение каждые 5 секунд
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        for event in self._update_events:
            event.cancel()
        self._update_events = []

    def update_all(self):
        """Полное обновление всех данных"""
        self.update_weather()
        self.update_sensors()
        self.update_display()

    def update_weather(self, *args):
        """Обновление данных о погоде"""
        app = App.get_running_app()
        if hasattr(app, 'weather_service') and app.weather_service:
            try:
                # Принудительное обновление с API
                app.weather_service.fetch_weather()
                logger.debug("Weather data updated from API")
            except Exception as e:
                logger.error(f"Error updating weather: {e}")

    def update_sensors(self, *args):
        """Обновление показаний датчиков"""
        app = App.get_running_app()
        if hasattr(app, 'sensor_service') and app.sensor_service:
            try:
                app.sensor_service.update_readings()
                self.sensor_available = app.sensor_service.sensor_available
                self.using_mock_sensors = getattr(app.sensor_service, 'using_mock_sensors', True)
                logger.debug("Sensor data updated")
            except Exception as e:
                logger.error(f"Error updating sensors: {e}")
                self.sensor_available = False
                self.using_mock_sensors = True
        else:
            self.sensor_available = False
            self.using_mock_sensors = True

    def update_display(self, *args):
        """Обновление отображения данных"""
        app = App.get_running_app()
        
        # Обновляем погоду
        if hasattr(app, 'weather_service') and app.weather_service:
            try:
                weather = app.weather_service.get_weather()
                
                # Текущая погода
                current = weather.get("current", {})
                if current:
                    temp = current.get('temperature', 0)
                    self.current_temp = f"{temp:.1f}°C"
                    self.current_condition = current.get('condition', 'Unknown')
                    precip = current.get('precipitation_probability', 0)
                    self.current_precipitation = f"Rain: {precip}%"
                
                # Недельный прогноз
                self.weekly_forecast = weather.get("weekly_forecast", [])
                
                # Обновляем виджет прогноза
                self.update_weekly_forecast()
                
            except Exception as e:
                logger.error(f"Error updating weather display: {e}")
                self.current_temp = "Error"
                self.current_condition = "Weather service error"
                self.current_precipitation = "Rain: --%"
        
        # ИЗМЕНЕНО: Обновляем датчики с новой логикой форматирования
        if hasattr(app, 'sensor_service') and app.sensor_service:
            try:
                sensors = app.sensor_service.get_readings()
                
                temp_value = sensors.get('temperature', 0)
                humidity_value = sensors.get('humidity', 0)
                co2_value = sensors.get('co2', 0)
                tvoc_value = sensors.get('tvoc', 0)
                air_quality = sensors.get('air_quality', 'Unknown')
                
                # ИЗМЕНЕНО: Новый формат строки без объединения цветов
                self.sensor_temp_humidity = f"Room: {temp_value:.1f}°C, Humidity: {humidity_value:.0f}%"
                self.sensor_co2_tvoc = f"CO2: {co2_value} ppm, TVOC: {tvoc_value} ppb"
                self.sensor_air_quality = f"Air Quality: {air_quality}"
                
            except Exception as e:
                logger.error(f"Error updating sensor display: {e}")
                self.sensor_temp_humidity = "Room: --°C, Humidity: --%"
                self.sensor_co2_tvoc = "CO2: -- ppm, TVOC: -- ppb"
                self.sensor_air_quality = "Air Quality: Unknown"
        else:
            # Если сервис датчиков недоступен
            self.sensor_temp_humidity = "Room: --°C, Humidity: --%"
            self.sensor_co2_tvoc = "CO2: -- ppm, TVOC: -- ppb"
            self.sensor_air_quality = "Air Quality: Unknown"

    def update_weekly_forecast(self):
        """Обновление виджета недельного прогноза"""
        if not hasattr(self, 'ids') or 'weekly_forecast_container' not in self.ids:
            return
            
        container = self.ids.weekly_forecast_container
        
        try:
            # Очищаем предыдущие виджеты
            container.clear_widgets()
            
            if self.weekly_forecast:
                # Добавляем дни недели
                for day_data in self.weekly_forecast:
                    day_item = DayForecastItem(day_data)
                    container.add_widget(day_item)
                
                # Добавляем отступ для прокрутки если нужно
                if len(self.weekly_forecast) < 7:
                    padding_height = (7 - len(self.weekly_forecast)) * dp(32)
                    padding = BoxLayout(size_hint_y=None, height=padding_height)
                    container.add_widget(padding)
            else:
                # Нет данных прогноза
                tm = self.get_theme_manager()
                
                no_data_label = Label(
                    text="No weekly forecast available",
                    font_name=tm.get_font("main") if tm else "",
                    font_size="18sp",
                    halign="center",
                    valign="center",
                    color=tm.get_rgba("text_secondary") if tm else [0.7, 0.7, 0.7, 1],
                    size_hint_y=None,
                    height=dp(80)
                )
                container.add_widget(no_data_label)
                
                # Добавляем отступ
                padding = BoxLayout(size_hint_y=None, height=dp(200))
                container.add_widget(padding)
            
        except Exception as e:
            logger.error(f"Error updating weekly forecast: {e}")

    def get_temperature_color(self, temp_value):
        """Получить цвет для температуры в зависимости от значения"""
        tm = self.get_theme_manager()
        
        if temp_value > 23:
            return [1, 0.6, 0, 1]  # Оранжевый для жаркой погоды
        elif temp_value < 18:
            return [0.2, 0.6, 1, 1]  # Синий для холодной погоды
        else:
            return tm.get_rgba("primary") if tm else [1, 1, 1, 1]

    def get_humidity_color(self, humidity_value):
        """Получить цвет для влажности - ДОБАВЛЕНО"""
        if humidity_value < 30:
            return [1, 0.2, 0.2, 1]  # Красный если меньше 30%
        elif humidity_value <= 40:
            return [1, 1, 1, 1]      # Белый от 30% до 40%
        else:
            return [0.2, 0.8, 0.2, 1]  # Зеленый если больше 40%

    def set_temp_color(self, widget, temp_str):
        """Установка цвета температуры в зависимости от значения"""
        try:
            # Извлекаем числовое значение температуры
            temp_value = float(temp_str.split('°')[0])
            widget.color = self.get_temperature_color(temp_value)
        except (ValueError, IndexError):
            # Если не удается распарсить температуру, используем стандартный цвет
            tm = self.get_theme_manager()
            widget.color = tm.get_rgba("text") if tm else [1, 1, 1, 1]

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов - ОБНОВЛЕНО"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return

        # Список виджетов для обновления темы
        widgets_to_update = [
            "current_temp_label", "current_condition_label", "current_precipitation_label",
            "sensor_temp_humidity_label", "sensor_co2_tvoc_label", 
            "sensor_air_quality_label"
        ]
        
        for widget_id in widgets_to_update:
            if hasattr(self, 'ids') and widget_id in self.ids:
                widget = self.ids[widget_id]
                
                # Обновляем шрифт
                if hasattr(widget, 'font_name'):
                    widget.font_name = tm.get_font("main")
                    
                # ИЗМЕНЕНО: Обновляем цвет текста с новой логикой для датчиков температуры и влажности
                if hasattr(widget, 'color'):
                    if widget_id == "current_temp_label":
                        # Применяем цветовую логику для температуры погоды
                        self.set_temp_color(widget, self.current_temp)
                    elif widget_id == "sensor_temp_humidity_label":
                        # НОВАЯ ЛОГИКА: Применяем обычный цвет, разбор по частям делается в KV
                        widget.color = tm.get_rgba("text")
                    elif widget_id == "current_condition_label":
                        widget.color = tm.get_rgba("text")
                    elif widget_id == "current_precipitation_label":
                        widget.color = tm.get_rgba("text_secondary")
                    elif widget_id == "sensor_co2_tvoc_label":
                        widget.color = tm.get_rgba("primary")
                    elif widget_id == "sensor_air_quality_label":
                        widget.color = tm.get_rgba("primary")
                    else:
                        widget.color = tm.get_rgba("text")
        
        # Обновляем прогноз
        Clock.schedule_once(lambda dt: self.update_weekly_forecast(), 0.1)

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        # Можно добавить локализацию заголовков
        pass

    def force_refresh(self):
        """Принудительное обновление всех данных"""
        logger.info("Manual weather refresh requested")
        self.update_all()