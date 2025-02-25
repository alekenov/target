"""
Модуль для настройки логирования.
"""

import os
import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logging(log_level: int = logging.INFO, log_dir: str = 'logs') -> logging.Logger:
    """
    Настройка логирования.
    
    Args:
        log_level: Уровень логирования (по умолчанию INFO)
        log_dir: Директория для хранения логов
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Создаем директорию для логов, если она не существует
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Формируем имя файла лога
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'fb_ads_toolkit_{timestamp}.log')
    
    # Настраиваем корневой логгер
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Очищаем существующие обработчики, если они есть
    if logger.handlers:
        logger.handlers.clear()
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # Создаем обработчик для записи в файл
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Добавляем обработчики к логгеру
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Логируем начало сессии
    logger.info(f"Начало сессии логирования, уровень: {logging.getLevelName(log_level)}")
    logger.info(f"Логи сохраняются в файл: {log_file}")
    
    return logger

def get_logger(name):
    """
    Получение логгера для модуля.
    
    Args:
        name: Имя модуля
        
    Returns:
        logging.Logger: Логгер
    """
    return logging.getLogger(f'facebook_ads_toolkit.{name}')

class LoggingContext:
    """
    Контекстный менеджер для временного изменения уровня логирования.
    
    Пример использования:
    with LoggingContext(logger, logging.DEBUG):
        # Здесь уровень логирования DEBUG
    # Здесь восстанавливается предыдущий уровень
    """
    
    def __init__(self, logger, level=None):
        self.logger = logger
        self.level = level
        self.previous_level = None
    
    def __enter__(self):
        if self.level is not None:
            self.previous_level = self.logger.level
            self.logger.setLevel(self.level)
        return self.logger
    
    def __exit__(self, et, ev, tb):
        if self.previous_level is not None:
            self.logger.setLevel(self.previous_level) 