#!/usr/bin/env python
"""
Скрипт для запуска Telegram-бота Facebook Ads Toolkit.

Этот скрипт запускает Telegram-бота, который позволяет получать отчеты
о рекламных кампаниях Facebook и управлять ими через Telegram.
"""

import asyncio
import logging
import sys
import os

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from facebook_ads_toolkit.telegram_integration.bot import main
from facebook_ads_toolkit.utils.logging_utils import setup_logger

# Настройка логирования
logger = setup_logger('telegram_bot_runner', 'logs/telegram_bot_runner.log')

if __name__ == "__main__":
    try:
        logger.info("Запуск Telegram-бота Facebook Ads Toolkit")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        print(f"Ошибка при запуске бота: {e}")
        sys.exit(1) 