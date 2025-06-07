#!/usr/bin/env python3
"""
Тест-скрипт для проверки WM8960 Audio Board с Bedrock 2.0
Запуск: python3 test_wm8960.py
"""

import os
import sys
import subprocess
import time

# Добавляем путь к Bedrock
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from services.audio_service import AudioService
    from services.volume_service import VolumeControlService
    from app.logger import app_logger as logger
except ImportError as e:
    print(f"Ошибка импорта Bedrock модулей: {e}")
    print("Убедитесь что вы запускаете скрипт из папки Bedrock")
    sys.exit(1)

def test_wm8960_detection():
    """Тест обнаружения WM8960"""
    print("🔍 === ТЕСТ ОБНАРУЖЕНИЯ WM8960 ===")
    
    try:
        # Проверяем ALSA карты
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📋 Доступные аудио устройства:")
            for line in result.stdout.split('\n'):
                if 'wm8960' in line.lower():
                    print(f"✅ WM8960 найден: {line.strip()}")
                elif 'card' in line.lower():
                    print(f"   {line.strip()}")
        
        # Проверяем миксеры
        result = subprocess.run(['amixer', 'scontrols'], capture_output=True, text=True)
        if result.returncode == 0:
            wm8960_mixers = []
            for line in result.stdout.split('\n'):
                if 'Simple mixer control' in line:
                    for mixer_name in ['Headphone', 'Speaker', 'Playback']:
                        if mixer_name in line:
                            wm8960_mixers.append(mixer_name)
            
            if wm8960_mixers:
                print(f"✅ WM8960 миксеры найдены: {wm8960_mixers}")
            else:
                print("❌ WM8960 миксеры не найдены")
                
    except Exception as e:
        print(f"❌ Ошибка проверки WM8960: {e}")

def test_audio_service():
    """Тест AudioService"""
    print("\n🎵 === ТЕСТ AUDIO SERVICE ===")
    
    try:
        audio = AudioService()
        info = audio.get_device_info()
        
        print(f"🔧 Аудио устройство: {info.get('device', 'Unknown')}")
        print(f"🔧 Тип устройства: {info.get('device_type', 'Unknown')}")
        print(f"🔧 ALSA доступно: {info.get('alsa_available', False)}")
        print(f"🔧 WM8960 обнаружен: {info.get('wm8960_detected', False)}")
        print(f"🔧 Pygame инициализирован: {info.get('mixer_initialized', False)}")
        
        if info.get('wm8960_detected'):
            print("✅ AudioService корректно обнаружил WM8960")
        else:
            print("⚠️ AudioService не обнаружил WM8960")
            
        # Тест воспроизведения звука (если есть тестовый файл)
        test_sound = "media/ringtones/robot.mp3"  # Или любой другой
        if os.path.exists(test_sound):
            print(f"🎵 Тестируем воспроизведение: {test_sound}")
            audio.play(test_sound)
            time.sleep(2)
            audio.stop()
            print("✅ Тест воспроизведения завершен")
        else:
            print(f"⚠️ Тестовый файл не найден: {test_sound}")
            
    except Exception as e:
        print(f"❌ Ошибка AudioService: {e}")

def test_volume_service():
    """Тест VolumeService"""
    print("\n🔊 === ТЕСТ VOLUME SERVICE ===")
    
    try:
        volume = VolumeControlService()
        status = volume.get_status()
        
        print(f"🔧 Активный миксер: {status.get('active_mixer', 'None')}")
        print(f"🔧 Доступные миксеры: {len(status.get('available_mixers', []))}")
        print(f"🔧 WM8960 обнаружен: {status.get('wm8960_detected', False)}")
        print(f"🔧 WM8960 миксеры: {status.get('wm8960_mixers', [])}")
        print(f"🔧 Текущая громкость: {status.get('current_volume', 0)}%")
        print(f"🔧 GPIO доступно: {status.get('gpio_available', False)}")
        
        if status.get('wm8960_detected'):
            print("✅ VolumeService корректно обнаружил WM8960")
            
            # Тест изменения громкости
            current_vol = volume.get_volume()
            print(f"🔊 Тестируем изменение громкости (текущая: {current_vol}%)")
            
            # Увеличиваем громкость
            volume.volume_up_manual()
            time.sleep(0.5)
            new_vol = volume.get_volume()
            print(f"📈 После увеличения: {new_vol}%")
            
            # Возвращаем обратно
            volume.volume_down_manual()
            time.sleep(0.5)
            final_vol = volume.get_volume()
            print(f"📉 После уменьшения: {final_vol}%")
            
            if new_vol > current_vol:
                print("✅ Управление громкостью работает")
            else:
                print("⚠️ Управление громкостью может не работать корректно")
        else:
            print("⚠️ VolumeService не обнаружил WM8960")
            
    except Exception as e:
        print(f"❌ Ошибка VolumeService: {e}")

def test_mixer_commands():
    """Тест прямых команд амиксера"""
    print("\n🎛️ === ТЕСТ КОМАНД АМИКСЕРА ===")
    
    wm8960_mixers = ['Headphone', 'Speaker', 'Playback']
    
    for mixer in wm8960_mixers:
        try:
            result = subprocess.run(['amixer', 'get', mixer], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Миксер '{mixer}' доступен")
                # Извлекаем текущую громкость
                for line in result.stdout.split('\n'):
                    if '[' in line and '%' in line:
                        print(f"   Текущие настройки: {line.strip()}")
                        break
            else:
                print(f"❌ Миксер '{mixer}' недоступен")
        except Exception as e:
            print(f"❌ Ошибка тестирования миксера '{mixer}': {e}")

def main():
    """Основная функция тестирования"""
    print("🎧 === ТЕСТ WM8960 AUDIO BOARD ДЛЯ BEDROCK 2.0 ===\n")
    
    # Проверяем что мы на Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' not in cpuinfo:
                print("⚠️ Внимание: Не обнаружен Raspberry Pi")
    except:
        pass
    
    # Запускаем тесты
    test_wm8960_detection()
    test_mixer_commands()
    test_audio_service()
    test_volume_service()
    
    print("\n🏁 === ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
    print("Если есть ошибки, проверьте:")
    print("1. Правильно ли установлен WM8960 драйвер")
    print("2. Загружен ли overlay в /boot/config.txt")
    print("3. Перезагружена ли система после установки")
    print("4. Подключены ли динамики/наушники к WM8960")

if __name__ == "__main__":
    main()