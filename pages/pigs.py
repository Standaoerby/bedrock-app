from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ColorProperty, StringProperty
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.app import App
from kivy.metrics import dp
from app.event_bus import event_bus
from app.logger import app_logger as logger
import os


class CustomProgressBar(Widget):
    """Кастомный прогресс бар для отображения состояния питомцев"""
    
    value = NumericProperty(50)  # Значение от 0 до 100
    bar_color = ColorProperty([0, 0.6, 0.8, 1])  # Цвет полосы
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.update_canvas)
        self.bind(pos=self.update_canvas)
        self.bind(value=self.update_canvas)
        self.bind(bar_color=self.update_canvas)  # ДОБАВЛЕНО: привязка к изменению цвета
        
        # Инициализация canvas
        with self.canvas:
            # Фон прогресс бара
            self.bg_color = Color(0.2, 0.2, 0.2, 0.6)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Заполнение прогресс бара
            self.fg_color = Color(*self.bar_color)
            self.fg_rect = Rectangle(pos=self.pos, size=(0, 0))
    
    def update_canvas(self, *args):
        """Обновление отображения прогресс бара"""
        if not self.canvas:
            return
            
        # Обновляем фон
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        
        # Обновляем заполнение на основе значения
        self.fg_color.rgba = self.bar_color
        self.fg_rect.pos = self.pos
        progress_width = self.width * (self.value / 100)
        self.fg_rect.size = (progress_width, self.height)


class PigsScreen(Screen):
    """Экран ухода за питомцами"""
    
    # Значения прогресс баров
    water_value = NumericProperty(100)
    food_value = NumericProperty(100)
    clean_value = NumericProperty(100)
    
    # Общий статус
    overall_status = NumericProperty(100)
    status_text = StringProperty("Perfect!")
    current_image = StringProperty("pigs_1.png")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("theme_changed", self.refresh_theme)
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_force_refresh", self.refresh_theme)
        # События для обновлений
        self._update_events = []

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering PigsScreen")
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
        logger.warning("ThemeManager not available in PigsScreen")
        return None

    def get_current_theme_variant(self):
        """ДОБАВЛЕНО: Получение текущего варианта темы"""
        app = App.get_running_app()
        if hasattr(app, 'user_config') and app.user_config:
            return app.user_config.get("variant", "light")
        return "light"

    def get_progress_bar_colors(self):
        """ДОБАВЛЕНО: Получение цветов прогресс-баров в зависимости от темы"""
        variant = self.get_current_theme_variant()
        
        if variant == "dark":
            # Темные цвета для темной темы
            return {
                "water": [0.1, 0.4, 0.7, 0.8],   # Темно-синий для воды
                "food": [0.7, 0.4, 0.1, 0.8],    # Темно-оранжевый для еды
                "clean": [0.1, 0.6, 0.1, 0.8]    # Темно-зеленый для уборки
            }
        else:
            # Светлые цвета для светлой темы
            return {
                "water": [0.2, 0.6, 1, 0.8],     # Голубой для воды
                "food": [1, 0.6, 0.2, 0.8],      # Оранжевый для еды
                "clean": [0.2, 0.8, 0.2, 0.8]    # Зеленый для уборки
            }

    def start_updates(self):
        """Запуск периодических обновлений"""
        self._update_events = [
            # Обновляем состояние каждые 5 минут
            Clock.schedule_interval(lambda dt: self.update_all_data(), 300),
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        for event in self._update_events:
            event.cancel()
        self._update_events = []

    def update_all_data(self, *args):
        """Полное обновление всех данных"""
        app = App.get_running_app()
        
        # Получаем данные от сервиса
        if hasattr(app, 'pigs_service') and app.pigs_service:
            try:
                # Получаем значения от сервиса
                values, overall = app.pigs_service.get_all_values()
                
                # Обновляем значения прогресс баров
                self.water_value = values.get("water", 50)
                self.food_value = values.get("food", 50)
                self.clean_value = values.get("clean", 50)
                
                # Обновляем общий статус
                self.overall_status = int(overall * 100)
                
                # Обновляем текст статуса
                self.update_status_text()
                
                # Обновляем изображение
                self.update_pig_image()
                
                # Обновляем прогресс бары в интерфейсе
                self.update_progress_bars()
                
                logger.debug(f"Pigs status updated: Water={self.water_value:.1f}, Food={self.food_value:.1f}, Clean={self.clean_value:.1f}, Overall={self.overall_status}%")
                
            except Exception as e:
                logger.error(f"Error updating pigs data: {e}")
                # Устанавливаем значения по умолчанию
                self._set_default_values()
        else:
            # Если сервис недоступен, используем тестовые данные
            logger.warning("PigsService not available, using mock data")
            self._set_default_values()

    def _set_default_values(self):
        """Установка значений по умолчанию"""
        self.water_value = 75
        self.food_value = 60
        self.clean_value = 85
        self.overall_status = 73
        self.status_text = "Mock data"
        self.update_pig_image()
        self.update_progress_bars()

    def update_status_text(self):
        """Обновление текста статуса на основе общего процента"""
        app = App.get_running_app()
        
        if hasattr(app, 'localizer'):
            if self.overall_status >= 90:
                self.status_text = app.localizer.tr("pigs_status_perfect", "Perfect! 🐷✨")
            elif self.overall_status >= 75:
                self.status_text = app.localizer.tr("pigs_status_happy", "Happy 🐷😊")
            elif self.overall_status >= 50:
                self.status_text = app.localizer.tr("pigs_status_ok", "OK 🐷😐")
            elif self.overall_status >= 25:
                self.status_text = app.localizer.tr("pigs_status_needs_care", "Needs care 🐷😟")
            else:
                self.status_text = app.localizer.tr("pigs_status_critical", "Critical! 🐷😰")
        else:
            # Fallback без локализации
            if self.overall_status >= 90:
                self.status_text = "Perfect! 🐷✨"
            elif self.overall_status >= 75:
                self.status_text = "Happy 🐷😊"
            elif self.overall_status >= 50:
                self.status_text = "OK 🐷😐"
            elif self.overall_status >= 25:
                self.status_text = "Needs care 🐷😟"
            else:
                self.status_text = "Critical! 🐷😰"

    def update_pig_image(self):
        """Обновление изображения питомцев на основе статуса"""
        if self.overall_status >= 85:
            self.current_image = "pigs_1.png"  # Счастливые
        elif self.overall_status >= 60:
            self.current_image = "pigs_2.png"  # Нормальные
        elif self.overall_status >= 30:
            self.current_image = "pigs_3.png"  # Грустные
        else:
            self.current_image = "pigs_4.png"  # Очень грустные
        
        # Обновляем изображение в интерфейсе
        if hasattr(self, 'ids') and 'pigs_image' in self.ids:
            image_path = self.get_pig_image_path()
            if os.path.exists(image_path):
                self.ids.pigs_image.source = image_path
            else:
                logger.warning(f"Pig image not found: {image_path}")

    def get_pig_image_path(self):
        """Получить полный путь к изображению питомцев"""
        return os.path.join("assets", "images", self.current_image)

    def update_progress_bars(self):
        """Обновление прогресс баров в интерфейсе"""
        if not hasattr(self, 'ids'):
            return
            
        # ИСПРАВЛЕНО: Получаем цвета для текущей темы
        colors = self.get_progress_bar_colors()
        
        # Обновляем значения и цвета прогресс баров
        if 'water_bar' in self.ids:
            self.ids.water_bar.value = self.water_value
            self.ids.water_bar.bar_color = colors["water"]
        if 'food_bar' in self.ids:
            self.ids.food_bar.value = self.food_value
            self.ids.food_bar.bar_color = colors["food"]
        if 'clean_bar' in self.ids:
            self.ids.clean_bar.value = self.clean_value
            self.ids.clean_bar.bar_color = colors["clean"]

    def reset_bar(self, bar_type):
        """Сброс определённой полосы (кормление/поение/уборка)"""
        try:
            app = App.get_running_app()
            
            # Воспроизводим звук подтверждения
            tm = self.get_theme_manager()
            if hasattr(app, 'audio_service') and app.audio_service and tm:
                sound_file = tm.get_sound("confirm")
                if sound_file:
                    app.audio_service.play_async(sound_file)
            
            # Сбрасываем полосу в сервисе
            if hasattr(app, 'pigs_service') and app.pigs_service:
                success = app.pigs_service.reset_bar(bar_type)
                if success:
                    logger.info(f"Reset {bar_type} bar")
                else:
                    logger.error(f"Failed to reset {bar_type} bar")
            else:
                # Если сервис недоступен, сбрасываем локально
                logger.warning("PigsService not available, resetting locally")
                if bar_type == "water":
                    self.water_value = 100
                elif bar_type == "food":
                    self.food_value = 100
                elif bar_type == "clean":
                    self.clean_value = 100
                
                # Пересчитываем общий статус
                avg_value = (self.water_value + self.food_value + self.clean_value) / 3
                self.overall_status = int(avg_value)
                self.update_status_text()
                self.update_pig_image()
                self.update_progress_bars()
            
            # Немедленно обновляем данные из сервиса
            Clock.schedule_once(lambda dt: self.update_all_data(), 0.1)
            
        except Exception as e:
            logger.error(f"Error resetting {bar_type} bar: {e}")
            # Воспроизводим звук ошибки
            app = App.get_running_app()
            tm = self.get_theme_manager()
            if hasattr(app, 'audio_service') and app.audio_service and tm:
                sound_file = tm.get_sound("error")
                if sound_file:
                    app.audio_service.play_async(sound_file)

    def refresh_theme(self, *args):
        """Обновление темы для всех элементов"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return

        # Список виджетов для обновления темы
        widgets_to_update = [
            "water_label", "food_label", "clean_label", 
            "water_button", "food_button", "clean_button"
        ]
        
        for widget_id in widgets_to_update:
            if hasattr(self, 'ids') and widget_id in self.ids:
                widget = self.ids[widget_id]
                
                # Обновляем шрифт
                if hasattr(widget, 'font_name'):
                    widget.font_name = tm.get_font("main")
                    
                # Обновляем цвет текста
                if hasattr(widget, 'color'):
                    if "label" in widget_id:
                        widget.color = tm.get_rgba("text")
                    else:
                        widget.color = tm.get_rgba("text")
                
                # Обновляем фон кнопок
                if hasattr(widget, 'background_normal'):
                    widget.background_normal = tm.get_image("button_bg")
                    widget.background_down = tm.get_image("button_bg_active")

        # ИСПРАВЛЕНО: Обновляем прогресс бары с цветами для текущей темы
        self.update_progress_bars()

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
            
        # Обновляем локализованные тексты
        if hasattr(self, 'ids'):
            if 'water_label' in self.ids:
                self.ids.water_label.text = app.localizer.tr("water", "Water")
            if 'food_label' in self.ids:
                self.ids.food_label.text = app.localizer.tr("food", "Food")
            if 'clean_label' in self.ids:
                self.ids.clean_label.text = app.localizer.tr("cleaning", "Cleaning")
            
            # Обновляем кнопки
            for btn_id in ['water_button', 'food_button', 'clean_button']:
                if btn_id in self.ids:
                    self.ids[btn_id].text = app.localizer.tr("done", "Done")
        
        # Обновляем текст статуса
        self.update_status_text()