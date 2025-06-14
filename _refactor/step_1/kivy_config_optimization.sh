#!/bin/bash
# ========================
# Шаг 2: Оптимизация конфигурации Kivy
# ========================

echo "🎨 === ОПТИМИЗАЦИЯ KIVY КОНФИГУРАЦИИ ==="

# Создаем резервную копию существующей конфигурации
if [ -f ~/.kivy/config.ini ]; then
    echo "💾 Создаем резервную копию ~/.kivy/config.ini"
    cp ~/.kivy/config.ini ~/.kivy/config.ini.backup.$(date +%Y%m%d_%H%M%S)
fi

# Создаем директорию .kivy если её нет
mkdir -p ~/.kivy

# Создаем оптимизированную конфигурацию
echo "⚙️  Создаем оптимизированную конфигурацию Kivy..."

cat > ~/.kivy/config.ini << 'EOF'
[kivy]
log_dir = logs
log_enable = 1
log_level = info
log_name = kivy_%y-%m-%d_%_.txt
log_maxfiles = 5
exit_on_escape = 1
pause_on_minimize = 0
desktop = 1
config_version = 20

[graphics]
# ПРОИЗВОДИТЕЛЬНОСТЬ: Ограничиваем FPS для экономии ресурсов
maxfps = 30

# ВАЖНО: Отключаем antialiasing для Pi 5
multisamples = 0

# Принудительно используем X11 window provider
window_providers = x11

# Оптимальное разрешение для Pi 5
width = 1024
height = 600
fullscreen = 1
show_cursor = 0
borderless = 1

# Отключаем screensaver для стабильности
allow_screensaver = 0

# Минимальное время между кадрами
min_state_time = 0.033

# Оптимизация рендеринга
position = auto
rotation = 0
resizable = 0

[input]
# Оптимизированные input providers для Pi 5
mouse = mouse
# Отключаем неиспользуемые input providers для экономии ресурсов
# mtdev_%(name)s = probesysfs,provider=mtdev
# hid_%(name)s = probesysfs,provider=hidinput

[postproc]
# Уменьшаем чувствительность для стабильности
double_tap_time = 300
double_tap_distance = 25
jitter_distance = 1
retain_time = 0

[widgets]
# Отключаем анимации для экономии ресурсов
scroll_timeout = 250
scroll_stoptime = 300
scroll_moves = 5

[network]
# Таймауты для сетевых операций
useragent = kivy
EOF

echo "✅ Конфигурация Kivy оптимизирована"
echo ""

# Проверяем конфигурацию
echo "🔍 Проверяем созданную конфигурацию:"
if [ -f ~/.kivy/config.ini ]; then
    echo "✅ ~/.kivy/config.ini создан"
    echo "📊 Размер файла: $(ls -lh ~/.kivy/config.ini | awk '{print $5}')"
else
    echo "❌ Ошибка создания ~/.kivy/config.ini"
    exit 1
fi

echo ""
echo "🎯 ОПТИМИЗАЦИИ ПРИМЕНЕНЫ:"
echo "   ✅ FPS ограничен до 30 (вместо 60)"
echo "   ✅ Antialiasing отключен"
echo "   ✅ X11 window provider принудительно"
echo "   ✅ Screensaver отключен"
echo "   ✅ Input providers оптимизированы"
echo ""
echo "🔄 СЛЕДУЮЩИЙ ШАГ:"
echo "   Протестируйте приложение и переходите к Шагу 3"
