from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.animation import Animation
from app.event_bus import event_bus
from datetime import datetime

class HomeScreen(Screen):
    # Данные для отображения
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("--°C")
    weather_5h_str = StringProperty("--°C")
    weather_trend_arrow = StringProperty("")
    notification_text = StringProperty("")
    current_date = StringProperty("")
    clock_time = StringProperty("--:--")
    
    # Для бегущей строки
    notification_scroll_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
        self._clock_event = None
        self._update_events = []
        self._scroll_animation = None

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        self.refresh_theme()
        self.refresh_text()
        self.update_all()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    def start_updates(self):
        """Запуск периодических обновлений"""
        if not self._clock_event:
            # Часы обновляются каждую секунду
            self._clock_event = Clock.schedule_interval(self.update_clock, 1)
            
        # Другие обновления
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_date(), 60),      # Дата раз в минуту
            Clock.schedule_interval(lambda dt: self.update_alarm(), 30),     # Будильник раз в 30 сек
            Clock.schedule_interval(lambda dt: self.update_weather(), 600),  # Погода раз в 10 минут
            Clock.schedule_interval(lambda dt: self.update_notification(), 15), # Уведомления раз в 15 сек
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None
            
        for event in self._update_events:
            event.cancel()
        self._update_events = []
        
        # Останавливаем анимацию бегущей строки
        if self._scroll_animation:
            self._scroll_animation.cancel(self)

    def update_all(self):
        """Полное обновление всех данных"""
        self.update_date()
        self.update_clock()
        self.update_alarm()
        self.update_weather()
        self.update_notification()

    def update_clock(self, *args):
        """Обновление времени"""
        now = datetime.now()
        self.clock_time = now.strftime("%H:%M")
        
        # Обновляем тени (если нужно)
        if hasattr(self, 'ids') and 'clock_shadow1' in self.ids:
            self.ids.clock_shadow1.text = self.clock_time
            self.ids.clock_shadow2.text = self.clock_time
            self.ids.clock_shadow3.text = self.clock_time

    def update_date(self, *args):
        """Обновление даты"""
        now = datetime.now()
        # Русский формат даты
        weekdays = {
            0: "Monday",
            1: "Tuesday",
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday"
        }
        months = {
            1: "Jan",
            2: "Feb",
            3: "Mar",
            4: "Apr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Aug",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dec"
        }
        
        weekday = weekdays[now.weekday()]
        month = months[now.month]
        self.current_date = f"{now.day} {month}, {weekday}"

    def update_alarm(self, *args):
        """Обновление информации о будильнике"""
        app = App.get_running_app()
        if hasattr(app, "alarm_service"):
            alarm = app.alarm_service.get_alarm()
            if alarm:
                self.current_alarm_time = alarm.get("time", "--:--")
                self.alarm_active = alarm.get("enabled", False)
            else:
                self.current_alarm_time = "--:--"
                self.alarm_active = False
        else:
            self.current_alarm_time = "--:--"
            self.alarm_active = False

    def toggle_alarm(self):
        """Переключение состояния будильника"""
        app = App.get_running_app()
        if hasattr(app, "alarm_service"):
            alarm = app.alarm_service.get_alarm()
            if alarm:
                # Переключаем состояние
                alarm["enabled"] = not alarm.get("enabled", False)
                app.alarm_service.set_alarm(alarm)
                
                # Обновляем отображение
                self.update_alarm()
                
                # Звук подтверждения
                if hasattr(app, "audio_service"):
                    sound = "confirm" if alarm["enabled"] else "click"
                    sound_file = app.theme_manager.get_sound(sound)
                    if sound_file:
                        app.audio_service.play(sound_file)

    def update_weather(self, *args):
        """Обновление информации о погоде"""
        app = App.get_running_app()
        if hasattr(app, "weather_service"):
            try:
                weather = app.weather_service.get_weather()
                
                # Текущая погода
                current = weather.get("current", {})
                if current:
                    temp = current.get("temperature", "--")
                    condition = current.get("condition", "")
                    # Сокращаем длинные названия условий для компактности
                    if len(condition) > 30:
                        condition = condition[:9] + "..."
                    # ИЗМЕНЕНО: используем запятую вместо переноса строки
                    self.weather_now_str = f"{temp}°C & {condition}"
                else:
                    self.weather_now_str = "--°C"
                
                # Прогноз на 5 часов
                forecast_5h = weather.get("forecast_5h", {})
                if forecast_5h and forecast_5h.get("temperature") is not None:
                    temp_5h = forecast_5h.get("temperature", "--")
                    condition_5h = forecast_5h.get("condition", "")
                    if len(condition_5h) > 30:
                        condition_5h = condition_5h[:9] + "..."
                    # ИЗМЕНЕНО: используем запятую вместо переноса строки
                    self.weather_5h_str = f"{temp_5h}°C & {condition_5h}"
                    
                    # Стрелка тренда температуры
                    try:
                        temp_now = float(current.get("temperature", 0))
                        temp_5h_val = float(temp_5h)
                        
                        if temp_5h_val > temp_now + 2:
                            self.weather_trend_arrow = "↗↗"  # Значительное потепление
                        elif temp_5h_val > temp_now + 0.5:
                            self.weather_trend_arrow = "↗"   # Потепление
                        elif temp_5h_val < temp_now - 2:
                            self.weather_trend_arrow = "↘↘"  # Значительное похолодание
                        elif temp_5h_val < temp_now - 0.5:
                            self.weather_trend_arrow = "↘"   # Похолодание
                        else:
                            self.weather_trend_arrow = "→"   # Без изменений
                    except (ValueError, TypeError):
                        self.weather_trend_arrow = "→"
                else:
                    self.weather_5h_str = "--°C"
                    self.weather_trend_arrow = ""
                    
            except Exception as e:
                print(f"[HomeScreen] Ошибка обновления погоды: {e}")
                self.weather_now_str = "Ошибка погоды"
                self.weather_5h_str = "--°C"
                self.weather_trend_arrow = ""
        else:
            self.weather_now_str = "Нет сервиса погоды"
            self.weather_5h_str = "--°C"
            self.weather_trend_arrow = ""

    def update_notification(self, *args):
        """Обновление уведомлений"""
        app = App.get_running_app()
        if hasattr(app, "notification_service"):
            try:
                # Получаем последнее непрочитанное уведомление
                unread = app.notification_service.list_unread()
                if unread:
                    latest = unread[-1]  # Последнее
                    text = latest.get("text", "")
                    self.notification_text = text
                    # Запускаем бегущую строку только если текст длинный
                    self.start_text_scroll(text)
                else:
                    self.notification_text = "Нет новых уведомлений"
                    self.start_text_scroll(self.notification_text)
            except Exception as e:
                print(f"[HomeScreen] Ошибка обновления уведомлений: {e}")
                self.notification_text = ""
        else:
            self.notification_text = "Сервис уведомлений недоступен"
            self.start_text_scroll(self.notification_text)

    def start_text_scroll(self, text):
        # Остановить старую анимацию
        if hasattr(self, '_scroll_animation') and self._scroll_animation:
            self._scroll_animation.cancel(self)

        # Проверить наличие id
        if not hasattr(self, 'ids') or 'notification_container' not in self.ids or 'notification_text_label' not in self.ids:
            return

        container = self.ids.notification_container
        label = self.ids.notification_text_label

        # Размеры могут быть ещё не готовы — пересчитать в конце кадра
        def _launch(dt):
            label_width = label.texture_size[0]
            container_width = container.width

            # Если текст помещается — не скроллим, оставляем слева
            if label_width <= container_width:
                self.notification_scroll_x = 0
                return

            # Сдвигаем от правого края контейнера
            self.notification_scroll_x = container_width
            end_x = -label_width
            duration = max((container_width + label_width) / 50, 3)  # px/sec

            def restart(*args):
                self.start_text_scroll(self.notification_text)

            self._scroll_animation = Animation(notification_scroll_x=end_x, duration=duration, t='linear')
            self._scroll_animation.bind(on_complete=restart)
            self._scroll_animation.start(self)

        # Гарантируем пересчёт размеров после обновления текста
        from kivy.clock import Clock
        Clock.schedule_once(_launch, 0.05)




    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        app = App.get_running_app()
        if not hasattr(app, 'theme_manager'):
            return
            
        tm = app.theme_manager

        # Обновляем цвета и шрифты для всех элементов
        widgets_to_update = [
            "date_label", "alarm_time_label", "alarm_toggle_btn",
            "clock_label", "clock_shadow1", "clock_shadow2", "clock_shadow3",
            "weather_now_label", "weather_5h_label", "weather_trend_label", 
            "notification_text_label"
        ]
        
        for widget_id in widgets_to_update:
            if hasattr(self, 'ids') and widget_id in self.ids:
                widget = self.ids[widget_id]
                
                # Шрифт
                if hasattr(widget, 'font_name'):
                    widget.font_name = tm.get_font("main")
                    
                # Цвет текста
                if hasattr(widget, 'color'):
                    if "clock" in widget_id and "shadow" not in widget_id:
                        widget.color = tm.get_rgba("clock_main")
                    elif "shadow" in widget_id:
                        # Тени остаются чёрными с разной прозрачностью
                        pass
                    elif widget_id == "alarm_time_label":
                        widget.color = tm.get_rgba("primary") if self.alarm_active else tm.get_rgba("text")
                    elif widget_id in ["weather_now_label", "weather_trend_label"]:
                        widget.color = tm.get_rgba("primary")
                    else:
                        widget.color = tm.get_rgba("text")
                
                # Фон кнопок
                if hasattr(widget, 'background_normal'):
                    widget.background_normal = tm.get_image("button_bg")
                    widget.background_down = tm.get_image("button_bg_active")

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
            
        # Обновляем дату в соответствии с языком
        self.update_date()
        
        # Можно добавить больше локализации по мере необходимости