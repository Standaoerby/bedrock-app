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


class ScheduleScreen(Screen):
    """Экран расписания занятий"""
    
    # Свойства для отображения
    current_week_str = StringProperty("")
    today_day = StringProperty("")
    schedule_data = ListProperty([])
    user_header = StringProperty("School Schedule")
    
    # ДОБАВЛЕНО: Свойства для нижнего блока
    today_full_date = StringProperty("")
    next_weekend_text = StringProperty("Next weekend soon!")

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
        
        # Формируем заголовок с именем пользователя
        if hasattr(app, 'user_config') and app.user_config:
            username = app.user_config.get("username", "Student")
            self.user_header = f"{username}, Devonshire House School, 5KW"
        else:
            self.user_header = "Student, Devonshire House School, 5KW"
        
        # ДОБАВЛЕНО: Формируем полную дату для нижнего блока
        day_names_full = [
            "Monday", "Tuesday", "Wednesday", "Thursday", 
            "Friday", "Saturday", "Sunday"
        ]
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        day_name_full = day_names_full[today.weekday()]
        month_name = month_names[today.month - 1]
        self.today_full_date = f"{today.day} {month_name}, {day_name_full}"
        
        # ДОБАВЛЕНО: Вычисляем дни до выходных
        self._calculate_next_weekend()
        
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

    def _calculate_next_weekend(self):
        """ДОБАВЛЕНО: Вычисление дней до следующих выходных"""
        today = datetime.now()
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
        
        tm = self.get_theme_manager()
        
        # Создаем колонки для каждого дня
        for day_data in self.schedule_data:
            day_column = self.create_day_column(day_data, tm)
            container.add_widget(day_column)
        
        # Правильно устанавливаем высоту контейнера после добавления виджетов
        Clock.schedule_once(self._fix_container_height, 0.1)

    def _fix_container_height(self, dt):
        """Исправление высоты контейнера расписания"""
        try:
            if hasattr(self, 'ids') and 'schedule_container' in self.ids:
                container = self.ids.schedule_container
                
                # Вычисляем максимальную высоту среди колонок
                max_column_height = 0
                for child in container.children:
                    if hasattr(child, 'height'):
                        max_column_height = max(max_column_height, child.height)
                
                # Устанавливаем высоту контейнера с запасом
                if max_column_height > 0:
                    container.height = max_column_height + dp(0)
                    logger.debug(f"Set schedule container height to {container.height}")
                
                # Принудительно сбрасываем скролл наверх
                parent_scroll = container.parent
                if hasattr(parent_scroll, 'scroll_y'):
                    parent_scroll.scroll_y = 1
                    logger.debug("Reset schedule scroll to top")
                    
        except Exception as e:
            logger.error(f"Error fixing container height: {e}")

    def create_day_column(self, day_data, theme_manager):
        """Создание колонки для одного дня"""
        day = day_data["day"]
        is_today = day_data["is_today"]
        lessons = day_data["lessons"]
        
        # Основной контейнер колонки
        column = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            size_hint_x=0.2,  # 5 колонок
            size_hint_y=None,
            padding=[dp(0), dp(0)]  # Добавляем padding для фона
        )
        
        # Фон для текущего дня
        if is_today and theme_manager:
            with column.canvas.before:
                Color(*theme_manager.get_rgba("background"))
                RoundedRectangle(
                    pos=column.pos,
                    size=column.size,
                    radius=[dp(8)]
                )
            # Привязываем обновление фона к размеру и позиции
            def update_bg(instance, value):
                column.canvas.before.clear()
                with column.canvas.before:
                    Color(*theme_manager.get_rgba("background"))
                    RoundedRectangle(
                        pos=instance.pos,
                        size=instance.size,
                        radius=[dp(8)]
                    )
            column.bind(pos=update_bg, size=update_bg)
        
        # Контейнер для уроков
        lessons_container = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=[dp(0), dp(0)],  # ИСПРАВЛЕНО: уменьшили верхний отступ
            size_hint_y=None
        )
        
        if not lessons:
            # Свободный день
            app = App.get_running_app()
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
            lessons_container.height = dp(48)  # Минимальная высота
        else:
            # Добавляем уроки
            total_height = 0
            for lesson in lessons:
                lesson_widget = self.create_lesson_widget(lesson, theme_manager, is_today)
                lessons_container.add_widget(lesson_widget)
                total_height += lesson_widget.height
            
            # Устанавливаем правильную высоту контейнера уроков
            lessons_container.height = total_height + (len(lessons) - 1) * dp(4) + dp(16)  # spacing + padding
        
        column.add_widget(lessons_container)
        
        # Устанавливаем общую высоту колонки
        column.height = lessons_container.height + dp(0)  # padding
        
        return column

    def create_lesson_widget(self, lesson, theme_manager, is_today):
        """Создание виджета урока"""
        container = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            size_hint_y=None,
            height=dp(48),  # Уменьшили высоту так как убрали кабинет
            padding=[dp(0), dp(4)]
        )
        
        # Время - выровнено по левому краю
        time_label = Label(
            text=lesson.get("time", ""),
            font_size='12sp',
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("text_secondary") if (theme_manager and is_today) else (theme_manager.get_rgba("text_secondary") if theme_manager else [0.7, 0.7, 0.7, 1]),
            size_hint_y=None,
            height=dp(16),
            halign='left',
            text_size=(dp(130), None)
        )
        container.add_widget(time_label)
        
        # Предмет - выровнен по левому краю
        subject_label = Label(
            text=lesson.get("subject", ""),
            font_size='14sp',
            font_name=theme_manager.get_font("main") if theme_manager else "",
            color=theme_manager.get_rgba("text") if theme_manager else [1, 1, 1, 1],
            size_hint_y=None,
            height=dp(24),
            halign='left',
            text_size=(dp(130), None),
            shorten=True,
            shorten_from='right'
        )
        container.add_widget(subject_label)
        
        return container

    def refresh_theme(self, *args):
        """Обновление темы"""
        tm = self.get_theme_manager()
        if not tm or not tm.is_loaded():
            return

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
            # ДОБАВЛЕНО: Обновляем стили для новых элементов нижнего блока
            if 'today_date_label' in self.ids:
                self.ids.today_date_label.font_name = tm.get_font("main")
                self.ids.today_date_label.color = tm.get_rgba("text")
            if 'weekend_info_label' in self.ids:
                self.ids.weekend_info_label.font_name = tm.get_font("main")
                self.ids.weekend_info_label.color = tm.get_rgba("text_secondary")
        
        # Пересоздаем виджеты с новой темой
        if hasattr(self, 'ids'):
            self.create_schedule_widgets()

    def refresh_text(self, *args):
        """Обновление локализованного текста"""
        app = App.get_running_app()
        
        # Обновляем заголовок с именем пользователя
        if hasattr(self, 'ids') and 'title_label' in self.ids:
            self.ids.title_label.text = self.user_header
            
        # Пересоздаем виджеты с новой локализацией
        self.create_schedule_widgets()