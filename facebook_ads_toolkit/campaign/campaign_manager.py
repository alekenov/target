"""
Модуль для управления рекламными кампаниями в Facebook Ads.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad

from ..auth.facebook_auth import FacebookAuth
from ..utils.api_helpers import retry_on_api_error

logger = logging.getLogger(__name__)

class CampaignManager:
    """Класс для управления рекламными кампаниями."""
    
    def __init__(self, account: AdAccount = None, api = None):
        """
        Инициализация менеджера кампаний.
        
        Args:
            account: Инициализированный рекламный аккаунт
            api: Инициализированный Facebook API
        """
        if not account or not api:
            auth = FacebookAuth()
            account, api = auth.initialize()
        
        self.account = account
        self.api = api
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """
        Загрузка конфигурации кампании из файла.
        
        Args:
            config_file: Путь к файлу конфигурации
            
        Returns:
            Dict[str, Any]: Конфигурация кампании
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Конфигурация успешно загружена из {config_file}")
            return config
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {str(e)}")
            raise
    
    @retry_on_api_error
    def create_campaign(self, config: Dict[str, Any]) -> Campaign:
        """
        Создание рекламной кампании.
        
        Args:
            config: Конфигурация кампании
            
        Returns:
            Campaign: Созданная кампания
        """
        try:
            logger.info(f"Создание кампании: {config.get('name', 'Без имени')}")
            
            campaign_params = {
                'name': config.get('name', f"Campaign_{str(id(config))}"),
                'objective': config.get('objective', 'REACH'),
                'status': config.get('status', 'PAUSED'),
                'special_ad_categories': config.get('special_ad_categories', []),
                'bid_strategy': config.get('bid_strategy', 'LOWEST_COST_WITHOUT_CAP')
            }
            
            # Добавляем бюджет
            if 'daily_budget' in config:
                campaign_params['daily_budget'] = config['daily_budget']
            elif 'lifetime_budget' in config:
                campaign_params['lifetime_budget'] = config['lifetime_budget']
            
            # Создаем кампанию
            campaign = self.account.create_campaign(params=campaign_params)
            
            logger.info(f"Кампания успешно создана: {campaign['id']}")
            return campaign
            
        except Exception as e:
            logger.error(f"Ошибка при создании кампании: {str(e)}")
            raise
    
    @retry_on_api_error
    def create_ad_set(self, campaign_id: str, config: Dict[str, Any]) -> AdSet:
        """
        Создание группы объявлений.
        
        Args:
            campaign_id: ID кампании
            config: Конфигурация группы объявлений
            
        Returns:
            AdSet: Созданная группа объявлений
        """
        try:
            logger.info(f"Создание группы объявлений: {config.get('name', 'Без имени')}")
            
            # Готовим параметры для создания группы объявлений
            ad_set_params = {
                'campaign_id': campaign_id,
                'name': config.get('name', f"AdSet_{str(id(config))}"),
                'targeting': config.get('targeting', {}),
                'optimization_goal': config.get('optimization_goal', 'REACH'),
                'billing_event': config.get('billing_event', 'IMPRESSIONS'),
                'bid_strategy': config.get('bid_strategy', 'LOWEST_COST_WITHOUT_CAP'),
                'status': config.get('status', 'PAUSED')
            }
            
            # Добавляем бюджет
            if 'daily_budget' in config:
                ad_set_params['daily_budget'] = config['daily_budget']
            elif 'lifetime_budget' in config:
                ad_set_params['lifetime_budget'] = config['lifetime_budget']
            
            # Добавляем promoted_object если есть
            if 'promoted_object' in config:
                promoted_object = config['promoted_object']
                
                # Заменяем переменные окружения в promoted_object
                if 'page_id' in promoted_object and promoted_object['page_id'].startswith('$'):
                    env_var = promoted_object['page_id'][1:]
                    promoted_object['page_id'] = os.getenv(env_var)
                
                ad_set_params['promoted_object'] = promoted_object
            
            # Добавляем Instagram Actor ID если есть
            if 'instagram_actor_id' in config:
                instagram_id = config['instagram_actor_id']
                
                # Заменяем переменные окружения
                if instagram_id.startswith('$'):
                    env_var = instagram_id[1:]
                    instagram_id = os.getenv(env_var)
                
                ad_set_params['instagram_actor_id'] = instagram_id
            
            # Создаем группу объявлений
            ad_set = self.account.create_ad_set(params=ad_set_params)
            
            logger.info(f"Группа объявлений успешно создана: {ad_set['id']}")
            return ad_set
            
        except Exception as e:
            logger.error(f"Ошибка при создании группы объявлений: {str(e)}")
            raise
    
    @retry_on_api_error
    def create_creative(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создание креатива для объявления.
        
        Args:
            config: Конфигурация креатива
            
        Returns:
            Dict[str, Any]: Созданный креатив
        """
        try:
            logger.info(f"Создание креатива: {config.get('name', 'Без имени')}")
            
            # Подготавливаем object_story_spec
            story_spec = {
                'page_id': config.get('page_id', os.getenv('FB_PAGE_ID'))
            }
            
            # Если указана ссылка - создаем link_data
            if 'link' in config:
                link_data = {
                    'link': config['link'],
                    'message': config.get('body', ''),
                    'name': config.get('title', '')
                }
                
                # Добавляем image_hash если есть
                if 'image_hash' in config:
                    link_data['image_hash'] = config['image_hash']
                elif 'image_url' in config:
                    link_data['image_url'] = config['image_url']
                
                story_spec['link_data'] = link_data
            
            # Создаем креатив
            creative_params = {
                'name': config.get('name', f"Creative_{str(id(config))}"),
                'object_story_spec': story_spec
            }
            
            creative = self.account.create_ad_creative(params=creative_params)
            
            logger.info(f"Креатив успешно создан: {creative['id']}")
            return creative
            
        except Exception as e:
            logger.error(f"Ошибка при создании креатива: {str(e)}")
            raise
    
    @retry_on_api_error
    def create_ad(self, ad_set_id: str, creative_id: str, config: Dict[str, Any]) -> Ad:
        """
        Создание объявления.
        
        Args:
            ad_set_id: ID группы объявлений
            creative_id: ID креатива
            config: Конфигурация объявления
            
        Returns:
            Ad: Созданное объявление
        """
        try:
            logger.info(f"Создание объявления: {config.get('name', 'Без имени')}")
            
            # Создаем объявление
            ad_params = {
                'name': config.get('name', f"Ad_{str(id(config))}"),
                'adset_id': ad_set_id,
                'creative': {'creative_id': creative_id},
                'status': config.get('status', 'PAUSED')
            }
            
            ad = self.account.create_ad(params=ad_params)
            
            logger.info(f"Объявление успешно создано: {ad['id']}")
            return ad
            
        except Exception as e:
            logger.error(f"Ошибка при создании объявления: {str(e)}")
            raise
    
    def create_campaign_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создание полной рекламной кампании из конфигурации.
        
        Args:
            config: Полная конфигурация рекламной кампании
            
        Returns:
            Dict[str, Any]: Словарь с созданными объектами
        """
        results = {
            'campaign': None,
            'ad_sets': [],
            'ads': []
        }
        
        try:
            # Проверяем наличие необходимых секций в конфигурации
            if 'campaign' not in config:
                raise ValueError("В конфигурации отсутствует секция 'campaign'")
            
            if 'ad_sets' not in config:
                raise ValueError("В конфигурации отсутствует секция 'ad_sets'")
            
            # Создаем кампанию
            campaign = self.create_campaign(config['campaign'])
            results['campaign'] = campaign
            
            # Для каждой группы объявлений
            for ad_set_config in config['ad_sets']:
                # Создаем группу объявлений
                ad_set = self.create_ad_set(campaign['id'], ad_set_config)
                results['ad_sets'].append(ad_set)
                
                # Для каждого объявления в группе
                if 'ads' in ad_set_config:
                    for ad_config in ad_set_config['ads']:
                        # Создаем креатив
                        creative = self.create_creative(ad_config)
                        
                        # Создаем объявление
                        ad = self.create_ad(ad_set['id'], creative['id'], ad_config)
                        results['ads'].append(ad)
            
            logger.info(f"Рекламная кампания успешно создана: {campaign['id']}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при создании рекламной кампании: {str(e)}")
            raise
    
    def create_test_campaign(self, config_file: str = 'campaign_config.json') -> Dict[str, Any]:
        """
        Создание тестовой рекламной кампании из файла конфигурации.
        
        Args:
            config_file: Путь к файлу конфигурации
            
        Returns:
            Dict[str, Any]: Словарь с созданными объектами
        """
        try:
            # Загружаем конфигурацию
            config = self.load_config(config_file)
            
            # Создаем кампанию
            return self.create_campaign_from_config(config)
            
        except Exception as e:
            logger.error(f"Ошибка при создании тестовой кампании: {str(e)}")
            raise 