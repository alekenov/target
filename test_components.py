#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для тестирования компонентов системы Facebook Ads.
Проверяет работу отчетов, форматирование и сбор данных.
"""

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from facebook_ads_toolkit.reports.daily_report import DailyReport
from facebook_ads_toolkit.reports.hourly_report import HourlyReport
from facebook_ads_toolkit.db.db_manager import DatabaseManager
from facebook_ads_toolkit.core.authenticator import FacebookAuth

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_reports():
    """Тестирование генерации отчетов."""
    try:
        # Тест часового отчета
        logger.info("Тестирование часового отчета...")
        hourly_report = HourlyReport()
        hourly_result = hourly_report.generate()
        logger.info("Часовой отчет успешно сгенерирован")
        logger.info(f"Длина отчета: {len(hourly_result)} символов")

        # Тест дневного отчета
        logger.info("Тестирование дневного отчета...")
        daily_report = DailyReport()
        daily_result = daily_report.generate()
        logger.info("Дневной отчет успешно сгенерирован")
        logger.info(f"Длина отчета: {len(daily_result)} символов")

        return True
    except Exception as e:
        logger.error(f"Ошибка при тестировании отчетов: {str(e)}")
        return False

def verify_telegram_formatting(report_text: str) -> bool:
    """
    Проверка форматирования Telegram.
    
    Args:
        report_text: Текст отчета для проверки
    """
    required_elements = ['▲', '▼', '→', '*', '_']
    
    for element in required_elements:
        if element not in report_text:
            logger.warning(f"Отсутствует элемент форматирования: {element}")
            return False
    
    logger.info("Форматирование Telegram корректно")
    return True

def test_incremental_collection():
    """Тестирование инкрементального сбора данных."""
    try:
        db = DatabaseManager()
        
        # Получаем текущее состояние синхронизации
        sync_state = db.get_last_sync_state('campaigns')
        logger.info(f"Текущее состояние синхронизации: {sync_state}")
        
        # Запускаем инкрементальный сбор
        os.system('python data_collector.py')
        
        # Проверяем обновление состояния
        new_sync_state = db.get_last_sync_state('campaigns')
        logger.info(f"Новое состояние синхронизации: {new_sync_state}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при тестировании инкрементального сбора: {str(e)}")
        return False

def test_full_cycle():
    """Тестирование полного цикла работы системы."""
    try:
        # 1. Сбор данных
        logger.info("Запуск сбора данных...")
        os.system('python data_collector.py')
        
        # 2. Генерация отчетов
        logger.info("Генерация отчетов...")
        hourly_report = HourlyReport()
        daily_report = DailyReport()
        
        hourly_result = hourly_report.generate()
        daily_result = daily_report.generate()
        
        # 3. Проверка форматирования
        if not verify_telegram_formatting(hourly_result):
            logger.error("Ошибка форматирования часового отчета")
            return False
            
        if not verify_telegram_formatting(daily_result):
            logger.error("Ошибка форматирования дневного отчета")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при тестировании полного цикла: {str(e)}")
        return False

def test_large_data_handling():
    """Тестирование обработки большого объема данных."""
    try:
        # Сбор данных за 30 дней
        logger.info("Запуск сбора данных за 30 дней...")
        os.system('python data_collector.py --force-full')
        
        # Проверка производительности отчетов
        start_time = datetime.now()
        
        daily_report = DailyReport()
        daily_result = daily_report.generate()
        
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Время выполнения: {execution_time} секунд")
        
        if execution_time > 30:  # Если выполнение занимает больше 30 секунд
            logger.warning("Время выполнения превышает ожидаемое")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Ошибка при тестировании обработки большого объема данных: {str(e)}")
        return False

def main():
    """Основная функция для запуска всех тестов."""
    load_dotenv()
    
    tests = {
        "Тест отчетов": test_reports,
        "Тест инкрементального сбора": test_incremental_collection,
        "Тест полного цикла": test_full_cycle,
        "Тест обработки больших данных": test_large_data_handling
    }
    
    results = {}
    
    for test_name, test_func in tests.items():
        logger.info(f"\nЗапуск теста: {test_name}")
        try:
            result = test_func()
            results[test_name] = "✅ Успешно" if result else "❌ Ошибка"
        except Exception as e:
            results[test_name] = f"❌ Исключение: {str(e)}"
    
    # Вывод результатов
    logger.info("\n=== Результаты тестирования ===")
    for test_name, result in results.items():
        logger.info(f"{test_name}: {result}")

if __name__ == "__main__":
    main()
