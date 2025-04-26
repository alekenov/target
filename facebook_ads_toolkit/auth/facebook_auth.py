#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для аутентификации в Facebook Marketing API.
"""

import os
import logging
from typing import Tuple, Optional
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.user import User
from facebook_business.exceptions import FacebookRequestError
from dotenv import load_dotenv

from facebook_ads_toolkit.utils.api_error_handler import ApiErrorHandler, with_error_handling

# Настройка логирования
logger = logging.getLogger(__name__)

class FacebookAuth:
    """Класс для аутентификации в Facebook Marketing API."""
    
    _instance = None
    _is_initialized = False
    
    def __new__(cls):
        """Реализация паттерна Singleton для предотвращения множественной инициализации."""
        if cls._instance is None:
            cls._instance = super(FacebookAuth, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация с загрузкой переменных окружения."""
        if not self._is_initialized:
            load_dotenv()
            
            # Загрузка основных параметров
            self.app_id = os.getenv('FACEBOOK_APP_ID')
            self.app_secret = os.getenv('FACEBOOK_APP_SECRET')
            self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
            self.account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
            
            # Проверка наличия всех необходимых параметров
            self._validate_env_vars()
            
            # Инициализация API и аккаунта
            self.api = None
            self.account = None
            
            # Создаем обработчик ошибок
            self.error_handler = ApiErrorHandler(
                max_retries=3,
                initial_delay=1,
                max_delay=10
            )
            
            self._is_initialized = True
    
    def _validate_env_vars(self):
        """Проверка наличия всех необходимых переменных окружения."""
        missing_vars = []
        
        if not self.app_id:
            missing_vars.append('FACEBOOK_APP_ID')
        if not self.app_secret:
            missing_vars.append('FACEBOOK_APP_SECRET')
        if not self.access_token:
            missing_vars.append('FACEBOOK_ACCESS_TOKEN')
        if not self.account_id:
            missing_vars.append('FACEBOOK_AD_ACCOUNT_ID')
        
        if missing_vars:
            error_msg = f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    @with_error_handling()
    def _initialize_api(self):
        """
        Инициализация Facebook API.
        
        Returns:
            FacebookAdsApi: Инициализированный API
            
        Raises:
            FacebookRequestError: Если произошла ошибка при инициализации
        """
        api = FacebookAdsApi.init(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=self.access_token
        )
        
        # Проверка валидности токена через запрос информации о пользователе
        me = User(fbid='me')
        me.api_get(fields=['id', 'name'])
        
        return api
    
    @with_error_handling()
    def _get_account_info(self):
        """
        Получение информации о рекламном аккаунте.
        
        Returns:
            Dict: Информация об аккаунте
            
        Raises:
            FacebookRequestError: Если произошла ошибка при получении информации
            Exception: Если аккаунт не активен
        """
        account = AdAccount(self.account_id)
        account_info = account.api_get(fields=['name', 'account_status', 'disable_reason'])
        
        # Проверка статуса аккаунта
        account_status = account_info.get('account_status')
        if account_status != 1:  # 1 = ACTIVE
            disable_reason = account_info.get('disable_reason')
            error_msg = f"Аккаунт {self.account_id} не активен. Статус: {account_status}, Причина: {disable_reason}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        return account, account_info
    
    def initialize(self) -> Tuple[Optional[AdAccount], Optional[FacebookAdsApi]]:
        """
        Инициализация Facebook API и получение объекта рекламного аккаунта.
        
        Returns:
            Tuple[Optional[AdAccount], Optional[FacebookAdsApi]]: 
            Кортеж из объекта рекламного аккаунта и API
        
        Raises:
            Exception: Если не удалось инициализировать API или получить доступ к аккаунту
        """
        try:
            # Инициализация API с обработкой ошибок
            self.api = self._initialize_api()
            
            # Получение и проверка доступа к рекламному аккаунту
            self.account, account_info = self._get_account_info()
            
            logger.info(f"Успешно подключились к рекламному аккаунту {self.account_id} ({account_info.get('name')})")
            return self.account, self.api
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Facebook API: {str(e)}")
            self.api = None
            self.account = None
            raise
    
    def validate_access(self) -> bool:
        """
        Проверка валидности доступа к API.
        
        Returns:
            bool: True если доступ валиден, False в противном случае
        """
        try:
            if not self.api or not self.account:
                self.initialize()
            return bool(self.api and self.account)
        except Exception as e:
            logger.error(f"Ошибка при проверке доступа: {str(e)}")
            return False
    
    def get_account(self) -> Optional[AdAccount]:
        """
        Получение объекта рекламного аккаунта.
        
        Returns:
            Optional[AdAccount]: Объект рекламного аккаунта или None в случае ошибки
        """
        if not self.account:
            try:
                self.initialize()
            except Exception:
                return None
        return self.account
    
    def get_api(self) -> Optional[FacebookAdsApi]:
        """
        Получение объекта API.
        
        Returns:
            Optional[FacebookAdsApi]: Объект API или None в случае ошибки
        """
        if not self.api:
            try:
                self.initialize()
            except Exception:
                return None
        return self.api 