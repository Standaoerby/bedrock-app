from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from app.event_bus import event_bus
from datetime import datetime, timedelta
from app.logger import app_logger as logger


# Дни недели на английском (сокращенно)
DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ScheduleScreen(Screen):
    """Экран расписания занятий"""
    
    # Свойства для отображения
    current_week_str = StringProperty("")
    today_day = StringProperty("")
    schedule_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
        self._update_events = []

    def on_pre_enter(self, *args):
        """Вызывается при входе на экран"""
        logger.info("Entering ScheduleScreen")
        self.refresh_theme()
        self.refresh_text()
        self.update_schedule_data()
        self.create_schedule_widgets()
        self.start_updates()

    def on_pre_leave(self, *args):
        """Вызывается при выходе с экрана"""
        self.stop_updates()

    def start_updates(self):
        """Запуск периодических обновлений"""
        # Обновляем текущий день раз в час
        self._update_events = [
            Clock.schedule_interval(lambda dt: self.update_current_day(), 3600),
        ]

    def stop_updates(self):
        """Остановка периодических обновлений"""
        for event in self._update_events:
            event.cancel()
        self._update_events = []

    def update_schedule_data(self):
        """Обновление данных расписания"""
        app = App.get_running_app()
        
        # Определяем текущий день недели
        today = datetime.now()
        current_day = DAYS_EN[today.weekday()]
        self.today_day = current_day
        
        # Формируем строку недели
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        self.current_week_str = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
        
        # Получаем расписание от сервиса
        schedule = {}
        if hasattr(app, 'schedule_service') and app.schedule_service:
            try:
                schedule = app.schedule_service.get_schedule()
                logger.debug("Schedule loaded from service")
            except Exception as e:
                logger.error(f"Error loading schedule: {e}")
                schedule = self._get_default_schedule()
        else:
            logger.warning("ScheduleService not available, using default schedule")
            schedule = self._get_default_schedule()
        
        # Подготавливаем данные для отображения
        self.schedule_data = []
        for day in DAYS_EN[:5]:  # Только рабочие дни
            day_schedule = schedule.get(day, [])
            self.schedule_data.append({
                "day": day,
                "is_today": day == current_day,
                "lessons": day_schedule
            })

    def _get_default_schedule(self):
        """Получение расписания по умолчанию"""
        return {
            "Mon": [
                {"time": "09:00", "subject": "Math", "room": "101"},
                {"time": "10:00", "subject": "English", "room": "102"},
                {"time": "11:00", "subject": "Science", "room": "103"},
                {"time": "12:00", "subject": "History", "room": "104"},
            ],
            "Tue": [
                {"time": "09:00", "subject": "Physics", "room": "105"},
                {"time": "10:00", "subject": "Chemistry", "room": "106"},
                {"time": "11:00", "subject": "Math", "room": "101"},
                {"time": "12:00", "subject": "Art", "room": "107"},
            ],
            "Wed": [
                {"time": "09:00", "subject": "English", "room": "102"},
                {"time": "10:00", "subject": "Geography", "room": "108"},
                {"time": "11:00", "subject": "PE", "room": "Gym"},
                {"time": "12:00", "subject": "Music", "room": "109"},
            ],
            "Thu": [
                {"time": "09:00", "subject": "Math", "room": "101"},
                {"time": "10:00", "subject": "Science", "room": "103"},
                {"time": "11:00", "subject": "History", "room": "104"},
                {"time": "12:00", "subject": "English", "room": "102"},
            ],
            "Fri": [
                {"time": "09:00", "subject": "Chemistry", "room": "106"},
                {"time": "10:00", "subject": "Physics", "room": "105"},
                {"time": "11:00", "subject": "Art", "room": "107"},
                {"time": "12:00", "subject": "Free Period", "room": ""},
            ],
            "Sat": [],
            "Sun": []
        }

    def update_current_day(self):
        """Обновление текущего дня"""
        self.update_schedule_data()
        self.create_schedule_widgets()

    def create_schedule_widgets(self):
        """Создание виджетов расписания"""
        if not hasattr(self, 'ids') or 'schedule_container' not in self.ids:
            return
            
        container = self.ids.schedule_container
        container.clear_widgets()
        
        app = App.get_running_app()
        tm = app.theme_manager if hasattr(app, 'theme_manager') else None
        
        # Создаем колонки для каждого дня
        for day_data in self.schedule_data:
            day_column = self.create_day_column(day_data, tm)
            container.add_widget(day_column)

    def create_day_column(self, day_data, theme_manager):
        """Создание колонки для одного дня"""
        day = day_data["day"]
        is_today = day_data["is_today"]
        lessons = day_data["lessons"]
        
        # Основной контейнер колонки
        column = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_x=0.2  # 5 колонок
        )
        
        # Заголовок дня
        app = App.get_running_app()
        if hasattr(app, 'localizer'):
            # Получаем локализованное название дня
            day_names = {
                "Mon": app.localizer.tr("day_monday", "Mon"),
                "Tue": app.localizer.tr("day_tuesday", "Tue"),
                "Wed": app.localizer.tr("day_wednesday", "Wed"),
                "Thu": app.localizer.tr("day_thursday", "Thu"),
                "Fri": app.localizer.tr("day_friday", "Fri"),
            }
            day_text = day_names.get(day, day)
        else:
            day_text = day
        
        header = Label(
            text=day_text,
            font_size='18sp',
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("primary") if (theme_manager and is_today) else (theme_manager.get_rgba("text") if theme_manager else [1, 1, 1, 1]),
            size_hint_y=None,
            height=dp(32),
            halign='center',
            bold=is_today
        )
        column.add_widget(header)
        
        # Контейнер для уроков
        lessons_container = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=[dp(8), dp(8)]
        )
        
        if not lessons:
            # Свободный день
            free_text = app.localizer.tr("free_day", "Free Day") if hasattr(app, 'localizer') else "Free Day"
            free_label = Label(
                text=free_text,
                font_size='14sp',
                font_name=theme_manager.get_font("main") if theme_manager else "",
                color=theme_manager.get_rgba("text_secondary") if theme_manager else [0.7, 0.7, 0.7, 1],
                size_hint_y=None,
                height=dp(32),
                halign='center',
                italic=True
            )
            lessons_container.add_widget(free_label)
        else:
            # Добавляем уроки
            for lesson in lessons:
                lesson_widget = self.create_lesson_widget(lesson, theme_manager, is_today)
                lessons_container.add_widget(lesson_widget)
        
        column.add_widget(lessons_container)
        return column

    def create_lesson_widget(self, lesson, theme_manager, is_today):
        """Создание виджета урока"""
        container = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            size_hint_y=None,
            height=dp(56),  # Кратно 8
            padding=[dp(4), dp(4)]
        )
        
        # Время
        time_label = Label(
            text=lesson.get("time", ""),
            font_size='12sp',
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("primary") if (theme_manager and is_today) else (theme_manager.get_rgba("text_secondary") if theme_manager else [0.7, 0.7, 0.7, 1]),
            size_hint_y=None,
            height=dp(16),
            halign='center'
        )
        container.add_widget(time_label)
        
        # Предмет
        subject_label = Label(
            text=lesson.get("subject", ""),
            font_size='14sp',
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("text") if theme_manager else [1, 1, 1, 1],
            size_hint_y=None,
            height=dp(24),
            halign='center',
            text_size=(dp(120), None),
            shorten=True,
            shorten_from='right'
        )
        container.add_widget(subject_label)
        
        # Кабинет
        room = lesson.get("room", "")
        if room:
            room_label = Label(
                text=room,
                font_size='10sp',
                font_name=theme_manager.get_font("main") if theme_manager else "",
                color=theme_manager.get_rgba("text_secondary") if theme_manager else [0.7, 0.7, 0.7, 1],
                size_hint_y=None,
                height=dp(16),
                halign='center'
            )
            container.add_widget(room_label)
        
        return container

    def refresh_theme(self, *args):
        """Обновление темы"""
        app = App.get_running_app()
        if not hasattr(app, 'theme_manager'):
            return
            
        tm = app.theme_manager

        # Обновляем заголовки
        if hasattr(self, 'ids'):
            if 'title_label' in self.ids:
                self.ids.title_label.font_name = tm.get_font("title")
                self.ids.title_label.color = tm.get_rgba("primary")
            if 'week_label' in self.ids:
                self.ids.week_label.font_name = tm.get_font("main")
                self.ids.week_label.color = tm.get_rgba("text")
            if 'today_highlight_label' in self.ids:
                self.ids.today_highlight_label.font_name = tm.get_font("main")
                self.ids.today_highlight_label.color = tm.get_rgba("primary")
        
        # Пересоздаем виджеты с новой темой
        if hasattr(self, 'ids'):
            self.create_schedule_widgets()

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        app = App.get_running_app()
        if not hasattr(app, 'localizer'):
            return
            
        # Обновляем заголовок
        if hasattr(self, 'ids') and 'title_label' in self.ids:
            self.ids.title_label.text = app.localizer.tr("schedule_title", "School Schedule")
            
        # Пересоздаем виджеты с новой локализацией
        self.create_schedule_widgets()