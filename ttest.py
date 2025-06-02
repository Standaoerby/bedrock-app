#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений в проекте Bedrock
"""
import os
import sys
import inspect

# Добавляем путь к проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_settings_screen():
    """Тест SettingsScreen на наличие всех необходимых методов"""
    print("=== Тестируем SettingsScreen ===")
    
    try:
        from pages.settings import SettingsScreen
        
        # Создаем экземпляр
        settings = SettingsScreen()
        
        # Проверяем наличие методов, которые могут вызываться из KV
        required_methods = [
            'on_username_change',
            'on_birth_day_change', 
            'on_birth_month_change',
            'on_birth_year_change',
            'on_theme_select',
            'on_variant_select',
            'on_language_select',
            'toggle_auto_theme',
            'on_threshold_change',
            'save_all_settings',
            'load_all_settings',
            '_cleanup_spinners'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(settings, method_name):
                missing_methods.append(method_name)
            else:
                print(f"✓ {method_name}")
        
        if missing_methods:
            print(f"✗ Отсутствующие методы: {missing_methods}")
            return False
        else:
            print("✓ Все методы присутствуют")
            
        # Проверяем свойства
        required_properties = [
            'current_theme', 'current_variant', 'current_language',
            'username', 'birth_day', 'birth_month', 'birth_year',
            'auto_theme_enabled', 'light_sensor_available', 'light_sensor_threshold'
        ]
        
        missing_properties = []
        for prop_name in required_properties:
            if not hasattr(settings, prop_name):
                missing_properties.append(prop_name)
            else:
                print(f"✓ Property: {prop_name}")
        
        if missing_properties:
            print(f"✗ Отсутствующие свойства: {missing_properties}")
            return False
        else:
            print("✓ Все свойства присутствуют")
            
        return True
        
    except Exception as e:
        print(f"✗ Ошибка при тестировании SettingsScreen: {e}")
        return False

def test_alarm_screen():
    """Тест AlarmScreen на наличие всех необходимых методов"""
    print("\n=== Тестируем AlarmScreen ===")
    
    try:
        from pages.alarm import AlarmScreen
        
        # Создаем экземпляр
        alarm = AlarmScreen()
        
        # Проверяем наличие методов
        required_methods = [
            'increment_hour', 'decrement_hour',
            'increment_minute', 'decrement_minute',
            'on_active_toggled', 'toggle_repeat',
            'on_fadein_toggled', 'select_ringtone',
            'toggle_play_ringtone', 'play_ringtone',
            'stop_ringtone', '_cleanup_spinners'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(alarm, method_name):
                missing_methods.append(method_name)
            else:
                print(f"✓ {method_name}")
        
        if missing_methods:
            print(f"✗ Отсутствующие методы: {missing_methods}")
            return False
        else:
            print("✓ Все методы присутствуют")
            
        return True
        
    except Exception as e:
        print(f"✗ Ошибка при тестировании AlarmScreen: {e}")
        return False

def test_imports():
    """Тест импортов основных модулей"""
    print("\n=== Тестируем импорты ===")
    
    modules_to_test = [
        'app.theme_manager',
        'app.localizer', 
        'app.user_config',
        'app.event_bus',
        'services.audio_service',
        'services.alarm_service',
        'services.weather_service',
        'services.sensor_service',
        'services.pigs_service',
        'services.notifications_service',
        'services.schedule_service',
        'pages.home',
        'pages.alarm',
        'pages.settings',
        'pages.weather',
        'pages.pigs',
        'pages.schedule',
        'widgets.root_widget',
        'widgets.top_menu'
    ]
    
    failed_imports = []
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except Exception as e:
            print(f"✗ {module_name}: {e}")
            failed_imports.append(module_name)
    
    if failed_imports:
        print(f"\n✗ Неудачные импорты: {failed_imports}")
        return False
    else:
        print("\n✓ Все импорты успешны")
        return True

def test_config_files():
    """Тест наличия конфигурационных файлов"""
    print("\n=== Тестируем конфигурационные файлы ===")
    
    config_files = [
        'config/user_config.json',
        'config/alarm.json', 
        'config/schedule.json',
        'config/pigs.json',
        'locale/en.json',
        'locale/ru.json'
    ]
    
    missing_files = []
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✓ {config_file}")
        else:
            print(f"? {config_file} (будет создан при запуске)")
    
    return True

def test_kv_files():
    """Тест наличия KV файлов"""
    print("\n=== Тестируем KV файлы ===")
    
    kv_files = [
        'widgets/root_widget.kv',
        'widgets/top_menu.kv',
        'widgets/overlay_card.kv',
        'pages/home.kv',
        'pages/alarm.kv',
        'pages/settings.kv',
        'pages/weather.kv',
        'pages/pigs.kv',
        'pages/schedule.kv'
    ]
    
    missing_files = []
    
    for kv_file in kv_files:
        if os.path.exists(kv_file):
            print(f"✓ {kv_file}")
        else:
            print(f"✗ {kv_file}")
            missing_files.append(kv_file)
    
    if missing_files:
        print(f"\n✗ Отсутствующие KV файлы: {missing_files}")
        return False
    else:
        print("\n✓ Все KV файлы присутствуют")
        return True

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование исправлений Bedrock 2.0")
    print("=" * 50)
    
    tests = [
        ("Импорты модулей", test_imports),
        ("SettingsScreen", test_settings_screen),
        ("AlarmScreen", test_alarm_screen),
        ("Конфигурационные файлы", test_config_files),
        ("KV файлы", test_kv_files)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Критическая ошибка в тесте {test_name}: {e}")
            results.append((test_name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nРезультат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Проект готов к запуску.")
        return True
    else:
        print("⚠️  Некоторые тесты провалены. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)