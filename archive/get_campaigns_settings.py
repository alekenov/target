from fb_auth import init_facebook_api
import json
import logging
from datetime import datetime, timedelta
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
import time
from time import sleep
from random import uniform
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class FacebookApiEncoder(json.JSONEncoder):
    """Специальный энкодер для объектов Facebook API."""
    def default(self, obj):
        if hasattr(obj, 'export_all_data'):
            return obj.export_all_data()
        elif hasattr(obj, 'export_data'):
            return obj.export_data()
        elif hasattr(obj, '_data'):
            return obj._data
        elif hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return str(obj)

def handle_api_call(func, *args, **kwargs):
    """Обработчик API вызовов с повторными попытками."""
    max_retries = 10  # Увеличиваем количество попыток
    base_delay = 120  # Увеличиваем базовую задержку до 2 минут
    
    for attempt in range(max_retries):
        try:
            # Увеличиваем случайную задержку
            sleep(uniform(3, 5))
            result = func(*args, **kwargs)
            
            # Успешный запрос - делаем дополнительную паузу
            sleep(uniform(2, 3))
            return result
            
        except Exception as e:
            error_code = None
            if hasattr(e, 'api_error_code'):
                error_code = e.api_error_code
            
            # Если это ошибка лимита (код 17)
            if error_code == 17:
                # Экспоненциальное увеличение времени ожидания
                wait_time = base_delay * (2 ** attempt)  
                logger.warning(f"Достигнут лимит API. Попытка {attempt + 1} из {max_retries}. Ожидаем {wait_time} секунд...")
                sleep(wait_time)
                continue
            else:
                logger.error(f"Неожиданная ошибка: {str(e)}")
                raise e
    
    raise Exception(f"Превышено максимальное количество попыток ({max_retries})")

def convert_to_json_serializable(obj):
    """Конвертирует объекты Facebook API в JSON-сериализуемый формат."""
    if hasattr(obj, 'export_all_data'):
        return obj.export_all_data()
    elif hasattr(obj, 'export_data'):
        return obj.export_data()
    elif hasattr(obj, '_data'):
        return obj._data
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(v) for v in obj]
    elif hasattr(obj, '__dict__'):
        # Конвертируем все атрибуты объекта
        return {k: convert_to_json_serializable(v) for k, v in obj.__dict__.items() 
                if not k.startswith('_')}
    else:
        try:
            # Пробуем сконвертировать в базовый тип
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            # Если не получается, возвращаем строковое представление
            return str(obj)

def get_high_spend_campaigns(account, min_spend=300):
    """Получение кампаний с расходами выше указанного значения."""
    try:
        logger.info(f"Получаем кампании с расходами выше ${min_spend}...")
        
        insights = handle_api_call(
            account.get_insights,
            params={
                'level': 'campaign',
                'fields': [
                    'campaign_id',
                    'campaign_name',
                    'spend'
                ],
                'time_range': {
                    'since': '2024-01-01',
                    'until': datetime.now().strftime('%Y-%m-%d')
                }
            }
        )
        
        # Фильтруем кампании по расходам
        high_spend_campaigns = []
        for insight in insights:
            spend = float(insight.get('spend', 0))
            if spend >= min_spend:
                high_spend_campaigns.append({
                    'id': insight['campaign_id'],
                    'name': insight['campaign_name'],
                    'spend': spend
                })
        
        logger.info(f"Найдено {len(high_spend_campaigns)} кампаний с расходами выше ${min_spend}")
        return high_spend_campaigns
    
    except Exception as e:
        logger.error(f"Ошибка при получении кампаний с высокими расходами: {str(e)}")
        return []

def get_campaign_settings(campaign):
    """Получение детальных настроек кампании."""
    try:
        campaign_data = handle_api_call(
            campaign.api_get,
            fields=[
                'id',
                'name',
                'objective',
                'status',
                'bid_strategy',
                'budget_remaining',
                'daily_budget',
                'lifetime_budget',
                'start_time',
                'stop_time',
                'special_ad_categories',
                'promoted_object'
            ]
        )
        
        # Преобразуем данные в словарь
        return {
            'campaign_id': campaign_data.get('id'),
            'name': campaign_data.get('name'),
            'objective': campaign_data.get('objective'),
            'status': campaign_data.get('status'),
            'budget': {
                'daily_budget': float(campaign_data.get('daily_budget', 0)) / 100 if campaign_data.get('daily_budget') else None,
                'lifetime_budget': float(campaign_data.get('lifetime_budget', 0)) / 100 if campaign_data.get('lifetime_budget') else None,
                'budget_remaining': float(campaign_data.get('budget_remaining', 0)) / 100 if campaign_data.get('budget_remaining') else None
            },
            'timing': {
                'start_time': campaign_data.get('start_time'),
                'stop_time': campaign_data.get('stop_time')
            },
            'bid_strategy': campaign_data.get('bid_strategy'),
            'special_ad_categories': campaign_data.get('special_ad_categories'),
            'promoted_object': campaign_data.get('promoted_object')
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении настроек кампании {campaign.get('id', 'UNKNOWN')}: {str(e)}")
        return None

def get_adset_settings(adset):
    """Получение детальных настроек группы объявлений."""
    try:
        adset_data = handle_api_call(
            adset.api_get,
            fields=[
                'id',
                'name',
                'campaign_id',
                'status',
                'targeting',
                'bid_amount',
                'bid_strategy',
                'billing_event',
                'optimization_goal',
                'daily_budget',
                'lifetime_budget',
                'start_time',
                'end_time',
                'destination_type',
                'instagram_actor_id',
                'promoted_object',
                'attribution_spec',
                'frequency_control_specs'
            ]
        )
        
        targeting = adset_data.get('targeting', {})
        
        return {
            'adset_id': adset_data.get('id'),
            'name': adset_data.get('name'),
            'status': adset_data.get('status'),
            'targeting': {
                'geo_locations': targeting.get('geo_locations'),
                'age_range': {
                    'min': targeting.get('age_min'),
                    'max': targeting.get('age_max')
                },
                'genders': targeting.get('genders'),
                'interests': targeting.get('interests'),
                'behaviors': targeting.get('behaviors'),
                'custom_audiences': targeting.get('custom_audiences'),
                'excluded_custom_audiences': targeting.get('excluded_custom_audiences'),
                'placements': {
                    'device_platforms': targeting.get('device_platforms'),
                    'facebook_positions': targeting.get('facebook_positions'),
                    'instagram_positions': targeting.get('instagram_positions'),
                    'publisher_platforms': targeting.get('publisher_platforms')
                },
                'languages': targeting.get('locales'),
                'flexible_spec': targeting.get('flexible_spec'),
                'exclusions': targeting.get('exclusions')
            },
            'budget': {
                'daily_budget': float(adset_data.get('daily_budget', 0)) / 100 if adset_data.get('daily_budget') else None,
                'lifetime_budget': float(adset_data.get('lifetime_budget', 0)) / 100 if adset_data.get('lifetime_budget') else None
            },
            'optimization': {
                'optimization_goal': adset_data.get('optimization_goal'),
                'billing_event': adset_data.get('billing_event'),
                'bid_strategy': adset_data.get('bid_strategy'),
                'bid_amount': float(adset_data.get('bid_amount', 0)) / 100 if adset_data.get('bid_amount') else None
            },
            'timing': {
                'start_time': adset_data.get('start_time'),
                'end_time': adset_data.get('end_time')
            },
            'frequency_control': adset_data.get('frequency_control_specs'),
            'destination_type': adset_data.get('destination_type'),
            'instagram_actor_id': adset_data.get('instagram_actor_id'),
            'promoted_object': adset_data.get('promoted_object'),
            'attribution_spec': adset_data.get('attribution_spec')
        }
    except Exception as e:
        logger.error(f"Ошибка при получении настроек группы объявлений {adset.get('id', 'UNKNOWN')}: {str(e)}")
        return None

def get_campaign_full_settings(campaign_info):
    """Получение полных настроек для одной кампании."""
    try:
        campaign_id = campaign_info['id']
        logger.info(f"Анализируем кампанию {campaign_info['name']} (расход: ${campaign_info['spend']:.2f})...")
        
        # Длительная пауза перед обработкой новой кампании
        sleep(uniform(15, 20))
        
        # Получаем настройки кампании
        campaign_settings = get_campaign_settings(Campaign(campaign_id))
        if not campaign_settings:
            return None
        
        # Добавляем информацию о расходах
        campaign_settings['spend'] = campaign_info['spend']
        
        # Сохраняем промежуточный результат
        temp_filename = f'temp_campaign_{campaign_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        save_data({'campaign': campaign_settings}, temp_filename)
        
        # Длительная пауза перед получением групп объявлений
        sleep(uniform(20, 30))
        
        try:
            adsets = handle_api_call(
                Campaign(campaign_id).get_ad_sets
            )
        except Exception as e:
            logger.error(f"Ошибка при получении групп объявлений для кампании {campaign_id}: {str(e)}")
            return {
                'campaign': campaign_settings,
                'ad_sets': [],
                'error': 'Failed to fetch ad sets'
            }
        
        adsets_settings = []
        for adset in adsets:
            try:
                # Длительная пауза между обработкой групп объявлений
                sleep(uniform(10, 15))
                
                adset_settings = get_adset_settings(AdSet(adset['id']))
                if adset_settings:
                    adsets_settings.append(adset_settings)
                    
                    # Сохраняем промежуточный результат после каждой группы
                    save_data({
                        'campaign': campaign_settings,
                        'ad_sets': adsets_settings
                    }, temp_filename)
                    
            except Exception as e:
                logger.error(f"Ошибка при получении настроек группы объявлений {adset['id']}: {str(e)}")
                continue
        
        # Удаляем временный файл
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        
        return {
            'campaign': campaign_settings,
            'ad_sets': adsets_settings
        }
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кампании {campaign_id}: {str(e)}")
        return None

def save_data(data, filename):
    """Сохранение данных в JSON файл."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=FacebookApiEncoder, ensure_ascii=False, indent=2)
        logger.info(f"Данные сохранены в {filename}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в {filename}: {str(e)}")

def get_account_campaigns(account_id):
    """Получение списка всех кампаний аккаунта."""
    try:
        logger.info(f"Получаем список кампаний для аккаунта {account_id}...")
        account = AdAccount(f'act_{account_id}')
        
        # Получаем список кампаний
        campaigns = handle_api_call(
            account.get_campaigns,
            params={
                'fields': [
                    'id',
                    'name',
                    'objective',
                    'status',
                    'configured_status',
                    'effective_status',
                    'bid_strategy',
                    'budget_remaining',
                    'daily_budget',
                    'lifetime_budget'
                ],
                'limit': 100
            }
        )
        
        return campaigns
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка кампаний: {str(e)}")
        raise

def get_campaign_settings_from_api(campaign_id):
    """Получение настроек кампании."""
    try:
        logger.info(f"Получаем настройки кампании {campaign_id}...")
        campaign = Campaign(campaign_id)
        
        # Получаем основные настройки кампании
        campaign_data = handle_api_call(
            campaign.api_get,
            fields=[
                'id',
                'name',
                'objective',
                'status',
                'configured_status',
                'effective_status',
                'bid_strategy',
                'budget_remaining',
                'daily_budget',
                'lifetime_budget',
                'start_time',
                'stop_time',
                'created_time',
                'updated_time',
                'special_ad_categories',
                'special_ad_category',
                'special_ad_category_country',
                'spend_cap'
            ]
        )
        
        # Получаем группы объявлений
        adsets = handle_api_call(
            campaign.get_ad_sets,
            params={
                'fields': [
                    'id',
                    'name',
                    'status',
                    'targeting',
                    'bid_amount',
                    'bid_strategy',
                    'billing_event',
                    'optimization_goal',
                    'attribution_spec',
                    'daily_budget',
                    'lifetime_budget',
                    'budget_remaining',
                    'destination_type',
                    'promoted_object',
                    'start_time',
                    'end_time',
                    'created_time',
                    'updated_time',
                    'frequency_control_specs',
                    'targeting_optimization',
                    'optimization_sub_event',
                    'pacing_type'
                ],
                'limit': 100
            }
        )
        
        # Формируем отчет
        report = {
            'campaign': {
                'id': campaign_id,
                'settings': campaign_data,
                'ad_sets': adsets
            },
            'generated_at': datetime.now().isoformat()
        }
        
        # Сохраняем отчет, используя специальный энкодер
        filename = f"campaign_{campaign_id}_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, cls=FacebookApiEncoder, ensure_ascii=False, indent=2)
        logger.info(f"Настройки сохранены в {filename}")
        
        return report
        
    except Exception as e:
        logger.error(f"Ошибка при получении настроек кампании {campaign_id}: {str(e)}")
        raise

def get_all_campaigns_settings(account_id):
    """Получение настроек всех кампаний аккаунта."""
    try:
        # Инициализируем API
        access_token = os.getenv('FB_ACCESS_TOKEN')
        app_id = os.getenv('FB_APP_ID', '1234567890')
        app_secret = os.getenv('FB_APP_SECRET', '')
        FacebookAdsApi.init(app_id, app_secret, access_token)
        
        # Получаем список кампаний
        campaigns = get_account_campaigns(account_id)
        logger.info(f"Найдено кампаний: {len(campaigns)}")
        
        # Получаем настройки каждой кампании
        settings = []
        for campaign in campaigns:
            try:
                campaign_settings = get_campaign_settings_from_api(campaign['id'])
                settings.append(campaign_settings)
            except Exception as e:
                logger.error(f"Ошибка при получении настроек кампании {campaign['id']}: {str(e)}")
                continue
        
        # Сохраняем общий отчет
        summary_report = {
            'account_id': account_id,
            'campaigns': settings,
            'total_campaigns': len(settings),
            'generated_at': datetime.now().isoformat()
        }
        
        filename = f"account_{account_id}_campaigns_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, cls=FacebookApiEncoder, ensure_ascii=False, indent=2)
        logger.info(f"Общий отчет сохранен в {filename}")
        
        return summary_report
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        raise

def main():
    try:
        logger.info("Начинаем анализ настроек рекламных кампаний...")
        
        # Инициализация API
        account, api = init_facebook_api()
        
        if not account:
            logger.error("Не удалось получить доступ к рекламному аккаунту")
            return
            
        logger.info("Успешно подключились к Facebook API")
        
        # Получаем кампании с высокими расходами
        high_spend_campaigns = get_high_spend_campaigns(account, min_spend=300)
        
        if not high_spend_campaigns:
            logger.error("Не найдено кампаний с расходами выше $300")
            return
        
        # Сортируем кампании по расходам (начнем с самых дорогих)
        high_spend_campaigns.sort(key=lambda x: x['spend'], reverse=True)
        
        # Получаем настройки для каждой кампании
        all_settings = []
        for i, campaign in enumerate(high_spend_campaigns, 1):
            logger.info(f"Обработка кампании {i} из {len(high_spend_campaigns)}")
            
            settings = get_campaign_full_settings(campaign)
            if settings:
                all_settings.append(settings)
                
                # Сохраняем результаты после каждой кампании
                temp_filename = f'campaign_settings_partial_{datetime.now().strftime("%Y%m%d")}.json'
                save_data(all_settings, temp_filename)
            
            # Длительная пауза между кампаниями
            sleep(uniform(30, 45))
        
        if all_settings:
            # Сохраняем финальные результаты
            filename = f'high_spend_campaign_settings_{datetime.now().strftime("%Y%m%d")}.json'
            save_data(all_settings, filename)
            logger.info("Анализ успешно завершен")
        else:
            logger.error("Не удалось получить настройки кампаний")
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    main()
