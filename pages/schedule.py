from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from app.event_bus import event_bus
from datetime import datetime, timedelta
from app.logger import app_logger as logger


# Дни недели на английском (сокращенно)
DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"]


class ScheduleScreen(Screen):
    """Экран расписания занятий"""
    
    # Свойства для отображения
    current_week_str = StringProperty("")
    schedule_data = ListProperty([])
    user_header = StringProperty("School Schedule")
    today_full_date = StringProperty("")
    next_weekend_text = StringProperty("Next weekend soon!")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Подписка на события
        event_bus.subscribe("language_changed", self.refresh_text)
        event_bus.subscribe("theme_changed", self.refresh_theme)
        self._update_events = []
        self._current_day = None

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

    def get_theme_manager(self):
        """Безопасное получение theme_manager"""
        app = App.get_running_app()
        if hasattr(app, 'theme_manager') and app.theme_manager:
            return app.theme_manager
        logger.warning("ThemeManager not available in ScheduleScreen")
        return None

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
        """ИСПРАВЛЕНО: Упрощенное обновление данных расписания"""
        app = App.get_running_app()
        today = datetime.now()
        
        # Определяем текущий день недели
        self._current_day = DAYS_EN[today.weekday()]
        
        # Формируем строки для отображения
        self._update_date_strings(today)
        self._load_user_header(app)
        self._load_schedule_data(app)

    def _update_date_strings(self, today):
        """Обновление строк даты и недели"""
        # Строка недели
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        self.current_week_str = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
        
        # Полная дата
        day_name_full = DAYS_FULL[today.weekday()]
        month_name = MONTHS[today.month - 1]
        self.today_full_date = f"{today.day} {month_name}, {day_name_full}"
        
        # Дни до выходных
        self._calculate_next_weekend(today)

    def _load_user_header(self, app):
        """Загрузка заголовка пользователя"""
        if hasattr(app, 'user_config') and app.user_config:
            username = app.user_config.get("username", "Student")
            self.user_header = f"{username}, Devonshire House School, 5KW"
        else:
            self.user_header = "Student, Devonshire House School, 5KW"

    def _load_schedule_data(self, app):
        """Загрузка данных расписания"""
        # Получаем расписание от сервиса
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
        
        # Подготавливаем данные для отображения (только рабочие дни)
        self.schedule_data = []
        for day in DAYS_EN[:5]:  # Понедельник-пятница
            day_lessons = schedule.get(day, [])
            self.schedule_data.append({
                "day": day,
                "is_today": day == self._current_day,
                "lessons": day_lessons
            })

    def _calculate_next_weekend(self, today):
        """Вычисление дней до следующих выходных"""
        current_weekday = today.weekday()  # 0 = понедельник, 6 = воскресенье
        
        if current_weekday < 5:  # Понедельник-пятница
            days_until_weekend = 5 - current_weekday  # Дни до субботы
            if days_until_weekend == 0:
                self.next_weekend_text = "Weekend today!"
            elif days_until_weekend == 1:
                self.next_weekend_text = "Weekend tomorrow!"
            else:
                self.next_weekend_text = f"Next weekend in {days_until_weekend} days!"
        elif current_weekday == 5:  # Суббота
            self.next_weekend_text = "Weekend now!"
        else:  # Воскресенье
            self.next_weekend_text = "Last day of weekend!"

    def _get_default_schedule(self):
        """Расписание по умолчанию"""
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
        """ИСПРАВЛЕНО: Упрощенное создание виджетов расписания"""
        if not hasattr(self, 'ids') or 'schedule_container' not in self.ids:
            return
            
        container = self.ids.schedule_container
        container.clear_widgets()
        
        tm = self.get_theme_manager()
        max_height = 0
        
        # Создаем колонки для каждого дня
        for day_data in self.schedule_data:
            day_column = self._create_day_column(day_data, tm)
            container.add_widget(day_column)
            max_height = max(max_height, day_column.height)
        
        # Устанавливаем высоту контейнера
        container.height = max_height + dp(8)
        
        # Сбрасываем скролл наверх
        Clock.schedule_once(self._reset_scroll, 0.1)

    def _create_day_column(self, day_data, theme_manager):
        """ИСПРАВЛЕНО: Упрощенное создание колонки дня"""
        day = day_data["day"]
        is_today = day_data["is_today"]
        lessons = day_data["lessons"]
        
        # ИСПРАВЛЕНО: Адаптивные отступы для текущего дня
        if is_today:
            padding_x = dp(3)  # Минимальные отступы для текущего дня
        else:
            padding_x = dp(1)  # Обычные отступы
        
        column = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            size_hint_x=0.2,
            size_hint_y=None,
            padding=[padding_x, dp(2)]  # ИСПРАВЛЕНО: Адаптивные отступы
        )
        
        # Фон для текущего дня
        if is_today and theme_manager:
            self._setup_today_background(column, theme_manager)

        # Добавляем уроки или сообщение о свободном дне
        if lessons:
            total_height = self._add_lessons_to_column(column, lessons, theme_manager, is_today)
        else:
            total_height = self._add_free_day_to_column(column, theme_manager)
        
        # Устанавливаем высоту колонки
        column.height = total_height + dp(8)  # padding
        
        return column

    def _setup_today_background(self, column, theme_manager):
        """Настройка фона для текущего дня"""
        with column.canvas.before:
            Color(*theme_manager.get_rgba("background"))
            RoundedRectangle(pos=column.pos, size=column.size, radius=[dp(6)])
        
        def update_bg(instance, value):
            column.canvas.before.clear()
            with column.canvas.before:
                Color(*theme_manager.get_rgba("background"))
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(6)])
        
        column.bind(pos=update_bg, size=update_bg)

    def _add_lessons_to_column(self, column, lessons, theme_manager, is_today):
        """ИСПРАВЛЕНО: Упрощенное добавление уроков в колонку"""
        total_height = 0
        
        for lesson in lessons:
            lesson_widget = self._create_lesson_widget(lesson, theme_manager, is_today)
            column.add_widget(lesson_widget)
            total_height += lesson_widget.height
        
        return total_height + (len(lessons) - 1) * dp(2)  # с учетом spacing

    def _add_free_day_to_column(self, column, theme_manager):
        """Добавление сообщения о свободном дне"""
        app = App.get_running_app()
        free_text = app.localizer.tr("free_day", "Free Day") if hasattr(app, 'localizer') else "Free Day"
        
        free_label = Label(
            text=free_text,
            font_size='12sp',  # ИСПРАВЛЕНО: Увеличили размер шрифта
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("text_secondary") if theme_manager else [0.7, 0.7, 0.7, 1],
            size_hint_y=None,
            height=dp(24),  # Уменьшили высоту
            halign='left',  # ИСПРАВЛЕНО: Выравнивание по левому краю
            text_size=(dp(120), None),  # Устанавливаем ширину для выравнивания
            italic=True
        )
        column.add_widget(free_label)
        return dp(24)

    def _create_lesson_widget(self, lesson, theme_manager, is_today):
        """ИСПРАВЛЕНО: Упрощенный виджет урока без лишних контейнеров"""
        container = BoxLayout(
            orientation="vertical",
            spacing=dp(1),
            size_hint_y=None,
            height=dp(36),
            padding=[dp(2), dp(1)]  # Минимальные отступы
        )
        
        # Время урока
        time_label = Label(
            text=lesson.get("time", ""),
            font_size='11sp',
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("text_secondary") if theme_manager else [0.7, 0.7, 0.7, 1],
            size_hint_y=None,
            height=dp(12),
            halign='left',
            valign='middle'
        )
        container.add_widget(time_label)
        
        # Название предмета
        subject_text = lesson.get("subject", "")
        if len(subject_text) > 15:  # Сокращаем длинные названия
            subject_text = subject_text[:14] + ".."
        
        subject_label = Label(
            text=subject_text,
            font_size='14sp',
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("text") if theme_manager else [1, 1, 1, 1],
            size_hint_y=None,
            height=dp(22),
            halign='left',
            valign='middle'
        )
        container.add_widget(subject_label)
        
        return container

    def _reset_scroll(self, dt):
        """Сброс скролла в начало"""
        try:
            if hasattr(self, 'ids') and 'schedule_container' in self.ids:
                container = self.ids.schedule_container
                parent_scroll = container.parent
                if hasattr(parent_scroll, 'scroll_y'):
                    parent_scroll.scroll_y = 1
                    logger.debug("Reset schedule scroll to top")
        except Exception as e:
            logger.error(f"Error resetting scroll: {e}")

    def refresh_theme(self, *args):
        """Обновление темы"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return

        # Обновляем заголовки
        if hasattr(self, 'ids'):
            widgets_to_update = {
                'title_label': ('title', 'primary'),
                'week_label': ('main', 'text'),
                'today_date_label': ('main', 'text'),
                'weekend_info_label': ('main', 'text_secondary')
            }
            
            for widget_id, (font_type, color_type) in widgets_to_update.items():
                if widget_id in self.ids:
                    widget = self.ids[widget_id]
                    widget.font_name = tm.get_font(font_type)
                    widget.color = tm.get_rgba(color_type)
        
        # Пересоздаем виджеты с новой темой
        self.create_schedule_widgets()

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        # Пересоздаем виджеты с новой локализацией
        self.create_schedule_widgets()