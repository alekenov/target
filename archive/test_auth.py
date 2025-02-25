from fb_auth import init_facebook_api
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auth():
    logger.info("Тестирование авторизации в Facebook API...")
    account, api = init_facebook_api()
    
    if account and api:
        try:
            # Пробуем получить базовую информацию об аккаунте
            account_info = account.api_get(fields=['name', 'account_status'])
            logger.info(f"Успешная авторизация! Информация об аккаунте:")
            logger.info(f"Название: {account_info.get('name')}")
            logger.info(f"Статус аккаунта: {account_info.get('account_status')}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при получении информации об аккаунте: {str(e)}")
            return False
    else:
        logger.error("Не удалось инициализировать Facebook API")
        return False

if __name__ == "__main__":
    test_auth()
