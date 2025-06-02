# Настройка Audio Bonnet для приложения Bedrock

Полное руководство по настройке WM8960 Audio Bonnet для вывода звука из приложения Bedrock на Raspberry Pi 5.

## Предварительные требования

- Raspberry Pi 5 с установленной ОС
- WM8960 Audio Bonnet (физически подключен к GPIO)
- Активная виртуальная среда Python (.venv)
- Приложение Bedrock

## 1. Проверка установки Audio Bonnet

### Проверить, что Audio Bonnet определился системой:

```bash
# Проверить доступные аудиоустройства
aplay -l

# Проверить содержимое /proc/asound/cards
cat /proc/asound/cards
```

**Ожидаемый результат:**
```
card 0: wm8960soundcard [wm8960-soundcard], device 0: ...
```

### Если Audio Bonnet не отображается:

1. Проверьте физическое подключение HAT к GPIO
2. Убедитесь в настройках `/boot/config.txt`:
   ```bash
   sudo nano /boot/config.txt
   ```
   Должно быть:
   ```
   dtparam=audio=on
   dtoverlay=wm8960-soundcard
   ```
3. Перезагрузите Pi: `sudo reboot`

## 2. Установка системных зависимостей

```bash
# Обновить систему
sudo apt update

# Установить ALSA утилиты и dev пакеты
sudo apt install alsa-utils python3-dev libasound2-dev

# Активировать виртуальную среду
source .venv/bin/activate

# Установить pyalsaaudio для работы с ALSA
pip install pyalsaaudio
```

## 3. Настройка ALSA конфигурации

### Создать файл конфигурации ALSA:

```bash
sudo nano /etc/asound.conf
```

### Добавить следующее содержимое:

```
# Конфигурация для WM8960 Audio Bonnet
pcm.!default {
    type plug
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
    }
}

ctl.!default {
    type hw
    card 0
}

# Дополнительные устройства для совместимости
pcm.wm8960 {
    type hw
    card 0
    device 0
}

pcm.bonnet {
    type plug
    slave {
        pcm "hw:0,0"
        rate 44100
        channels 2
        format S16_LE
    }
}
```

## 4. Установка громкости

```bash
# Установить громкость для различных миксеров
amixer -c 0 set Speaker 80% unmute 2>/dev/null
amixer -c 0 set Headphone 80% unmute 2>/dev/null  
amixer -c 0 set Master 80% unmute 2>/dev/null

# Проверить доступные миксеры
amixer -c 0 scontrols
```

## 5. Обновление AudioService

### Заменить содержимое файла `services/audio_service.py`:

```python
import os
import time
import logging
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
    def __init__(self):
        self.is_playing = False
        self.current_file = None
        self.is_long_audio = False
        self.last_play_time = 0
        self._is_stopped = False
        self.audio_device = None
        
        # Инициализируем аудиосистему
        self._init_audio()
        
    def _init_audio(self):
        """Инициализация аудиосистемы с поддержкой Audio Bonnet"""
        try:
            # Сначала пытаемся найти Audio Bonnet
            bonnet_device = self._find_audio_bonnet()
            
            if bonnet_device:
                logger.info(f"Found Audio Bonnet: {bonnet_device}")
                self._init_pygame_with_device(bonnet_device)
            else:
                logger.warning("Audio Bonnet not found, using default audio")
                self._init_pygame_default()
                
        except Exception as e:
            logger.error(f"Audio initialization error: {e}")
            # Fallback к базовой инициализации
            self._init_pygame_default()

    def _find_audio_bonnet(self):
        """Поиск Audio Bonnet в системе"""
        try:
            if ALSA_AVAILABLE:
                # Ищем карты ALSA
                cards = alsaaudio.cards()
                logger.info(f"Available ALSA cards: {cards}")
                
                # Ищем Audio Bonnet по известным именам
                bonnet_names = [
                    'audioinjectorpi', 
                    'audioinjector-pi-soundcard',
                    'AudioInjector',
                    'wm8731',
                    'wm8960soundcard',  # WM8960 Audio Bonnet
                    'wm8960-soundcard',
                    'wm8960'
                ]
                
                for i, card in enumerate(cards):
                    for bonnet_name in bonnet_names:
                        if bonnet_name.lower() in card.lower():
                            logger.info(f"Found Audio Bonnet card: {card} (index {i})")
                            return f"hw:{i},0"
                            
            # Альтернативный метод через /proc/asound/cards
            try:
                with open('/proc/asound/cards', 'r') as f:
                    cards_info = f.read()
                    logger.debug(f"ALSA cards info:\n{cards_info}")
                    
                    lines = cards_info.strip().split('\n')
                    for line in lines:
                        if any(name in line.lower() for name in ['audioinjector', 'wm8731', 'wm8960']):
                            # Извлекаем номер карты
                            card_num = line.split()[0]
                            return f"hw:{card_num},0"
                            
            except Exception as e:
                logger.warning(f"Could not read /proc/asound/cards: {e}")
                
        except Exception as e:
            logger.error(f"Error finding Audio Bonnet: {e}")
            
        return None

    def _init_pygame_with_device(self, device):
        """Инициализация pygame с конкретным аудиоустройством"""
        try:
            # Настраиваем переменную окружения для SDL
            os.environ['SDL_AUDIODRIVER'] = 'alsa'
            os.environ['AUDIODEV'] = device
            
            # Инициализируем pygame mixer с оптимальными настройками для Audio Bonnet
            mixer.pre_init(
                frequency=44100,    # CD качество
                size=-16,           # 16-bit signed
                channels=2,         # Стерео
                buffer=1024         # Буфер для низкой задержки
            )
            mixer.init()
            
            # Тест воспроизведения
            if self._test_audio_output():
                logger.info(f"AudioService initialized with Audio Bonnet device: {device}")
                self.audio_device = device
                return True
            else:
                logger.warning("Audio Bonnet test failed, falling back to default")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing pygame with Audio Bonnet: {e}")
            return False

    def _init_pygame_default(self):
        """Базовая инициализация pygame mixer"""
        try:
            mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            mixer.init()
            logger.info("AudioService initialized with default audio")
            self.audio_device = "default"
        except Exception as e:
            logger.error(f"Default audio initialization error: {e}")

    def _test_audio_output(self):
        """Тест аудиовыхода"""
        try:
            # Простой тест - проверяем, что mixer инициализирован
            return mixer.get_init() is not None
        except Exception as e:
            logger.error(f"Audio test failed: {e}")
            return False

    def set_volume(self, value):
        """Установка громкости"""
        try:
            volume = max(0.0, min(1.0, value))
            mixer.music.set_volume(volume)
            
            # Дополнительно устанавливаем системную громкость если доступно ALSA
            if ALSA_AVAILABLE and self.audio_device and 'hw:' in self.audio_device:
                try:
                    card_index = int(self.audio_device.split(':')[1].split(',')[0])
                    mixer_control = alsaaudio.Mixer('Master', cardindex=card_index)
                    alsa_volume = int(volume * 100)
                    mixer_control.setvolume(alsa_volume)
                    logger.debug(f"Set ALSA volume to {alsa_volume}%")
                except Exception as e:
                    logger.warning(f"Could not set ALSA volume: {e}")
                    
        except Exception as e:
            logger.error(f"AudioService set_volume error: {e}")

    def play(self, filepath, fadein=0):
        """Воспроизведение файла"""
        if not filepath or not os.path.isfile(filepath):
            logger.warning(f"Audio file not found: {filepath}")
            return
            
        try:
            is_ringtone = 'ringtones' in filepath
            is_theme_sound = any(sound_type in filepath for sound_type in 
                               ['click', 'confirm', 'error', 'notify', 'startup'])
            
            current_time = time.time()
            
            # Не прерываем рингтон коротким звуком
            if (self.is_playing and self.is_long_audio and is_theme_sound):
                return
            
            # Не играем короткий звук слишком часто
            if (self.is_playing and not self.is_long_audio and 
                (current_time - self.last_play_time) < 0.2):
                return
            
            # Останавливаем текущее воспроизведение если нужно
            if self.is_playing:
                if (self.is_long_audio and is_ringtone) or (not self.is_long_audio):
                    self.stop()
            
            self.is_playing = True
            self.current_file = filepath
            self.is_long_audio = is_ringtone
            self.last_play_time = current_time
            
            mixer.music.load(filepath)
            if fadein > 0:
                mixer.music.play(loops=0, fade_ms=int(fadein * 1000))
            else:
                mixer.music.play()
            mixer.music.set_volume(1.0)
            
            logger.debug(f"Playing audio: {os.path.basename(filepath)} on device: {self.audio_device}")
            
        except Exception as e:
            logger.error(f"AudioService play error: {e}")
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def stop(self):
        """Остановка воспроизведения"""
        try:
            mixer.music.stop()
        except Exception as e:
            logger.error(f"AudioService stop error: {e}")
        finally:
            self.is_playing = False
            self.current_file = None
            self.is_long_audio = False

    def is_busy(self):
        """Проверка активности воспроизведения"""
        try:
            return mixer.music.get_busy()
        except Exception as e:
            logger.error(f"AudioService is_busy error: {e}")
            return False

    def get_device_info(self):
        """Получение информации об аудиоустройстве"""
        info = {
            "device": self.audio_device,
            "alsa_available": ALSA_AVAILABLE,
            "mixer_initialized": mixer.get_init() is not None
        }
        
        if ALSA_AVAILABLE:
            try:
                info["alsa_cards"] = alsaaudio.cards()
            except:
                info["alsa_cards"] = []
                
        return info

    def reinitialize_audio(self):
        """Переинициализация аудиосистемы"""
        logger.info("Reinitializing audio system...")
        try:
            mixer.quit()
        except:
            pass
            
        self._init_audio()


# Создаем глобальный экземпляр
audio_service = AudioService()
```

## 6. Настройка переменных окружения

### Создать файл переменных окружения:

```bash
cat > ~/.bashrc_audio << 'EOF'
# Переменные окружения для аудио
export SDL_AUDIODRIVER=alsa
export AUDIODEV=hw:0,0
export ALSA_CARD=0
EOF
```

### Добавить в .bashrc:

```bash
echo 'source ~/.bashrc_audio' >> ~/.bashrc
source ~/.bashrc
```

## 7. Тестирование установки

### Создать тестовый файл `test_audio.py`:

```python
#!/usr/bin/env python3
import os
import sys
import time

# Добавляем путь к проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from services.audio_service import AudioService

def test_audio_system():
    print("=== Тест Audio Bonnet ===")
    
    audio = AudioService()
    device_info = audio.get_device_info()
    
    print(f"Аудиоустройство: {device_info['device']}")
    print(f"ALSA доступно: {device_info['alsa_available']}")
    print(f"Mixer инициализирован: {device_info['mixer_initialized']}")
    
    if device_info['alsa_available']:
        print(f"ALSA карты: {device_info['alsa_cards']}")
    
    # Тест воспроизведения
    test_sounds = [
        "themes/minecraft/sounds/click.ogg",
        "themes/minecraft/sounds/notify.ogg"
    ]
    
    for sound in test_sounds:
        if os.path.exists(sound):
            print(f"Тестируем: {sound}")
            audio.play(sound)
            time.sleep(1)
            audio.stop()
            print("✓ Готово")
        else:
            print(f"✗ Файл не найден: {sound}")

if __name__ == "__main__":
    test_audio_system()
```

### Запустить тест:

```bash
python test_audio.py
```

**Ожидаемый результат:**
```
=== Тест Audio Bonnet ===
[INFO] Found Audio Bonnet card: wm8960soundcard (index 0)
[INFO] AudioService initialized with Audio Bonnet device: hw:0,0
Аудиоустройство: hw:0,0
ALSA доступно: True
Mixer инициализирован: True
ALSA карты: ['wm8960soundcard', 'vc4hdmi0', 'vc4hdmi1']
✓ Готово
```

## 8. Дополнительные команды для диагностики

### Прямое тестирование Audio Bonnet:

```bash
# Тест speaker-test
speaker-test -c 2 -r 44100 -D hw:0,0 -t sine -l 1

# Проверка статуса ALSA
aplay -l
cat /proc/asound/cards

# Управление громкостью
alsamixer
amixer -c 0 scontrols
```

### Если звук не воспроизводится:

1. **Проверить подключение наушников/колонок** к Audio Bonnet
2. **Проверить громкость**: `amixer -c 0 set Speaker 90%`
3. **Перезагрузить Pi**: `sudo reboot`
4. **Проверить физическое подключение** HAT к GPIO

## 9. Запуск основного приложения

После успешного тестирования:

```bash
# Запустить приложение Bedrock
python main.py
```

Теперь все звуки интерфейса (клики, уведомления, будильник) будут воспроизводиться через Audio Bonnet!

## Результат

✅ **WM8960 Audio Bonnet полностью настроен и работает с приложением Bedrock**  
✅ **Все звуки приложения выводятся через Audio Bonnet**  
✅ **Поддержка как коротких звуков интерфейса, так и длинных мелодий будильника**  
✅ **Автоматическое определение и использование правильного аудиоустройства**