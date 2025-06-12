# services/audio_service.py - ИСПРАВЛЕНИЕ для thread safety с toggle кнопками
import os
import time
import threading
from kivy.clock import Clock, mainthread
from app.logger import app_logger as logger

try:
    from pygame import mixer
    PYGAME_AVAILABLE = True
    logger.info("🎵 Pygame mixer imported successfully")
except ImportError as e:
    PYGAME_AVAILABLE = False
    logger.error(f"❌ Failed to import pygame mixer: {e}")

try:
    import alsaaudio
    ALSA_AVAILABLE = True
except ImportError:
    ALSA_AVAILABLE = False

class AudioService:
    """
    Thread-safe аудио сервис с исправлениями для toggle кнопок
    """
    
    def __init__(self, device_preference=None):
        # ИСПРАВЛЕНИЕ: Добавляем thread safety
        self._init_lock = threading.RLock()  # RLock позволяет повторные блокировки в том же потоке
        self._state_lock = threading.Lock()   # Отдельный lock для состояния
        
        # Состояние воспроизведения (thread-safe)
        self._is_playing = False
        self._current_file = None
        self._is_long_audio = False
        self._last_play_time = 0
        
        # ИСПРАВЛЕНИЕ: Callbacks для UI обновлений
        self._ui_callbacks = []
        
        # Настройки устройства
        self.audio_device = device_preference
        self._mixer_initialized = False
        self._initialization_attempted = False
        
        # Инициализация в отдельном потоке
        self._init_thread = threading.Thread(target=self._initialize_audio, daemon=True)
        self._init_thread.start()

    def _initialize_audio(self):
        """Thread-safe инициализация аудио системы"""
        with self._init_lock:
            if self._initialization_attempted:
                return
            self._initialization_attempted = True
            
            if not PYGAME_AVAILABLE:
                logger.error("❌ Pygame not available - audio service disabled")
                return

            try:
                # Настройка ALSA устройства если доступно
                if ALSA_AVAILABLE and self.audio_device:
                    self._setup_alsa_device()
                
                # Инициализация pygame mixer
                mixer.pre_init(
                    frequency=44100,
                    size=-16,
                    channels=2,
                    buffer=1024
                )
                mixer.init()
                
                self._mixer_initialized = True
                logger.info(f"🎵 Audio service initialized successfully on {self.audio_device}")
                
                # Уведомляем UI об успешной инициализации
                self._notify_ui_callbacks('audio_initialized', True)
                
            except Exception as e:
                logger.error(f"❌ Audio service initialization failed: {e}")
                self._mixer_initialized = False
                self._notify_ui_callbacks('audio_initialized', False)

    def _setup_alsa_device(self):
        """Настройка ALSA устройства"""
        try:
            if isinstance(self.audio_device, str) and self.audio_device.startswith("hw:"):
                os.environ['SDL_AUDIODRIVER'] = 'alsa'
                os.environ['ALSA_CARD'] = self.audio_device.replace("hw:", "")
                logger.info(f"🔊 ALSA device configured: {self.audio_device}")
        except Exception as e:
            logger.warning(f"⚠️ ALSA device setup failed: {e}")

    # ========================================
    # THREAD-SAFE STATE MANAGEMENT
    # ========================================

    def _get_state(self):
        """Thread-safe получение состояния"""
        with self._state_lock:
            return {
                'is_playing': self._is_playing,
                'current_file': self._current_file,
                'is_long_audio': self._is_long_audio,
                'last_play_time': self._last_play_time
            }

    def _set_state(self, **kwargs):
        """Thread-safe обновление состояния"""
        with self._state_lock:
            if 'is_playing' in kwargs:
                self._is_playing = kwargs['is_playing']
            if 'current_file' in kwargs:
                self._current_file = kwargs['current_file']
            if 'is_long_audio' in kwargs:
                self._is_long_audio = kwargs['is_long_audio']
            if 'last_play_time' in kwargs:
                self._last_play_time = kwargs['last_play_time']

    def _reset_state(self):
        """Thread-safe сброс состояния"""
        with self._state_lock:
            old_playing = self._is_playing
            self._is_playing = False
            self._current_file = None
            self._is_long_audio = False
            
            # Уведомляем UI о изменении состояния если нужно
            if old_playing:
                self._notify_ui_callbacks('playback_stopped', None)

    # ========================================
    # UI CALLBACKS MANAGEMENT
    # ========================================

    def add_ui_callback(self, callback):
        """Добавить callback для уведомления UI"""
        if callback not in self._ui_callbacks:
            self._ui_callbacks.append(callback)

    def remove_ui_callback(self, callback):
        """Удалить callback"""
        if callback in self._ui_callbacks:
            self._ui_callbacks.remove(callback)

    @mainthread
    def _notify_ui_callbacks(self, event_type, data):
        """Thread-safe уведомление UI callbacks"""
        for callback in self._ui_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in UI callback: {e}")

    # ========================================
    # THREAD-SAFE AUDIO PLAYBACK
    # ========================================

    def play(self, filepath, fadein=0):
        """Thread-safe воспроизведение звука"""
        if not self.is_mixer_initialized():
            logger.warning("🔇 Audio service not initialized - skipping playback")
            return
            
        if not os.path.exists(filepath):
            logger.error(f"❌ Audio file not found: {filepath}")
            return

        # Выполняем актуальное воспроизведение в фоновом потоке
        threading.Thread(
            target=self._play_audio_thread,
            args=(filepath, fadein),
            daemon=True
        ).start()

    def _play_audio_thread(self, filepath, fadein):
        """Фоновое воспроизведение аудио (НЕ блокирует UI)"""
        with self._init_lock:
            try:
                # Проверяем состояние и защиту от спама
                state = self._get_state()
                is_ringtone = not any(short_sound in os.path.basename(filepath).lower() 
                                    for short_sound in ['click', 'confirm', 'error', 'notify', 'startup'])
                
                current_time = time.time()
                
                # Защита от слишком частого воспроизведения
                if current_time - state['last_play_time'] < 0.1 and not is_ringtone:
                    logger.debug(f"Skipping audio play - too frequent")
                    return
                
                # Если уже играет длинный звук (рингтон), не прерываем
                if state['is_long_audio'] and self._is_pygame_busy():
                    if not is_ringtone:
                        logger.debug(f"Skipping audio play - ringtone is playing")
                        return
                
                # Останавливаем текущее воспроизведение
                if self._is_pygame_busy():
                    mixer.music.stop()
                    time.sleep(0.05)  # Короткая задержка для освобождения
                
                # Устанавливаем состояние
                self._set_state(
                    is_playing=True,
                    current_file=filepath,
                    is_long_audio=is_ringtone,
                    last_play_time=current_time
                )
                
                # Загружаем и воспроизводим файл
                mixer.music.load(filepath)
                
                if fadein > 0:
                    mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
                else:
                    mixer.music.play()
                    
                mixer.music.set_volume(1.0)
                
                logger.debug(f"🎵 Playing audio: {os.path.basename(filepath)} on {self.audio_device}")
                
                # Уведомляем UI о начале воспроизведения
                self._notify_ui_callbacks('playback_started', {
                    'file': filepath,
                    'is_ringtone': is_ringtone
                })
                
                # Если это рингтон, запускаем мониторинг завершения
                if is_ringtone:
                    self._monitor_ringtone_completion()
                    
            except Exception as e:
                logger.error(f"❌ AudioService play error: {e}")
                self._reset_state()

    def _monitor_ringtone_completion(self):
        """Мониторинг завершения воспроизведения рингтона"""
        def check_completion():
            try:
                if not self._is_pygame_busy():
                    logger.debug("🎵 Ringtone playback completed")
                    self._reset_state()
                else:
                    # Проверяем снова через 0.5 секунды
                    Clock.schedule_once(lambda dt: check_completion(), 0.5)
            except Exception as e:
                logger.error(f"Error monitoring ringtone: {e}")
                self._reset_state()
        
        Clock.schedule_once(lambda dt: check_completion(), 0.5)

    def play_async(self, filepath, fadein=0):
        """Асинхронное воспроизведение звука (алиас для play)"""
        self.play(filepath, fadein)

    def stop(self):
        """Thread-safe остановка воспроизведения"""
        logger.debug(f"🛑 AudioService.stop() called")
        
        if not self.is_mixer_initialized():
            logger.debug("Mixer not initialized - clearing state only")
            self._reset_state()
            return
        
        try:
            with self._init_lock:
                if self._get_state()['is_playing'] or self._is_pygame_busy():
                    mixer.music.stop()
                    time.sleep(0.05)  # Короткая задержка
        except Exception as e:
            logger.error(f"❌ AudioService stop error: {e}")
        finally:
            self._reset_state()

    # ========================================
    # THREAD-SAFE STATE QUERIES
    # ========================================

    def is_busy(self):
        """Thread-safe проверка активности воспроизведения"""
        if not self.is_mixer_initialized():
            # Если mixer не инициализирован, сбрасываем состояние
            if self._get_state()['is_playing']:
                self._reset_state()
            return False
            
        try:
            busy = self._is_pygame_busy()
            
            # Синхронизируем состояние с pygame
            state = self._get_state()
            if not busy and state['is_playing']:
                logger.debug(f"🔍 Pygame not busy but is_playing=True - syncing state")
                self._reset_state()
                
            return busy
        except Exception as e:
            logger.error(f"❌ AudioService is_busy error: {e}")
            self._reset_state()
            return False

    def _is_pygame_busy(self):
        """Безопасная проверка состояния pygame"""
        try:
            return mixer.music.get_busy()
        except Exception:
            return False

    def is_mixer_initialized(self):
        """Thread-safe проверка инициализации mixer"""
        with self._init_lock:
            return self._mixer_initialized and PYGAME_AVAILABLE

    # ========================================
    # UTILITY METHODS
    # ========================================

    def get_device_info(self):
        """Получение информации об аудиоустройстве"""
        info = {
            "device": self.audio_device,
            "device_type": "usb" if "hw:" in str(self.audio_device) else "system_default",
            "alsa_available": ALSA_AVAILABLE,
            "mixer_initialized": self.is_mixer_initialized(),
            "current_state": self._get_state()
        }
        
        if ALSA_AVAILABLE:
            try:
                info["alsa_cards"] = alsaaudio.cards()
            except:
                info["alsa_cards"] = []
                
        return info

    def cleanup(self):
        """Освобождение ресурсов"""
        logger.info("🧹 Cleaning up audio service...")
        
        try:
            self.stop()
            
            if self.is_mixer_initialized():
                mixer.quit()
                
            self._ui_callbacks.clear()
            
        except Exception as e:
            logger.error(f"Error during audio service cleanup: {e}")

    def __del__(self):
        """Деструктор"""
        try:
            self.cleanup()
        except:
            pass  # Игнорируем ошибки в деструкторе


# Создаем глобальный экземпляр для совместимости с main.py
audio_service = AudioService()