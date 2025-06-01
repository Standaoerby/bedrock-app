import os
import json
from app.logger import app_logger as logger

class Localizer:
    """
    Менеджер локализации приложения.
    Хранит переводы для всех поддерживаемых языков и возвращает строки по ключу.
    Позволяет динамически переключать язык.
    """
    def __init__(self, locale_dir="locale"):
        self.locale_dir = locale_dir
        self.translations = {}
        self.language = "en"

    def load(self, language):
        """Загрузить переводы для нового языка, fallback — английский."""
        self.language = language
        # Загружаем основной язык
        lang_path = os.path.join(self.locale_dir, f"{language}.json")
        self.translations = self._load_json(lang_path)
        # Загружаем fallback (en) если язык не английский
        if language != "en":
            en_path = os.path.join(self.locale_dir, "en.json")
            self.translations_fallback = self._load_json(en_path)
        else:
            self.translations_fallback = {}

        logger.info(f"Localization loaded: {language}")

    def _load_json(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as ex:
            logger.warning(f"Failed to load locale: {path} — {ex}")
            return {}

    def tr(self, key, default=""):
        """Получить перевод по ключу. Fallback — английский, потом default."""
        # Первый уровень — выбранный язык
        value = self.translations.get(key)
        if value:
            return value
        # Второй уровень — fallback (en)
        if self.translations_fallback:
            value = self.translations_fallback.get(key)
            if value:
                return value
        # Третий уровень — дефолт
        if default:
            return default
        # Для dev-режима можно возвращать ключ как есть
        return f"[{key}]"

# Глобальный singleton для использования во всём проекте
localizer = Localizer()
