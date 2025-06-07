# 🎧 Настройка Waveshare WM8960 Audio Board для Bedrock 2.0

## ✅ Текущий статус
По диагностике видно что **WM8960 аудио-плата работает корректно**:
- Обнаружена как `wm8960soundcard` (card 0)
- Доступны миксеры: Headphone, Speaker, Playbook и другие
- Звук слышно (подтверждено пользователем)

## 🔧 Необходимые исправления в Bedrock 2.0

### 1. Обновление AudioService
В файле `services/audio_service.py` нужно:
- Добавить `'wm8960-soundcard'` (с дефисом) в список поиска
- Увеличить buffer size до 2048 для стабильности I2S
- Добавить специальную диагностику для WM8960

### 2. Обновление VolumeService  
В файле `services/volume_service.py` нужно:
- Обновить приоритеты миксеров: `Headphone`, `Speaker`, `Playbook` в начало списка
- Добавить специальную логику для WM8960 миксеров
- Улучшить диагностику и тестирование

## 🚀 Быстрое применение исправлений

### Вариант 1: Автоматический патч
```bash
# Сохраните скрипт apply_wm8960_patches.sh в папку Bedrock
chmod +x apply_wm8960_patches.sh
./apply_wm8960_patches.sh
```

### Вариант 2: Ручное применение
1. Замените методы в `services/audio_service.py` на версии из артефакта
2. Замените приоритеты в `services/volume_service.py` на:
```python
MIXER_PRIORITIES = [
    'Headphone',    # WM8960 основной выход
    'Speaker',      # WM8960 динамики  
    'Playbook',     # WM8960 общий плейбэк
    'Master', 'PCM', 'Digital', 'Line Out'
]
```

## 🧪 Тестирование

### 1. Быстрый тест аппаратуры
```bash
# Проверка аудио карт
aplay -l | grep wm8960

# Проверка миксеров
amixer scontrols | grep -E "(Headphone|Speaker|Playbook)"

# Тест воспроизведения (если есть тестовый файл)
speaker-test -c 2 -r 44100 -t wav -D hw:0,0
```

### 2. Тест Bedrock сервисов
```bash
# Запустите тест-скрипт
python3 test_wm8960.py
```

### 3. Полный тест в приложении
1. Запустите Bedrock: `python3 main.py`
2. Перейдите в настройки (Settings)
3. Попробуйте кнопки VOL+ / VOL- 
4. Перейдите на экран будильника (Alarm)
5. Протестируйте воспроизведение мелодии

## 🔍 Диагностика проблем

### Если нет звука:
1. Проверьте подключение динамиков/наушников к WM8960
2. Проверьте уровни миксеров:
```bash
amixer get Headphone
amixer get Speaker  
amixer get Playbook
```
3. Попробуйте установить громкость:
```bash
amixer set Headphone 80%
amixer set Speaker 80%
```

### Если не работает управление громкостью:
1. Проверьте доступные миксеры: `amixer scontrols`
2. Убедитесь что миксеры не в состоянии "off"
3. Проверьте логи Bedrock для ошибок VolumeService

### Если pygame не инициализируется:
1. Убедитесь что установлены библиотеки: `pip install pygame`
2. Проверьте что ALSA работает: `python3 -c "import alsaaudio; print(alsaaudio.cards())"`
3. Перезагрузите Raspberry Pi после установки драйверов

## 📋 Диагностическая информация

### Ваша текущая конфигурация:
- **Аудио карта**: `wm8960soundcard` (card 0)
- **Устройство**: `hw:0,0`
- **Доступные миксеры**: Headphone, Speaker, Playbook и другие
- **Статус**: Звук работает ✅

### Рекомендуемые настройки /boot/config.txt:
```
# Если у вас Waveshare WM8960 Audio Board
dtoverlay=wm8960-soundcard
```

## 🎯 Ожидаемые результаты после исправлений:

1. ✅ **AudioService** корректно обнаружит WM8960 как `hw:0,0`
2. ✅ **VolumeService** будет использовать миксер `Headphone` или `Speaker`
3. ✅ **Управление громкостью** через кнопки VOL+/VOL- в настройках
4. ✅ **Воспроизведение звуков** темы (клики, уведомления)
5. ✅ **Воспроизведение мелодий** будильника
6. ✅ **Аппаратные кнопки громкости** (если подключены к GPIO 23/24)

## 🏁 После применения исправлений

Перезапустите Bedrock и проверьте в логах сообщения типа:
```
AudioService initialized with WM8960 Audio Board: hw:0,0
VolumeService: Selected mixer: Headphone
```

Если видите такие сообщения - всё работает корректно! 🎉