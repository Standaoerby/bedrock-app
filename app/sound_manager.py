import time
from app.logger import app_logger as logger

class SoundManager:
    """Централизованное управление звуками UI с защитой от дублирования"""
    
    def __init__(self):
        self._last_click_time = 0
        self._last_toggle_time = 0
        self._click_delay = 0.2  # 200мс между кликами
        self._toggle_delay = 0.3  # 300мс между toggle звуками
    
    def play_click(self, force=False):
        """Воспроизведение звука клика"""
        current_time = time.time()
        
        if not force and current_time - self._last_click_time < self._click_delay:
            return False
            
        self._last_click_time = current_time
        return self._play_sound("click")
    def play_confirm(self, force=False):
        """Воспроизведение звука подтверждения"""
        return self._play_sound("confirm")

    def play_error(self, force=False):
        """Воспроизведение звука ошибки"""
        return self._play_sound("error")

    def play_notify(self, force=False):
        """Воспроизведение звука уведомления"""
        return self._play_sound("notify")
    
    def play_toggle(self, force=False):
        """Воспроизведение звука переключения"""
        current_time = time.time()
        
        if not force and current_time - self._last_toggle_time < self._toggle_delay:
            return False
            
        self._last_toggle_time = current_time
        return self._play_sound("click")  # Используем тот же звук
    
    def _play_sound(self, sound_name):
        """Базовый метод воспроизведения звука"""
        try:
            from kivy.app import App
            app = App.get_running_app()
            
            if not hasattr(app, 'audio_service') or not app.audio_service:
                return False
                
            if not hasattr(app, 'theme_manager') or not app.theme_manager:
                return False
                
            sound_file = app.theme_manager.get_sound(sound_name)
            if sound_file:
                app.audio_service.play(sound_file)
                return True
                
        except Exception as e:
            logger.error(f"Error playing sound '{sound_name}': {e}")
            
        return False

# Глобальный экземпляр
sound_manager = SoundManager()