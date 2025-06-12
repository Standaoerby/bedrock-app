# app/localizer.py
# ИСПРАВЛЕНО: Добавлен правильный атрибут translations_fallback

import os
import json
from app.logger import app_logger as logger

class Localizer:
    """
    ИСПРАВЛЕНО: Менеджер локализации приложения.
    Хранит переводы для всех поддерживаемых языков и возвращает строки по ключу.
    Позволяет динамически переключать язык.
    """
    def __init__(self, locale_dir="locale"):
        self.locale_dir = locale_dir
        self.translations = {}
        self.translations_fallback = {}  # ИСПРАВЛЕНО: Добавлен атрибут
        self.language = "en"

    def load(self, language):
        """ИСПРАВЛЕНО: Загрузить переводы для нового языка, fallback — английский."""
        self.language = language
        
        # Загружаем основной язык
        lang_path = os.path.join(self.locale_dir, f"{language}.json")
        self.translations = self._load_json(lang_path)
        
        # ИСПРАВЛЕНО: Всегда загружаем fallback, даже для английского
        en_path = os.path.join(self.locale_dir, "en.json")
        self.translations_fallback = self._load_json(en_path)
        
        # Если основной язык английский, используем его же как fallback
        if language == "en" and not self.translations_fallback:
            self.translations_fallback = self.translations.copy()

        logger.info(f"Localization loaded: {language}")
        logger.debug(f"Translations loaded: {len(self.translations)} keys")
        logger.debug(f"Fallback loaded: {len(self.translations_fallback)} keys")

    def _load_json(self, path):
        """ИСПРАВЛЕНО: Загрузка JSON с лучшей обработкой ошибок"""
        try:
            if not os.path.isfile(path):
                logger.warning(f"Locale file not found: {path}")
                return {}
                
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                
            if not isinstance(data, dict):
                logger.error(f"Invalid locale file format: {path}")
                return {}
                
            logger.debug(f"Loaded locale file: {path} ({len(data)} keys)")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {path}: {e}")
            return {}
        except Exception as ex:
            logger.warning(f"Failed to load locale: {path} — {ex}")
            return {}

    def tr(self, key, default=""):
        """ИСПРАВЛЕНО: Получить перевод по ключу с улучшенным fallback."""
        if not isinstance(key, str):
            logger.warning(f"Translation key must be string, got: {type(key)}")
            return str(default) if default else f"[{key}]"
        
        # Первый уровень — выбранный язык
        if key in self.translations and self.translations[key]:
            return self.translations[key]
            
        # Второй уровень — fallback (en)
        if key in self.translations_fallback and self.translations_fallback[key]:
            return self.translations_fallback[key]
            
        # Третий уровень — дефолт
        if default:
            return str(default)
            
        # Для dev-режима возвращаем ключ как есть
        logger.debug(f"Translation missing for key: {key}")
        return f"[{key}]"

    def has_translation(self, key):
        """НОВОЕ: Проверить наличие перевода для ключа"""
        return (key in self.translations or 
                key in self.translations_fallback)

    def get_available_languages(self):
        """НОВОЕ: Получить список доступных языков"""
        try:
            if not os.path.isdir(self.locale_dir):
                return ["en"]
                
            languages = []
            for filename in os.listdir(self.locale_dir):
                if filename.endswith('.json'):
                    lang_code = filename[:-5]  # Убираем .json
                    languages.append(lang_code)
                    
            return languages if languages else ["en"]
            
        except Exception as e:
            logger.error(f"Error getting available languages: {e}")
            return ["en"]

    def get_language_info(self):
        """НОВОЕ: Получить информацию о текущем языке"""
        return {
            "current_language": self.language,
            "available_languages": self.get_available_languages(),
            "translations_count": len(self.translations),
            "fallback_count": len(self.translations_fallback),
            "locale_dir": self.locale_dir
        }

    def diagnose_state(self):
        """НОВОЕ: Диагностика состояния Localizer"""
        return {
            "language": self.language,
            "locale_dir": self.locale_dir,
            "translations_keys": len(self.translations),
            "fallback_keys": len(self.translations_fallback),
            "has_translations_fallback": hasattr(self, 'translations_fallback'),
            "available_languages": self.get_available_languages(),
            "sample_translations": dict(list(self.translations.items())[:5]) if self.translations else {}
        }

    def verify_instance(self):
        """НОВОЕ: Верификация экземпляра Localizer"""
        return {
            "class_name": self.__class__.__name__,
            "has_translations_fallback": hasattr(self, 'translations_fallback'),
            "translations_fallback_type": type(self.translations_fallback).__name__,
            "methods": [method for method in dir(self) if not method.startswith('_')]
        }

# ИСПРАВЛЕНО: Глобальный singleton с правильной инициализацией
localizer = Localizer()

def get_localizer():
    """НОВОЕ: Безопасное получение экземпляра Localizer"""
    return localizer

def validate_localizer_module():
    """НОВОЕ: Валидация модуля Localizer для отладки"""
    try:
        loc = Localizer()
        assert hasattr(loc, 'translations_fallback'), "translations_fallback attribute missing"
        assert hasattr(loc, 'load'), "load method missing"
        assert hasattr(loc, 'tr'), "tr method missing"
        
        # Тестируем загрузку
        loc.load("en")
        assert hasattr(loc, 'translations_fallback'), "translations_fallback missing after load"
        
        print("✅ Localizer module validation passed")
        return True
    except Exception as e:
        print(f"❌ Localizer module validation failed: {e}")
        return False

# Только в режиме разработки
if __name__ == "__main__":
    validate_localizer_module()