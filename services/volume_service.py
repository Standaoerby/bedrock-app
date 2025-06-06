# services/volume_service.py - ИСПРАВЛЕНИЯ для Waveshare WM8960
# Заменить приоритеты миксеров и методы инициализации

# ИСПРАВЛЕНО: Приоритетный список миксеров для WM8960 Waveshare
MIXER_PRIORITIES = [
    # WM8960 специфичные миксеры (высший приоритет)
    'Headphone',        # ДОБАВЛЕНО: Основной выход WM8960
    'Speaker',          # ДОБАВЛЕНО: Выход на динамики WM8960  
    'Playback',         # ДОБАВЛЕНО: Общий плейбэк WM8960
    # Стандартные миксеры
    'Master',
    'PCM', 
    'Digital',
    'Line Out',
]

def _discover_mixers(self):
    """Обнаружение доступных миксеров через amixer - УЛУЧШЕННАЯ ВЕРСИЯ"""
    self._available_mixers = []
    
    try:
        # Получаем список всех доступных миксеров
        result = subprocess.run(
            ['amixer', 'scontrols'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            # Парсим вывод amixer scontrols
            for line in result.stdout.split('\n'):
                if "Simple mixer control" in line:
                    # Извлекаем имя миксера между апострофами
                    match = re.search(r"'([^']+)'", line)
                    if match:
                        mixer_name = match.group(1)
                        self._available_mixers.append(mixer_name)
            
            # ДОБАВЛЕНО: Специальная диагностика для WM8960
            wm8960_mixers = [m for m in self._available_mixers if any(
                wm8960_term in m.lower() for wm8960_term in ['headphone', 'speaker', 'playback']
            )]
            
            logger.info(f"Discovered mixers: {self._available_mixers}")
            if wm8960_mixers:
                logger.info(f"WM8960 compatible mixers found: {wm8960_mixers}")
            else:
                logger.warning("No WM8960 specific mixers detected")
                
        else:
            logger.warning(f"Failed to discover mixers: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout discovering mixers")
    except FileNotFoundError:
        logger.warning("amixer not available - cannot discover mixers")
    except Exception as e:
        logger.error(f"Error discovering mixers: {e}")

def _select_best_mixer(self):
    """Выбор лучшего миксера из доступных - ОПТИМИЗИРОВАНО для WM8960"""
    self._active_mixer = None
    
    if not self._available_mixers:
        logger.warning("No mixers discovered")
        return
    
    # ДОБАВЛЕНО: Специальная логика для WM8960
    wm8960_detected = any("wm8960" in mixer.lower() for mixer in self._available_mixers)
    if wm8960_detected:
        logger.info("WM8960 audio board detected, using optimized mixer selection")
    
    # Ищем миксер по приоритету
    for priority_mixer in MIXER_PRIORITIES:
        for available_mixer in self._available_mixers:
            if priority_mixer.lower() == available_mixer.lower():
                # Точное совпадение имеет наивысший приоритет
                if self._test_mixer(available_mixer):
                    self._active_mixer = available_mixer
                    logger.info(f"Selected exact match mixer: {self._active_mixer}")
                    return
            elif priority_mixer.lower() in available_mixer.lower():
                # Частичное совпадение
                if self._test_mixer(available_mixer):
                    self._active_mixer = available_mixer
                    logger.info(f"Selected partial match mixer: {self._active_mixer}")
                    return
    
    # Если ничего не подошло, пробуем первый рабочий
    for mixer in self._available_mixers:
        if self._test_mixer(mixer):
            self._active_mixer = mixer
            logger.info(f"Selected fallback mixer: {self._active_mixer}")
            return
    
    logger.error("No working mixer found")

def get_status(self):
    """Get service status for debugging - РАСШИРЕННАЯ ДИАГНОСТИКА"""
    status = {
        'running': self.running,
        'gpio_available': self.gpio_available,
        'gpio_lib': self.gpio_lib,
        'current_volume': self._current_volume,
        'volume_step': VOLUME_STEP,
        'debounce_time': DEBOUNCE_TIME,
        'active_mixer': self._active_mixer,
        'available_mixers': self._available_mixers,
        'mixer_card': self._mixer_card,
        'button_pins': {
            'volume_up': VOLUME_UP_PIN,
            'volume_down': VOLUME_DOWN_PIN
        },
        'lgpio_available': LGPIO_AVAILABLE,
        'rpi_gpio_available': RPI_GPIO_AVAILABLE,
        # ДОБАВЛЕНО: WM8960 специфичная информация
        'wm8960_detected': any("wm8960" in mixer.lower() for mixer in self._available_mixers) if self._available_mixers else False,
        'wm8960_mixers': [m for m in self._available_mixers if any(
            term in m.lower() for term in ['headphone', 'speaker', 'playback']
        )] if self._available_mixers else []
    }
    
    return status

def _test_mixer(self, mixer_name):
    """Тестирование работоспособности миксера - УЛУЧШЕННАЯ ВЕРСИЯ"""
    try:
        result = subprocess.run(
            ['amixer', 'get', mixer_name], 
            capture_output=True, 
            text=True, 
            timeout=3
        )
        
        if result.returncode == 0:
            # Проверяем что в выводе есть процент громкости
            has_volume = '[' in result.stdout and '%' in result.stdout
            
            # ДОБАВЛЕНО: Дополнительная проверка для WM8960 миксеров
            if has_volume:
                # Для WM8960 также проверяем что миксер не в состоянии "off"
                is_on = 'on' in result.stdout.lower() or not ('off' in result.stdout.lower())
                logger.debug(f"Mixer {mixer_name}: volume={has_volume}, active={is_on}")
                return has_volume and is_on
            
            return has_volume
        
        return False
        
    except Exception as e:
        logger.debug(f"Mixer {mixer_name} test failed: {e}")
        return False