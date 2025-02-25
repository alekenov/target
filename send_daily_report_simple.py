import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from facebook_ads_toolkit.auth.facebook_auth import initialize_api
from facebook_ads_toolkit.reports.report_generator import get_campaigns_list
from facebook_ads_toolkit.telegram.telegram_sender import send_telegram_message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """
    Основная функция для отправки ежедневного отчета.
    """
    logger.info("Запуск скрипта отправки ежедневного отчета")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Инициализируем Facebook API
    logger.info("Инициализация Facebook API")
    account_id = initialize_api()
    logger.info(f"Facebook API инициализирован. Аккаунт: {account_id}")
    
    # Получаем данные о кампаниях
    logger.info("Получение данных о кампаниях")
    campaigns = get_campaigns_list(status='ACTIVE')
    
    if not campaigns:
        logger.warning("Не удалось получить список кампаний")
        message = "⚠️ *Ежедневный отчет*\n\nНе удалось получить данные о кампаниях. Пожалуйста, проверьте настройки API и доступ к рекламному аккаунту."
    else:
        logger.info(f"Получено {len(campaigns)} активных кампаний")
        
        # Формируем отчет
        message = "*📊 Ежедневный отчет по рекламным кампаниям*\n\n"
        message += f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
        message += f"Всего активных кампаний: {len(campaigns)}\n\n"
        
        # Добавляем информацию о каждой кампании
        for i, campaign in enumerate(campaigns, 1):
            campaign_data = campaign
            
            # Получаем бюджет
            budget = "Не указан"
            if 'daily_budget' in campaign_data and campaign_data['daily_budget']:
                budget = f"{float(campaign_data['daily_budget'])/100:.2f} USD/день"
            elif 'lifetime_budget' in campaign_data and campaign_data['lifetime_budget']:
                budget = f"{float(campaign_data['lifetime_budget'])/100:.2f} USD (на весь период)"
            
            message += f"*{i}. {campaign_data.get('name', 'Без названия')}*\n"
            message += f"ID: `{campaign_data.get('id', 'Н/Д')}`\n"
            message += f"Статус: {campaign_data.get('effective_status', 'Н/Д')}\n"
            message += f"Бюджет: {budget}\n"
            
            if i < len(campaigns):
                message += "\n"
    
    # Отправляем сообщение в Telegram
    channel_id = os.environ.get('TELEGRAM_LOG_CHANNEL_ID')
    logger.info(f"Отправка сообщения в канал {channel_id}")
    
    result = send_telegram_message(channel_id, message)
    if result:
        logger.info("Сообщение успешно отправлено")
    else:
        logger.error("Ошибка при отправке сообщения")

if __name__ == "__main__":
    main() 