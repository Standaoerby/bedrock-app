# Bedrock 2.1 - Smart Home Control System

🏠 Система управления умным домом для Raspberry Pi 5 с сенсорным интерфейсом, построенная на Python и Kivy framework.

## 📋 Оглавление

- [Особенности](#особенности)
- [Требования](#требования)
- [Установка](#установка)
- [Архитектура](#архитектура)
- [Конфигурация](#конфигурация)
- [Использование](#использование)
- [Разработка](#разработка)
- [Темы](#темы)
- [Локализация](#локализация)
- [API](#api)
- [Устранение неполадок](#устранение-неполадок)

## ✨ Особенности

### 🎯 Основная функциональность
- **Умный будильник** с настраиваемыми мелодиями и отсрочкой
- **Мониторинг погоды** с прогнозами и визуализацией
- **Система расписания** для управления задачами и событиями
- **Мониторинг питомцев** (специализировано для морских свинок)
- **Аудио система** с поддержкой Voice Bonnet/I2S
- **Сенсорное управление** оптимизированное для сенсорных экранов

### 🎨 Пользовательский интерфейс
- **Система тем** с полной кастомизацией
- **Адаптивный дизайн** с сеткой позиционирования 8px
- **Темная/светлая темы** включая тему Minecraft
- **Анимированные переходы** между экранами
- **Локализация** интерфейса

### 🔧 Техническая архитектура
- **Модульная архитектура** с разделением на сервисы
- **Event Bus** для связи между компонентами
- **Централизованное управление состоянием**
- **Система логирования**
- **Cross-platform** поддержка (Raspberry Pi + Windows)

## 📋 Требования

### Аппаратные требования
- **Raspberry Pi 5** (рекомендуется 4GB+ RAM)
- **Сенсорный экран** 7-10 дюймов
- **SD карта** Class 10, 32GB+
- **Voice Bonnet** или USB аудио (опционально)
- **GPIO сенсоры** (опционально)

### Программные требования
- **Python 3.9+**
- **Raspberry Pi OS** (Bookworm рекомендуется)
- **Git** для клонирования репозитория

## 🚀 Установка

### Быстрая установка на Raspberry Pi

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/bedrock-2.1.git
cd bedrock-2.1

# Установка зависимостей
sudo apt update
sudo apt install python3-pip python3-venv git

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
pip install -r requirements.txt

# Первый запуск
python main.py
```

### Установка для разработки на Windows 11

```bash
# Клонирование в VS Code
git clone https://github.com/yourusername/bedrock-2.1.git

# Открытие в VS Code
code bedrock-2.1

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Запуск в режиме разработки
python main.py --dev
```

## 🏗️ Архитектура

### Структура проекта

```
bedrock-2.1/
├── main.py                 # Точка входа приложения
├── app/
│   ├── app_state.py        # Глобальное состояние
│   ├── event_bus.py        # Система событий
│   ├── theme_manager.py    # Управление темами
│   └── logger.py           # Система логирования
├── services/
│   ├── audio_service.py    # Аудио система
│   ├── alarm_service.py    # Сервис будильника
│   ├── weather_service.py  # Погодный сервис
│   ├── pigs_service.py     # Уход за питомцами
│   └── sensor_service.py   # GPIO сенсоры
├── pages/
│   ├── home.py            # Главный экран
│   ├── alarm.py           # Настройки будильника
│   ├── weather.py         # Погода
│   ├── schedule.py        # Расписание
│   ├── pigs.py           # Мониторинг питомцев
│   └── settings.py        # Настройки системы
├── themes/
│   └── minecraft/         # Тема Minecraft
│       ├── light/
│       └── dark/
├── config/                # Конфигурационные файлы
├── assets/               # Ресурсы (шрифты, звуки, изображения)
└── tests/                # Тесты
```

### Ключевые компоненты

#### **main.py**
Точка входа приложения:
- Инициализация ScreenManager
- Подключение event bus
- Загрузка тем и настроек

#### **app_state.py**
Централизованное состояние:
```python
from app.app_state import AppState

# Получение состояния
state = AppState()
current_user = state.get('user_name', 'Guest')

# Обновление состояния
state.set('last_alarm', '07:30')
```

#### **event_bus.py**
Система событий:
```python
from app.event_bus import EventBus

# Подписка на события
EventBus.subscribe('alarm_triggered', self.handle_alarm)

# Отправка событий
EventBus.publish('theme_changed', {'theme': 'minecraft'})
```

#### **theme_manager.py**
Управление темами:
```python
from app.theme_manager import ThemeManager

# Получение цветов
primary_color = theme_manager.get_rgba('primary')
font_path = theme_manager.get_font('main')
```

## ⚙️ Конфигурация

### Основные настройки

**config/main.json**
```json
{
  "app": {
    "name": "Bedrock 2.1",
    "version": "2.1.0",
    "debug": false,
    "fullscreen": true
  },
  "audio": {
    "device": "hw:0,0",
    "volume": 0.8,
    "enabled": true
  },
  "display": {
    "width": 1024,
    "height": 600,
    "orientation": "landscape"
  }
}
```

**config/pigs.json** (Уход за питомцами)
```json
{
  "pigs": [
    {"name": "Korovka", "breed": "Guinea Pig"},
    {"name": "Karamelka", "breed": "Guinea Pig"}
  ],
  "care_items": {
    "water": {"max_hours": 8, "label": "Water"},
    "food": {"max_hours": 6, "label": "Food"},
    "clean": {"max_hours": 12, "label": "Cleaning"}
  }
}
```

### Переменные окружения

Создайте файл `.env`:
```bash
# API ключи
WEATHER_API_KEY=your_weather_api_key
TIMEZONE=Europe/Moscow

# GPIO настройки (только для Pi)
GPIO_ENABLED=true
VOLUME_PIN=18
SENSOR_PINS=19,20,21

# Режим разработки
DEBUG=false
DEV_MODE=false
```

## 🎮 Использование

### Основные экраны

#### 🏠 Главный экран (Home)
- Отображение времени и даты
- Быстрый доступ к основным функциям
- Статус системы и уведомления

#### ⏰ Будильник (Alarm)
- Настройка времени будильника
- Выбор мелодий
- Настройка повторений

#### 🌤️ Погода (Weather)
- Текущая погода
- Прогноз на несколько дней
- Графики температуры

#### 🐹 Питомцы (Pigs)
- Мониторинг кормления
- Отслеживание ухода
- Напоминания о задачах

#### ⚙️ Настройки (Settings)
- Смена тем
- Настройки звука
- Конфигурация системы

### Горячие клавиши

- **ESC** - Выход из приложения
- **F11** - Переключение полноэкранного режима
- **Ctrl+R** - Перезагрузка приложения
- **Ctrl+T** - Смена темы

## 🛠️ Разработка

### Настройка среды разработки

#### VS Code на Windows 11
```bash
# Установка расширений
code --install-extension ms-python.python
code --install-extension ms-python.pylint
code --install-extension ms-python.black-formatter

# Настройка Python интерпретатора
# Ctrl+Shift+P -> Python: Select Interpreter
# Выберите venv/Scripts/python.exe
```

#### Настройка для Raspberry Pi
```bash
# SSH подключение для удаленной разработки
ssh pi@raspberrypi.local

# Синхронизация кода
rsync -av --exclude 'venv' . pi@raspberrypi.local:~/bedrock-2.1/
```

### Создание нового экрана

```python
# pages/new_screen.py
from kivy.uix.screenmanager import Screen
from app.event_bus import EventBus
from app.logger import app_logger as logger

class NewScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("NewScreen initialized")
        
    def on_enter(self):
        """Вызывается при входе на экран"""
        EventBus.publish('screen_changed', {'screen': 'new_screen'})
        
    def on_leave(self):
        """Вызывается при выходе с экрана"""
        pass
```

### Создание нового сервиса

```python
# services/new_service.py
from app.logger import app_logger as logger
from app.event_bus import EventBus

class NewService:
    def __init__(self):
        self.enabled = True
        logger.info("NewService initialized")
        
    def start(self):
        """Запуск сервиса"""
        if self.enabled:
            logger.info("NewService started")
            
    def stop(self):
        """Остановка сервиса"""
        logger.info("NewService stopped")
```

### Тестирование

```bash
# Запуск всех тестов
python -m pytest tests/

# Тестирование конкретного модуля
python -m pytest tests/test_services.py

# Тестирование с покрытием
python -m pytest --cov=app tests/
```

## 🎨 Темы

### Структура темы

```
themes/theme_name/
├── variant/              # light/dark
│   ├── theme.json       # Основная конфигурация
│   ├── assets/          # Ресурсы темы
│   │   ├── images/      # Изображения
│   │   ├── sounds/      # Звуки
│   │   └── fonts/       # Шрифты
```

### Создание новой темы

**themes/custom/light/theme.json**
```json
{
  "colors": {
    "background": "#FFFFFF",
    "primary": "#2196F3",
    "text": "#212121",
    "text_secondary": "#757575"
  },
  "fonts": {
    "main": "Roboto-Regular.ttf",
    "title": "Roboto-Bold.ttf"
  },
  "images": {
    "background": "bg.jpg",
    "button_bg": "btn.9.png"
  },
  "sounds": {
    "click": "click.wav",
    "notify": "notification.wav"
  }
}
```

### Использование темы в коде

```python
# В KV файлах
color: app.theme_manager.get_rgba("primary")
font_name: app.theme_manager.get_font("main")

# В Python коде
from app.theme_manager import ThemeManager
theme = ThemeManager()
bg_color = theme.get_rgba("background")
```

## 🌍 Локализация

### Поддерживаемые языки
- 🇷🇺 Русский (ru)
- 🇺🇸 English (en)
- 🇩🇪 Deutsch (de) - в разработке

### Добавление перевода

**locales/ru/LC_MESSAGES/messages.po**
```po
msgid "Good morning!"
msgstr "Доброе утро!"

msgid "Settings"
msgstr "Настройки"
```

### Использование в коде

```python
from app.i18n import _

# В Python
title = _("Settings")

# В KV файлах  
text: app.get_text("Good morning!")
```

## 📡 API

### Event Bus API

```python
# Подписка на события
EventBus.subscribe('alarm_triggered', callback)

# Отправка событий
EventBus.publish('theme_changed', {'theme': 'dark'})

# Отписка от событий
EventBus.unsubscribe('alarm_triggered', callback)
```

### Сервисы API

#### Audio Service
```python
from services.audio_service import AudioService

audio = AudioService()
audio.play("notification.wav")
audio.set_volume(0.8)
audio.stop_all()
```

#### Pigs Service
```python
from services.pigs_service import PigsService

pigs = PigsService()
pigs.reset_care("water")
status = pigs.get_care_status("food")
```

## 🔧 Устранение неполадок

### Общие проблемы

#### Приложение не запускается
```bash
# Проверка зависимостей
pip list | grep -i kivy

# Проверка Python версии
python --version  # Должно быть 3.9+

# Запуск с отладкой
python main.py --debug
```

#### Проблемы с аудио на Pi
```bash
# Проверка аудио устройств
aplay -l

# Тестирование звука
speaker-test -t wav -c 2

# Настройка алсы
sudo raspi-config -> Advanced Options -> Audio
```

#### GPIO ошибки
```bash
# Проверка прав доступа
sudo usermod -a -G gpio pi

# Освобождение GPIO
sudo systemctl stop bedrock
```

### Логи и отладка

```bash
# Просмотр логов приложения
tail -f logs/bedrock.log

# Системные логи
journalctl -u bedrock -f

# Отладочный режим
DEBUG=true python main.py
```

### Производительность

```bash
# Мониторинг ресурсов
htop

# Профилирование Python
python -m cProfile main.py

# Проверка температуры Pi
vcgencmd measure_temp
```

## 📞 Поддержка

### Сообщение о проблемах
- **GitHub Issues**: [github.com/yourusername/bedrock-2.1/issues](https://github.com/yourusername/bedrock-2.1/issues)
- **Wiki**: [github.com/yourusername/bedrock-2.1/wiki](https://github.com/yourusername/bedrock-2.1/wiki)

### Участие в разработке
1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## 📄 Лицензия

Распространяется под MIT License. См. `LICENSE` для подробностей.

## 🙏 Благодарности

- **Kivy Team** за отличный UI framework
- **Raspberry Pi Foundation** за замечательную платформу
- **Сообщество разработчиков** за вклад и обратную связь

---

**Версия**: 2.1.0  
**Последнее обновление**: Июнь 2025  
**Совместимость**: Python 3.9+, Raspberry Pi 5, Windows 11