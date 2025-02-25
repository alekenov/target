#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль интеграции Facebook Ads Toolkit с Telegram.

Этот модуль предоставляет функциональность для отправки отчетов
и уведомлений о рекламных кампаниях Facebook через Telegram.
"""

from facebook_ads_toolkit.telegram_integration.report_sender import ReportSender
from facebook_ads_toolkit.telegram_integration.bot import main as run_bot
from facebook_ads_toolkit.telegram_integration.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_LOG_CHANNEL_ID,
    MESSAGE_TEMPLATES,
    REPORT_SETTINGS
)

__all__ = [
    'ReportSender',
    'run_bot',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_LOG_CHANNEL_ID',
    'MESSAGE_TEMPLATES',
    'REPORT_SETTINGS'
] 