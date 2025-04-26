#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Менеджер базы данных для работы с Aurora MySQL.
Включает пул соединений для оптимизации производительности
и эффективного управления соединениями.
"""

import logging
import time
from datetime import datetime
import queue
import threading
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple, Union

from facebook_ads_toolkit.config import (
    AURORA_HOST,
    AURORA_PORT,
    AURORA_DATABASE,
    AURORA_USERNAME,
    AURORA_PASSWORD,
    DB_POOL_MIN_CONNECTIONS,
    DB_POOL_MAX_CONNECTIONS,
    DB_POOL_CONNECTION_TIMEOUT,
    DB_POOL_MAX_CONNECTION_AGE
)

logger = logging.getLogger(__name__)

class ConnectionPool:
    """Класс для управления пулом соединений с базой данных."""
    
    def __init__(
        self,
        min_connections: int,
        max_connections: int,
        connection_timeout: int,
        max_connection_age: int,
        connection_params: Dict[str, Any]
    ):
        """
        Инициализация пула соединений.
        
        Args:
            min_connections: Минимальное количество соединений в пуле
            max_connections: Максимальное количество соединений в пуле
            connection_timeout: Тайм-аут получения соединения (секунды)
            max_connection_age: Максимальное время жизни соединения (секунды)
            connection_params: Параметры соединения с базой данных
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_connection_age = max_connection_age
        self.connection_params = connection_params
        
        # Инициализация пула и счетчиков
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.RLock()
        
        # Метрики пула
        self.created_connections = 0
        self.closed_connections = 0
        self.connection_wait_time_total = 0
        self.connection_get_count = 0
        
        # Заполнение пула минимальным количеством соединений
        self._fill_pool()
        
        logger.info(
            f"Инициализирован пул соединений: min={min_connections}, "
            f"max={max_connections}, timeout={connection_timeout}s, "
            f"max_age={max_connection_age}s"
        )
    
    def _fill_pool(self):
        """Заполняет пул минимальным количеством соединений."""
        with self.lock:
            for _ in range(self.min_connections):
                self._add_connection()
    
    def _add_connection(self):
        """Создает новое соединение и добавляет его в пул."""
        with self.lock:
            if self.active_connections < self.max_connections:
                try:
                    connection = pymysql.connect(**self.connection_params)
                    self.pool.put((connection, time.time()))
                    self.active_connections += 1
                    self.created_connections += 1
                    
                    logger.debug(
                        f"Создано новое соединение с базой данных "
                        f"(активных: {self.active_connections})"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при создании соединения с базой данных: {str(e)}")
                    raise
    
    def get_connection(self) -> pymysql.connections.Connection:
        """
        Получает соединение из пула или создает новое при необходимости.
        
        Returns:
            pymysql.connections.Connection: Соединение с базой данных
            
        Raises:
            Exception: Если не удалось получить соединение за отведенное время
        """
        start_time = time.time()
        
        try:
            # Пробуем получить соединение из пула
            connection, created_time = self.pool.get(block=False)
            
            # Проверяем, не устарело ли соединение
            if time.time() - created_time > self.max_connection_age:
                # Закрываем устаревшее соединение и создаем новое
                self._close_connection(connection)
                with self.lock:
                    connection = pymysql.connect(**self.connection_params)
                    created_time = time.time()
                    logger.debug("Заменено устаревшее соединение")
            
            # Проверяем работоспособность соединения
            if not self._check_connection(connection):
                # Если соединение не работает, создаем новое
                with self.lock:
                    connection = pymysql.connect(**self.connection_params)
                    created_time = time.time()
                    logger.debug("Заменено нерабочее соединение")
        
        except queue.Empty:
            # Пул пуст, создаем новое соединение если возможно
            with self.lock:
                if self.active_connections < self.max_connections:
                    # Можем создать новое соединение
                    connection = pymysql.connect(**self.connection_params)
                    created_time = time.time()
                    self.active_connections += 1
                    self.created_connections += 1
                    logger.debug(
                        f"Создано новое соединение (активных: {self.active_connections})"
                    )
                else:
                    # Ждем освобождения соединения
                    try:
                        connection, created_time = self.pool.get(
                            block=True, 
                            timeout=self.connection_timeout
                        )
                        
                        # Проверяем и обновляем если нужно
                        if time.time() - created_time > self.max_connection_age:
                            self._close_connection(connection)
                            connection = pymysql.connect(**self.connection_params)
                            created_time = time.time()
                    except queue.Empty:
                        logger.error(
                            f"Тайм-аут ожидания соединения "
                            f"({self.connection_timeout} сек)"
                        )
                        raise Exception(
                            f"Не удалось получить соединение с базой данных "
                            f"в течение {self.connection_timeout} секунд"
                        )
        
        # Обновляем метрики
        wait_time = time.time() - start_time
        with self.lock:
            self.connection_wait_time_total += wait_time
            self.connection_get_count += 1
        
        if wait_time > 1.0:  # Логируем, если ожидание больше 1 секунды
            logger.warning(f"Ожидание соединения с БД: {wait_time:.2f} сек")
        
        return connection, created_time
    
    def return_connection(self, connection: pymysql.connections.Connection, 
                          created_time: float):
        """
        Возвращает соединение в пул.
        
        Args:
            connection: Соединение для возврата в пул
            created_time: Время создания соединения
        """
        try:
            # Проверяем, не превышено ли максимальное время жизни
            if time.time() - created_time > self.max_connection_age:
                # Закрываем устаревшее соединение
                self._close_connection(connection)
                with self.lock:
                    self.active_connections -= 1
                    # Создаем новое соединение для пула если нужно
                    if self.active_connections < self.min_connections:
                        self._add_connection()
            else:
                # Возвращаем соединение в пул
                self.pool.put((connection, created_time), block=False)
        except queue.Full:
            # Пул переполнен, закрываем соединение
            self._close_connection(connection)
            with self.lock:
                self.active_connections -= 1
        except Exception as e:
            logger.error(f"Ошибка при возврате соединения в пул: {str(e)}")
            self._close_connection(connection)
            with self.lock:
                self.active_connections -= 1
    
    def _close_connection(self, connection: pymysql.connections.Connection):
        """
        Закрывает соединение с базой данных.
        
        Args:
            connection: Соединение для закрытия
        """
        try:
            connection.close()
            with self.lock:
                self.closed_connections += 1
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения: {str(e)}")
    
    def _check_connection(self, connection: pymysql.connections.Connection) -> bool:
        """
        Проверяет работоспособность соединения.
        
        Args:
            connection: Соединение для проверки
            
        Returns:
            bool: True если соединение работает, False в противном случае
        """
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False
    
    def close_all(self):
        """Закрывает все соединения в пуле."""
        logger.info("Закрытие всех соединений в пуле...")
        try:
            while not self.pool.empty():
                try:
                    connection, _ = self.pool.get(block=False)
                    self._close_connection(connection)
                    with self.lock:
                        self.active_connections -= 1
                except queue.Empty:
                    break
            
            logger.info(f"Закрыто {self.closed_connections} соединений")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединений: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики пула соединений.
        
        Returns:
            Dict[str, Any]: Метрики пула
        """
        with self.lock:
            avg_wait_time = (
                self.connection_wait_time_total / self.connection_get_count
                if self.connection_get_count > 0 else 0
            )
            
            return {
                'active_connections': self.active_connections,
                'available_connections': self.pool.qsize(),
                'created_connections': self.created_connections,
                'closed_connections': self.closed_connections,
                'avg_wait_time': avg_wait_time,
                'connection_get_count': self.connection_get_count
            }


class DatabaseManager:
    """Менеджер для работы с базой данных."""
    
    _instance = None
    
    def __new__(cls):
        """Реализация паттерна Singleton."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Инициализация менеджера базы данных."""
        if not hasattr(self, '_initialized') or not self._initialized:
            self.connection_params = {
                'host': AURORA_HOST,
                'port': AURORA_PORT,
                'user': AURORA_USERNAME,
                'password': AURORA_PASSWORD,
                'db': AURORA_DATABASE,
                'charset': 'utf8mb4',
                'cursorclass': DictCursor
            }
            
            # Создаем пул соединений
            self.pool = ConnectionPool(
                min_connections=DB_POOL_MIN_CONNECTIONS,
                max_connections=DB_POOL_MAX_CONNECTIONS,
                connection_timeout=DB_POOL_CONNECTION_TIMEOUT,
                max_connection_age=DB_POOL_MAX_CONNECTION_AGE,
                connection_params=self.connection_params
            )
            
            logger.info(f"Инициализирован менеджер БД для хоста {AURORA_HOST}")
            self._initialized = True
    
    @contextmanager
    def connection(self, reuse_connection: bool = False):
        """
        Контекстный менеджер для работы с соединением.
        
        Args:
            reuse_connection: Флаг повторного использования соединения
            
        Yields:
            Tuple[pymysql.Connection, pymysql.cursors.Cursor]: Соединение и курсор
        """
        conn = None
        cursor = None
        connection_created_time = None
        
        try:
            # Получаем соединение из пула
            conn, connection_created_time = self.pool.get_connection()
            cursor = conn.cursor()
            yield conn, cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка при работе с базой данных: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn and connection_created_time:
                if reuse_connection:
                    # Возвращаем соединение в пул для повторного использования
                    self.pool.return_connection(conn, connection_created_time)
                else:
                    # Закрываем и утилизируем соединение
                    self.pool.return_connection(conn, connection_created_time)
    
    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для получения соединения с базой данных.
        Используется для прямого взаимодействия с соединением.
        
        Yields:
            pymysql.Connection: Соединение с базой данных
        """
        conn = None
        connection_created_time = None
        
        try:
            # Получаем соединение из пула
            conn, connection_created_time = self.pool.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка при работе с базой данных: {str(e)}")
            raise
        finally:
            if conn and connection_created_time:
                # Возвращаем соединение в пул
                self.pool.return_connection(conn, connection_created_time)
    
    def get_last_sync_state(self, entity_type: str) -> Dict:
        """
        Получение состояния последней синхронизации.
        
        Args:
            entity_type: Тип сущности (campaigns, ad_sets, ads, insights)
            
        Returns:
            Dict: Состояние синхронизации
        """
        query = """
            SELECT last_sync, status, error_message, updated_at
            FROM sync_state
            WHERE entity_type = %s
            ORDER BY updated_at DESC
            LIMIT 1
        """
        
        with self.connection(reuse_connection=True) as (conn, cursor):
            cursor.execute(query, (entity_type,))
            result = cursor.fetchone()
            
        return result if result else {
            'last_sync': None,
            'status': None,
            'error_message': None,
            'updated_at': None
        }
    
    def update_last_sync(self, entity_type: str, sync_time: datetime,
                        status: str = 'success', error_message: str = None) -> None:
        """
        Обновление состояния синхронизации.
        
        Args:
            entity_type: Тип сущности
            sync_time: Время синхронизации
            status: Статус (success/error)
            error_message: Сообщение об ошибке
        """
        query = """
            INSERT INTO sync_state (entity_type, last_sync, status, error_message, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            last_sync = VALUES(last_sync),
            status = VALUES(status),
            error_message = VALUES(error_message),
            updated_at = VALUES(updated_at)
        """
        
        with self.connection() as (conn, cursor):
            cursor.execute(query, (entity_type, sync_time, status, error_message))
    
    def upsert_campaigns(self, campaigns: List[Dict]) -> None:
        """
        Обновление или вставка данных о кампаниях.
        
        Args:
            campaigns: Список кампаний
        """
        query = """
            INSERT INTO campaigns (
                id, name, status, objective, daily_budget,
                lifetime_budget, start_time, stop_time
            ) VALUES (
                %(id)s, %(name)s, %(status)s, %(objective)s,
                %(daily_budget)s, %(lifetime_budget)s,
                %(start_time)s, %(stop_time)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                status = VALUES(status),
                objective = VALUES(objective),
                daily_budget = VALUES(daily_budget),
                lifetime_budget = VALUES(lifetime_budget),
                start_time = VALUES(start_time),
                stop_time = VALUES(stop_time)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, campaigns)
    
    def upsert_ad_sets(self, ad_sets: List[Dict]) -> None:
        """
        Обновление или вставка данных о группах объявлений.
        
        Args:
            ad_sets: Список групп объявлений
        """
        query = """
            INSERT INTO ad_sets (
                id, campaign_id, name, status, daily_budget,
                lifetime_budget, targeting
            ) VALUES (
                %(id)s, %(campaign_id)s, %(name)s, %(status)s,
                %(daily_budget)s, %(lifetime_budget)s, %(targeting)s
            ) ON DUPLICATE KEY UPDATE
                campaign_id = VALUES(campaign_id),
                name = VALUES(name),
                status = VALUES(status),
                daily_budget = VALUES(daily_budget),
                lifetime_budget = VALUES(lifetime_budget),
                targeting = VALUES(targeting)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, ad_sets)
    
    def upsert_ads(self, ads: List[Dict]) -> None:
        """
        Обновление или вставка данных об объявлениях.
        
        Args:
            ads: Список объявлений
        """
        query = """
            INSERT INTO ads (
                id, ad_set_id, name, status, creative
            ) VALUES (
                %(id)s, %(ad_set_id)s, %(name)s,
                %(status)s, %(creative)s
            ) ON DUPLICATE KEY UPDATE
                ad_set_id = VALUES(ad_set_id),
                name = VALUES(name),
                status = VALUES(status),
                creative = VALUES(creative)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, ads)
    
    def upsert_insights(self, insights: List[Dict]) -> None:
        """
        Обновление или вставка статистики.
        
        Args:
            insights: Список записей статистики
        """
        query = """
            INSERT INTO ad_insights (
                ad_id, date_start, impressions, clicks, spend,
                ctr, cpc, conversations, cost_per_conversation
            ) VALUES (
                %(ad_id)s, %(date_start)s, %(impressions)s,
                %(clicks)s, %(spend)s, %(ctr)s, %(cpc)s,
                %(conversations)s, %(cost_per_conversation)s
            ) ON DUPLICATE KEY UPDATE
                impressions = VALUES(impressions),
                clicks = VALUES(clicks),
                spend = VALUES(spend),
                ctr = VALUES(ctr),
                cpc = VALUES(cpc),
                conversations = VALUES(conversations),
                cost_per_conversation = VALUES(cost_per_conversation)
        """
        
        with self.connection() as (conn, cursor):
            cursor.executemany(query, insights)
    
    def standardize_collation(self) -> None:
        """Стандартизация collation для всех таблиц."""
        tables = [
            'campaigns', 'ad_sets', 'ads', 'ad_insights',
            'sync_state', 'reports'
        ]
        
        with self.connection() as (conn, cursor):
            for table in tables:
                cursor.execute(f"""
                    ALTER TABLE {table}
                    CONVERT TO CHARACTER SET utf8mb4
                    COLLATE utf8mb4_unicode_ci
                """)
                logger.info(f"Стандартизирована collation для таблицы {table}")
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """
        Получает метрики пула соединений.
        
        Returns:
            Dict[str, Any]: Метрики пула соединений
        """
        return self.pool.get_metrics()
    
    def close_pool(self) -> None:
        """Закрывает все соединения в пуле."""
        self.pool.close_all()
        logger.info("Пул соединений закрыт")
    
    def execute_query(self, query: str, params: Optional[Union[Dict, Tuple]] = None) -> List[Dict]:
        """
        Выполняет SQL-запрос и возвращает результаты.
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
            
        Returns:
            List[Dict]: Результаты запроса
        """
        with self.connection(reuse_connection=True) as (conn, cursor):
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[Union[Dict, Tuple]] = None) -> int:
        """
        Выполняет SQL-запрос на обновление и возвращает количество затронутых строк.
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
            
        Returns:
            int: Количество затронутых строк
        """
        with self.connection() as (conn, cursor):
            affected_rows = cursor.execute(query, params)
            return affected_rows
    
    def save_checkpoint(self, checkpoint_data: Dict) -> None:
        """
        Сохраняет контрольную точку в базу данных.
        
        Args:
            checkpoint_data: Данные контрольной точки
        """
        query = """
            INSERT INTO collection_checkpoints (
                collection_type, last_processed_id, processed_items,
                total_items, status, metadata, timestamp
            ) VALUES (
                %(collection_type)s, %(last_processed_id)s, %(processed_items)s,
                %(total_items)s, %(status)s, %(metadata)s, %(timestamp)s
            )
        """
        
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, checkpoint_data)
                conn.commit()
                logger.debug(
                    f"Сохранена контрольная точка для {checkpoint_data['collection_type']}"
                )
        except Exception as e:
            logger.error(f"Ошибка при сохранении контрольной точки: {str(e)}")
            raise
    
    def get_last_checkpoint(self, collection_type: str) -> Optional[Dict]:
        """
        Получает последнюю контрольную точку для указанного типа сбора.
        
        Args:
            collection_type: Тип собираемых данных
            
        Returns:
            Dict: Данные последней контрольной точки или None
        """
        query = """
            SELECT *
            FROM collection_checkpoints
            WHERE collection_type = %(collection_type)s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, {'collection_type': collection_type})
                result = cursor.fetchone()
                return result if result else None
        except Exception as e:
            logger.error(
                f"Ошибка при получении последней контрольной точки: {str(e)}"
            )
            return None
    
    def update_checkpoint_status(self, checkpoint_id: int, 
                               status: str, error_message: str = None) -> None:
        """
        Обновляет статус контрольной точки.
        
        Args:
            checkpoint_id: ID контрольной точки
            status: Новый статус
            error_message: Сообщение об ошибке (опционально)
        """
        query = """
            UPDATE collection_checkpoints
            SET status = %(status)s,
                metadata = JSON_SET(
                    COALESCE(metadata, '{}'),
                    '$.error_message',
                    %(error_message)s
                )
            WHERE id = %(checkpoint_id)s
        """
        
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, {
                    'checkpoint_id': checkpoint_id,
                    'status': status,
                    'error_message': error_message
                })
                conn.commit()
                logger.debug(f"Обновлен статус контрольной точки {checkpoint_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса контрольной точки: {str(e)}")
            raise
    
    def cleanup_old_checkpoints(self, days_to_keep: int = 7) -> None:
        """
        Удаляет старые контрольные точки.
        
        Args:
            days_to_keep: Количество дней, за которые сохранять точки
        """
        query = """
            DELETE FROM collection_checkpoints
            WHERE timestamp < DATE_SUB(NOW(), INTERVAL %(days)s DAY)
        """
        
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, {'days': days_to_keep})
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Удалено {deleted_count} старых контрольных точек")
        except Exception as e:
            logger.error(f"Ошибка при очистке старых контрольных точек: {str(e)}")
            raise