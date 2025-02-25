#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
from datetime import datetime
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_file='campaign_config.json'):
    """Загрузка конфигурации из файла."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации: {str(e)}")
        raise

def create_campaign(account, config):
    """Создание кампании."""
    try:
        campaign = account.create_campaign(
            params={
                'name': config['name'],
                'objective': config['objective'],
                'status': config['status'],
                'special_ad_categories': config['special_ad_categories'],
                'bid_strategy': config['bid_strategy'],
                'daily_budget': config['daily_budget']
            }
        )
        logger.info(f"Создана кампания: {campaign['id']}")
        return campaign
    except Exception as e:
        logger.error(f"Ошибка при создании кампании: {str(e)}")
        raise

def create_ad_set(account, campaign_id, config):
    """Создание группы объявлений."""
    try:
        # Заменяем переменные окружения
        if 'instagram_actor_id' in config:
            config['instagram_actor_id'] = os.getenv('FB_INSTAGRAM_ID')
        if 'promoted_object' in config and 'page_id' in config['promoted_object']:
            config['promoted_object']['page_id'] = os.getenv('FB_PAGE_ID')

        params = {
            'campaign_id': campaign_id,
            'name': config['name'],
            'targeting': config['targeting'],
            'billing_event': config['billing_event'],
            'optimization_goal': config['optimization_goal'],
            'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
            'status': 'PAUSED',
            'daily_budget': config['daily_budget'],
            'promoted_object': config['promoted_object']
        }

        if 'instagram_actor_id' in config:
            params['instagram_actor_id'] = config['instagram_actor_id']

        ad_set = account.create_ad_set(params=params)
        logger.info(f"Создана группа объявлений: {ad_set['id']}")
        return ad_set
    except Exception as e:
        logger.error(f"Ошибка при создании группы объявлений: {str(e)}")
        raise

def create_creative(account, ad_data):
    """Создание креатива для объявления."""
    try:
        creative = account.create_ad_creative(
            params={
                'name': ad_data['name'],
                'object_story_spec': {
                    'page_id': os.getenv('FB_PAGE_ID'),
                    'link_data': {
                        'link': ad_data['link'],
                        'message': ad_data['body'],
                        'name': ad_data['title'],
                        'image_hash': ad_data['image_url']
                    }
                }
            }
        )
        logger.info(f"Создан креатив: {creative['id']}")
        return creative
    except Exception as e:
        logger.error(f"Ошибка при создании креатива: {str(e)}")
        raise

def create_ad(account, ad_set_id, creative_id, ad_data):
    """Создание объявления."""
    try:
        ad = account.create_ad(
            params={
                'name': ad_data['name'],
                'adset_id': ad_set_id,
                'creative': {'creative_id': creative_id},
                'status': 'PAUSED'
            }
        )
        logger.info(f"Создано объявление: {ad['id']}")
        return ad
    except Exception as e:
        logger.error(f"Ошибка при создании объявления: {str(e)}")
        raise

def create_test_campaign():
    """Создание тестовой кампании."""
    try:
        # Инициализация API
        access_token = os.getenv('FB_ACCESS_TOKEN')
        FacebookAdsApi.init(access_token=access_token)

        # Получаем данные аккаунта
        account = AdAccount('act_' + os.getenv('FB_ACCOUNT_ID'))

        # Загружаем конфигурацию
        with open('campaign_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Создаем кампанию
        campaign = create_campaign(account, config['campaign'])

        # Для каждой группы объявлений
        for ad_set_config in config['ad_sets']:
            # Создаем группу объявлений
            ad_set = create_ad_set(account, campaign['id'], ad_set_config)

            # Для каждого объявления в группе
            for ad_data in ad_set_config['ads']:
                # Создаем креатив
                creative = create_creative(account, ad_data)
                
                # Создаем объявление
                create_ad(account, ad_set['id'], creative['id'], ad_data)

    except Exception as e:
        logger.error(f"Ошибка при создании тестовой кампании: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        create_test_campaign()
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
