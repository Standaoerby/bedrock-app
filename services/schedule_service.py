import json
import os
from datetime import datetime
from app.logger import app_logger as logger


class ScheduleService:
    """Сервис для управления расписанием занятий"""
    
    def __init__(self, config_path="config/schedule.json"):
        self.config_path = config_path
        self.schedule = {}
        
        # Создаем директорию config если её нет
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Расписание по умолчанию
        self.default_schedule = {
            "Mon": [
                {"time": "09:00", "subject": "Mathematics", "room": "101", "teacher": "Smith"},
                {"time": "10:00", "subject": "English", "room": "102", "teacher": "Johnson"},
                {"time": "11:00", "subject": "Science", "room": "103", "teacher": "Brown"},
                {"time": "12:00", "subject": "History", "room": "104", "teacher": "Davis"},
                {"time": "13:00", "subject": "Lunch Break", "room": "", "teacher": ""},
                {"time": "14:00", "subject": "Art", "room": "107", "teacher": "Wilson"}
            ],
            "Tue": [
                {"time": "09:00", "subject": "Physics", "room": "105", "teacher": "Taylor"},
                {"time": "10:00", "subject": "Chemistry", "room": "106", "teacher": "Miller"},
                {"time": "11:00", "subject": "Mathematics", "room": "101", "teacher": "Smith"},
                {"time": "12:00", "subject": "PE", "room": "Gym", "teacher": "Anderson"},
                {"time": "13:00", "subject": "Lunch Break", "room": "", "teacher": ""},
                {"time": "14:00", "subject": "Music", "room": "109", "teacher": "Garcia"}
            ],
            "Wed": [
                {"time": "09:00", "subject": "English", "room": "102", "teacher": "Johnson"},
                {"time": "10:00", "subject": "Geography", "room": "108", "teacher": "Martinez"},
                {"time": "11:00", "subject": "Computer Science", "room": "Lab", "teacher": "Lee"},
                {"time": "12:00", "subject": "Mathematics", "room": "101", "teacher": "Smith"},
                {"time": "13:00", "subject": "Lunch Break", "room": "", "teacher": ""},
                {"time": "14:00", "subject": "Library Time", "room": "Library", "teacher": ""}
            ],
            "Thu": [
                {"time": "09:00", "subject": "Science", "room": "103", "teacher": "Brown"},
                {"time": "10:00", "subject": "History", "room": "104", "teacher": "Davis"},
                {"time": "11:00", "subject": "English", "room": "102", "teacher": "Johnson"},
                {"time": "12:00", "subject": "Art", "room": "107", "teacher": "Wilson"},
                {"time": "13:00", "subject": "Lunch Break", "room": "", "teacher": ""},
                {"time": "14:00", "subject": "Mathematics", "room": "101", "teacher": "Smith"}
            ],
            "Fri": [
                {"time": "09:00", "subject": "Chemistry", "room": "106", "teacher": "Miller"},
                {"time": "10:00", "subject": "Physics", "room": "105", "teacher": "Taylor"},
                {"time": "11:00", "subject": "PE", "room": "Gym", "teacher": "Anderson"},
                {"time": "12:00", "subject": "Music", "room": "109", "teacher": "Garcia"},
                {"time": "13:00", "subject": "Lunch Break", "room": "", "teacher": ""},
                {"time": "14:00", "subject": "Free Period", "room": "", "teacher": ""}
            ],
            "Sat": [],
            "Sun": []
        }
        
        # Загружаем конфигурацию
        self.load()
        logger.info("ScheduleService initialized")
    
    def load(self):
        """Загрузка расписания из файла"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.schedule = data.get("schedule", self.default_schedule)
                logger.info(f"Loaded schedule from {self.config_path}")
            else:
                # Создаем файл с расписанием по умолчанию
                self.schedule = self.default_schedule.copy()
                self.save()
                logger.info("Created default schedule configuration")
        except Exception as e:
            logger.error(f"Error loading schedule: {e}")
            self.schedule = self.default_schedule.copy()
    
    def save(self):
        """Сохранение расписания в файл"""
        try:
            data = {
                "schedule": self.schedule,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved schedule to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving schedule: {e}")
            return False
    
    def get_schedule(self, day=None):
        """Получение расписания на день или всего расписания"""
        if day:
            return self.schedule.get(day, [])
        return self.schedule
    
    def get_current_day_schedule(self):
        """Получение расписания на сегодня"""
        today = datetime.now()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        current_day = day_names[today.weekday()]
        return self.get_schedule(current_day)
    
    def get_next_lesson(self):
        """Получение следующего урока"""
        try:
            today_schedule = self.get_current_day_schedule()
            if not today_schedule:
                return None
                
            current_time = datetime.now()
            current_time_str = current_time.strftime("%H:%M")
            
            # Ищем следующий урок
            for lesson in today_schedule:
                lesson_time = lesson.get("time", "")
                if lesson_time > current_time_str:
                    return lesson
                    
            # Если уроков на сегодня больше нет, возвращаем первый урок завтра
            tomorrow = (current_time.weekday() + 1) % 7
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            tomorrow_day = day_names[tomorrow]
            tomorrow_schedule = self.get_schedule(tomorrow_day)
            
            if tomorrow_schedule:
                return {**tomorrow_schedule[0], "day": tomorrow_day}
                
            return None
        except Exception as e:
            logger.error(f"Error getting next lesson: {e}")
            return None
    
    def get_current_lesson(self):
        """Получение текущего урока"""
        try:
            today_schedule = self.get_current_day_schedule()
            if not today_schedule:
                return None
                
            current_time = datetime.now()
            current_time_str = current_time.strftime("%H:%M")
            
            # Ищем текущий урок (предполагаем уроки по 50 минут)
            for i, lesson in enumerate(today_schedule):
                lesson_start = lesson.get("time", "")
                
                # Вычисляем время окончания урока (+ 50 минут)
                try:
                    start_hour, start_min = map(int, lesson_start.split(":"))
                    end_min = start_min + 50
                    end_hour = start_hour
                    if end_min >= 60:
                        end_hour += 1
                        end_min -= 60
                    lesson_end = f"{end_hour:02d}:{end_min:02d}"
                    
                    if lesson_start <= current_time_str <= lesson_end:
                        return lesson
                except ValueError:
                    continue
                    
            return None
        except Exception as e:
            logger.error(f"Error getting current lesson: {e}")
            return None
    
    def add_lesson(self, day, lesson):
        """Добавление урока в расписание"""
        try:
            if day not in self.schedule:
                self.schedule[day] = []
            
            self.schedule[day].append(lesson)
            
            # Сортируем по времени
            self.schedule[day].sort(key=lambda x: x.get("time", ""))
            
            self.save()
            logger.info(f"Added lesson to {day}: {lesson}")
            return True
        except Exception as e:
            logger.error(f"Error adding lesson: {e}")
            return False
    
    def remove_lesson(self, day, lesson_time):
        """Удаление урока из расписания"""
        try:
            if day not in self.schedule:
                return False
                
            self.schedule[day] = [
                lesson for lesson in self.schedule[day] 
                if lesson.get("time") != lesson_time
            ]
            
            self.save()
            logger.info(f"Removed lesson from {day} at {lesson_time}")
            return True
        except Exception as e:
            logger.error(f"Error removing lesson: {e}")
            return False
    
    def update_lesson(self, day, lesson_time, updated_lesson):
        """Обновление урока в расписании"""
        try:
            if day not in self.schedule:
                return False
                
            for i, lesson in enumerate(self.schedule[day]):
                if lesson.get("time") == lesson_time:
                    self.schedule[day][i] = updated_lesson
                    self.save()
                    logger.info(f"Updated lesson in {day} at {lesson_time}")
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error updating lesson: {e}")
            return False
    
    def get_week_summary(self):
        """Получение краткой сводки на неделю"""
        summary = {}
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
            day_schedule = self.get_schedule(day)
            summary[day] = {
                "lessons_count": len([l for l in day_schedule if l.get("subject") != "Lunch Break"]),
                "first_lesson": day_schedule[0].get("time") if day_schedule else None,
                "last_lesson": day_schedule[-1].get("time") if day_schedule else None
            }
        return summary