#!/bin/bash
# ========================
# Безопасная оптимизация Kivy конфигурации
# Версия 2.0 - изменяет только нужные параметры
# ========================

echo "🛡️ === БЕЗОПАСНАЯ ОПТИМИЗАЦИЯ KIVY v2.0 ==="
echo ""

# Проверяем что конфигурация существует
if [ ! -f ~/.kivy/config.ini ]; then
    echo "❌ ~/.kivy/config.ini не найден"
    echo "   Сначала запустите приложение для создания конфигурации"
    exit 1
fi

# Создаем резервную копию
BACKUP_FILE=~/.kivy/config.ini.backup.$(date +%Y%m%d_%H%M%S)
cp ~/.kivy/config.ini "$BACKUP_FILE"
echo "💾 Резервная копия создана: $BACKUP_FILE"

# Создаем временный файл для безопасного редактирования
TEMP_FILE=$(mktemp)
cp ~/.kivy/config.ini "$TEMP_FILE"

echo "🔧 Применяем оптимизации..."

# Функция для безопасного изменения параметра
update_config_param() {
    local section="$1"
    local key="$2"
    local value="$3"
    local file="$4"
    
    # Проверяем есть ли секция
    if grep -q "^\[$section\]" "$file"; then
        # Проверяем есть ли параметр в секции
        if sed -n "/^\[$section\]/,/^\[/p" "$file" | grep -q "^$key\s*="; then
            # Обновляем существующий параметр
            sed -i "/^\[$section\]/,/^\[/ s/^$key\s*=.*/$key = $value/" "$file"
            echo "   ✏️  Обновлен [$section] $key = $value"
        else
            # Добавляем новый параметр в секцию
            sed -i "/^\[$section\]/a $key = $value" "$file"
            echo "   ➕ Добавлен [$section] $key = $value"
        fi
    else
        # Создаем новую секцию
        echo -e "\n[$section]\n$key = $value" >> "$file"
        echo "   🆕 Создана секция [$section] с $key = $value"
    fi
}

# Применяем критические оптимизации для Pi 5
echo ""
echo "⚡ Применяем оптимизации производительности:"

# Graphics оптимизации
update_config_param "graphics" "maxfps" "30" "$TEMP_FILE"
update_config_param "graphics" "multisamples" "0" "$TEMP_FILE" 
update_config_param "graphics" "allow_screensaver" "0" "$TEMP_FILE"
update_config_param "graphics" "min_state_time" "0.035" "$TEMP_FILE"

# Input оптимизации (только если параметр отсутствует)
if ! grep -q "mouse = mouse" "$TEMP_FILE"; then
    update_config_param "input" "mouse" "mouse" "$TEMP_FILE"
fi

# Widgets оптимизации  
update_config_param "widgets" "scroll_timeout" "250" "$TEMP_FILE"
update_config_param "widgets" "scroll_stoptime" "300" "$TEMP_FILE"
update_config_param "widgets" "scroll_moves" "5" "$TEMP_FILE"

# Postproc оптимизации
update_config_param "postproc" "double_tap_time" "300" "$TEMP_FILE"
update_config_param "postproc" "double_tap_distance" "25" "$TEMP_FILE"
update_config_param "postproc" "jitter_distance" "1" "$TEMP_FILE"

echo ""
echo "🔍 Проверяем результат..."

# Проверяем что файл валидный
python3 -c "
import configparser
try:
    config = configparser.ConfigParser()
    config.read('$TEMP_FILE')
    print('✅ Конфигурация валидна')
    
    # Проверяем ключевые параметры
    if config.has_option('graphics', 'maxfps'):
        print(f'✅ maxfps = {config.get(\"graphics\", \"maxfps\")}')
    if config.has_option('graphics', 'multisamples'):  
        print(f'✅ multisamples = {config.get(\"graphics\", \"multisamples\")}')
    if config.has_option('kivy', 'kivy_clock'):
        print(f'✅ kivy_clock = {config.get(\"kivy\", \"kivy_clock\")}')
    else:
        print('⚠️  kivy_clock отсутствует (будет использован default)')
        
except Exception as e:
    print(f'❌ Ошибка конфигурации: {e}')
    exit(1)
" || {
    echo "❌ Конфигурация повреждена, восстанавливаем из резервной копии"
    cp "$BACKUP_FILE" ~/.kivy/config.ini
    rm "$TEMP_FILE"
    exit 1
}

# Если проверка прошла успешно, применяем изменения
cp "$TEMP_FILE" ~/.kivy/config.ini
rm "$TEMP_FILE"

echo ""
echo "✅ БЕЗОПАСНАЯ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА"
echo ""
echo "🎯 ПРИМЕНЕННЫЕ ОПТИМИЗАЦИИ:"
echo "   ✅ FPS ограничен до 30 (экономия ресурсов)"
echo "   ✅ Antialiasing отключен (ускорение рендеринга)"
echo "   ✅ Screensaver отключен (стабильность)"
echo "   ✅ Scroll оптимизирован (плавность)"
echo "   ✅ Touch оптимизирован (отзывчивость)"
echo ""
echo "💾 РЕЗЕРВНАЯ КОПИЯ: $BACKUP_FILE"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo "   python3 main.py"
echo ""
echo "🔙 ОТКАТ (если нужен):"
echo "   cp $BACKUP_FILE ~/.kivy/config.ini"
