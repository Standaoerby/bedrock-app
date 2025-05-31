import json
import os

class Localizer:
    def __init__(self, lang="ru", locales_dir="locale"):
        self.lang = lang
        self.locales_dir = locales_dir
        self.strings = {}
        self.load(lang)

    def load(self, lang):
        self.lang = lang
        path = os.path.join(self.locales_dir, f"{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.strings = json.load(f)
        except Exception as e:
            print(f"[Localizer] Ошибка загрузки перевода {lang}: {e}")
            self.strings = {}

    def t(self, key, **kwargs):
        text = self.strings.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

# Глобальный экземпляр
localizer = Localizer()
