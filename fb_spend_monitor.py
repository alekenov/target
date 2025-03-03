import os
from datetime import datetime, timedelta
import requests
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def init_facebook_api():
    """Инициализация Facebook API"""
    try:
        access_token = os.getenv('FB_ACCESS_TOKEN')
        if not access_token:
            raise ValueError("FB_ACCESS_TOKEN не найден в .env файле")
            
        account_id = os.getenv('FB_ACCOUNT_ID')
        if not account_id:
            raise ValueError("FB_ACCOUNT_ID не найден в .env файле")
            
        # Инициализация API только с access_token
        FacebookAdsApi.init(access_token=access_token)
        
        # Убираем 'act_' из ID аккаунта если он есть
        account_id = account_id.replace('act_', '')
        return f'act_{account_id}'
        
    except Exception as e:
        print(f"Ошибка при инициализации Facebook API: {str(e)}")
        raise

def get_active_campaigns(account_id):
    """Получение активных кампаний и их метрик"""
    try:
        account = AdAccount(account_id)
        
        # Получаем список активных кампаний
        campaigns = account.get_campaigns(
            params={
                'effective_status': ['ACTIVE'],
                'fields': [
                    'name',
                    'objective',
                    'status',
                    'created_time'
                ]
            }
        )
        
        campaign_data = []
        
        for campaign in campaigns:
            # Получаем статистику по каждой кампании
            insights = campaign.get_insights(
                params={
                    'fields': [
                        'spend',
                        'impressions',
                        'clicks',
                        'reach'
                    ],
                    'date_preset': 'today'
                }
            )
            
            stats = insights[0] if insights else {'spend': '0', 'impressions': '0', 'clicks': '0', 'reach': '0'}
            
            campaign_data.append({
                'id': campaign['id'],
                'name': campaign['name'],
                'status': campaign['status'],
                'spend': float(stats.get('spend', 0)),
                'impressions': int(stats.get('impressions', 0)),
                'clicks': int(stats.get('clicks', 0)),
                'reach': int(stats.get('reach', 0))
            })
            
        return campaign_data
        
    except Exception as e:
        print(f"Ошибка при получении данных кампаний: {str(e)}")
        return None

def format_number(num):
    """Форматирование чисел для красивого вывода"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def send_telegram_message(message):
    """Отправка сообщения в Telegram"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Сообщение успешно отправлено в Telegram")
    except Exception as e:
        print(f"Ошибка при отправке в Telegram: {str(e)}")

def main():
    # Инициализация Facebook API
    account_id = init_facebook_api()
    
    # Получение данных об активных кампаниях
    campaigns = get_active_campaigns(account_id)
    
    if campaigns:
        current_time = datetime.now()
        
        # Подсчет общих показателей
        total_spend = sum(c['spend'] for c in campaigns)
        total_impressions = sum(c['impressions'] for c in campaigns)
        total_clicks = sum(c['clicks'] for c in campaigns)
        total_reach = sum(c['reach'] for c in campaigns)
        
        # Форматирование сообщения
        message = f"📊 <b>Отчет по активным кампаниям Facebook Ads</b>\n\n"
        message += f"💰 Общие траты за сегодня: ${total_spend:.2f}\n"
        message += f"👥 Охват: {format_number(total_reach)}\n"
        message += f"👁 Показы: {format_number(total_impressions)}\n"
        message += f"🖱 Клики: {format_number(total_clicks)}\n\n"
        
        message += "<b>Активные кампании:</b>\n"
        for campaign in campaigns:
            message += f"\n🎯 <b>{campaign['name']}</b>\n"
            message += f"├ Траты: ${campaign['spend']:.2f}\n"
            message += f"├ Показы: {format_number(campaign['impressions'])}\n"
            message += f"├ Клики: {format_number(campaign['clicks'])}\n"
            message += f"└ Охват: {format_number(campaign['reach'])}\n"
        
        message += f"\n📅 Дата: {current_time.strftime('%Y-%m-%d')}\n"
        message += f"⏰ Время отчета: {current_time.strftime('%H:%M:%S')}\n"
        message += f"📱 Рекламный аккаунт: {account_id}"
        
        # Отправка в Telegram
        send_telegram_message(message)
    else:
        error_message = "❌ Не удалось получить данные о кампаниях или нет активных кампаний"
        send_telegram_message(error_message)

if __name__ == "__main__":
    main() 