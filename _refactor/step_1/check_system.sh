#!/bin/bash
# ========================
# Проверка системы после оптимизаций
# ========================

echo "🔍 === ПРОВЕРКА СИСТЕМНЫХ ОПТИМИЗАЦИЙ ==="
echo ""

# 1. Проверяем firmware
echo "📱 Firmware version:"
vcgencmd version
echo ""

# 2. Проверяем GPU память
echo "🎮 GPU память:"
GPU_MEM=$(vcgencmd get_mem gpu | cut -d'=' -f2)
echo "GPU Memory: $GPU_MEM"
if [[ "$GPU_MEM" == "128M" ]]; then
    echo "✅ GPU память настроена правильно"
else
    echo "❌ GPU память не настроена ($GPU_MEM вместо 128M)"
fi
echo ""

# 3. Проверяем CPU частоту
echo "⚡ CPU частота:"
CPU_FREQ=$(vcgencmd measure_clock arm)
echo "CPU Clock: $CPU_FREQ"
echo ""

# 4. Проверяем температуру
echo "🌡️  Температура:"
TEMP=$(vcgencmd measure_temp)
echo "Temperature: $TEMP"
echo ""

# 5. Проверяем дисплейный сервер
echo "🖥️  Дисплейный сервер:"
if [[ "$XDG_SESSION_TYPE" == "x11" ]]; then
    echo "✅ Используется X11"
elif [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
    echo "⚠️  Используется Wayland (рекомендуется X11 для Kivy)"
else
    echo "❓ Неизвестный дисплейный сервер: $XDG_SESSION_TYPE"
fi
echo ""

# 6. Проверяем config.txt
echo "⚙️  Конфигурация в config.txt:"
if grep -q "gpu_mem=128" /boot/firmware/config.txt; then
    echo "✅ gpu_mem=128 найдено"
else
    echo "❌ gpu_mem=128 не найдено"
fi

if grep -q "sdram_freq=800" /boot/firmware/config.txt; then
    echo "✅ sdram_freq=800 найдено"
else
    echo "❌ sdram_freq=800 не найдено"
fi
echo ""

# 7. Проверяем производительность памяти
echo "�� Тест производительности памяти:"
echo "Запускаем быстрый тест..."
time dd if=/dev/zero of=/tmp/speedtest bs=1M count=100 2>/dev/null
rm -f /tmp/speedtest
echo ""

echo "✅ Проверка завершена"
echo ""
echo "🔄 ЕСЛИ ВСЕ ПРОВЕРКИ ПРОШЛИ УСПЕШНО:"
echo "   Переходите к Шагу 2 - Оптимизация Kivy"
echo "🔄 ЕСЛИ ЕСТЬ ОШИБКИ:"
echo "   Сообщите результаты и мы исправим проблемы"
