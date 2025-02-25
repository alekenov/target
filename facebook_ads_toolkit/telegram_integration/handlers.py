#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Обработчики команд для Telegram-бота.
Содержит функции для обработки команд и сообщений от пользователей.
"""

import logging
from typing import Dict, Any, List, Optional
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from facebook_ads_toolkit.telegram_integration.config import (
    MESSAGE_TEMPLATES,
    KEYBOARD_BUTTONS
)
from facebook_ads_toolkit.telegram_integration.report_sender import (
    ReportSender
)

# Инициализация логгера
logger = logging.getLogger(__name__)

# Инициализация отправителя отчетов
report_sender = ReportSender()

def create_keyboard():
    """Создает клавиатуру для бота."""
    return ReplyKeyboardMarkup(
        KEYBOARD_BUTTONS,
        resize_keyboard=True
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")
    
    # Получаем шаблон приветственного сообщения
    welcome_message = MESSAGE_TEMPLATES.get('welcome_message', 
        f"Привет, {user.first_name}! 👋\n\n"
        "Я бот для работы с Facebook Ads Toolkit. "
        "Я помогу тебе получать отчеты о рекламных кампаниях и управлять ими.\n\n"
        "Используй команду /help, чтобы узнать, что я умею.")
    
    # Если в шаблоне есть плейсхолдер для имени, подставляем его
    if "{user_name}" in welcome_message:
        welcome_message = welcome_message.format(user_name=user.first_name)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=create_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил помощь")
    
    # Получаем шаблон сообщения с помощью
    help_text = MESSAGE_TEMPLATES.get('help_message',
        "Вот что я умею:\n\n"
        "/daily - Получить ежедневный отчет\n"
        "/weekly - Получить еженедельный отчет\n"
        "/list - Показать список активных кампаний\n"
        "/campaign <id> - Получить информацию о конкретной кампании\n"
        "/alerts - Показать текущие предупреждения\n"
        "/help - Показать эту справку")
    
    await update.message.reply_text(
        help_text,
        reply_markup=create_keyboard()
    )

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /list для получения списка активных кампаний."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил список кампаний")
    
    # Отправляем сообщение о том, что запрос обрабатывается
    await update.message.reply_text(
        "🔄 Получаю список активных кампаний...",
        reply_markup=create_keyboard()
    )
    
    try:
        # Получаем и отправляем список кампаний
        await report_sender.send_campaign_list(update.effective_chat.id)
    except Exception as e:
        logger.error(f"Ошибка при получении списка кампаний: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении списка кампаний. Пожалуйста, попробуйте позже.",
            reply_markup=create_keyboard()
        )

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /daily для получения ежедневного отчета."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил ежедневный отчет")
    
    # Отправляем сообщение о том, что запрос обрабатывается
    await update.message.reply_text(
        "🔄 Формирую ежедневный отчет...",
        reply_markup=create_keyboard()
    )
    
    try:
        # Получаем и отправляем ежедневный отчет
        await report_sender.send_daily_report(update.effective_chat.id)
    except Exception as e:
        logger.error(f"Ошибка при формировании ежедневного отчета: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при формировании отчета. Пожалуйста, попробуйте позже.",
            reply_markup=create_keyboard()
        )

async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /weekly для получения еженедельного отчета."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил еженедельный отчет")
    
    # Отправляем сообщение о том, что запрос обрабатывается
    await update.message.reply_text(
        "🔄 Формирую еженедельный отчет...",
        reply_markup=create_keyboard()
    )
    
    try:
        # Получаем и отправляем еженедельный отчет
        await report_sender.send_weekly_report(update.effective_chat.id)
    except Exception as e:
        logger.error(f"Ошибка при формировании еженедельного отчета: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при формировании отчета. Пожалуйста, попробуйте позже.",
            reply_markup=create_keyboard()
        )

async def campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /campaign для получения информации о конкретной кампании."""
    user = update.effective_user
    
    # Проверяем, указан ли ID кампании
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Пожалуйста, укажите ID кампании. Например: /campaign 123456789",
            reply_markup=create_keyboard()
        )
        return
    
    campaign_id = context.args[0]
    logger.info(f"Пользователь {user.id} запросил информацию о кампании {campaign_id}")
    
    # Отправляем сообщение о том, что запрос обрабатывается
    await update.message.reply_text(
        f"🔄 Получаю информацию о кампании {campaign_id}...",
        reply_markup=create_keyboard()
    )
    
    try:
        # Получаем и отправляем информацию о кампании
        await report_sender.send_campaign_info(update.effective_chat.id, campaign_id)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о кампании {campaign_id}: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при получении информации о кампании {campaign_id}. Пожалуйста, проверьте ID и попробуйте снова.",
            reply_markup=create_keyboard()
        )

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /alerts для получения текущих предупреждений."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил текущие предупреждения")
    
    # Отправляем сообщение о том, что запрос обрабатывается
    await update.message.reply_text(
        "🔄 Проверяю наличие предупреждений...",
        reply_markup=create_keyboard()
    )
    
    try:
        # Получаем и отправляем текущие предупреждения
        await report_sender.send_alerts(update.effective_chat.id)
    except Exception as e:
        logger.error(f"Ошибка при получении предупреждений: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при проверке предупреждений. Пожалуйста, попробуйте позже.",
            reply_markup=create_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки клавиатуры."""
    query = update.message.text
    user = update.effective_user
    logger.info(f"Пользователь {user.id} нажал кнопку: {query}")
    
    if query == "📊 Ежедневный отчет":
        await daily_command(update, context)
    elif query == "📈 Еженедельный отчет":
        await weekly_command(update, context)
    elif query == "📋 Список кампаний":
        await list_command(update, context)
    elif query == "⚠️ Предупреждения":
        await alerts_command(update, context)
    elif query == "❓ Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "Неизвестная команда. Используйте /help для получения списка доступных команд.",
            reply_markup=create_keyboard()
        )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик неизвестных команд."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} отправил неизвестную команду: {update.message.text}")
    
    await update.message.reply_text(
        "Неизвестная команда. Используйте /help для получения списка доступных команд.",
        reply_markup=create_keyboard()
    ) 