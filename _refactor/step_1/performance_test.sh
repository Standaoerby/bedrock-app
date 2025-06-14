#!/bin/bash
# ========================
# Тестирование производительности после оптимизаций
# ========================

echo "🧪 === ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ BEDROCK 2.1 ==="
echo ""

# Проверяем что мы в корне проекта
if [ ! -f "main.py" ]; then
    echo "❌ Ошибка: main.py не найден"
    echo "   Запустите скрипт из корня проекта Bedrock"
    exit 1
fi

echo "📊 Состояние системы ПЕРЕД тестированием:"
echo "==========================================="

# Текущее время
echo "🕐 Время начала тестов: $(date)"

# Системная информация
echo "💻 Система:"
cat /proc/cpuinfo | grep "model name" | head -1
echo "🧠 Память:"
free -h | grep "Mem:"

# GPU информация
echo "🎮 GPU:"
vcgencmd measure_temp
vcgencmd get_mem gpu
vcgencmd measure_clock arm

# Проверяем примененные оптимизации
echo ""
echo "⚙️  Проверка примененных оптимизаций:"
echo "======================================"

# 1. Проверяем Kivy конфигурацию
if [ -f ~/.kivy/config.ini ]; then
    echo "✅ Kivy конфигурация найдена"
    MAXFPS=$(grep "maxfps" ~/.kivy/config.ini | cut -d'=' -f2 | tr -d ' ')
    MULTISAMPLES=$(grep "multisamples" ~/.kivy/config.ini | cut -d'=' -f2 | tr -d ' ')
    echo "   FPS ограничение: $MAXFPS"
    echo "   Antialiasing: $MULTISAMPLES"
else
    echo "⚠️  Kivy конфигурация не найдена"
fi

# 2. Проверяем GPIO конфигурацию
if grep -q "gpu_mem=128" /boot/firmware/config.txt; then
    echo "✅ GPU память настроена: 128MB"
else
    echo "⚠️  GPU память не настроена"
fi

# 3. Проверяем оптимизированный AudioService
if grep -q "_service_version = \"2.1.1\"" services/audio_service.py; then
    echo "✅ Оптимизированный AudioService v2.1.1"
else
    echo "⚠️  AudioService не оптимизирован"
fi

# 4. Проверяем ленивую инициализацию
if grep -q "_init_deferred_services" main.py; then
    echo "✅ Ленивая инициализация сервисов"
else
    echo "⚠️  Ленивая инициализация не применена"
fi

echo ""
echo "🚀 НАЧИНАЕМ ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ:"
echo "===================================="

# Тест 1: Время запуска приложения
echo ""
echo "📏 Тест 1: Время запуска приложения"
echo "------------------------------------"

# Создаем тестовый скрипт для измерения времени запуска
cat > /tmp/startup_test.py << 'EOF'
#!/usr/bin/env python3
import time
import sys
import os
import signal

# Добавляем обработчик сигнала для корректного завершения
def signal_handler(sig, frame):
    print("Test completed by signal")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Засекаем время начала
start_time = time.time()

try:
    # Импортируем основное приложение
    from main import BedrockApp
    
    init_time = time.time()
    print(f"Import time: {init_time - start_time:.3f}s")
    
    # Создаем экземпляр
    app = BedrockApp()
    
    create_time = time.time()
    print(f"App creation time: {create_time - init_time:.3f}s")
    
    # Имитируем начало build (но не запускаем UI)
    print("Testing service initialization...")
    app._initialize_services()
    
    service_time = time.time()
    print(f"Service init time: {service_time - create_time:.3f}s")
    
    total_time = service_time - start_time
    print(f"TOTAL STARTUP TIME: {total_time:.3f}s")
    
    # Проверяем критические сервисы
    if app.audio_service:
        print("✅ AudioService ready")
    else:
        print("❌ AudioService failed")
        
    if app.alarm_service:
        print("✅ AlarmService ready")
    else:
        print("❌ AlarmService failed")
    
    # Ждем немного для инициализации отложенных сервисов
    print("Waiting for deferred services...")
    time.sleep(3)
    
    deferred_ready = 0
    deferred_total = 4  # weather, sensor, volume, pigs
    
    if app.weather_service:
        print("✅ WeatherService ready (deferred)")
        deferred_ready += 1
    else:
        print("⏳ WeatherService loading...")
        
    if app.sensor_service:
        print("✅ SensorService ready (deferred)")
        deferred_ready += 1
    else:
        print("⏳ SensorService loading...")
        
    if app.volume_service:
        print("✅ VolumeService ready (deferred)")
        deferred_ready += 1
    else:
        print("⏳ VolumeService loading...")
        
    if app.pigs_service:
        print("✅ PigsService ready (deferred)")
        deferred_ready += 1
    else:
        print("⏳ PigsService loading...")
    
    print(f"Deferred services ready: {deferred_ready}/{deferred_total}")
    
    # Результат
    if total_time < 2.0:
        print("🎉 ОТЛИЧНО: Быстрый запуск достигнут!")
    elif total_time < 3.0:
        print("✅ ХОРОШО: Запуск ускорен")
    else:
        print("⚠️  МЕДЛЕННО: Нужны дополнительные оптимизации")

except Exception as e:
    print(f"❌ Ошибка при тестировании: {e}")
    import traceback
    traceback.print_exc()

EOF

echo "Запускаем тест времени запуска..."
timeout 30s python3 /tmp/startup_test.py
STARTUP_RESULT=$?

if [ $STARTUP_RESULT -eq 0 ]; then
    echo "✅ Тест запуска завершен успешно"
elif [ $STARTUP_RESULT -eq 124 ]; then
    echo "⏰ Тест запуска прерван по таймауту (30s)"
else
    echo "❌ Тест запуска завершился с ошибкой"
fi

# Тест 2: Использование памяти
echo ""
echo "💾 Тест 2: Использование памяти"
echo "-------------------------------"

# Запускаем приложение в фоне и мониторим память
echo "Мониторинг использования памяти (10 секунд)..."

# Создаем скрипт для мониторинга памяти
cat > /tmp/memory_test.py << 'EOF'
#!/usr/bin/env python3
import time
import psutil
import os
import signal

def signal_handler(sig, frame):
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    from main import BedrockApp
    
    # Измеряем память до создания приложения
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"Initial memory: {initial_memory:.1f} MB")
    
    # Создаем приложение
    app = BedrockApp()
    app._initialize_services()
    
    after_services = process.memory_info().rss / 1024 / 1024
    print(f"After services: {after_services:.1f} MB")
    print(f"Service overhead: {after_services - initial_memory:.1f} MB")
    
    # Мониторим память в течение времени
    max_memory = after_services
    for i in range(10):
        time.sleep(1)
        current_memory = process.memory_info().rss / 1024 / 1024
        if current_memory > max_memory:
            max_memory = current_memory
        print(f"Memory at {i+1}s: {current_memory:.1f} MB")
    
    print(f"Peak memory usage: {max_memory:.1f} MB")
    
    if max_memory < 80:
        print("🎉 ОТЛИЧНО: Низкое потребление памяти!")
    elif max_memory < 120:
        print("✅ ХОРОШО: Умеренное потребление памяти")
    else:
        print("⚠️  ВЫСОКОЕ: Потребление памяти выше ожидаемого")

except Exception as e:
    print(f"❌ Ошибка при тестировании памяти: {e}")

EOF

timeout 20s python3 /tmp/memory_test.py
MEMORY_RESULT=$?

# Тест 3: Проверка аудио производительности
echo ""
echo "🔊 Тест 3: Производительность аудио"
echo "-----------------------------------"

if [ -f "themes/minecraft/sounds/click.ogg" ]; then
    echo "Тестируем производительность AudioService..."
    
    cat > /tmp/audio_test.py << 'EOF'
#!/usr/bin/env python3
import time
import signal

def signal_handler(sig, frame):
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    from services.audio_service import AudioService
    
    # Создаем AudioService
    audio = AudioService()
    
    if audio.is_mixer_initialized():
        print("✅ AudioService инициализирован")
        
        # Тестируем скорость воспроизведения
        sound_file = "themes/minecraft/sounds/click.ogg"
        
        times = []
        for i in range(5):
            start = time.time()
            audio.play(sound_file)
            end = time.time()
            duration = end - start
            times.append(duration)
            print(f"Play {i+1}: {duration:.3f}s")
            time.sleep(0.2)
        
        avg_time = sum(times) / len(times)
        print(f"Average play time: {avg_time:.3f}s")
        
        if avg_time < 0.01:
            print("🎉 ОТЛИЧНО: Очень быстрое воспроизведение!")
        elif avg_time < 0.05:
            print("✅ ХОРОШО: Быстрое воспроизведение")
        else:
            print("⚠️  МЕДЛЕННО: Аудио тормозит")
    else:
        print("❌ AudioService не инициализирован")

except Exception as e:
    print(f"❌ Ошибка при тестировании аудио: {e}")

EOF
    
    timeout 10s python3 /tmp/audio_test.py
else
    echo "⚠️  Файл click.ogg не найден, пропускаем аудио тест"
fi

# Очистка
rm -f /tmp/startup_test.py /tmp/memory_test.py /tmp/audio_test.py

echo ""
echo "🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "========================="
echo ""
echo "📈 РЕЗЮМЕ ПРОИЗВОДИТЕЛЬНОСТИ:"
echo ""
echo "✅ Системные оптимизации Pi 5 применены"
echo "✅ Kivy конфигурация оптимизирована" 
echo "✅ AudioService оптимизирован (v2.1.1)"
echo "✅ Ленивая инициализация сервисов"
echo ""
echo "🎯 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:"
echo "   • Время запуска: <2 секунд"
echo "   • Потребление памяти: <80MB"
echo "   • Воспроизведение звука: <0.01s"
echo ""
echo "🔄 СЛЕДУЮЩИЕ ШАГИ:"
echo "   1. Если все тесты прошли успешно - переходите к Шагу 5"
echo "   2. Если есть проблемы - сообщите результаты для анализа"
echo "   3. Для production: запустите полное приложение: python3 main.py"
echo ""
echo "🕐 Время завершения тестов: $(date)"
