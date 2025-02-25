#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Конфигурационный файл для модуля интеграции с Telegram.
Содержит настройки и загрузку шаблонов сообщений.
"""

import os
import yaml
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки логирования
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO
LOG_DIR = Path(__file__).parent.parent.parent / 'logs'
LOG_FILE = LOG_DIR / 'telegram_integration.log'

# Создаем директорию для логов, если она не существует
os.makedirs(LOG_DIR, exist_ok=True)

# Настройки Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_LOG_CHANNEL_ID = os.getenv('TELEGRAM_LOG_CHANNEL_ID')

# Проверка наличия необходимых переменных окружения
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

if not TELEGRAM_LOG_CHANNEL_ID:
    logging.warning("TELEGRAM_LOG_CHANNEL_ID не найден в переменных окружения. Некоторые функции могут быть недоступны.")

# Пути к шаблонам
TEMPLATES_DIR = Path(__file__).parent / 'templates'
MESSAGE_TEMPLATES_FILE = TEMPLATES_DIR / 'message_templates.yaml'

# Загрузка шаблонов сообщений
def load_message_templates():
    """Загружает шаблоны сообщений из YAML-файла."""
    try:
        with open(MESSAGE_TEMPLATES_FILE, 'r', encoding='utf-8') as file:
            templates = yaml.safe_load(file)
        logging.info(f"Шаблоны сообщений успешно загружены из {MESSAGE_TEMPLATES_FILE}")
        return templates
    except FileNotFoundError:
        logging.error(f"Файл шаблонов сообщений не найден: {MESSAGE_TEMPLATES_FILE}")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"Ошибка при парсинге YAML-файла шаблонов: {e}")
        return {}

# Загружаем шаблоны сообщений
MESSAGE_TEMPLATES = load_message_templates()

# Настройки для отчетов
REPORT_SETTINGS = {
    'daily_report': {
        'send_time': '09:00',  # Время отправки ежедневного отчета (UTC)
        'include_recommendations': True,  # Включать ли рекомендации в отчет
        'max_campaigns_to_show': 5,  # Максимальное количество кампаний для отображения
    },
    'weekly_report': {
        'send_day': 'Monday',  # День недели для отправки еженедельного отчета
        'send_time': '10:00',  # Время отправки еженедельного отчета (UTC)
        'include_performance_change': True,  # Включать ли изменение производительности
    },
    'alerts': {
        'min_budget_spend_percentage': 80,  # Минимальный процент расхода бюджета для оповещения
        'max_cpc_increase_percentage': 20,  # Максимальный процент увеличения CPC для оповещения
        'min_ctr_decrease_percentage': 15,  # Минимальный процент снижения CTR для оповещения
    }
}

# Настройки для команд бота
BOT_COMMANDS = [
    ('start', 'Начать работу с ботом'),
    ('help', 'Показать справку по командам'),
    ('daily', 'Получить ежедневный отчет'),
    ('weekly', 'Получить еженедельный отчет'),
    ('list', 'Показать список активных кампаний'),
    ('campaign', 'Получить информацию о конкретной кампании'),
    ('alerts', 'Показать текущие предупреждения'),
]

# Настройки для клавиатуры бота
KEYBOARD_BUTTONS = [
    ['📊 Ежедневный отчет', '📈 Еженедельный отчет'],
    ['📋 Список кампаний', '⚠️ Предупреждения'],
    ['❓ Помощь']
] 