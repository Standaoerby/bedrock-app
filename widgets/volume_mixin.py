# widgets/volume_mixin.py
from kivy.app import App
from kivy.clock import Clock
from app.logger import app_logger as logger


class VolumeControlMixin:
    """Миксин для добавления управления громкостью через VolumeManager на любой экран"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_volume = 50
        self._volume_manager_available = False
    
    def setup_volume_control(self):
        """Инициализация управления громкостью (вызывать в on_pre_enter)"""
        try:
            app = App.get_running_app()
            # ИСПРАВЛЕНО: используем volume_manager вместо volume_service
            if hasattr(app, 'volume_manager') and app.volume_manager:
                self._volume_manager_available = True
                self._current_volume = app.volume_manager.get_volume()
                logger.debug(f"Volume control готов на {self.__class__.__name__}: {self._current_volume}%")
            else:
                self._volume_manager_available = False
                logger.warning(f"VolumeManager недоступен на {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Ошибка инициализации volume control на {self.__class__.__name__}: {e}")
            self._volume_manager_available = False
    
    def volume_up(self, step=5):
        """Увеличение громкости (можно вызывать из любого экрана)"""
        if not self._volume_manager_available:
            logger.warning("VolumeManager недоступен")
            return False
            
        try:
            app = App.get_running_app()
            old_volume = self._current_volume
            
            # ИСПРАВЛЕНО: используем методы VolumeManager
            success = app.volume_manager.volume_up(step)
            new_volume = app.volume_manager.get_volume()
            
            if success:
                self._current_volume = new_volume
                logger.info(f"🔊 Громкость UP на {self.__class__.__name__}: {old_volume}% → {new_volume}%")
                self._play_volume_sound("confirm")
                return True
            else:
                logger.warning(f"Громкость не изменилась на {self.__class__.__name__}: {old_volume}% → {new_volume}%")
                self._play_volume_sound("error")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка volume_up на {self.__class__.__name__}: {e}")
            return False
    
    def volume_down(self, step=5):
        """Уменьшение громкости (можно вызывать из любого экрана)"""
        if not self._volume_manager_available:
            logger.warning("VolumeManager недоступен")
            return False
            
        try:
            app = App.get_running_app()
            old_volume = self._current_volume
            
            # ИСПРАВЛЕНО: используем методы VolumeManager
            success = app.volume_manager.volume_down(step)
            new_volume = app.volume_manager.get_volume()
            
            if success:
                self._current_volume = new_volume
                logger.info(f"🔉 Громкость DOWN на {self.__class__.__name__}: {old_volume}% → {new_volume}%")
                self._play_volume_sound("click") 
                return True
            else:
                logger.warning(f"Громкость не изменилась на {self.__class__.__name__}: {old_volume}% → {new_volume}%")
                self._play_volume_sound("error")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка volume_down на {self.__class__.__name__}: {e}")
            return False
    
    def get_volume(self):
        """Получение текущей громкости"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_manager') and app.volume_manager:
                volume = app.volume_manager.get_volume()
                self._current_volume = volume
                return volume
            return self._current_volume
        except Exception as e:
            logger.error(f"Ошибка получения громкости: {e}")
            return self._current_volume
    
    def mute_toggle(self):
        """Переключение отключения звука"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'volume_manager') and app.volume_manager:
                status = app.volume_manager.get_status()
                if status.get('is_muted', False):
                    success = app.volume_manager.unmute()
                    action = "включен"
                else:
                    success = app.volume_manager.mute()
                    action = "отключен"
                
                if success:
                    logger.info(f"🔇 Звук {action} на {self.__class__.__name__}")
                    self._play_volume_sound("click")
                    return True
                else:
                    logger.warning(f"Не удалось переключить звук на {self.__class__.__name__}")
                    return False
            return False
        except Exception as e:
            logger.error(f"Ошибка переключения звука: {e}")
            return False
    
    def _play_volume_sound(self, sound_name):
        """Воспроизведение звука обратной связи"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'audio_service') and hasattr(app, 'theme_manager'):
                if app.audio_service and app.theme_manager:
                    sound_file = app.theme_manager.get_sound(sound_name)
                    if sound_file:
                        Clock.schedule_once(lambda dt: app.audio_service.play(sound_file), 0.01)
        except Exception as e:
            logger.debug(f"Не удалось воспроизвести звук '{sound_name}': {e}")


