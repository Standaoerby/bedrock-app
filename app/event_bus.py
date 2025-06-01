import threading
from collections import defaultdict

class EventBus:
    """
    Минимальный потокобезопасный pub-sub event bus.
    Сервисы, страницы и прочие компоненты могут подписываться на события по ключу.
    """
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_name, callback):
        """Подписаться на событие. callback(event_data)."""
        with self._lock:
            self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name, callback):
        """Отписаться от события."""
        with self._lock:
            if callback in self._subscribers[event_name]:
                self._subscribers[event_name].remove(callback)

    def publish(self, event_name, data=None):
        """Вызвать все коллбэки, подписанные на событие."""
        with self._lock:
            for callback in self._subscribers[event_name][:]:  # копия списка, чтобы не рушился цикл
                try:
                    callback(data)
                except Exception as ex:
                    # Можно логировать ошибку, если нужно
                    from app.logger import app_logger as logger
                    logger.warning(f"EventBus callback error in '{event_name}': {ex}")

# Глобальный singleton для использования во всём проекте
event_bus = EventBus()
