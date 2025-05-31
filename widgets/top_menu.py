from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.app import App
from app.event_bus import event_bus

class TopMenu(BoxLayout):
    current_page = StringProperty("home")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        event_bus.subscribe("language_changed", self.refresh_text)

    def on_kv_post(self, base_widget):
        self.refresh_text()

    def select(self, page_name):
        app = App.get_running_app()
        
        # Воспроизводим звук ДО смены экрана
        if hasattr(app, 'audio_service'):
            sound_file = app.theme_manager.get_sound("click")
            if sound_file:
                app.audio_service.play(sound_file)
        
        # Меняем экран
        if hasattr(app.root, "switch_screen"):
            app.root.switch_screen(page_name)

    def refresh_theme(self):
        app = App.get_running_app()
        self.canvas.ask_update()
        for btn in self.children:
            if hasattr(btn, 'background_normal'):
                btn.background_normal = app.theme_manager.get_image("menu_button_bg")
                btn.background_down = app.theme_manager.get_image("menu_button_bg_active")
                btn.color = app.theme_manager.get_rgba("menu_button_text")
                
    def refresh_text(self, *args):
        app = App.get_running_app()
        if "btn_home" in self.ids:
            self.ids.btn_home.text = app.localizer.t("menu_home")
        if "btn_alarm" in self.ids:
            self.ids.btn_alarm.text = app.localizer.t("menu_alarm")
        if "btn_schedule" in self.ids:
            self.ids.btn_schedule.text = app.localizer.t("menu_schedule")
        if "btn_weather" in self.ids:
            self.ids.btn_weather.text = app.localizer.t("menu_weather")
        if "btn_pigs" in self.ids:
            self.ids.btn_pigs.text = app.localizer.t("menu_pigs")
        if "btn_settings" in self.ids:
            self.ids.btn_settings.text = app.localizer.t("menu_settings")

