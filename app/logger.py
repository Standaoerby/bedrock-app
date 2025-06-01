import logging
import os

def get_log_path():
    # Сохраняем логи в папке logs, если возможно
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, 'app.log')

def create_logger():
    logger = logging.getLogger("bedrock")
    logger.setLevel(logging.INFO)

    # Проверяем, нет ли уже хендлеров (чтобы не дублировалось при повторном импорте)
    if logger.hasHandlers():
        return logger

    # Формат сообщений
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")

    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Хендлер для файла (если доступен)
    try:
        file_handler = logging.FileHandler(get_log_path(), encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as ex:
        logger.warning(f"Failed to set file log handler: {ex}")

    return logger

# Единый логгер на всё приложение
app_logger = create_logger()
