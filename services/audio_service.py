# services/audio_service.py - ИСПРАВЛЕНИЯ для Waveshare WM8960
# Заменить метод _find_audio_bonnet()

def _find_audio_bonnet(self):
    """Поиск Audio Bonnet в системе - ОБНОВЛЕНО для WM8960"""
    try:
        if ALSA_AVAILABLE:
            # Ищем карты ALSA
            cards = alsaaudio.cards()
            logger.info(f"Available ALSA cards: {cards}")
            
            # ИСПРАВЛЕНО: Обновленный список для WM8960 Waveshare
            bonnet_names = [
                # Waveshare WM8960 Audio Board
                'wm8960soundcard',      # Основное имя для Waveshare
                'wm8960-soundcard',     # ДОБАВЛЕНО: С дефисом
                'wm8960',               # Короткое имя
                # Остальные аудио-платы
                'audioinjectorpi', 
                'audioinjector-pi-soundcard',
                'AudioInjector',
                'wm8731',
            ]
            
            for i, card in enumerate(cards):
                for bonnet_name in bonnet_names:
                    if bonnet_name.lower() in card.lower():
                        logger.info(f"Found Audio Board: {card} (index {i}) - WM8960 compatible")
                        return f"hw:{i},0"
                        
        # Альтернативный метод через /proc/asound/cards
        try:
            with open('/proc/asound/cards', 'r') as f:
                cards_info = f.read()
                logger.debug(f"ALSA cards info:\n{cards_info}")
                
                lines = cards_info.strip().split('\n')
                for line in lines:
                    # ИСПРАВЛЕНО: Расширенный поиск для WM8960
                    wm8960_indicators = [
                        'wm8960soundcard', 'wm8960-soundcard', 'wm8960',
                        'audioinjector', 'wm8731'
                    ]
                    if any(name in line.lower() for name in wm8960_indicators):
                        # Извлекаем номер карты
                        card_num = line.split()[0]
                        logger.info(f"Found audio card via /proc: {line.strip()}")
                        return f"hw:{card_num},0"
                        
        except Exception as e:
            logger.warning(f"Could not read /proc/asound/cards: {e}")
            
    except Exception as e:
        logger.error(f"Error finding Audio Board: {e}")
        
    return None

def _init_pygame_with_device(self, device):
    """Инициализация pygame с конкретным аудиоустройством - ОПТИМИЗИРОВАНО для WM8960"""
    try:
        # Настраиваем переменную окружения для SDL
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
        os.environ['AUDIODEV'] = device
        
        # ИСПРАВЛЕНО: Оптимальные настройки для WM8960
        mixer.pre_init(
            frequency=44100,    # WM8960 отлично работает с 44.1kHz
            size=-16,           # 16-bit signed
            channels=2,         # Стерео
            buffer=2048         # УВЕЛИЧЕНО: Больший буфер для стабильности I2S
        )
        mixer.init()
        
        # Тест воспроизведения
        if self._test_audio_output():
            logger.info(f"AudioService initialized with WM8960 Audio Board: {device}")
            self.audio_device = device
            return True
        else:
            logger.warning("WM8960 Audio Board test failed, falling back to default")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing pygame with WM8960: {e}")
        return False

def get_device_info(self):
    """Получение информации об аудиоустройстве - РАСШИРЕННАЯ ДИАГНОСТИКА"""
    info = {
        "device": self.audio_device,
        "alsa_available": ALSA_AVAILABLE,
        "mixer_initialized": mixer.get_init() is not None,
        "device_type": "WM8960 Waveshare" if "wm8960" in str(self.audio_device).lower() else "Unknown"
    }
    
    if ALSA_AVAILABLE:
        try:
            info["alsa_cards"] = alsaaudio.cards()
            # ДОБАВЛЕНО: Специальная диагностика для WM8960
            info["wm8960_detected"] = any("wm8960" in card.lower() for card in alsaaudio.cards())
        except:
            info["alsa_cards"] = []
            info["wm8960_detected"] = False
            
    return info