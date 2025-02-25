#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для отправки ежедневного отчета в Telegram канал.

Этот скрипт отправляет ежедневный отчет о производительности рекламных кампаний
Facebook в указанный Telegram канал.
"""

import os
import logging
import asyncio
import traceback
from datetime import datetime
from dotenv import load_dotenv

from telegram import Bot

from facebook_ads_toolkit.telegram_integration.report_sender import ReportSender
from facebook_ads_toolkit.telegram_integration.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_LOG_CHANNEL_ID,
    LOG_LEVEL,
    LOG_FORMAT
)
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth

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
    
    # Выводим значения переменных для отладки (без токенов)
    logger.info(f"TELEGRAM_LOG_CHANNEL_ID: {TELEGRAM_LOG_CHANNEL_ID}")
    logger.info(f"FACEBOOK_AD_ACCOUNT_ID: {os.getenv('FACEBOOK_AD_ACCOUNT_ID')}")
    
    return True

async def send_direct_message_to_channel(message):
    """
    Отправка сообщения напрямую в Telegram канал.
    
    Args:
        message (str): Текст сообщения для отправки.
    """
    try:
        logger.info(f"Попытка отправки сообщения в канал {TELEGRAM_LOG_CHANNEL_ID}")
        logger.info(f"Используется токен бота: {'Установлен' if TELEGRAM_BOT_TOKEN else 'Не установлен'}")
        
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("Бот инициализирован")
        
        # Проверяем, что бот работает
        me = await bot.get_me()
        logger.info(f"Бот авторизован как: {me.username}")
        
        # Отправляем сообщение
        await bot.send_message(
            chat_id=TELEGRAM_LOG_CHANNEL_ID,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"Сообщение успешно отправлено в канал {TELEGRAM_LOG_CHANNEL_ID}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Стек вызовов: {traceback.format_exc()}")
        return False

async def send_daily_report():
    """
    Отправка ежедневного отчета в Telegram канал.
    """
    logger.info("Инициализация отправки ежедневного отчета")
    
    # Инициализируем Facebook API
    try:
        auth = FacebookAuth()
        auth.initialize()
        logger.info(f"Facebook API инициализирован. Аккаунт: {auth.get_ad_account_id()}")
    except Exception as e:
        logger.error(f"Ошибка при инициализации Facebook API: {e}")
        # Отправляем сообщение об ошибке
        await send_direct_message_to_channel(
            "❌ *Ошибка при формировании ежедневного отчета*\n\n"
            "Не удалось инициализировать Facebook API. Пожалуйста, проверьте настройки доступа."
        )
        return
    
    # Создаем отправителя отчетов
    report_sender = ReportSender()
    
    # Отправляем ежедневный отчет
    try:
        logger.info(f"Отправка ежедневного отчета в канал {TELEGRAM_LOG_CHANNEL_ID}")
        success = await report_sender.send_daily_report(TELEGRAM_LOG_CHANNEL_ID)
        
        if success:
            logger.info("Ежедневный отчет успешно отправлен")
        else:
            logger.error("Не удалось отправить ежедневный отчет")
            
            # Отправляем базовый отчет, если стандартный отчет не удалось отправить
            current_date = datetime.now().strftime('%d.%m.%Y')
            message = (
                f"📊 *Ежедневный отчет по рекламным кампаниям Facebook*\n"
                f"📅 Дата: {current_date}\n\n"
                f"⚠️ *Внимание:* Не удалось получить данные от Facebook API.\n\n"
                f"Возможные причины:\n"
                f"• Недействительный или просроченный токен доступа\n"
                f"• Отсутствие доступа к рекламному аккаунту\n"
                f"• Проблемы с подключением к Facebook API\n\n"
                f"Пожалуйста, проверьте настройки доступа и попробуйте снова."
            )
            
            logger.info("Отправка базового отчета")
            await send_direct_message_to_channel(message)
    except Exception as e:
        logger.error(f"Ошибка при отправке ежедневного отчета: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Стек вызовов: {traceback.format_exc()}")
        
        await send_direct_message_to_channel(
            "❌ *Ошибка при отправке ежедневного отчета*\n\n"
            f"Произошла ошибка: {str(e)}\n\n"
            "Пожалуйста, проверьте логи для получения дополнительной информации."
        )

async def main():
    """
    Основная функция для запуска отправки отчета.
    """
    logger.info("Запуск скрипта отправки ежедневного отчета")
    
    # Проверяем наличие необходимых переменных окружения
    if not check_environment():
        return
    
    # Отправляем ежедневный отчет
    await send_daily_report()

if __name__ == "__main__":
    asyncio.run(main()) 