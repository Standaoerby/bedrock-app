#!/usr/bin/env python3

import threading
import time
from app.logger import app_logger as logger
from app.event_bus import event_bus
from kivy.app import App
from kivy.clock import Clock



class AutoThemeService:
    """
    Сервис автоматического переключения темы на основе освещенности
    Версия 1.1.0 - Добавлен метод check_and_update_theme
    """
    
    def __init__(self, sensor_service, theme_manager):
        self.sensor_service = sensor_service
        self.theme_manager = theme_manager
        self.enabled = False
        self.running = False
        self.threshold_seconds = 3  # Время удержания для переключения
        self.calibration_time = 3   # Время калибровки
        self.check_thread = None
        
        # Состояние освещенности
        self.current_light_state = None  # True = светло, False = темно
        self.state_start_time = None
        self.state_stable = False
        
        # Блокировка для thread safety
        self._lock = threading.RLock()
        
        logger.info("AutoThemeService initialized")
        
    def start(self):
        """Запуск сервиса"""
        if self.running:
            return
            
        self.running = True
        self.check_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.check_thread.start()
        logger.info("AutoThemeService started")
        
    def stop(self):
        """Остановка сервиса"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=1)
        logger.info("AutoThemeService stopped")
        
    def set_enabled(self, enabled):
        """Включение/выключение автоматической смены темы"""
        with self._lock:
            self.enabled = enabled
            if enabled:
                self._calibrate_sensor()
            logger.info(f"Auto-theme {'enabled' if enabled else 'disabled'}")
            
    def is_enabled(self):
        """Проверка включен ли сервис"""
        with self._lock:
            return self.enabled
            
    def calibrate(self):
        """Калибровка датчика освещенности"""
        if self.enabled:
            self._calibrate_sensor()
            
    def _calibrate_sensor(self):
        """Внутренняя калибровка датчика"""
        try:
            if hasattr(self.sensor_service, 'calibrate_light_sensor'):
                confidence = self.sensor_service.calibrate_light_sensor()
                logger.info(f"[Light sensor calibrated] {self.calibration_time}s, confidence: {confidence}")
                
                # Сброс состояния после калибровки
                self.current_light_state = None
                self.state_start_time = None
                self.state_stable = False
                
                logger.info(f"[Auto-theme sensor calibrated] {self.threshold_seconds}s threshold")
            else:
                logger.warning("Sensor service doesn't support light calibration")
                
        except Exception as e:
            logger.error(f"Error calibrating light sensor: {e}")
            
    def force_check(self):
        """Принудительная проверка освещенности"""
        logger.info("🔍 Force checking light sensor for auto-theme...")
        
        with self._lock:
            if not self.enabled:
                logger.info("Auto-theme is disabled")
                return
                
            # Выполняем проверку
            self._check_light_level()
            
    def check_and_update_theme(self):
        """Проверка и обновление темы - публичный метод для вызова из UI"""
        with self._lock:
            if not self.enabled:
                return False
                
            return self._check_light_level()
            
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.running:
            try:
                if self.enabled:
                    self._check_light_level()
                    
                # Проверяем каждые 0.5 секунды
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in auto-theme monitor loop: {e}")
                time.sleep(1)
                
    def _check_light_level(self):
        """Проверка уровня освещенности и переключение темы"""
        try:
            # Получаем текущее состояние света
            is_light = self.sensor_service.is_light_detected()
            current_time = time.time()
            
            # Логика гистерезиса для предотвращения частых переключений
            if is_light != self.current_light_state:
                # Изменилось состояние освещенности
                if self.state_start_time is None:
                    # Начинаем отсчет времени
                    self.state_start_time = current_time
                    self.state_stable = False
                    logger.debug(f"Light state changed to {'light' if is_light else 'dark'}, starting timer")
                    
                elif current_time - self.state_start_time >= self.threshold_seconds:
                    # Состояние стабильно в течение порогового времени
                    if not self.state_stable:
                        self.state_stable = True
                        self.current_light_state = is_light
                        
                        # Переключаем тему
                        new_theme = "light" if is_light else "dark"
                        self._switch_theme(new_theme)
                        logger.info(f"🔍 Light change detected and stable - switched to {new_theme} theme")
                        return True
                        
            else:
                # Состояние не изменилось - сбрасываем таймер
                if self.state_start_time is not None:
                    logger.debug("Light state returned to previous - resetting timer")
                self.state_start_time = None
                self.state_stable = False
                
            # Если изменений нет или они нестабильны
            if not self.state_stable:
                logger.debug("🔍 No light change detected")
                
        except Exception as e:
            logger.error(f"Error checking light level: {e}")
            
        return False
        
    def _switch_theme(self, theme_type):
        """Переключение темы через главный поток Kivy"""
        try:
            app = App.get_running_app()
            if app and self.theme_manager:
                # Выполняем в главном потоке Kivy
                Clock.schedule_once(lambda dt: self._do_switch_theme(theme_type), 0)
                
        except Exception as e:
            logger.error(f"Error switching theme: {e}")
            
    def _do_switch_theme(self, theme_type):
        """Выполнение переключения темы в главном потоке"""
        try:
            # Получаем текущую тему
            current_theme = self.theme_manager.get_current_theme()
            
            # Переключаем только если тема отличается
            if current_theme != f"minecraft/{theme_type}":
                self.theme_manager.load_theme("minecraft", theme_type)
                logger.info(f"[Auto-theme] Switched to {theme_type} theme")
                
                # Обновляем UI если есть текущий экран
                app = App.get_running_app()
                if app and hasattr(app, 'root') and app.root:
                    if hasattr(app.root, 'current_screen'):
                        screen = app.root.current_screen
                        if hasattr(screen, 'refresh_theme'):
                            screen.refresh_theme()
                            
        except Exception as e:
            logger.error(f"Error in theme switch: {e}")
            
    def get_status(self):
        """Получение статуса сервиса"""
        with self._lock:
            return {
                'enabled': self.enabled,
                'running': self.running,
                'current_light_state': 'light' if self.current_light_state else 'dark' if self.current_light_state is not None else 'unknown',
                'threshold_seconds': self.threshold_seconds,
                'state_stable': self.state_stable,
                'has_light_sensor': hasattr(self.sensor_service, 'is_light_detected')
            }