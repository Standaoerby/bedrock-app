# app/theme_manager.py - ИСПРАВЛЕНА проблема с путями к шрифтам
"""
КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
✅ Исправлена логика get_font() - правильные пути к шрифтам
✅ Добавлена детальная отладка для диагностики
✅ Улучшена обработка ошибок
✅ Защита от пустых путей
"""

import os
import json
from app.event_bus import event_bus
from app.logger import app_logger as logger


class ThemeManager:
    """
    Менеджер тем с исправленными путями к шрифтам.
    Отвечает за загрузку, хранение и отдачу ресурсов темы:
    цвета, изображения, шрифты, иконки, оверлеи, звуки и т.д.
    """
    
    def __init__(self, themes_dir="themes"):
        self.themes_dir = themes_dir
        self.theme_name = None
        self.variant = None
        self.theme_data = {}
        
        # Совместимость с существующим кодом
        self.current_theme = None
        self.current_variant = None
        
        # 🔥 ЗАЩИТА ОТ ЦИКЛИЧЕСКИХ РЕКУРСИЙ
        self._loading_in_progress = False
        self._notification_disabled = False
        
        # Дефолтная тема для предотвращения ошибок
        self.default_theme = {
            "colors": {
                "primary": "#40916c",
                "background": "#f0efeb",
                "accent": "#277da1",
                "text": "#000000",
                "text_secondary": "#666666",
                "text_inactive": "#999999",
                "text_accent": "#277da1",
                "text_accent_2": "#40916c",
                "clock_main": "#000000",
                "clock_shadow": "#00000040",
                "background_highlighted": "#e8e8e8",
                "overlay_card": "#ffffff",
                "menu_color": "#25252580",
                "menu_button_text": "#ffffff",
                "menu_button_text_active": "#40916c"
            },
            "fonts": {
                "main": "",  # Пустая строка = дефолтный шрифт Kivy
                "title": "",
                "clock": ""
            },
            "images": {
                "background": "background.png",
                "button_bg": "btn_bg.png",
                "button_bg_active": "btn_bg_active.png",
                "menu_button_bg": "menu_btn.png",
                "menu_button_bg_active": "menu_btn_active.png",
                "overlay_home": "overlay_home.png",
                "overlay_alarm": "overlay_alarm.png",
                "overlay_schedule": "overlay_schedule.png",
                "overlay_weather": "overlay_weather.png",
                "overlay_pigs": "overlay_pigs.png",
                "overlay_settings": "overlay_settings.png",
                "overlay_default": "overlay_default.png"
            },
            "menu": {
                "menu_height": 64,
                "menu_button_height": 48,
                "menu_button_width": 152
            },
            "sounds": {
                "click": "click.ogg",
                "confirm": "confirm.ogg",
                "error": "error.ogg",
                "notify": "notify.ogg",
                "startup": "startup.ogg"
            }
        }

    # ================================================
    # ЗАГРУЗКА ТЕМЫ
    # ================================================

    def load_theme(self, theme, variant):
        """Загрузка темы (основной метод)"""
        return self.load(theme, variant)

    def load(self, theme_name, variant="light"):
        """🔥 ГЛАВНЫЙ МЕТОД загрузки темы с защитой от циклов"""
        # Защита от циклических вызовов
        if self._loading_in_progress:
            logger.warning(f"Theme loading already in progress, skipping: {theme_name}/{variant}")
            return False
            
        try:
            self._loading_in_progress = True
            logger.info(f"[Loading theme] {theme_name}/{variant}")
            
            # Загружаем данные темы
            success = self._load_theme_data(theme_name, variant)
            
            if success:
                # Устанавливаем текущую тему
                self.theme_name = theme_name
                self.variant = variant
                self.current_theme = theme_name
                self.current_variant = variant
                
                logger.info(f"[✅ Theme loaded] {theme_name}/{variant}")
                
                # Уведомляем о смене темы
                self._notify_theme_changed()
                return True
            else:
                logger.error(f"[❌ Theme load failed] {theme_name}/{variant}")
                return False
                
        except Exception as e:
            logger.error(f"[❌ Critical error loading theme] {theme_name}/{variant}: {e}")
            return False
        finally:
            self._loading_in_progress = False

    def load_silently(self, theme_name, variant="light"):
        """🔥 НОВЫЙ: Загрузка темы БЕЗ публикации событий"""
        try:
            self._notification_disabled = True
            return self.load(theme_name, variant)
        finally:
            self._notification_disabled = False

    def force_reload(self, theme_name=None, variant=None):
        """🔥 НОВЫЙ: Принудительная перезагрузка темы"""
        theme_name = theme_name or self.theme_name
        variant = variant or self.variant
        
        if theme_name and variant:
            # Сбрасываем все флаги и состояние
            self._loading_in_progress = False
            self._notification_disabled = False
            self.theme_data = {}
            return self.load(theme_name, variant)
        return False

    def _load_theme_data(self, theme_name, variant):
        """Внутренний метод загрузки данных темы"""
        try:
            theme_path = os.path.join(self.themes_dir, theme_name, variant, "theme.json")
            
            if not os.path.isfile(theme_path):
                logger.error(f"Theme file not found: {theme_path}")
                logger.info("Using default theme")
                self.theme_data = self.default_theme.copy()
                return False
                
            with open(theme_path, encoding="utf-8") as f:
                loaded_data = json.load(f)
                
            # Мерджим с дефолтными значениями
            self.theme_data = self._merge_with_defaults(loaded_data)
            
            # ОТЛАДКА: Проверяем загруженные шрифты
            fonts = self.theme_data.get("fonts", {})
            logger.info(f"🔍 Loaded fonts: {fonts}")
            
            return True
            
        except Exception as ex:
            logger.warning(f"Failed to load theme data {theme_name}/{variant}: {ex}")
            logger.info("Using default theme")
            self.theme_data = self.default_theme.copy()
            return False

    def _merge_with_defaults(self, loaded_data):
        """Мерджим загруженные данные с дефолтными для предотвращения ошибок"""
        merged = self.default_theme.copy()
        
        for section, values in loaded_data.items():
            if section in merged and isinstance(values, dict):
                merged[section].update(values)
            else:
                merged[section] = values
                
        return merged

    def _notify_theme_changed(self):
        """🔥 УВЕДОМЛЕНИЕ О СМЕНЕ ТЕМЫ с защитой от циклов"""
        try:
            if not self._notification_disabled:
                event_bus.publish("theme_changed", {
                    "theme": self.theme_name,
                    "variant": self.variant
                })
                logger.debug(f"Theme change event published: {self.theme_name}/{self.variant}")
        except Exception as e:
            logger.error(f"Error publishing theme change event: {e}")

    # ================================================
    # ПОЛУЧЕНИЕ РЕСУРСОВ ТЕМЫ
    # ================================================

    def get_color(self, name, fallback="#000000"):
        """Получить цвет в hex формате"""
        try:
            color = self.theme_data.get("colors", {}).get(name, fallback)
            return color if color else fallback
        except Exception as e:
            logger.error(f"Error getting color {name}: {e}")
            return fallback

    def get_rgba(self, name, fallback=None):
        """Получить цвет в формате RGBA [r, g, b, a]"""
        if fallback is None:
            fallback = [0, 0, 0, 1]
            
        try:
            hex_color = self.get_color(name)
            if not hex_color or not hex_color.startswith("#"):
                return fallback
                
            # Конвертируем hex в RGBA
            hex_color = hex_color.lstrip("#")
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                return [r, g, b, 1.0]
            elif len(hex_color) == 8:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                a = int(hex_color[6:8], 16) / 255.0
                return [r, g, b, a]
            else:
                return fallback
        except Exception as e:
            logger.error(f"Error converting color {name} to RGBA: {e}")
            return fallback

    def get_param(self, name, fallback=None):
        """Получить параметр темы"""
        try:
            # Проверяем сначала в menu секции
            menu_param = self.theme_data.get("menu", {}).get(name)
            if menu_param is not None:
                return menu_param
                
            # Проверяем в корневых параметрах
            root_param = self.theme_data.get(name)
            return root_param if root_param is not None else fallback
        except Exception as e:
            logger.error(f"Error getting param {name}: {e}")
            return fallback

    def get_font(self, name, fallback=""):
        """ИСПРАВЛЕНО: Получить путь к шрифту с детальной отладкой"""
        try:
            logger.debug(f"🔍 Getting font '{name}'...")
            
            # Проверяем, загружена ли тема
            if not self.theme_name:
                logger.warning(f"❌ Theme not loaded, using default font for '{name}'")
                return fallback
            
            # Получаем данные о шрифтах
            fonts = self.theme_data.get("fonts", {})
            logger.debug(f"🔍 Available fonts: {fonts}")
            
            font_file = fonts.get(name)
            logger.debug(f"🔍 Font file for '{name}': '{font_file}'")
            
            # Если шрифт не задан, возвращаем fallback
            if not font_file:
                logger.debug(f"🔍 Font '{name}' not defined, using fallback: '{fallback}'")
                return fallback
            
            # Строим путь к шрифту
            # Шрифты лежат в папке themes/minecraft/fonts/
            if os.path.sep in font_file or '/' in font_file:
                # Абсолютный или относительный путь
                path = font_file
            else:
                # Простое имя файла - строим путь
                path = os.path.join(self.themes_dir, self.theme_name, "fonts", font_file)
            
            path = os.path.normpath(path)
            logger.debug(f"🔍 Constructed font path: '{path}'")
            
            # Проверяем существование файла
            if not os.path.isfile(path):
                logger.warning(f"❌ Font file not found: {path}")
                logger.debug(f"🔍 Current working directory: {os.getcwd()}")
                logger.debug(f"🔍 Checking if themes directory exists: {os.path.exists(self.themes_dir)}")
                
                # Проверяем структуру папок
                theme_fonts_dir = os.path.join(self.themes_dir, self.theme_name, "fonts")
                logger.debug(f"🔍 Theme fonts directory: {theme_fonts_dir}")
                logger.debug(f"🔍 Theme fonts directory exists: {os.path.exists(theme_fonts_dir)}")
                
                if os.path.exists(theme_fonts_dir):
                    # Показываем, какие файлы есть в папке
                    try:
                        files = os.listdir(theme_fonts_dir)
                        logger.debug(f"🔍 Files in fonts directory: {files}")
                    except Exception as e:
                        logger.debug(f"🔍 Error listing fonts directory: {e}")
                
                logger.info(f"Using fallback font for '{name}': '{fallback}'")
                return fallback
                
            logger.info(f"✅ Font found: {name} -> {path}")
            return path
            
        except Exception as e:
            logger.error(f"❌ Error getting font {name}: {e}")
            return fallback

    def get_image(self, name):
        """Получить путь к изображению"""
        try:
            img_file = self.theme_data.get("images", {}).get(name)
            if not img_file:
                # Фолбэк: имя файла совпадает с именем
                img_file = f"{name}.png"
            
            if not self.theme_name or not self.variant:
                logger.warning("Theme not loaded, using fallback")
                return ""
            
            # Проверяем полный путь vs относительный
            if os.path.sep in img_file or '/' in img_file:
                path = img_file
            else:
                # Изображения лежат в папке варианта
                path = os.path.join(self.themes_dir, self.theme_name, self.variant, img_file)
            
            path = os.path.normpath(path)
                
            if not os.path.isfile(path):
                logger.warning(f"Image not found: {path}, trying fallback")
                # Фолбэк на дефолтный фон
                fallback_path = os.path.join(
                    self.themes_dir, self.theme_name, self.variant, "background.png"
                )
                fallback_path = os.path.normpath(fallback_path)
                if os.path.isfile(fallback_path):
                    return fallback_path
                else:
                    logger.warning(f"Fallback image also not found: {fallback_path}")
                    return ""
            return path
        except Exception as e:
            logger.error(f"Error getting image {name}: {e}")
            return ""

    def get_overlay(self, page_name):
        """Получить путь к overlay-файлу для страницы"""
        try:
            overlay_name = f"overlay_{page_name}.png"
            if not self.theme_name or not self.variant:
                return ""
                
            path = os.path.join(self.themes_dir, self.theme_name, self.variant, overlay_name)
            path = os.path.normpath(path)
            
            if os.path.isfile(path):
                return path
            
            # Фолбэк: overlay_default.png
            fallback = os.path.join(
                self.themes_dir, self.theme_name, self.variant, "overlay_default.png"
            )
            fallback = os.path.normpath(fallback)
            if os.path.isfile(fallback):
                return fallback
            return ""
        except Exception as e:
            logger.error(f"Error getting overlay {page_name}: {e}")
            return ""

    def get_sound(self, name):
        """Получить путь к звуковому файлу"""
        try:
            sound_file = self.theme_data.get("sounds", {}).get(name)
            if not sound_file:
                sound_file = f"{name}.ogg"
            
            if not self.theme_name:
                return ""
            
            # Проверяем полный путь vs относительный
            if os.path.sep in sound_file or '/' in sound_file:
                path = sound_file
            else:
                # Звуки лежат в папке темы, НЕ в папке варианта
                path = os.path.join(self.themes_dir, self.theme_name, "sounds", sound_file)
            
            path = os.path.normpath(path)
                
            if not os.path.isfile(path):
                logger.warning(f"Sound not found: {path}")
                return ""
            return path
        except Exception as e:
            logger.error(f"Error getting sound {name}: {e}")
            return ""

    # ================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ================================================

    def is_loaded(self):
        """Проверить, загружена ли тема"""
        return self.theme_name is not None and self.variant is not None

    def diagnose_state(self):
        """РАСШИРЕННАЯ диагностика состояния ThemeManager"""
        state = {
            "theme_name": self.theme_name,
            "variant": self.variant,
            "current_theme": self.current_theme,
            "current_variant": self.current_variant,
            "is_loaded": self.is_loaded(),
            "loading_in_progress": self._loading_in_progress,
            "notification_disabled": self._notification_disabled,
            "themes_dir": self.themes_dir,
            "themes_dir_exists": os.path.exists(self.themes_dir),
            "theme_data_keys": list(self.theme_data.keys()) if self.theme_data else [],
            "colors_count": len(self.theme_data.get("colors", {})),
            "fonts_count": len(self.theme_data.get("fonts", {})),
            "images_count": len(self.theme_data.get("images", {})),
            "sounds_count": len(self.theme_data.get("sounds", {}))
        }
        
        # Проверяем структуру папок
        if self.theme_name:
            theme_dir = os.path.join(self.themes_dir, self.theme_name)
            fonts_dir = os.path.join(theme_dir, "fonts")
            variant_dir = os.path.join(theme_dir, self.variant) if self.variant else None
            
            state.update({
                "theme_dir": theme_dir,
                "theme_dir_exists": os.path.exists(theme_dir),
                "fonts_dir": fonts_dir,
                "fonts_dir_exists": os.path.exists(fonts_dir),
                "variant_dir": variant_dir,
                "variant_dir_exists": os.path.exists(variant_dir) if variant_dir else False
            })
            
            # Список файлов в папке шрифтов
            if os.path.exists(fonts_dir):
                try:
                    state["fonts_files"] = os.listdir(fonts_dir)
                except Exception as e:
                    state["fonts_files_error"] = str(e)
        
        return state

    def debug_font_path(self, font_name):
        """НОВЫЙ: Отладочная информация о пути к конкретному шрифту"""
        logger.info(f"🔍 DEBUG: Font path analysis for '{font_name}'")
        
        # Базовая информация
        logger.info(f"  Theme: {self.theme_name}")
        logger.info(f"  Variant: {self.variant}")
        logger.info(f"  Themes dir: {self.themes_dir}")
        
        # Проверяем theme_data
        fonts = self.theme_data.get("fonts", {})
        logger.info(f"  Available fonts: {fonts}")
        
        font_file = fonts.get(font_name)
        logger.info(f"  Font file for '{font_name}': '{font_file}'")
        
        if font_file:
            # Строим путь
            path = os.path.join(self.themes_dir, self.theme_name, "fonts", font_file)
            path = os.path.normpath(path)
            logger.info(f"  Constructed path: '{path}'")
            logger.info(f"  File exists: {os.path.isfile(path)}")
            
            # Проверяем структуру папок
            fonts_dir = os.path.join(self.themes_dir, self.theme_name, "fonts")
            logger.info(f"  Fonts directory: '{fonts_dir}'")
            logger.info(f"  Fonts directory exists: {os.path.exists(fonts_dir)}")
            
            if os.path.exists(fonts_dir):
                try:
                    files = os.listdir(fonts_dir)
                    logger.info(f"  Files in fonts directory: {files}")
                except Exception as e:
                    logger.info(f"  Error listing fonts directory: {e}")


# ================================================
# ГЛОБАЛЬНЫЕ ФУНКЦИИ
# ================================================

# Глобальный экземпляр
theme_manager = ThemeManager()


def get_theme_manager():
    """Безопасное получение экземпляра ThemeManager"""
    return theme_manager


def validate_theme_manager_module():
    """Валидация модуля ThemeManager для отладки"""
    try:
        tm = ThemeManager()
        
        # Проверяем наличие всех методов
        required_methods = [
            'load_theme', 'load', 'load_silently', 'force_reload',
            'get_color', 'get_rgba', 'get_param', 'get_font', 
            'get_image', 'get_overlay', 'get_sound',
            'is_loaded', 'diagnose_state', 'debug_font_path'
        ]
        
        for method in required_methods:
            assert hasattr(tm, method), f"{method} method missing"
        
        # Проверяем защиту от циклов
        assert hasattr(tm, '_loading_in_progress'), "_loading_in_progress flag missing"
        assert hasattr(tm, '_notification_disabled'), "_notification_disabled flag missing"
        
        print("✅ ThemeManager module validation passed")
        return True
    except Exception as e:
        print(f"❌ ThemeManager module validation failed: {e}")
        return False


# Только в режиме разработки
if __name__ == "__main__":
    validate_theme_manager_module()