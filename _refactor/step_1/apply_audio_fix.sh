#!/bin/bash
# ========================
# Применение исправления AudioService
# ========================

echo "🔧 === ПРИМЕНЕНИЕ ИСПРАВЛЕНИЯ AUDIOSERVICE ==="
echo ""

# Проверяем что мы в корне проекта
if [ ! -f "main.py" ] || [ ! -d "services" ]; then
    echo "❌ Ошибка: Запустите скрипт из корня проекта Bedrock"
    echo "   Должны быть файлы main.py и папка services/"
    exit 1
fi

# Создаем резервную копию
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
echo "💾 Создаем резервную копию в $BACKUP_DIR/"
mkdir -p "$BACKUP_DIR"

if [ -f "services/audio_service.py" ]; then
    cp "services/audio_service.py" "$BACKUP_DIR/audio_service_original.py"
    echo "✅ Резервная копия создана: $BACKUP_DIR/audio_service_original.py"
else
    echo "⚠️  Файл services/audio_service.py не найден - создаем новый"
fi

# Проверяем зависимости
echo ""
echo "🔍 Проверяем зависимости..."

# Проверяем pygame
python3 -c "import pygame; print('✅ pygame доступен')" 2>/dev/null || {
    echo "❌ pygame не найден"
    echo "   Установите: pip install pygame"
    exit 1
}

# Проверяем app.logger
python3 -c "from app.logger import app_logger; print('✅ app.logger доступен')" 2>/dev/null || {
    echo "❌ app.logger не найден"
    echo "   Проверьте структуру проекта"
    exit 1
}

# Проверяем alsaaudio (опционально)
python3 -c "import alsaaudio; print('✅ alsaaudio доступен')" 2>/dev/null || {
    echo "⚠️  alsaaudio не найден (необязательно для Pi 5)"
    echo "   Можно установить: sudo apt install python3-alsaaudio"
}

echo ""
echo "🚀 Применяем оптимизированный AudioService..."

# Создаем оптимизированный AudioService
cat > services/audio_service.py << 'EOF'
# services/audio_service.py
# ОПТИМИЗИРОВАНО v2.1.1: Убрана избыточная диагностика для производительности

import os
import time
import threading
from pygame import mixer
from app.logger import app_logger as logger

# Попытка импорта ALSA для прямого управления
try:
    import alsaaudio
    ALSA_AVAILABLE = True
except ImportError:
    ALSA_AVAILABLE = False
    logger.warning("alsaaudio not available - using default pygame mixer")


class AudioService:
    """
    ОПТИМИЗИРОВАНО: Сервис для воспроизведения аудио 
    - Убрана избыточная диагностика
    - Убраны дорогие inspect.stack() вызовы
    - Оптимизирован logging
    - Улучшен thread safety
    """
    
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False
        self.last_play_time = 0
        self._is_stopped = False
        self.audio_device = None
        self._mixer_initialized = False
        self._init_lock = threading.RLock()  # ИЗМЕНЕНО: RLock вместо Lock
        
        # ОПТИМИЗИРОВАНО: Версионирование без избыточного логирования
        self._service_version = "2.1.1"  # Версия с оптимизациями
        self._instance_id = id(self)
        
        # КРИТИЧНО: Убираем детальное логирование при инициализации
        logger.debug(f"AudioService v{self._service_version} initializing")
        
        # Инициализируем аудиосистему
        self._safe_init_audio()
        
        logger.info("AudioService initialization complete")

    def _safe_init_audio(self):
        """ОПТИМИЗИРОВАНО: Инициализация аудио без избыточного логирования"""
        try:
            with self._init_lock:
                # Проверяем, не инициализирован ли уже mixer
                if mixer.get_init():
                    logger.debug("Pygame mixer already initialized")
                    self._mixer_initialized = True
                    self.audio_device = "system_default"
                    return

                # Безопасно завершаем предыдущую инициализацию
                self._safe_quit_mixer()
                
                # Попытка найти USB устройство (быстро, без детального логирования)
                usb_device = self._find_usb_audio_device()
                
                # Инициализация
                if usb_device and self._init_pygame_with_device(usb_device):
                    logger.info(f"USB audio device initialized: {usb_device}")
                elif self._init_pygame_default():
                    logger.info("System default audio initialized")
                else:
                    logger.error("Failed to initialize any audio device")
                    self._mixer_initialized = False
                    return
                
                self._mixer_initialized = True
                
        except Exception as e:
            logger.error(f"Audio initialization error: {e}")
            self._mixer_initialized = False

    def _find_usb_audio_device(self):
        """ОПТИМИЗИРОВАНО: Быстрый поиск USB устройства без детального логирования"""
        if not ALSA_AVAILABLE:
            return None
            
        try:
            cards = alsaaudio.cards()
            # Быстрая проверка USB устройств
            for i, card_name in enumerate(cards):
                if any(usb_indicator in card_name.lower() for usb_indicator in ['usb', 'gs3']):
                    return f"hw:{i},0"
        except Exception:
            pass  # Игнорируем ошибки, используем fallback
            
        return None

    def _init_pygame_with_device(self, device):
        """ОПТИМИЗИРОВАНО: Инициализация с устройством"""
        try:
            import os
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            os.environ['AUDIODEV'] = device
            
            mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
            mixer.init()
            
            self.audio_device = device
            return True
            
        except Exception:
            return False

    def _init_pygame_default(self):
        """ОПТИМИЗИРОВАНО: Инициализация по умолчанию"""
        try:
            mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
            mixer.init()
            self.audio_device = "system_default"
            return True
        except Exception:
            return False

    def _safe_quit_mixer(self):
        """Безопасное завершение mixer"""
        try:
            if mixer.get_init():
                mixer.quit()
                time.sleep(0.05)
        except Exception:
            pass

    def is_mixer_initialized(self):
        """Проверка инициализации mixer"""
        try:
            return self._mixer_initialized and mixer.get_init() is not None
        except Exception:
            self._mixer_initialized = False
            return False

    def play(self, filepath, fadein=0):
        """
        КРИТИЧЕСКИ ОПТИМИЗИРОВАНО: Воспроизведение файла
        - Убран дорогой inspect.stack() вызов
        - Убрана избыточная диагностика
        - Упрощено логирование
        """
        if not filepath or not os.path.isfile(filepath):
            logger.warning(f"Audio file not found: {filepath}")
            return
            
        # БЫСТРАЯ ПРОВЕРКА: mixer готов?
        if not self.is_mixer_initialized():
            logger.warning("AudioService: mixer not ready")
            return
            
        try:
            with self._init_lock:
                # Определяем тип аудио (быстро)
                file_size = os.path.getsize(filepath)
                self.is_long_audio = file_size > 1024 * 1024
                
                # ОПТИМИЗИРОВАНО: Минимальное логирование
                logger.debug(f"Playing: {os.path.basename(filepath)}")
                
                # Останавливаем предыдущее
                if mixer.music.get_busy():
                    mixer.music.stop()
                    time.sleep(0.02)  # Уменьшенная задержка
                
                # Загружаем и воспроизводим
                mixer.music.load(filepath)
                
                if fadein > 0:
                    mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
                else:
                    mixer.music.play(loops=0)
                
                # Обновляем состояние
                self.is_playing = True
                self.current_file = filepath
                self.last_play_time = time.time()
                
                # УПРОЩЕННОЕ логирование
                logger.debug(f"✅ Playing: {os.path.basename(filepath)}")
                
        except Exception as e:
            logger.error(f"AudioService play error: {e}")
            self._reset_state()

    def play_async(self, filepath, fadein=0):
        """Асинхронное воспроизведение"""
        threading.Thread(
            target=self.play,
            args=(filepath,),
            kwargs={"fadein": fadein},
            daemon=True,
        ).start()

    def stop(self):
        """ОПТИМИЗИРОВАНО: Остановка воспроизведения"""
        if not self.is_mixer_initialized():
            self._reset_state()
            return
        
        try:
            with self._init_lock:
                if mixer.music.get_busy():
                    mixer.music.stop()
                    time.sleep(0.02)  # Уменьшенная задержка
        except Exception as e:
            logger.error(f"AudioService stop error: {e}")
        finally:
            self._reset_state()

    def _reset_state(self):
        """Сброс внутреннего состояния"""
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False

    def is_busy(self):
        """Проверка активности воспроизведения"""
        if not self.is_mixer_initialized():
            if self.is_playing:
                self._reset_state()
            return False
            
        try:
            busy = mixer.music.get_busy()
            # Синхронизируем состояние
            if not busy and self.is_playing:
                self._reset_state()
            return busy
        except Exception:
            self._reset_state()
            return False

    def set_volume(self, value):
        """Установка громкости"""
        if not self.is_mixer_initialized():
            return
            
        try:
            volume = max(0.0, min(1.0, value))
            mixer.music.set_volume(volume)
        except Exception as e:
            logger.error(f"AudioService set_volume error: {e}")

    def diagnose_state(self):
        """Диагностика состояния (ТОЛЬКО для отладки)"""
        try:
            mixer_init = self.is_mixer_initialized()
            pygame_busy = mixer.music.get_busy() if mixer_init else False
            pygame_init = mixer.get_init() if mixer_init else None
            
            return {
                "instance_id": self._instance_id,
                "service_version": self._service_version,
                "mixer_initialized": mixer_init,
                "is_playing": self.is_playing,
                "current_file": self.current_file,
                "is_long_audio": self.is_long_audio,
                "pygame_busy": pygame_busy,
                "pygame_init": pygame_init,
                "audio_device": self.audio_device,
                "alsa_available": ALSA_AVAILABLE
            }
        except Exception as e:
            return {"error": str(e), "instance_id": self._instance_id}

    def verify_instance(self):
        """Верификация экземпляра AudioService"""
        return {
            "class_name": self.__class__.__name__,
            "instance_id": self._instance_id,
            "service_version": getattr(self, '_service_version', 'unknown'),
            "has_diagnose_state": hasattr(self, 'diagnose_state'),
            "has_play": hasattr(self, 'play'),
            "has_stop": hasattr(self, 'stop'),
            "methods": [method for method in dir(self) if not method.startswith('_')]
        }


# КРИТИЧНО: НЕ создаем глобальный экземпляр
EOF

echo "✅ Оптимизированный AudioService применен"
echo ""
echo "🔄 ВАЖНЫЕ ИЗМЕНЕНИЯ:"
echo "   ✅ Убраны дорогие inspect.stack() вызовы"
echo "   ✅ Уменьшено логирование при каждом звуке"
echo "   ✅ Оптимизированы задержки (0.02s вместо 0.05s)"
echo "   ✅ Улучшен thread safety (RLock)"
echo "   ✅ Быстрая инициализация USB аудио"
echo ""
echo "📦 РЕЗЕРВНАЯ КОПИЯ:"
echo "   Оригинал сохранен в: $BACKUP_DIR/audio_service_original.py"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo "   1. Запустите приложение: python3 main.py"
echo "   2. Проверьте логи на уменьшение verbose сообщений"
echo "   3. Протестируйте воспроизведение звуков"
echo "   4. Переходите к Шагу 4 если все работает"
echo ""
echo "🔙 ОТКАТ (если нужен):"
echo "   cp $BACKUP_DIR/audio_service_original.py services/audio_service.py"
