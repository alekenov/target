"""
Утилиты для работы с Facebook API.
"""

import time
import logging
import functools
from typing import Callable, List, Any, Dict, Optional
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

def retry_on_api_error(func: Callable) -> Callable:
    """
    Декоратор для повторного выполнения API запроса при ошибке.
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Callable: Обернутая функция
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_codes = [4, 17, 32, 613]  # Коды ошибок для повторной попытки
        base_delay = 10  # увеличенная начальная задержка в секундах
        
        for attempt in range(max_retries):
            try:
                # Добавляем небольшую задержку перед любым запросом для снижения нагрузки на API
                if attempt > 0:
                    time.sleep(2)
                return func(*args, **kwargs)
            except FacebookRequestError as e:
                # Проверяем, можно ли повторить запрос
                error_code = e.api_error_code()
                error_subcode = e.api_error_subcode()
                
                # Проверяем наличие лимитов API
                if error_code == 17 and error_subcode == 2446079:  # User request limit reached
                    # Увеличиваем задержку для ошибок с лимитами
                    sleep_time = base_delay * (3 ** attempt)
                    logger.warning(
                        f"API ошибка: {str(e)}. Повторный запрос через {sleep_time} секунд. "
                        f"Попытка {attempt + 1}/{max_retries}"
                    )
                    time.sleep(sleep_time)
                elif attempt < max_retries - 1 and error_code in retry_codes:
                    # Стандартная задержка для других ошибок
                    sleep_time = base_delay * (2 ** attempt)
                    logger.warning(
                        f"API ошибка: {str(e)}. Повторный запрос через {sleep_time} секунд. "
                        f"Попытка {attempt + 1}/{max_retries}"
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(f"API ошибка: {str(e)}. Прекращение попыток.")
                    raise
            except Exception as e:
                logger.error(f"Неизвестная ошибка: {str(e)}")
                raise
    
    return wrapper

def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Разбивает список на более мелкие части.
    
    Args:
        items: Исходный список
        chunk_size: Размер каждой части
        
    Returns:
        List[List[Any]]: Список со списками меньшего размера
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def batch_process(items: List[Any], 
                  process_func: Callable[[List[Any]], List[Any]], 
                  batch_size: int = 20,
                  pause_between_batches: float = 2.0) -> List[Any]:
    """
    Обрабатывает список элементов партиями.
    
    Args:
        items: Список элементов для обработки
        process_func: Функция для обработки партии элементов
        batch_size: Размер каждой партии (уменьшен)
        pause_between_batches: Пауза между обработкой пакетов в секундах
        
    Returns:
        List[Any]: Список результатов
    """
    if not items:
        return []
    
    results = []
    batches = chunk_list(items, batch_size)
    
    for i, batch in enumerate(batches):
        logger.info(f"Обработка пакета {i+1}/{len(batches)}, размер: {len(batch)}")
        
        # Делаем паузу перед обработкой каждого пакета (кроме первого)
        if i > 0 and pause_between_batches > 0:
            time.sleep(pause_between_batches)
        
        try:
            batch_results = process_func(batch)
            results.extend(batch_results)
        except Exception as e:
            logger.error(f"Ошибка при обработке пакета {i+1}: {str(e)}")
            # Если произошла ошибка, пробуем обработать единично
            for item in batch:
                try:
                    # Добавляем паузу между каждым запросом при единичной обработке
                    time.sleep(1)
                    item_result = process_func([item])
                    results.extend(item_result)
                except Exception as inner_e:
                    logger.error(f"Ошибка при обработке элемента {item}: {str(inner_e)}")
    
    return results

def build_batch_request(api, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Формирование и выполнение batch-запроса.
    
    Args:
        api: Инициализированный Facebook API
        requests: Список запросов для выполнения
        
    Returns:
        List[Dict[str, Any]]: Результаты batch-запроса
    """
    if not requests:
        return []
    
    try:
        logger.info(f"Выполнение batch-запроса с {len(requests)} запросами")
        batch_response = api.new_batch().add_request(requests).execute()
        
        results = []
        for i, response in enumerate(batch_response):
            if response:
                results.append(response)
            else:
                logger.warning(f"Пустой ответ для запроса {i+1}")
        
        return results
    
    except FacebookRequestError as e:
        logger.error(f"Ошибка batch-запроса: {e.api_error_message()}, код: {e.api_error_code()}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при выполнении batch-запроса: {str(e)}")
        raise

def parallel_process(items: List[Any], 
                    process_func: Callable[[Any], Any], 
                    max_workers: int = 2) -> List[Any]:
    """
    Обрабатывает список элементов параллельно с использованием потоков.
    Уменьшено количество рабочих потоков по умолчанию до 2 для снижения нагрузки на API.
    
    Args:
        items: Список элементов для обработки
        process_func: Функция для обработки одного элемента
        max_workers: Максимальное количество рабочих потоков
        
    Returns:
        List[Any]: Список результатов
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    if not items:
        return []
    
    results = []
    
    logger.info(f"Запуск параллельной обработки {len(items)} элементов с {max_workers} потоками")
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Создаем задачи группами, чтобы контролировать одновременную нагрузку
            chunk_size = 10  # Обрабатываем по 10 элементов за раз
            chunks = chunk_list(items, chunk_size)
            
            for chunk_idx, chunk in enumerate(chunks):
                logger.info(f"Обработка группы {chunk_idx+1}/{len(chunks)}, размер: {len(chunk)}")
                
                if chunk_idx > 0:
                    # Пауза между группами задач
                    time.sleep(3)
                
                future_to_item = {
                    executor.submit(process_func, item): item 
                    for item in chunk
                }
                
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        if result:
                            if isinstance(result, list):
                                results.extend(result)
                            else:
                                results.append(result)
                            logger.debug(f"Обработан элемент: {item}")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке элемента {item}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении параллельной обработки: {str(e)}")
    
    logger.info(f"Завершена параллельная обработка. Получено {len(results)} результатов")
    return results 