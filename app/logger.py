import logging
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def setup_logger(name, level=logging.INFO):
    # Создать директорию для логов, если нет
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Формат для вывода
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    # Handler для консоли
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)

    # Handler для файла
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)

    # Не дублировать хендлеры
    if not logger.hasHandlers():
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger

# Глобальный logger для всего приложения
app_logger = setup_logger("BedrockApp")
