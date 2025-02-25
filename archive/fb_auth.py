from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

def init_facebook_api():
    """Инициализация Facebook API."""
    try:
        load_dotenv()
        
        access_token = os.getenv('FB_ACCESS_TOKEN')
        account_id = os.getenv('FB_ACCOUNT_ID')
        app_id = os.getenv('FB_APP_ID', '1610313936433257')
        
        if not access_token or not account_id:
            raise ValueError("Missing required environment variables: FB_ACCESS_TOKEN, FB_ACCOUNT_ID")
        
        # Инициализация API
        api = FacebookAdsApi.init(app_id=app_id, access_token=access_token)
        account = AdAccount(f'act_{account_id}')
        
        return account, api
    
    except Exception as e:
        logger.error(f"Ошибка при инициализации Facebook API: {str(e)}")
        return None, None
