# ========================
# Шаг 1: Системные оптимизации Raspberry Pi 5
# ========================

echo "🔧 === СИСТЕМНЫЕ ОПТИМИЗАЦИИ RPi5 ==="

# 1. Проверим текущее состояние системы
echo "📊 Текущее состояние:"
vcgencmd version
vcgencmd measure_temp
vcgencmd get_mem gpu
vcgencmd measure_clock arm

# 2. КРИТИЧНО: Обновляем firmware с SDRAM оптимизациями 
echo "🚀 Обновляем firmware..."
sudo rpi-update
echo "⚠️  ТРЕБУЕТСЯ ПЕРЕЗАГРУЗКА после обновления!"

# 3. Оптимизируем GPU память (запустить после перезагрузки)
echo "🎮 Настраиваем GPU память..."
sudo raspi-config nonint do_memory_split 128

# 4. Переключаемся на X11 вместо Wayland для лучшей совместимости с Kivy
echo "🖥️  Переключаемся на X11..."
sudo raspi-config nonint do_wayland W1  # W1 = X11

# 5. Добавляем оптимизации в config.txt
echo "⚙️  Добавляем оптимизации в config.txt..."
sudo tee -a /boot/firmware/config.txt << 'EOF'

# === BEDROCK PERFORMANCE OPTIMIZATIONS ===
# GPU Memory для Kivy
gpu_mem=128

# SDRAM оптимизации (новые в 2024-2025)
sdram_freq=800
over_voltage=2

# Boost производительности
arm_boost=1
temp_limit=80

# I2C оптимизации для датчиков
dtparam=i2c_arm_baudrate=400000

# GPIO оптимизации
gpio=2-27=op,pu  # Pull-up для всех GPIO
EOF

echo "✅ Системные оптимизации применены"
echo ""
echo "🔄 СЛЕДУЮЩИЕ ШАГИ:"
echo "1. Перезагрузите Pi: sudo reboot"
echo "2. После перезагрузки проверьте изменения командой:"
echo "   bash check_system.sh"
echo "3. Переходите к Шагу 2"