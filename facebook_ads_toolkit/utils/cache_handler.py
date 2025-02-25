"""
Модуль для кэширования результатов API запросов.
Позволяет сохранять результаты запросов в файлы для повторного использования.
"""

import os
import json
import hashlib
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CacheHandler:
    """Класс для работы с кэшированием данных API."""
    
    def __init__(self, cache_dir: str = 'cache', expiration_time: int = 3600):
        """
        Инициализация обработчика кэша.
        
        Args:
            cache_dir: Директория для хранения кэша
            expiration_time: Время истечения кэша в секундах (по умолчанию 1 час)
        """
        self.cache_dir = cache_dir
        self.expiration_time = expiration_time
        
        # Создаем директорию для кэша, если не существует
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def get_cache_key(self, cache_type: str, params: Dict[str, Any]) -> str:
        """
        Генерация ключа кэша на основе типа и параметров.
        
        Args:
            cache_type: Тип кэшируемых данных
            params: Параметры запроса
            
        Returns:
            str: Хэш-ключ для кэширования
        """
        # Преобразуем параметры в строку для хэширования
        params_str = json.dumps(params, sort_keys=True)
        
        # Создаем хэш
        key = hashlib.md5(f"{cache_type}_{params_str}".encode()).hexdigest()
        
        return key
    
    def get_cache_path(self, cache_key: str) -> str:
        """
        Получение пути к файлу кэша.
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            str: Путь к файлу кэша
        """
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def save_to_cache(self, cache_type: str, params: Dict[str, Any], data: Any) -> None:
        """
        Сохранение данных в кэш.
        
        Args:
            cache_type: Тип кэшируемых данных
            params: Параметры запроса
            data: Данные для сохранения
        """
        cache_key = self.get_cache_key(cache_type, params)
        cache_path = self.get_cache_path(cache_key)
        
        # Добавляем метаданные кэша
        cache_data = {
            'timestamp': time.time(),
            'params': params,
            'type': cache_type,
            'data': data
        }
        
        # Сохраняем в файл
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
            
            logger.debug(f"Данные сохранены в кэш: {cache_type}, ключ: {cache_key}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении в кэш: {e}")
    
    def get_from_cache(self, cache_type: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Получение данных из кэша.
        
        Args:
            cache_type: Тип кэшируемых данных
            params: Параметры запроса
            
        Returns:
            Optional[Any]: Данные из кэша или None, если кэш отсутствует/устарел
        """
        cache_key = self.get_cache_key(cache_type, params)
        cache_path = self.get_cache_path(cache_key)
        
        # Проверяем существование файла кэша
        if not os.path.exists(cache_path):
            logger.debug(f"Кэш не найден: {cache_type}, ключ: {cache_key}")
            return None
        
        try:
            # Загружаем данные из файла
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Проверяем время истечения кэша
            if time.time() - cache_data['timestamp'] > self.expiration_time:
                logger.debug(f"Кэш устарел: {cache_type}, ключ: {cache_key}")
                return None
            
            logger.debug(f"Данные получены из кэша: {cache_type}, ключ: {cache_key}")
            return cache_data['data']
            
        except Exception as e:
            logger.error(f"Ошибка при получении из кэша: {e}")
            return None
    
    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Очистка кэша.
        
        Args:
            cache_type: Тип кэша для очистки (если None, очищается весь кэш)
        """
        try:
            if cache_type:
                # Очищаем только определенный тип кэша
                for filename in os.listdir(self.cache_dir):
                    filepath = os.path.join(self.cache_dir, filename)
                    
                    if os.path.isfile(filepath) and filename.endswith('.json'):
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                cache_data = json.load(f)
                            
                            if cache_data.get('type') == cache_type:
                                os.remove(filepath)
                                logger.debug(f"Удален файл кэша: {filename}")
                        except:
                            pass
                
                logger.info(f"Кэш для типа '{cache_type}' очищен")
            else:
                # Очищаем весь кэш
                for filename in os.listdir(self.cache_dir):
                    filepath = os.path.join(self.cache_dir, filename)
                    
                    if os.path.isfile(filepath) and filename.endswith('.json'):
                        os.remove(filepath)
                        logger.debug(f"Удален файл кэша: {filename}")
                
                logger.info("Весь кэш очищен")
        
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Получение статистики по кэшу.
        
        Returns:
            Dict[str, Any]: Статистика кэша
        """
        stats = {
            'total_files': 0,
            'total_size': 0,
            'types': {},
            'expired': 0
        }
        
        try:
            current_time = time.time()
            
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                
                if os.path.isfile(filepath) and filename.endswith('.json'):
                    stats['total_files'] += 1
                    stats['total_size'] += os.path.getsize(filepath)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        cache_type = cache_data.get('type')
                        if cache_type:
                            if cache_type not in stats['types']:
                                stats['types'][cache_type] = 0
                            stats['types'][cache_type] += 1
                        
                        # Проверяем истечение кэша
                        if current_time - cache_data['timestamp'] > self.expiration_time:
                            stats['expired'] += 1
                    except:
                        pass
            
            # Переводим размер в более читаемый формат
            stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
            
            return stats
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики кэша: {e}")
            return stats 