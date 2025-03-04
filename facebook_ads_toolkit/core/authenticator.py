#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для аутентификации в Facebook Marketing API.
"""

import os
import logging
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

logger = logging.getLogger(__name__)

class FacebookAuth:
    """Класс для авторизации в Facebook Marketing API."""
    
    API_VERSION = 'v22.0'
    
    def __init__(self):
        """Инициализация класса авторизации."""
        self.app_id = os.getenv('FB_APP_ID')
        self.app_secret = os.getenv('FB_APP_SECRET', '')
        self.access_token = os.getenv('FB_ACCESS_TOKEN')
        self.account_id = os.getenv('FB_ACCOUNT_ID')
        
        if not self.app_id or not self.access_token or not self.account_id:
            logger.error("Не указаны FB_APP_ID, FB_ACCESS_TOKEN или FB_ACCOUNT_ID")
            raise ValueError("Не указаны обязательные переменные окружения")
    
    def initialize(self):
        """
        Инициализирует соединение с Facebook API.
        
        Returns:
            tuple: (AdAccount, FacebookAdsApi) - объект аккаунта и API
        """
        try:
            # Инициализация API с указанием версии
            api = FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token,
                api_version=self.API_VERSION
            )
            
            # Получение объекта аккаунта
            # Удаляем префикс "act_" если он уже есть, затем добавляем его
            clean_account_id = self.account_id.replace('act_', '')
            account_id_with_prefix = f'act_{clean_account_id}'
            account = AdAccount(account_id_with_prefix)
            
            logger.info(f"Успешно инициализировано соединение с Facebook API v{self.API_VERSION} для аккаунта {account_id_with_prefix}")
            return account, api
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Facebook API: {str(e)}")
            return None, None
