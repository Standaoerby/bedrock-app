#!/usr/bin/env python3
"""
Тестовый скрипт для проверки GS3 USB audio
Проверяет работу AudioService и VolumeService с вашим GS3 устройством
"""

import sys
import os
import time

# Добавляем путь к проекту
sys.path.append('/home/standa/bedrock-app')

try:
    from services.audio_service import audio_service
    from services.volume_service import volume_service
    print("✅ Сервисы импортированы успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def test_audio_service():
    """Тест AudioService"""
    print("\n🎵 === ТЕСТ AUDIOSERVICE ===")
    
    # Диагностика устройства
    device_info = audio_service.get_device_info()
    print(f"Аудиоустройство: {device_info['device']}")
    print(f"Тип устройства: {device_info['device_type']}")
    print(f"ALSA доступна: {device_info['alsa_available']}")
    print(f"Pygame инициализирован: {device_info['mixer_initialized']}")
    
    if device_info.get('pygame_settings'):
        settings = device_info['pygame_settings']
        print(f"Настройки pygame: {settings['frequency']}Hz, {settings['channels']} каналов")
    
    # Список доступных устройств
    devices = audio_service.get_available_devices()
    print(f"\nДоступные аудиоустройства: {len(devices)}")
    for i, dev in enumerate(devices):
        print(f"  {i}: {dev['name']} ({dev['device']}) - {dev['type']}")
    
    # Диагностика состояния
    state = audio_service.diagnose_state()
    print(f"\nСостояние AudioService:")
    for key, value in state.items():
        print(f"  {key}: {value}")

def test_volume_service():
    """Тест VolumeService"""
    print("\n🔊 === ТЕСТ VOLUMESERVICE ===")
    
    # Диагностика аудиосистемы
    status = volume_service.diagnose_audio_system()
    
    print(f"\nСтатус VolumeService:")
    print(f"  ALSA доступна: {status['alsa_available']}")
    print(f"  USB карт найдено: {status['usb_cards_count']}")
    print(f"  Доступных миксеров: {status['available_mixers_count']}")
    print(f"  Активный миксер: {status['active_mixer']}")
    print(f"  Карта миксера: {status['mixer_card']}")
    print(f"  Текущая громкость: {status['current_volume']}%")
    print(f"  GPIO доступен: {status['gpio_available']} ({status['gpio_library']})")
    
    # Детали USB карт
    if status['usb_cards']:
        print(f"\nUSB аудиокарты:")
        for card in status['usb_cards']:
            print(f"  - {card['name']} (карта {card['index']})")
    
    # Детали миксеров
    if status['available_mixers']:
        print(f"\nДоступные миксеры:")
        for mixer in status['available_mixers']:
            print(f"  - {mixer['name']} на карте {mixer['card_index']} ({mixer['card_name']})")

def test_volume_control():
    """Тест управления громкостью"""
    print("\n🎚️ === ТЕСТ УПРАВЛЕНИЯ ГРОМКОСТЬЮ ===")
    
    if not volume_service._active_mixer:
        print("❌ Нет активного миксера - тест невозможен")
        return
    
    try:
        # Получаем текущую громкость
        current_vol = volume_service.get_volume()
        print(f"Текущая громкость: {current_vol}%")
        
        # Тестируем установку громкости
        test_volumes = [30, 50, 70, current_vol]  # Возвращаем к исходной
        
        for vol in test_volumes:
            print(f"Устанавливаем громкость: {vol}%")
            if volume_service.set_volume(vol):
                time.sleep(0.5)
                actual_vol = volume_service.get_volume()
                print(f"  ✅ Установлено: {actual_vol}%")
            else:
                print(f"  ❌ Ошибка установки громкости")
                
    except Exception as e:
        print(f"❌ Ошибка в тесте громкости: {e}")

def test_audio_playback():
    """Тест воспроизведения (если есть тестовые файлы)"""
    print("\n🎶 === ТЕСТ ВОСПРОИЗВЕДЕНИЯ ===")
    
    # Ищем тестовые аудиофайлы
    test_files = [
        '/usr/share/sounds/alsa/Front_Left.wav',
        'sounds/startup.wav',
        'sounds/click.wav'
    ]
    
    played_any = False
    for filepath in test_files:
        if os.path.exists(filepath):
            print(f"Воспроизводим: {filepath}")
            try:
                audio_service.play(filepath)
                time.sleep(2)  # Даём время для воспроизведения
                audio_service.stop()
                print(f"  ✅ Воспроизведение завершено")
                played_any = True
                break
            except Exception as e:
                print(f"  ❌ Ошибка воспроизведения: {e}")
    
    if not played_any:
        print("⚠️ Тестовые аудиофайлы не найдены")

def main():
    """Основная функция тестирования"""
    print("🚀 === ТЕСТ GS3 USB AUDIO СИСТЕМЫ ===")
    print("Проверяем работу аудио сервисов с USB устройством GS3")
    
    try:
        # Тестируем AudioService
        test_audio_service()
        
        # Тестируем VolumeService
        test_volume_service()
        
        # Тестируем управление громкостью
        test_volume_control()
        
        # Тестируем воспроизведение
        test_audio_playback()
        
        print("\n✅ === ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
        
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка в тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()