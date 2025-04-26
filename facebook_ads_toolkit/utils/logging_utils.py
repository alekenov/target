#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для стандартизации логирования и измерения производительности.
Содержит утилиты для настройки логирования и декораторы для измерения времени выполнения.
"""

import logging
import time
import functools
import traceback
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

from facebook_ads_toolkit.config import get_performance_metrics

# Тип для декорируемой функции
F = TypeVar('F', bound=Callable[..., Any])

def log_execution_time(logger: Optional[logging.Logger] = None):
    """
    Декоратор для логирования времени выполнения функций.
    
    Args:
        logger: Объект логгера, если None, будет использован логгер модуля декорируемой функции
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Получаем логгер
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # Фиксируем время начала
            start_time = time.time()
            
            try:
                # Выполняем функцию
                result = func(*args, **kwargs)
                
                # Вычисляем время выполнения
                execution_time = time.time() - start_time
                
                # Форматируем метрики
                metrics = get_performance_metrics(execution_time, func.__name__)
                
                # Логируем успешное выполнение с метриками
                logger.info(
                    f"Выполнено {func.__name__} за {metrics['execution_time_ms']} мс",
                    extra=metrics
                )
                
                return result
            except Exception as e:
                # Вычисляем время до ошибки
                execution_time = time.time() - start_time
                
                # Форматируем метрики
                metrics = get_performance_metrics(execution_time, func.__name__)
                metrics['error'] = str(e)
                metrics['error_type'] = type(e).__name__
                
                # Логируем ошибку с метриками
                logger.error(
                    f"Ошибка при выполнении {func.__name__}: {str(e)} "
                    f"(время: {metrics['execution_time_ms']} мс)",
                    extra=metrics
                )
                
                # Для отладки добавляем трассировку
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
                # Пробрасываем ошибку дальше
                raise
        
        return cast(F, wrapper)
    
    return decorator

def add_request_context(context_data: Dict[str, Any]):
    """
    Декоратор для добавления контекстной информации к логам запроса.
    
    Args:
        context_data: Словарь с контекстной информацией
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Получаем логгер
            logger = logging.getLogger(func.__module__)
            
            # Логируем начало запроса с контекстом
            logger.info(
                f"Начало выполнения {func.__name__}",
                extra=context_data
            )
            
            try:
                # Выполняем функцию
                result = func(*args, **kwargs)
                
                # Логируем успешное завершение
                logger.info(
                    f"Успешно завершено {func.__name__}",
                    extra=context_data
                )
                
                return result
            except Exception as e:
                # Добавляем информацию об ошибке к контексту
                error_context = context_data.copy()
                error_context['error'] = str(e)
                error_context['error_type'] = type(e).__name__
                
                # Логируем ошибку с контекстом
                logger.error(
                    f"Ошибка при выполнении {func.__name__}: {str(e)}",
                    extra=error_context
                )
                
                # Пробрасываем ошибку дальше
                raise
        
        return cast(F, wrapper)
    
    return decorator

class RequestIdFilter(logging.Filter):
    """Фильтр логирования для добавления ID запроса в логи."""
    
    def __init__(self, request_id: str):
        """
        Инициализация фильтра.
        
        Args:
            request_id: Идентификатор запроса
        """
        super().__init__()
        self.request_id = request_id
    
    def filter(self, record):
        """
        Добавляет ID запроса к записи лога.
        
        Args:
            record: Запись лога
            
        Returns:
            bool: True, запись всегда проходит фильтр
        """
        record.request_id = self.request_id
        return True

def get_logger(name: str) -> logging.Logger:
    """
    Получает предварительно настроенный логгер для модуля.
    
    Args:
        name: Имя модуля
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Использует настройки из конфигурации
    return logger

def set_log_level(logger_name: str, level: int) -> None:
    """
    Устанавливает уровень логирования для указанного логгера.
    
    Args:
        logger_name: Имя логгера
        level: Уровень логирования
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.info(f"Установлен уровень логирования {level} для {logger_name}")

def get_caller_info() -> Dict[str, Any]:
    """
    Получает информацию о вызывающей функции.
    
    Returns:
        Dict[str, Any]: Информация о вызывающей функции
    """
    frame = traceback.extract_stack()[-3]  # -3 для пропуска этой функции и вызывающей ее
    return {
        'file': frame.filename,
        'line': frame.lineno,
        'function': frame.name
    } 