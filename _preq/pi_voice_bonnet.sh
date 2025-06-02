#!/bin/bash
# Скрипт настройки WM8960 Voice Bonnet для Raspberry Pi

echo "=== Настройка Adafruit Voice Bonnet WM8960 ==="

# 1. Проверяем что устройство распознано
echo "Проверяем доступные аудио устройства..."
aplay -l
echo ""

# 2. Создаем конфигурацию ALSA
echo "Создаем конфигурацию ALSA..."

# Создаем резервную копию существующего файла
if [ -f ~/.asoundrc ]; then
    cp ~/.asoundrc ~/.asoundrc.backup
    echo "Создана резервная копия ~/.asoundrc"
fi

# Создаем новую конфигурацию
cat > ~/.asoundrc << 'EOF'
# Configuration for Adafruit Voice Bonnet WM8960

# PCM configuration
pcm.wm8960 {
    type hw
    card 1  # Обычно Voice Bonnet это card 1, проверьте aplay -l
    device 0
}

pcm.!default {
    type asym
    playback.pcm "wm8960_playback"
    capture.pcm "wm8960_capture"
}

pcm.wm8960_playback {
    type plug
    slave.pcm "wm8960"
    slave.channels 2
    slave.rate 44100
    slave.format S16_LE
}

pcm.wm8960_capture {
    type plug
    slave.pcm "wm8960"
    slave.channels 2
    slave.rate 44100
    slave.format S16_LE
}

# Control configuration
ctl.!default {
    type hw
    card 1
}

ctl.wm8960 {
    type hw
    card 1
}
EOF

echo "Создан файл ~/.asoundrc"

# 3. Создаем системную конфигурацию (требует sudo)
echo "Создаем системную конфигурацию..."
sudo tee /etc/asound.conf > /dev/null << 'EOF'
# System configuration for Adafruit Voice Bonnet WM8960

defaults.pcm.card 1
defaults.ctl.card 1

pcm.!default {
    type hw
    card 1
    device 0
}

ctl.!default {
    type hw
    card 1
}
EOF

echo "Создан файл /etc/asound.conf"

# 4. Устанавливаем громкость по умолчанию
echo "Настраиваем громкость..."
amixer -c 1 sset 'Headphone' 80%
amixer -c 1 sset 'Speaker' 60%
amixer -c 1 sset 'Capture' 50%

# 5. Тестируем аудио
echo "Тестируем воспроизведение..."
speaker-test -c 2 -t wav -l 1 -D wm8960

echo ""
echo "=== Настройка завершена ==="
echo "Перезапустите приложение для применения изменений"
echo ""
echo "Для тестирования используйте:"
echo "  aplay -D wm8960 /usr/share/sounds/alsa/Front_Left.wav"
echo "  speaker-test -D wm8960 -c 2"
echo ""
echo "Для проверки устройств:"
echo "  aplay -l"
echo "  amixer -c 1"