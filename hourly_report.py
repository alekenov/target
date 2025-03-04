import os
import logging
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from decimal import Decimal
import pytz  # Добавляем поддержку часовых поясов

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Создает подключение к базе данных."""
    return pymysql.connect(
        host=os.getenv('AURORA_HOST'),
        user=os.getenv('AURORA_MASTER_USERNAME'),
        password=os.getenv('AURORA_MASTER_PASSWORD'),
        database=os.getenv('AURORA_DATABASE_NAME'),
        port=int(os.getenv('AURORA_PORT', 3306)),
        connect_timeout=10,
        cursorclass=DictCursor,
        charset='utf8mb4',
        collation='utf8mb4_0900_ai_ci'
    )

def get_metrics_for_period(cursor, start_time, end_time):
    """Получает метрики за указанный период."""
    query = """
        SELECT 
            CONVERT(c.objective USING utf8mb4) COLLATE utf8mb4_0900_ai_ci as objective,
            SUM(i.impressions) as impressions,
            SUM(i.clicks) as clicks,
            SUM(i.spend) as spend,
            SUM(i.conversations) as conversations,
            SUM(i.link_clicks) as link_clicks,
            ROUND(SUM(i.clicks) / NULLIF(SUM(i.impressions), 0) * 100, 2) as ctr,
            ROUND(SUM(i.spend) / NULLIF(SUM(i.clicks), 0), 2) as cpc,
            CONVERT(c.name USING utf8mb4) COLLATE utf8mb4_0900_ai_ci as campaign_name
        FROM ad_insights i
        LEFT JOIN ads a ON CONVERT(i.ad_id USING utf8mb4) COLLATE utf8mb4_0900_ai_ci = CONVERT(a.id USING utf8mb4) COLLATE utf8mb4_0900_ai_ci
        LEFT JOIN ad_sets s ON CONVERT(a.ad_set_id USING utf8mb4) COLLATE utf8mb4_0900_ai_ci = CONVERT(s.id USING utf8mb4) COLLATE utf8mb4_0900_ai_ci
        LEFT JOIN campaigns c ON CONVERT(s.campaign_id USING utf8mb4) COLLATE utf8mb4_0900_ai_ci = CONVERT(c.id USING utf8mb4) COLLATE utf8mb4_0900_ai_ci
        WHERE i.date_start >= %s AND i.date_start < %s
        GROUP BY c.objective, c.name
    """
    
    # Логируем параметры запроса для отладки
    logger.info(f"SQL запрос с параметрами: start_time={start_time}, end_time={end_time}")
    
    cursor.execute(query, (start_time, end_time))
    results = cursor.fetchall()
    
    # Логируем результаты запроса
    logger.info(f"Найдено {len(results)} записей")
    
    return results

def calculate_metrics_diff(current_metrics, previous_metrics):
    """Вычисляет разницу между текущими и предыдущими метриками."""
    metrics_diff = {}
    
    # Группируем текущие метрики по objective
    current_by_objective = {}
    for metric in current_metrics:
        objective = metric['objective']
        if objective not in current_by_objective:
            current_by_objective[objective] = []
        current_by_objective[objective].append(metric)
        
    # Группируем предыдущие метрики по objective
    previous_by_objective = {}
    for metric in previous_metrics:
        objective = metric['objective']
        if objective not in previous_by_objective:
            previous_by_objective[objective] = []
        previous_by_objective[objective].append(metric)
    
    # Объединяем все уникальные objectives
    all_objectives = set(list(current_by_objective.keys()) + list(previous_by_objective.keys()))
    
    for objective in all_objectives:
        current_campaigns = current_by_objective.get(objective, [])
        previous_campaigns = previous_by_objective.get(objective, [])
        
        # Инициализируем метрики для objective
        metrics_diff[objective] = {
            'impressions': 0,
            'clicks': 0,
            'spend': 0,
            'conversations': 0,
            'link_clicks': 0,
            'ctr_diff': 0,
            'cpc_diff': 0,
            'ctr_current': 0,
            'cpc_current': 0,
            'campaigns': []
        }
        
        # Считаем общие метрики по objective
        total_current_impressions = sum(c['impressions'] for c in current_campaigns)
        total_current_clicks = sum(c['clicks'] for c in current_campaigns)
        total_current_spend = sum(c['spend'] for c in current_campaigns)
        
        total_previous_impressions = sum(p['impressions'] for p in previous_campaigns)
        total_previous_clicks = sum(p['clicks'] for p in previous_campaigns)
        total_previous_spend = sum(p['spend'] for p in previous_campaigns)
        
        # Вычисляем разницу
        metrics_diff[objective]['impressions'] = total_current_impressions - total_previous_impressions
        metrics_diff[objective]['clicks'] = total_current_clicks - total_previous_clicks
        metrics_diff[objective]['spend'] = float(total_current_spend - total_previous_spend)
        metrics_diff[objective]['conversations'] = sum(c['conversations'] for c in current_campaigns) - sum(p['conversations'] for p in previous_campaigns)
        metrics_diff[objective]['link_clicks'] = sum(c['link_clicks'] for c in current_campaigns) - sum(p['link_clicks'] for p in previous_campaigns)
        
        # Вычисляем текущий и предыдущий CTR
        current_ctr = (total_current_clicks / total_current_impressions * 100) if total_current_impressions > 0 else 0
        previous_ctr = (total_previous_clicks / total_previous_impressions * 100) if total_previous_impressions > 0 else 0
        metrics_diff[objective]['ctr_diff'] = current_ctr - previous_ctr
        metrics_diff[objective]['ctr_current'] = current_ctr
        
        # Вычисляем текущий и предыдущий CPC
        current_cpc = float(total_current_spend / total_current_clicks) if total_current_clicks > 0 else 0
        previous_cpc = float(total_previous_spend / total_previous_clicks) if total_previous_clicks > 0 else 0
        metrics_diff[objective]['cpc_diff'] = current_cpc - previous_cpc
        metrics_diff[objective]['cpc_current'] = current_cpc
        
        # Анализируем каждую кампанию
        for current in current_campaigns:
            campaign_name = current['campaign_name']
            previous = next((p for p in previous_campaigns if p['campaign_name'] == campaign_name), None)
            
            campaign_diff = {
                'name': campaign_name,
                'impressions': int(current['impressions'] - (previous['impressions'] if previous else 0)),
                'clicks': int(current['clicks'] - (previous['clicks'] if previous else 0)),
                'spend': float(current['spend'] - (previous['spend'] if previous else 0)),
                'conversations': int(current['conversations'] - (previous['conversations'] if previous else 0)),
                'link_clicks': int(current['link_clicks'] - (previous['link_clicks'] if previous else 0)),
                'ctr': float(current['ctr'] if current['ctr'] is not None else 0),
                'cpc': float(current['cpc'] if current['cpc'] is not None else 0)
            }
            
            if campaign_diff['impressions'] != 0 or campaign_diff['clicks'] != 0 or campaign_diff['spend'] != 0:
                metrics_diff[objective]['campaigns'].append(campaign_diff)
    
    return metrics_diff

def format_message(metrics_diff, start_time, end_time):
    """Форматирует сообщение для отправки в Telegram."""
    message = f"📊 Отчет по рекламным кампаниям\n"
    message += f"🕒 Период: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n\n"
    
    for objective, metrics in metrics_diff.items():
        if not metrics['campaigns']:  # Пропускаем цели без активных кампаний
            continue
            
        if objective == 'MESSAGES':
            campaign_type = "Сообщения"
        elif objective == 'OUTCOME_TRAFFIC':
            campaign_type = "Трафик"
        elif objective == 'OUTCOME_LEADS':
            campaign_type = "Лиды"
        elif objective == 'OUTCOME_ENGAGEMENT':
            campaign_type = "Вовлеченность"
        else:
            campaign_type = objective
            
        message += f"🎯 {campaign_type}:\n"
        
        # Общая статистика по цели
        message += "📊 Общая статистика:\n"
        if metrics['impressions'] != 0:
            message += f"👁 Показы: {format_change(metrics['impressions'])}\n"
        if metrics['clicks'] != 0:
            message += f"👆 Клики: {format_change(metrics['clicks'])}\n"
        if metrics['spend'] != 0:
            message += f"💰 Расходы: ${format_change(metrics['spend'], 2)}\n"
        if metrics['ctr_current'] > 0:
            message += f"📈 CTR: {format_change(metrics['ctr_diff'], 2, '%')} (текущий: {metrics['ctr_current']:.2f}%)\n"
        if metrics['cpc_current'] > 0:
            message += f"💵 CPC: ${format_change(metrics['cpc_diff'], 2)} (текущий: ${metrics['cpc_current']:.2f})\n"
        if metrics['conversations'] != 0:
            message += f"✉️ Переписки: {format_change(metrics['conversations'])}\n"
        if metrics['link_clicks'] != 0:
            message += f"🔗 Переходы: {format_change(metrics['link_clicks'])}\n"
            
        # Статистика по отдельным кампаниям
        message += "\n📑 По кампаниям:\n"
        for campaign in metrics['campaigns']:
            message += f"📌 {campaign['name']}:\n"
            if campaign['impressions'] != 0:
                message += f"   👁 Показы: {format_change(campaign['impressions'])}\n"
            if campaign['clicks'] != 0:
                message += f"   👆 Клики: {format_change(campaign['clicks'])}\n"
            if campaign['spend'] != 0:
                message += f"   💰 Расходы: ${format_change(campaign['spend'], 2)}\n"
            if campaign['ctr'] > 0:
                message += f"   📈 CTR: {campaign['ctr']:.2f}%\n"
            if campaign['cpc'] > 0:
                message += f"   💵 CPC: ${campaign['cpc']:.2f}\n"
            if campaign['conversations'] != 0:
                message += f"   ✉️ Переписки: {format_change(campaign['conversations'])}\n"
            if campaign['link_clicks'] != 0:
                message += f"   🔗 Переходы: {format_change(campaign['link_clicks'])}\n"
            message += "\n"
        
        message += "\n"
        
    if not message:
        message = "За указанный период изменений не обнаружено."
        
    return message

def format_change(value, decimals=0, suffix=''):
    """Форматирует изменение значения со стрелкой."""
    if isinstance(value, Decimal):
        value = float(value)
    
    if decimals > 0:
        formatted = f"{abs(value):.{decimals}f}"
    else:
        formatted = f"{int(abs(value))}"
        
    if value > 0:
        return f"📈 +{formatted}{suffix}"
    elif value < 0:
        return f"📉 -{formatted}{suffix}"
    else:
        return f"➡️ {formatted}{suffix}"

def send_telegram_message(message):
    """Отправляет сообщение в Telegram."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.error("Не настроены переменные окружения для Telegram")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {str(e)}")
        return False

def main():
    """Основная функция."""
    try:
        # Получаем текущее время в часовом поясе Казахстана
        kz_tz = pytz.timezone('Asia/Almaty')
        end_time = datetime.now(kz_tz)
        # Начало прошлого часа
        start_time = end_time.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        # Начало позапрошлого часа для сравнения
        previous_start = start_time - timedelta(hours=1)
        
        logger.info(f"Получаем данные за период: {start_time} - {end_time}")
        
        # Подключаемся к базе данных
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Проверяем наличие данных в базе
        check_query = "SELECT MIN(date_start), MAX(date_start) FROM ad_insights"
        cursor.execute(check_query)
        min_date, max_date = cursor.fetchone()
        logger.info(f"Диапазон дат в базе: с {min_date} по {max_date}")
        
        # Получаем метрики
        current_metrics = get_metrics_for_period(cursor, start_time.astimezone(pytz.UTC), end_time.astimezone(pytz.UTC))
        logger.info(f"Текущие метрики: {current_metrics}")
        
        previous_metrics = get_metrics_for_period(cursor, previous_start.astimezone(pytz.UTC), start_time.astimezone(pytz.UTC))
        logger.info(f"Предыдущие метрики: {previous_metrics}")
        
        # Вычисляем разницу
        metrics_diff = calculate_metrics_diff(current_metrics, previous_metrics)
        
        # Форматируем сообщение
        message = format_message(metrics_diff, start_time, end_time)
        
        # Выводим сообщение в консоль для отладки
        print("\nСформированный отчет:")
        print("-" * 50)
        print(message)
        print("-" * 50)
        
        # Отправляем в Telegram
        if send_telegram_message(message):
            logger.info("Отчет успешно отправлен в Telegram")
        else:
            logger.error("Не удалось отправить отчет в Telegram")
            
    except Exception as e:
        logger.error(f"Ошибка при формировании отчета: {str(e)}")
        raise
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    main()
