#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Основной модуль для работы с Telegram-ботом.
Отвечает за инициализацию и запуск бота.
"""

import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from telegram import Update, Bot, ReplyKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from facebook_ads_toolkit.telegram_integration.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_LOG_CHANNEL_ID,
    BOT_COMMANDS,
    KEYBOARD_BUTTONS,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_DIR,
    LOG_FILE
)
from facebook_ads_toolkit.telegram_integration.handlers import (
    start_command,
    help_command,
    list_command,
    daily_command,
    weekly_command,
    campaign_command,
    alerts_command,
    button_handler,
    unknown_command
)

# Настройка логирования
def setup_logging():
    """Настраивает логирование для бота."""
    # Создаем директорию для логов, если она не существует
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Настраиваем логирование
    logger = logging.getLogger("facebook_ads_toolkit")
    logger.setLevel(LOG_LEVEL if isinstance(LOG_LEVEL, int) else getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Создаем обработчик для файла
    file_handler = logging.FileHandler(log_dir / LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Создаем обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

async def send_startup_notification(bot: Bot):
    """Отправляет уведомление о запуске бота в канал логирования."""
    if TELEGRAM_LOG_CHANNEL_ID:
        try:
            await bot.send_message(
                chat_id=TELEGRAM_LOG_CHANNEL_ID,
                text=f"🚀 Бот Facebook Ads Toolkit запущен и готов к работе.\n\n"
                     f"Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            logging.info(f"Уведомление о запуске отправлено в канал {TELEGRAM_LOG_CHANNEL_ID}")
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление о запуске: {e}")

async def setup_commands(application: Application):
    """Настраивает команды в меню бота."""
    commands = [BotCommand(command=cmd[0], description=cmd[1]) for cmd in BOT_COMMANDS]
    await application.bot.set_my_commands(commands)
    logging.info("Команды бота настроены")

def create_keyboard():
    """Создает клавиатуру для бота."""
    return ReplyKeyboardMarkup(
        KEYBOARD_BUTTONS,
        resize_keyboard=True
    )

async def setup_bot():
    """Настраивает и запускает бота."""
    logger = setup_logging()
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден. Бот не может быть запущен.")
        return None
    
    # Создаем экземпляр приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Инициализируем приложение
    await application.initialize()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("weekly", weekly_command))
    application.add_handler(CommandHandler("campaign", campaign_command))
    application.add_handler(CommandHandler("alerts", alerts_command))
    
    # Обработчик для кнопок
    application.add_handler(MessageHandler(
        filters.Regex('^(📊 Ежедневный отчет|📈 Еженедельный отчет|📋 Список кампаний|⚠️ Предупреждения|❓ Помощь)$'),
        button_handler
    ))
    
    # Обработчик для неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Настраиваем команды в меню бота
    await setup_commands(application)
    
    # Отправляем уведомление о запуске
    await send_startup_notification(application.bot)
    
    logger.info("Бот настроен и готов к запуску")
    return application

async def run_bot():
    """Запускает бота."""
    application = await setup_bot()
    if application:
        # Запускаем бота
        await application.updater.initialize()
        await application.start()
        await application.updater.start_polling()
        logging.info("Бот запущен и ожидает сообщений")
        
        # Держим бота запущенным до прерывания
        try:
            # Ждем сигнала остановки
            stop_signal = asyncio.Future()
            await stop_signal
        except asyncio.CancelledError:
            pass
        finally:
            await application.stop()
            logging.info("Бот остановлен")

def main():
    """Основная функция для запуска бота."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Произошла ошибка при запуске бота: {e}", exc_info=True)

if __name__ == "__main__":
    main() 