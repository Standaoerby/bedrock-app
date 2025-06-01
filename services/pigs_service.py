"""
Сервис для управления уходом за питомцами (морские свинки)
Отслеживает кормление, поение и уборку с временными интервалами
"""
import json
import os
from datetime import datetime, timedelta
from app.logger import app_logger as logger


class PigsService:
    """Сервис для управления уходом за питомцами"""
    
    def __init__(self, config_path="config/pigs.json"):
        self.config_path = config_path
        
        # Создаем директорию config если её нет
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Конфигурация по умолчанию
        self.default_config = {
            "pigs": [
                {"name": "Korovka", "breed": "Guinea Pig"},
                {"name": "Karamelka", "breed": "Guinea Pig"}
            ],
            "care_items": {
                "water": {
                    "label": "Water",
                    "max_hours": 8,  # Максимальное время без воды (часы)
                    "last_reset": self._get_current_time_iso(),
                    "description": "Fresh water for drinking"
                },
                "food": {
                    "label": "Food", 
                    "max_hours": 6,  # Максимальное время без еды (часы)
                    "last_reset": self._get_current_time_iso(),
                    "description": "Hay, pellets, and vegetables"
                },
                "clean": {
                    "label": "Cleaning",
                    "max_hours": 12,  # Максимальное время без уборки (часы)
                    "last_reset": self._get_current_time_iso(),
                    "description": "Cage cleaning and maintenance"
                }
            },
            "settings": {
                "reminder_threshold": 25,  # Процент для напоминаний
                "critical_threshold": 10   # Критический процент
            }
        }
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        logger.info("PigsService initialized")
    
    def _get_current_time_iso(self):
        """Получить текущее время в ISO формате"""
        return datetime.now().isoformat()
    
    def _parse_iso_datetime(self, datetime_str):
        """Парсинг ISO datetime строки без использования dateutil"""
        try:
            # Убираем микросекунды если есть
            if '.' in datetime_str:
                datetime_str = datetime_str.split('.')[0]
                
            # Убираем timezone info если есть
            if '+' in datetime_str:
                datetime_str = datetime_str.split('+')[0]
            elif 'Z' in datetime_str:
                datetime_str = datetime_str.replace('Z', '')
                
            # Парсим очищенную строку
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            logger.error(f"Error parsing datetime '{datetime_str}': {e}")
            return datetime.now()
    
    def _load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded pigs config from {self.config_path}")
                
                # Проверяем и дополняем недостающие поля
                config = self._validate_config(config)
                return config
            else:
                # Создаем файл с конфигурацией по умолчанию
                self._save_config(self.default_config)
                logger.info("Created default pigs config")
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error loading pigs config: {e}")
            return self.default_config.copy()
    
    def _validate_config(self, config):
        """Валидация и дополнение конфигурации"""
        # Убеждаемся что все необходимые поля есть
        validated = self.default_config.copy()
        
        # Обновляем из загруженной конфигурации
        if "pigs" in config:
            validated["pigs"] = config["pigs"]
        if "care_items" in config:
            validated["care_items"].update(config["care_items"])
        if "settings" in config:
            validated["settings"].update(config["settings"])
            
        return validated
    
    def _save_config(self, config=None):
        """Сохранение конфигурации в файл"""
        if config is None:
            config = self.config
            
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.debug("Saved pigs config")
            return True
        except Exception as e:
            logger.error(f"Error saving pigs config: {e}")
            return False
    
    def get_bar_percentage(self, care_type):
        """
        Вычислить процент оставшегося времени для типа ухода
        Возвращает процент от 0 до 100 (100 = только что сделано, 0 = критично)
        """
        try:
            care_item = self.config["care_items"].get(care_type, {})
            max_hours = care_item.get("max_hours", 24)
            last_reset_str = care_item.get("last_reset", self._get_current_time_iso())
            
            # Парсим время последнего сброса
            last_reset = self._parse_iso_datetime(last_reset_str)
            now = datetime.now()
            
            # Вычисляем прошедшее время в часах
            elapsed_hours = (now - last_reset).total_seconds() / 3600
            
            # Вычисляем оставшийся процент
            if elapsed_hours >= max_hours:
                return 0  # Критично
            
            # Процент оставшегося времени
            percentage = 100 - (elapsed_hours / max_hours * 100)
            return max(0, min(100, percentage))
            
        except Exception as e:
            logger.error(f"Error calculating percentage for {care_type}: {e}")
            return 50  # Значение по умолчанию при ошибке
    
    def get_all_values(self):
        """
        Получить все значения полос и общий статус
        Возвращает (dict значений полос, общий статус 0-1)
        """
        try:
            values = {}
            total_percentage = 0
            
            for care_type in self.config["care_items"].keys():
                percentage = self.get_bar_percentage(care_type)
                values[care_type] = percentage
                total_percentage += percentage
            
            # Средний процент по всем типам ухода
            if len(values) > 0:
                overall_status = total_percentage / len(values) / 100
            else:
                overall_status = 0.5
            
            logger.debug(f"Calculated values: {values}, overall: {overall_status:.2f}")
            return values, overall_status
            
        except Exception as e:
            logger.error(f"Error getting all values: {e}")
            # Возвращаем значения по умолчанию
            default_values = {"water": 50, "food": 50, "clean": 50}
            return default_values, 0.5
    
    def reset_bar(self, care_type):
        """Сбросить определённый тип ухода (отметить как выполненный)"""
        try:
            if care_type in self.config["care_items"]:
                self.config["care_items"][care_type]["last_reset"] = self._get_current_time_iso()
                self._save_config()
                logger.info(f"Reset {care_type} care item")
                return True
            else:
                logger.error(f"Care type '{care_type}' not found in config")
                return False
        except Exception as e:
            logger.error(f"Error resetting {care_type}: {e}")
            return False
    
    def get_care_status(self, care_type):
        """Получить детальный статус определённого типа ухода"""
        try:
            percentage = self.get_bar_percentage(care_type)
            care_item = self.config["care_items"].get(care_type, {})
            
            # Определяем статус
            if percentage >= 75:
                status = "excellent"
            elif percentage >= 50:
                status = "good"
            elif percentage >= 25:
                status = "warning"
            else:
                status = "critical"
            
            # Вычисляем время до следующего ухода
            max_hours = care_item.get("max_hours", 24)
            hours_remaining = (percentage / 100) * max_hours
            
            return {
                "type": care_type,
                "label": care_item.get("label", care_type.title()),
                "percentage": percentage,
                "status": status,
                "hours_remaining": hours_remaining,
                "last_reset": care_item.get("last_reset"),
                "description": care_item.get("description", "")
            }
        except Exception as e:
            logger.error(f"Error getting status for {care_type}: {e}")
            return {
                "type": care_type,
                "label": care_type.title(),
                "percentage": 50,
                "status": "unknown",
                "hours_remaining": 12,
                "last_reset": self._get_current_time_iso(),
                "description": ""
            }
    
    def get_all_care_status(self):
        """Получить детальный статус всех типов ухода"""
        statuses = {}
        for care_type in self.config["care_items"].keys():
            statuses[care_type] = self.get_care_status(care_type)
        return statuses
    
    def needs_attention(self):
        """Проверить, нужно ли внимание (есть ли элементы с низким статусом)"""
        threshold = self.config["settings"].get("reminder_threshold", 25)
        
        for care_type in self.config["care_items"].keys():
            percentage = self.get_bar_percentage(care_type)
            if percentage <= threshold:
                return True
        return False
    
    def get_critical_items(self):
        """Получить список критичных элементов ухода"""
        threshold = self.config["settings"].get("critical_threshold", 10)
        critical_items = []
        
        for care_type in self.config["care_items"].keys():
            percentage = self.get_bar_percentage(care_type)
            if percentage <= threshold:
                critical_items.append({
                    "type": care_type,
                    "label": self.config["care_items"][care_type].get("label", care_type.title()),
                    "percentage": percentage
                })
        
        return critical_items
    
    def get_pigs_info(self):
        """Получить информацию о питомцах"""
        return self.config.get("pigs", [])
    
    def update_pig_info(self, pig_index, info):
        """Обновить информацию о питомце"""
        try:
            if 0 <= pig_index < len(self.config["pigs"]):
                self.config["pigs"][pig_index].update(info)
                self._save_config()
                logger.info(f"Updated pig {pig_index} info")
                return True
            else:
                logger.error(f"Invalid pig index: {pig_index}")
                return False
        except Exception as e:
            logger.error(f"Error updating pig info: {e}")
            return False