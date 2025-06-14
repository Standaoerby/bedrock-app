# app/theme_manager.py
# 🔥 FULLY FIXED - Enhanced theme manager with 8-digit hex color support for 2025

import os
import json
from kivy.utils import get_color_from_hex
from app.logger import app_logger as logger
from app.event_bus import event_bus


class ThemeManager:
    """
    🔥 ENHANCED theme manager with full 8-digit hex color support.
    Handles RGBA hex colors properly for modern UI transparency effects.
    """
    
    def __init__(self, themes_dir="themes"):
        self.themes_dir = themes_dir
        self.theme_name = None
        self.variant = None
        self.theme_data = {}
        
        # Compatibility with existing code
        self.current_theme = None
        self.current_variant = None
        
        # Protection against circular loading
        self._loading_in_progress = False
        self._notification_disabled = False
        
        # Resource caching for performance
        self._resource_cache = {}
        
        # Enhanced default theme with fallbacks
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
                "background_highlighted": "#e8e8e8",
                "overlay_card": "#ffffff80",  # 8-digit hex example
                "menu_color": "#25252580",
                "menu_button_text": "#ffffff",
                "menu_button_text_active": "#40916c"
            },
            "fonts": {
                "main": "",
                "title": ""
            },
            "images": {
                "background": "",
                "button_bg": "",
                "button_bg_active": "",
                "menu_button_bg": "", 
                "menu_button_bg_active": "",
                "overlay_home": "",
                "overlay_alarm": "",
                "overlay_schedule": "",
                "overlay_weather": "",
                "overlay_pigs": "",
                "overlay_settings": "",
                "overlay_default": ""
            },
            "sounds": {
                "click": "",
                "notify": "",
                "error": "",
                "confirm": "",
                "startup": ""
            }
        }

    def load(self, theme_name, variant="dark"):
        """🔥 ENHANCED: Load theme with better error handling"""
        if self._loading_in_progress:
            logger.warning("Theme loading already in progress, skipping")
            return False
            
        self._loading_in_progress = True
        try:
            theme_path = os.path.join(self.themes_dir, theme_name, variant, "theme.json")
            
            if not os.path.isfile(theme_path):
                logger.error(f"Theme file not found: {theme_path}")
                self._load_default_theme()
                return False
            
            with open(theme_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            # Validate and merge with defaults
            self.theme_data = self._merge_with_defaults(theme_data)
            self.theme_name = theme_name
            self.variant = variant
            
            # Update compatibility properties
            self.current_theme = theme_name
            self.current_variant = variant
            
            # Clear cache and notify
            self._clear_resource_cache()
            self._notify_theme_change()
            
            logger.info(f"✅ Theme loaded: {theme_name}/{variant}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading theme {theme_name}/{variant}: {e}")
            self._load_default_theme()
            return False
        finally:
            self._loading_in_progress = False

    def _merge_with_defaults(self, theme_data):
        """🔥 NEW: Merge theme data with defaults to prevent missing keys"""
        merged = self.default_theme.copy()
        
        # Deep merge each section
        for section in ["colors", "fonts", "images", "sounds"]:
            if section in theme_data:
                merged[section].update(theme_data[section])
        
        # Merge other sections directly
        for key, value in theme_data.items():
            if key not in ["colors", "fonts", "images", "sounds"]:
                merged[key] = value
                
        return merged

    def _load_default_theme(self):
        """Load default theme as fallback"""
        self.theme_data = self.default_theme.copy()
        self.theme_name = "default"
        self.variant = "light"
        self.current_theme = "default"
        self.current_variant = "light"
        logger.info("Loaded default theme as fallback")

    def _hex_to_rgba(self, hex_color):
        """🔥 FIXED: Enhanced hex to RGBA conversion with 8-digit support"""
        try:
            if not hex_color or not hex_color.startswith('#'):
                logger.warning(f"Invalid hex color format: {hex_color}")
                return (1.0, 1.0, 1.0, 1.0)
            
            hex_clean = hex_color[1:]  # Remove #
            
            if len(hex_clean) == 6:
                # Standard 6-digit hex (RGB)
                r = int(hex_clean[0:2], 16) / 255.0
                g = int(hex_clean[2:4], 16) / 255.0  
                b = int(hex_clean[4:6], 16) / 255.0
                return (r, g, b, 1.0)
                
            elif len(hex_clean) == 8:
                # 🔥 NEW: 8-digit hex (RGBA) support
                r = int(hex_clean[0:2], 16) / 255.0
                g = int(hex_clean[2:4], 16) / 255.0
                b = int(hex_clean[4:6], 16) / 255.0
                a = int(hex_clean[6:8], 16) / 255.0
                return (r, g, b, a)
                
            else:
                logger.warning(f"Invalid hex color length: {hex_color}")
                return (1.0, 1.0, 1.0, 1.0)
                
        except ValueError as e:
            logger.error(f"Error converting hex to RGBA: {e}")
            return (1.0, 1.0, 1.0, 1.0)

    def get_rgba(self, color_name, fallback=(1, 1, 1, 1)):
        """🔥 ENHANCED: Get color in RGBA format with caching and better fallback"""
        cache_key = f"rgba_{color_name}_{self.theme_name}_{self.variant}"
        
        if cache_key not in self._resource_cache:
            try:
                hex_color = self.theme_data.get("colors", {}).get(color_name)
                
                if hex_color:
                    rgba = self._hex_to_rgba(hex_color)
                    self._resource_cache[cache_key] = rgba
                else:
                    # Try fallback from default theme
                    fallback_hex = self.default_theme["colors"].get(color_name)
                    if fallback_hex:
                        rgba = self._hex_to_rgba(fallback_hex)
                        self._resource_cache[cache_key] = rgba
                    else:
                        self._resource_cache[cache_key] = fallback
                        
            except Exception as e:
                logger.warning(f"Error getting RGBA for {color_name}: {e}")
                self._resource_cache[cache_key] = fallback
                
        return self._resource_cache[cache_key]

    def get_image(self, image_name, fallback=""):
        """🔥 ENHANCED: Get image with better path resolution and validation"""
        try:
            image_path = self.theme_data.get("images", {}).get(image_name, fallback)
            
            if not image_path:
                return fallback
                
            # Handle absolute paths
            if os.path.isabs(image_path):
                if os.path.isfile(image_path):
                    return image_path
                else:
                    logger.warning(f"Absolute image path not found: {image_path}")
                    return fallback
            
            # Handle relative paths
            theme_images_dir = os.path.join(self.themes_dir, self.theme_name, self.variant, "images")
            full_path = os.path.join(theme_images_dir, image_path)
            
            if os.path.isfile(full_path):
                return full_path
            else:
                logger.warning(f"Image file not found: {full_path}")
                
                # 🔥 NEW: Try creating missing images directory
                if not os.path.exists(theme_images_dir):
                    logger.info(f"Creating missing images directory: {theme_images_dir}")
                    os.makedirs(theme_images_dir, exist_ok=True)
                
                return fallback
                
        except Exception as e:
            logger.warning(f"Error getting image {image_name}: {e}")
            return fallback

    def get_color(self, color_name, fallback="#FFFFFF"):
        """Get color in HEX format with caching"""
        cache_key = f"color_{color_name}_{self.theme_name}_{self.variant}"
        
        if cache_key not in self._resource_cache:
            try:
                color_value = self.theme_data.get("colors", {}).get(color_name, fallback)
                self._resource_cache[cache_key] = color_value
            except Exception as e:
                logger.warning(f"Error getting color {color_name}: {e}")
                self._resource_cache[cache_key] = fallback
                
        return self._resource_cache[cache_key]

    def get_font(self, font_name, fallback=""):
        """Get font path with validation"""
        try:
            font_path = self.theme_data.get("fonts", {}).get(font_name, fallback)
            
            if not font_path:
                return fallback
                
            if not os.path.isabs(font_path):
                theme_font_dir = os.path.join(self.themes_dir, self.theme_name, "fonts")
                full_path = os.path.join(theme_font_dir, font_path)
                
                if os.path.isfile(full_path):
                    return full_path
                else:
                    logger.warning(f"Font file not found: {full_path}")
                    return fallback
            
            return font_path if os.path.isfile(font_path) else fallback
            
        except Exception as e:
            logger.warning(f"Error getting font {font_name}: {e}")
            return fallback

    def get_param(self, param_name, fallback=None):
        """Get theme parameter from menu, layout, or params sections"""
        try:
            for section in ["menu", "layout", "params"]:
                if section in self.theme_data:
                    value = self.theme_data[section].get(param_name)
                    if value is not None:
                        return value
            return fallback
        except Exception as e:
            logger.warning(f"Error getting param {param_name}: {e}")
            return fallback

    def get_overlay(self, page_name):
        """Get overlay image for page"""
        return self.get_image(f"overlay_{page_name}", self.get_image("overlay_default"))

    def get_sound(self, sound_name, fallback=""):
        """Get sound path with validation"""
        try:
            sound_path = self.theme_data.get("sounds", {}).get(sound_name, fallback)
            
            if not sound_path:
                return fallback
                
            if not os.path.isabs(sound_path):
                theme_sounds_dir = os.path.join(self.themes_dir, self.theme_name, "sounds")
                full_path = os.path.join(theme_sounds_dir, sound_path)
                
                if os.path.isfile(full_path):
                    return full_path
                else:
                    logger.warning(f"Sound file not found: {full_path}")
                    return fallback
            
            return sound_path if os.path.isfile(sound_path) else fallback
            
        except Exception as e:
            logger.warning(f"Error getting sound {sound_name}: {e}")
            return fallback

    def _clear_resource_cache(self):
        """Clear resource cache"""
        self._resource_cache.clear()
        logger.debug("Resource cache cleared")

    def _notify_theme_change(self):
        """Notify about theme change"""
        if self._notification_disabled:
            return
            
        try:
            event_bus.publish("theme_changed", {
                "theme": self.theme_name,
                "variant": self.variant,
                "source": "theme_manager"
            })
            logger.info(f"🎨 Theme changed event published: {self.theme_name}/{self.variant}")
        except Exception as e:
            logger.error(f"Error notifying theme change: {e}")

    def is_loaded(self):
        """Check if theme is loaded"""
        return bool(self.theme_data and self.theme_name)

    def diagnose_state(self):
        """🔥 NEW: Diagnostic method for debugging"""
        return {
            "theme_name": self.theme_name,
            "variant": self.variant,
            "is_loaded": self.is_loaded(),
            "cache_size": len(self._resource_cache),
            "loading_in_progress": self._loading_in_progress,
            "colors_count": len(self.theme_data.get("colors", {})),
            "images_count": len(self.theme_data.get("images", {}))
        }