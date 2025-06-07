import subprocess
import logging
import platform
from typing import Optional

class VolumeManager:
    """Улучшенный менеджер громкости без циклических зависимостей"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_volume = 50
        self.is_muted = False
        self.system = platform.system()
        self.volume_backend = self._detect_volume_backend()
        
    def _detect_volume_backend(self):
        """Определяет доступный метод управления звуком"""
        if self.system == "Linux":
            # Проверяем доступность команд
            try:
                subprocess.run(['which', 'amixer'], check=True, capture_output=True)
                return 'alsa'
            except subprocess.CalledProcessError:
                try:
                    subprocess.run(['which', 'pactl'], check=True, capture_output=True)
                    return 'pulseaudio'
                except subprocess.CalledProcessError:
                    return 'mock'
        elif self.system == "Windows":
            return 'windows'
        else:
            return 'mock'
    
    def get_volume(self) -> int:
        """Получает текущую громкость из системы"""
        try:
            if self.volume_backend == 'alsa':
                result = subprocess.run(
                    ['amixer', 'get', 'Master'], 
                    capture_output=True, text=True, check=True
                )
                # Парсим вывод amixer для получения громкости
                for line in result.stdout.split('\n'):
                    if 'Playback' in line and '[' in line:
                        # Ищем значение в скобках типа [50%]
                        start = line.find('[') + 1
                        end = line.find('%]')
                        if start > 0 and end > start:
                            volume = int(line[start:end])
                            self.current_volume = volume
                            return volume
                            
            elif self.volume_backend == 'pulseaudio':
                result = subprocess.run(
                    ['pactl', 'get-sink-volume', '@DEFAULT_SINK@'],
                    capture_output=True, text=True, check=True
                )
                # Парсим вывод pactl
                if 'Volume:' in result.stdout:
                    # Формат: Volume: front-left: 32768 /  50% / -18.06 dB
                    parts = result.stdout.split('/')
                    if len(parts) >= 2:
                        volume_str = parts[1].strip().replace('%', '')
                        volume = int(volume_str)
                        self.current_volume = volume
                        return volume
                        
            elif self.volume_backend == 'windows':
                # Для Windows можно использовать pycaw или WMI
                # Пока возвращаем текущее значение
                pass
                
        except Exception as e:
            self.logger.error(f"Ошибка получения громкости: {e}")
            
        return self.current_volume
    
    def set_volume(self, volume: int) -> bool:
        """Устанавливает громкость системы"""
        volume = max(0, min(100, volume))  # Ограничиваем 0-100
        
        self.logger.info(f"Устанавливаем громкость: {volume}% (backend: {self.volume_backend})")
        
        try:
            if self.volume_backend == 'alsa':
                result = subprocess.run(
                    ['amixer', 'set', 'Master', f'{volume}%'],
                    capture_output=True, text=True, check=True
                )
                self.logger.info(f"amixer вывод: {result.stdout}")
                
            elif self.volume_backend == 'pulseaudio':
                result = subprocess.run(
                    ['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{volume}%'],
                    capture_output=True, text=True, check=True
                )
                self.logger.info(f"pactl выполнен успешно")
                
            elif self.volume_backend == 'windows':
                # Для Windows реализация через WMI или pycaw
                self.logger.warning("Windows volume control не реализован")
                
            elif self.volume_backend == 'mock':
                self.logger.info(f"Mock режим: громкость 'установлена' на {volume}%")
            
            # Проверяем что громкость действительно изменилась
            actual_volume = self.get_volume()
            if abs(actual_volume - volume) <= 2:  # Допуск 2%
                self.current_volume = volume
                self.logger.info(f"Громкость успешно установлена: {volume}%")
                return True
            else:
                self.logger.warning(f"Громкость не изменилась: ожидали {volume}%, получили {actual_volume}%")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ошибка команды громкости: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при установке громкости: {e}")
            return False
    
    def mute(self) -> bool:
        """Отключает звук"""
        try:
            if self.volume_backend == 'alsa':
                subprocess.run(['amixer', 'set', 'Master', 'mute'], check=True)
            elif self.volume_backend == 'pulseaudio':
                subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', '1'], check=True)
            
            self.is_muted = True
            self.logger.info("Звук отключен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отключения звука: {e}")
            return False
    
    def unmute(self) -> bool:
        """Включает звук"""
        try:
            if self.volume_backend == 'alsa':
                subprocess.run(['amixer', 'set', 'Master', 'unmute'], check=True)
            elif self.volume_backend == 'pulseaudio':
                subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', '0'], check=True)
            
            self.is_muted = False
            self.logger.info("Звук включен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка включения звука: {e}")
            return False
    
    def volume_up(self, step: int = 5) -> bool:
        """Увеличивает громкость на заданный шаг"""
        new_volume = min(100, self.current_volume + step)
        return self.set_volume(new_volume)
    
    def volume_down(self, step: int = 5) -> bool:
        """Уменьшает громкость на заданный шаг"""
        new_volume = max(0, self.current_volume - step)
        return self.set_volume(new_volume)
    
    def get_status(self) -> dict:
        """Возвращает текущий статус громкости"""
        return {
            'volume': self.get_volume(),
            'is_muted': self.is_muted,
            'backend': self.volume_backend,
            'system': self.system
        }


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    vm = VolumeManager()
    print(f"Статус: {vm.get_status()}")
    
    # Тест установки громкости
    print(f"Устанавливаем громкость 75%: {vm.set_volume(75)}")
    print(f"Текущая громкость: {vm.get_volume()}%")
    
    # Тест изменения громкости
    print(f"Увеличиваем громкость: {vm.volume_up(10)}")
    print(f"Уменьшаем громкость: {vm.volume_down(5)}")
    
    print(f"Финальный статус: {vm.get_status()}")