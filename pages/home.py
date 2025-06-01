from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.animation import Animation
from app.event_bus import event_bus
from datetime import datetime

class HomeScreen(Screen):
    current_alarm_time = StringProperty("--:--")
    alarm_active = BooleanProperty(False)
    weather_now_str = StringProperty("--°C")
    weather_5h_str = StringProperty("--°C")
    weather_trend_arrow = StringProperty("")
    notification_text = StringProperty("")
    current_date = StringProperty("")
    clock_time = StringProperty("--:--")
    
    alarm_snooze_active = BooleanProperty(False)
    alarm_snooze_time = StringProperty("")
    
    notification_scroll_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
        event_bus.subscribe("alarm_snoozed", self.on_alarm_snoozed)
        event_bus.subscribe("alarm_dismissed", self.on_alarm_dismissed)
        event_bus.subscribe("alarm_triggered", self.on_alarm_triggered)
        
        self._clock_event = None
        self._update_events = []
        self._scroll_animation = None

    def on_pre_enter(self, *args):
        # ИСПРАВЛЕНО: сначала обновляем данные, потом тему
        self.update_all()
        self.refresh_text()
        self.refresh_theme()
        self.start_updates()

    def on_pre_leave(self, *args):
        self.stop_updates()

    def start_updates(self):
        if not self._clock_event:
            self._clock_event = Clock.schedule_interval(self.update_clock, 1)
            
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_date(), 60),
            Clock.schedule_interval(lambda dt: self.update_alarm(), 30),
            Clock.schedule_interval(lambda dt: self.update_weather(), 600),
            Clock.schedule_interval(lambda dt: self.update_notification(), 15),
        ]

    def stop_updates(self):
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None
            
        for event in self._update_events:
            event.cancel()
        self._update_events = []
        
        if self._scroll_animation:
            self._scroll_animation.cancel(self)

    def update_all(self):
        self.update_date()
        self.update_clock()
        self.update_alarm()
        self.update_weather()
        self.update_notification()

    def update_clock(self, *args):
        now = datetime.now()
        self.clock_time = now.strftime("%H:%M")
        
        if hasattr(self, 'ids') and 'clock_shadow1' in self.ids:
            self.ids.clock_shadow1.text = self.clock_time
            self.ids.clock_shadow2.text = self.clock_time
            self.ids.clock_shadow3.text = self.clock_time

    def update_date(self, *args):
        now = datetime.now()
        weekdays = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
            4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        months = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }
        
        weekday = weekdays[now.weekday()]
        month = months[now.month]
        self.current_date = f"{now.day} {month}, {weekday}"

    def update_alarm(self, *args):
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
        
        if hasattr(app, "alarm_clock") and app.alarm_clock:
            try:
                status = app.alarm_clock.get_status()
                self.alarm_snooze_active = status.get("is_snoozed", False)
                if self.alarm_snooze_active:
                    snooze_time = status.get("snooze_time", "")
                    self.alarm_snooze_time = f"Snooze: {snooze_time}"
                else:
                    self.alarm_snooze_time = ""
            except Exception:
                self.alarm_snooze_active = False
                self.alarm_snooze_time = ""
        else:
            self.alarm_snooze_active = False
            self.alarm_snooze_time = ""
        
        # ДОБАВЛЕНО: обновляем тему после изменения состояния
        Clock.schedule_once(lambda dt: self.refresh_theme(), 0.1)

    def toggle_alarm(self):
        app = App.get_running_app()
        if hasattr(app, "alarm_service"):
            alarm = app.alarm_service.get_alarm()
            if alarm:
                alarm["enabled"] = not alarm.get("enabled", False)
                app.alarm_service.set_alarm(alarm)
                
                self.update_alarm()
                
                if hasattr(app, "audio_service"):
                    sound = "confirm" if alarm["enabled"] else "click"
                    sound_file = app.theme_manager.get_sound(sound)
                    if sound_file:
                        app.audio_service.play(sound_file)

    def update_weather(self, *args):
        app = App.get_running_app()
        if hasattr(app, "weather_service"):
            try:
                weather = app.weather_service.get_weather()
                
                current = weather.get("current", {})
                if current:
                    temp = current.get("temperature", "--")
                    condition = current.get("condition", "")
                    if len(condition) > 30:
                        condition = condition[:9] + "..."
                    self.weather_now_str = f"{temp}°C & {condition}"
                else:
                    self.weather_now_str = "--°C"
                
                forecast_5h = weather.get("forecast_5h", {})
                if forecast_5h and forecast_5h.get("temperature") is not None:
                    temp_5h = forecast_5h.get("temperature", "--")
                    condition_5h = forecast_5h.get("condition", "")
                    if len(condition_5h) > 30:
                        condition_5h = condition_5h[:9] + "..."
                    self.weather_5h_str = f"{temp_5h}°C & {condition_5h}"
                    
                    try:
                        temp_now = float(current.get("temperature", 0))
                        temp_5h_val = float(temp_5h)
                        
                        if temp_5h_val > temp_now + 2:
                            self.weather_trend_arrow = "↗↗"
                        elif temp_5h_val > temp_now + 0.5:
                            self.weather_trend_arrow = "↗"
                        elif temp_5h_val < temp_now - 2:
                            self.weather_trend_arrow = "↘↘"
                        elif temp_5h_val < temp_now - 0.5:
                            self.weather_trend_arrow = "↘"
                        else:
                            self.weather_trend_arrow = "→"
                    except (ValueError, TypeError):
                        self.weather_trend_arrow = "→"
                else:
                    self.weather_5h_str = "--°C"
                    self.weather_trend_arrow = ""
                    
            except Exception as e:
                print(f"[HomeScreen] Weather error: {e}")
                self.weather_now_str = "Weather Error"
                self.weather_5h_str = "--°C"
                self.weather_trend_arrow = ""
        else:
            self.weather_now_str = "No Weather Service"
            self.weather_5h_str = "--°C"
            self.weather_trend_arrow = ""

    def update_notification(self, *args):
        app = App.get_running_app()
        
        if self.alarm_snooze_active and self.alarm_snooze_time:
            self.notification_text = self.alarm_snooze_time
            self.start_text_scroll(self.notification_text)
            return
        
        if hasattr(app, "notification_service"):
            try:
                unread = app.notification_service.list_unread()
                if unread:
                    latest = unread[-1]
                    text = latest.get("text", "")
                    self.notification_text = text
                    self.start_text_scroll(text)
                else:
                    self.notification_text = "No new notifications"
                    self.start_text_scroll(self.notification_text)
            except Exception as e:
                print(f"[HomeScreen] Notification error: {e}")
                self.notification_text = ""
        else:
            self.notification_text = "Notification service unavailable"
            self.start_text_scroll(self.notification_text)

    def start_text_scroll(self, text):
        if hasattr(self, '_scroll_animation') and self._scroll_animation:
            self._scroll_animation.cancel(self)

        if not hasattr(self, 'ids') or 'notification_container' not in self.ids or 'notification_text_label' not in self.ids:
            return

        container = self.ids.notification_container
        label = self.ids.notification_text_label

        def _launch(dt):
            label_width = label.texture_size[0]
            container_width = container.width

            if label_width <= container_width:
                self.notification_scroll_x = 0
                return

            self.notification_scroll_x = container_width
            end_x = -label_width
            duration = max((container_width + label_width) / 50, 3)

            def restart(*args):
                self.start_text_scroll(self.notification_text)

            self._scroll_animation = Animation(notification_scroll_x=end_x, duration=duration, t='linear')
            self._scroll_animation.bind(on_complete=restart)
            self._scroll_animation.start(self)

        Clock.schedule_once(_launch, 0.05)

    def on_alarm_snoozed(self, snooze_time=None, **kwargs):
        if snooze_time:
            self.alarm_snooze_active = True
            self.alarm_snooze_time = f"Snooze: {snooze_time.strftime('%H:%M')}"
            self.update_notification()

    def on_alarm_dismissed(self, **kwargs):
        self.alarm_snooze_active = False
        self.alarm_snooze_time = ""
        self.update_notification()

    def on_alarm_triggered(self, **kwargs):
        pass

    def refresh_theme(self, *args):
        app = App.get_running_app()
        if not hasattr(app, 'theme_manager'):
            return
            
        tm = app.theme_manager

        widgets_to_update = [
            "date_label", "alarm_time_label", "alarm_toggle_btn",
            "clock_label", "clock_shadow1", "clock_shadow2", "clock_shadow3",
            "weather_now_label", "weather_5h_label", "weather_trend_label", 
            "notification_text_label"
        ]
        
        for widget_id in widgets_to_update:
            if hasattr(self, 'ids') and widget_id in self.ids:
                widget = self.ids[widget_id]
                
                if hasattr(widget, 'font_name'):
                    widget.font_name = tm.get_font("main")
                    
                if hasattr(widget, 'color'):
                    if "clock" in widget_id and "shadow" not in widget_id:
                        widget.color = tm.get_rgba("clock_main")
                    elif "shadow" in widget_id:
                        pass
                    elif widget_id == "alarm_time_label":
                        # ИСПРАВЛЕНО: правильная проверка состояния будильника
                        if self.alarm_snooze_active or self.alarm_active:
                            widget.color = tm.get_rgba("text_accent")
                        else:
                            widget.color = tm.get_rgba("text_inactive")
                    elif widget_id == "alarm_toggle_btn":
                        # ИСПРАВЛЕНО: правильная проверка состояния будильника
                        if self.alarm_snooze_active or self.alarm_active:
                            widget.color = tm.get_rgba("text_accent")
                        else:
                            widget.color = tm.get_rgba("text_inactive")
                    elif widget_id in ["weather_now_label", "weather_trend_label"]:
                        widget.color = tm.get_rgba("primary")
                    elif widget_id == "notification_text_label":
                        if self.alarm_snooze_active:
                            widget.color = tm.get_rgba("text_accent")
                        else:
                            widget.color = tm.get_rgba("text")
                    else:
                        widget.color = tm.get_rgba("text")
                
                if hasattr(widget, 'background_normal'):
                    widget.background_normal = tm.get_image("button_bg")
                    widget.background_down = tm.get_image("button_bg_active")

    def refresh_text(self, *args):
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
            
        self.update_date()