#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Пример использования интеграции с Telegram для Facebook Ads Toolkit.

Этот скрипт демонстрирует, как запустить Telegram-бота для мониторинга
и управления рекламными кампаниями Facebook.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv

# Импортируем необходимые компоненты из нашего пакета
from facebook_ads_toolkit.telegram_integration import run_bot
from facebook_ads_toolkit.telegram_integration.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_LOG_CHANNEL_ID,
    LOG_LEVEL,
    LOG_FORMAT
)

# Настройка логирования
logging.basicConfig(
    level=LOG_LEVEL if isinstance(LOG_LEVEL, int) else getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

def check_environment():
    """
    Проверка наличия необходимых переменных окружения.
    
    Returns:
        bool: True, если все необходимые переменные окружения установлены, иначе False.
    """
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    required_vars = [
        'FACEBOOK_APP_ID',
        'FACEBOOK_APP_SECRET',
        'FACEBOOK_ACCESS_TOKEN',
        'FACEBOOK_AD_ACCOUNT_ID',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_LOG_CHANNEL_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}")
        logger.error("Пожалуйста, создайте файл .env и добавьте в него необходимые переменные.")
        return False
    
    return True

def main():
    """
    Основная функция для запуска Telegram-бота.
    """
    logger.info("Запуск примера использования Telegram-интеграции")
    
    # Проверяем наличие необходимых переменных окружения
    if not check_environment():
        return
    
    # Выводим информацию о настройках
    logger.info(f"Токен бота: {'Установлен' if TELEGRAM_BOT_TOKEN else 'Не установлен'}")
    logger.info(f"ID канала для логов: {TELEGRAM_LOG_CHANNEL_ID}")
    
    try:
        # Запускаем бота
        logger.info("Запуск Telegram-бота...")
        run_bot()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main() 