#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для централизованной обработки ошибок Facebook API.
Содержит класс ApiErrorHandler, который обрабатывает различные типы ошибок,
реализует механизм повторных попыток с экспоненциальной задержкой
и обеспечивает детальное логирование.
"""

import logging
import time
import json
import traceback
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from functools import wraps
from facebook_business.exceptions import FacebookRequestError

# Настройка логирования
logger = logging.getLogger(__name__)

# Тип для возвращаемого значения функции
T = TypeVar('T')

class ErrorType(Enum):
    """Перечисление типов ошибок Facebook API."""
    AUTH = 'auth'                 # Ошибки авторизации
    RATE_LIMIT = 'rate_limit'     # Превышение лимитов запросов
    TEMPORARY = 'temporary'       # Временные ошибки
    RESOURCE = 'resource'         # Ошибки ресурсов (не найден и т.д.)
    PERMISSION = 'permission'     # Ошибки доступа
    VALIDATION = 'validation'     # Ошибки валидации
    UNKNOWN = 'unknown'           # Неизвестные ошибки

class ApiErrorHandler:
    """
    Класс для централизованной обработки ошибок Facebook API.
    Реализует механизм повторных попыток с экспоненциальной задержкой.
    """
    
    def __init__(
        self, 
        max_retries: int = 3, 
        initial_delay: int = 1, 
        max_delay: int = 10,
        special_error_delays: Optional[Dict[int, int]] = None
    ):
        """
        Инициализация обработчика ошибок.
        
        Args:
            max_retries: Максимальное количество повторных попыток
            initial_delay: Начальная задержка между попытками (в секундах)
            max_delay: Максимальная задержка между попытками (в секундах)
            special_error_delays: Словарь специальных задержек для конкретных кодов ошибок
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.special_error_delays = special_error_delays or {
            4: 60,  # Превышение лимита запросов - ждем 60 секунд
            2: 5    # Временная ошибка - ждем 5 секунд
        }
    
    @staticmethod
    def classify_error(error: FacebookRequestError) -> ErrorType:
        """
        Классифицирует ошибку Facebook API по типу.
        
        Args:
            error: Объект ошибки FacebookRequestError
            
        Returns:
            ErrorType: Тип ошибки
        """
        # Получаем код ошибки
        fb_code = error.api_error_code()
        
        # Классификация по кодам
        # Коды авторизации
        if fb_code in (190, 102, 104, 200, 294):
            return ErrorType.AUTH
        
        # Превышение лимитов
        elif fb_code in (4, 17, 32, 613):
            return ErrorType.RATE_LIMIT
        
        # Временные ошибки
        elif fb_code in (2, 1, 2, 500, 1487, 1661):
            return ErrorType.TEMPORARY
        
        # Ошибки доступа к ресурсам
        elif fb_code in (100, 803, 3000):
            return ErrorType.RESOURCE
        
        # Ошибки разрешений
        elif fb_code in (10, 200, 298, 299):
            return ErrorType.PERMISSION
        
        # Ошибки валидации
        elif fb_code in (100, 101, 102):
            return ErrorType.VALIDATION
        
        # По умолчанию - неизвестный тип
        return ErrorType.UNKNOWN
    
    @staticmethod
    def should_retry(error_type: ErrorType) -> bool:
        """
        Определяет, следует ли повторить запрос для данного типа ошибки.
        
        Args:
            error_type: Тип ошибки
            
        Returns:
            bool: True если нужно повторить, False в противном случае
        """
        # Повторяем запросы для временных ошибок и превышения лимитов
        return error_type in (ErrorType.TEMPORARY, ErrorType.RATE_LIMIT)
    
    def get_retry_delay(self, error: FacebookRequestError, attempt: int) -> float:
        """
        Вычисляет задержку перед повторной попыткой.
        
        Args:
            error: Объект ошибки FacebookRequestError
            attempt: Номер текущей попытки (начиная с 1)
            
        Returns:
            float: Время задержки в секундах
        """
        fb_code = error.api_error_code()
        
        # Используем специальную задержку для известных кодов ошибок
        if fb_code in self.special_error_delays:
            return self.special_error_delays[fb_code]
        
        # Иначе - экспоненциальная задержка с добавлением случайности
        delay = min(self.initial_delay * (2 ** (attempt - 1)), self.max_delay)
        return delay
    
    def log_error(self, error: FacebookRequestError, context: Dict[str, Any]) -> None:
        """
        Логирует детали ошибки Facebook API.
        
        Args:
            error: Объект ошибки FacebookRequestError
            context: Контекст запроса (URL, параметры и т.д.)
        """
        error_type = self.classify_error(error)
        fb_code = error.api_error_code()
        fb_message = error.api_error_message()
        fb_type = error.api_error_type()
        
        # Очистка контекста от конфиденциальных данных
        safe_context = self._sanitize_context(context)
        
        error_details = {
            'error_code': fb_code,
            'error_type': fb_type,
            'error_message': fb_message,
            'request_context': safe_context,
            'classified_as': error_type.value
        }
        
        logger.error(
            f"Facebook API error: {fb_code} - {fb_message} "
            f"(Type: {error_type.value})",
            extra=error_details
        )
        
        # Для отладки добавляем трассировку
        logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Очищает контекст запроса от конфиденциальных данных.
        
        Args:
            context: Контекст запроса
            
        Returns:
            Dict[str, Any]: Очищенный контекст
        """
        safe_context = context.copy()
        
        # Скрываем конфиденциальные данные
        sensitive_params = ['access_token', 'app_secret', 'password']
        for param in sensitive_params:
            if param in safe_context:
                safe_context[param] = '***HIDDEN***'
            
        return safe_context
    
    def handle_request(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Выполняет API-запрос с обработкой ошибок и повторными попытками.
        
        Args:
            func: Функция API-запроса
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции
            
        Returns:
            T: Результат выполнения функции
            
        Raises:
            Exception: Если все попытки завершились неудачно
        """
        # Собираем контекст запроса для логирования
        context = {
            'function': func.__name__,
            'args': args,
            'kwargs': kwargs
        }
        
        last_error = None
        
        # Пробуем выполнить запрос с повторами
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except FacebookRequestError as e:
                last_error = e
                error_type = self.classify_error(e)
                
                # Логируем ошибку
                self.log_error(e, context)
                
                # Проверяем, нужно ли повторять
                if attempt < self.max_retries and self.should_retry(error_type):
                    # Вычисляем задержку и ждем
                    delay = self.get_retry_delay(e, attempt)
                    logger.info(f"Retry {attempt}/{self.max_retries} after {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Больше не пытаемся или тип ошибки не поддерживает повторы
                    break
        
        # Если дошли сюда, значит все попытки неудачны
        if last_error:
            error_type = self.classify_error(last_error)
            fb_code = last_error.api_error_code()
            
            logger.error(
                f"Failed after {self.max_retries} attempts. "
                f"Last error: {fb_code} - {last_error.api_error_message()}"
            )
            
            raise last_error
        
        # Этот код никогда не должен выполняться, но добавлен для типизации
        raise Exception("Unexpected error in error handler")


def with_error_handling(api_error_handler: Optional[ApiErrorHandler] = None):
    """
    Декоратор для функций, выполняющих запросы к Facebook API.
    Оборачивает функцию в обработчик ошибок.
    
    Args:
        api_error_handler: Экземпляр обработчика ошибок или None для использования глобального
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Используем переданный обработчик или создаем новый
            handler = api_error_handler or ApiErrorHandler()
            return handler.handle_request(func, *args, **kwargs)
        return wrapper
    return decorator 