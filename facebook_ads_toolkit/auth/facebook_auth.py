"""
Модуль для авторизации в Facebook Ads API.
"""

import os
import logging
from typing import Tuple, Optional
from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

logger = logging.getLogger(__name__)

class FacebookAuth:
    """Класс для авторизации в Facebook Ads API."""
    
    def __init__(self, env_path: Optional[str] = None):
        """
        Инициализация авторизации Facebook API.
        
        Args:
            env_path: Путь к файлу .env (опционально)
        """
        self.api = None
        self.account = None
        
        # Загружаем переменные окружения
        if env_path:
            load_dotenv(env_path)
        else:
            # Сначала пробуем найти .env в текущей директории
            if os.path.exists('.env'):
                load_dotenv('.env')
            # Затем проверяем в директории конфигурации
            elif os.path.exists('facebook_ads_toolkit/config/.env'):
                load_dotenv('facebook_ads_toolkit/config/.env')
            else:
                logger.warning("Файл .env не найден")
        
        # Получаем переменные окружения, поддерживая оба формата (FACEBOOK_ и FB_)
        self.app_id = os.getenv('FACEBOOK_APP_ID') or os.getenv('FB_APP_ID')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET') or os.getenv('FB_APP_SECRET')
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN') or os.getenv('FB_ACCESS_TOKEN')
        self.account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID') or os.getenv('FB_ACCOUNT_ID')
        
        if not all([self.app_id, self.access_token, self.account_id]):
            logger.error("Не все параметры авторизации заданы в .env файле")
            logger.error(f"app_id: {self.app_id}, access_token: {'Задан' if self.access_token else 'Не задан'}, account_id: {self.account_id}")
    
    def initialize(self) -> Tuple[Optional[AdAccount], Optional[FacebookAdsApi]]:
        """
        Инициализация Facebook API и рекламного аккаунта.
        
        Returns:
            Tuple[Optional[AdAccount], Optional[FacebookAdsApi]]: Кортеж из рекламного аккаунта и API
        """
        try:
            # Проверяем наличие всех необходимых параметров
            if not all([self.app_id, self.access_token, self.account_id]):
                logger.error("Недостаточно параметров для инициализации API")
                return None, None
            
            # Инициализируем API
            self.api = FacebookAdsApi.init(
                app_id=self.app_id,
                access_token=self.access_token
            )
            
            # Устанавливаем API по умолчанию
            FacebookAdsApi.set_default_api(self.api)
            
            # Получаем рекламный аккаунт
            account_id = self.account_id
            if not account_id.startswith('act_'):
                account_id = f'act_{account_id}'
            
            self.account = AdAccount(account_id)
            
            logger.info(f"API и рекламный аккаунт {account_id} успешно инициализированы")
            return self.account, self.api
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Facebook API: {str(e)}")
            return None, None
    
    def get_account(self) -> Optional[AdAccount]:
        """
        Получение рекламного аккаунта.
        
        Returns:
            Optional[AdAccount]: Рекламный аккаунт или None в случае ошибки
        """
        if not self.account:
            logger.warning("Рекламный аккаунт не инициализирован. Вызовите метод initialize()")
        
        return self.account
    
    def get_api(self) -> Optional[FacebookAdsApi]:
        """
        Получение Facebook API.
        
        Returns:
            Optional[FacebookAdsApi]: Facebook API или None в случае ошибки
        """
        if not self.api:
            logger.warning("Facebook API не инициализирован. Вызовите метод initialize()")
        
        return self.api
        
    def get_ad_account_id(self) -> Optional[str]:
        """
        Получение ID рекламного аккаунта.
        
        Returns:
            Optional[str]: ID рекламного аккаунта или None
        """
        return self.account_id


# Функция для обратной совместимости
def init_facebook_api(env_path=None):
    """
    Инициализация Facebook API (для обратной совместимости).
    
    Args:
        env_path (str, optional): Путь к файлу .env. По умолчанию None.
        
    Returns:
        tuple: (account, api) если успешно, иначе (None, None)
    """
    auth = FacebookAuth(env_path)
    return auth.initialize()

def get_api():
    """
    Получает инициализированный объект API Facebook.
    
    Returns:
        FacebookAdsApi: Инициализированный объект API.
    """
    auth = FacebookAuth()
    auth.initialize()
    return auth.get_api()

def get_ad_account():
    """
    Получает объект рекламного аккаунта Facebook.
    
    Returns:
        AdAccount: Объект рекламного аккаунта.
    """
    auth = FacebookAuth()
    auth.initialize()
    return AdAccount(auth.get_ad_account_id()) 