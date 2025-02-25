"""
Модуль для оптимизации рекламных кампаний на основе данных анализа.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount

from ..auth.facebook_auth import FacebookAuth
from ..analysis.data_fetchers import AdDataFetcher
from ..analysis.ad_analyzer import AdAnalyzer
from ..campaign.campaign_manager import CampaignManager
from ..utils.api_helpers import retry_on_api_error

logger = logging.getLogger(__name__)

class CampaignOptimizer:
    """Класс для оптимизации рекламных кампаний на основе данных анализа."""
    
    def __init__(self, account: AdAccount = None, api = None):
        """
        Инициализация оптимизатора кампаний.
        
        Args:
            account: Инициализированный рекламный аккаунт
            api: Инициализированный Facebook API
        """
        if not account or not api:
            auth = FacebookAuth()
            account, api = auth.initialize()
        
        self.account = account
        self.api = api
        self.manager = CampaignManager(account, api)
        self.data_fetcher = AdDataFetcher(account, api)
        self.analyzer = AdAnalyzer()
        
        # Пороги для принятия решений по оптимизации
        self.thresholds = {
            'ctr': {
                'excellent': 2.0,  # CTR выше 2% считается отличным
                'good': 1.0,       # CTR выше 1% считается хорошим
                'poor': 0.5        # CTR ниже 0.5% считается плохим
            },
            'cpc': {
                'excellent': 0.5,  # CPC ниже 0.5$ считается отличным
                'good': 1.0,       # CPC ниже 1.0$ считается хорошим
                'poor': 2.0        # CPC выше 2.0$ считается плохим
            },
            'roas': {
                'excellent': 3.0,  # ROAS выше 3 считается отличным
                'good': 2.0,       # ROAS выше 2 считается хорошим
                'poor': 1.0        # ROAS ниже 1 считается плохим
            },
            'min_data': {
                'impressions': 1000, # Минимум 1000 показов для принятия решений
                'spend': 50         # Минимум 50$ расходов для принятия решений
            }
        }
    
    def set_thresholds(self, thresholds: Dict[str, Any]):
        """
        Установка пользовательских порогов для оптимизации.
        
        Args:
            thresholds: Словарь с порогами для оптимизации
        """
        if thresholds:
            for category, values in thresholds.items():
                if category in self.thresholds:
                    self.thresholds[category].update(values)
        
        logger.info(f"Установлены пользовательские пороги для оптимизации")
    
    def analyze_account(self, days: int = 30) -> Dict[str, Any]:
        """
        Анализ рекламного аккаунта для оптимизации.
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        logger.info(f"Начинаем анализ аккаунта за последние {days} дней")
        
        # Устанавливаем временной диапазон
        self.data_fetcher.set_default_time_range(days)
        
        # Получаем данные с помощью параллельной обработки
        ad_data = self.data_fetcher.fetch_all_parallel()
        
        # Анализируем данные
        self.analyzer.set_data(ad_data)
        analysis_results = self.analyzer.analyze()
        
        logger.info(f"Анализ аккаунта завершен")
        
        return analysis_results
    
    def optimize_campaigns(self, analysis_results: Optional[Dict[str, Any]] = None, 
                         days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """
        Оптимизация кампаний на основе результатов анализа.
        
        Args:
            analysis_results: Результаты анализа (если не предоставлены, будут получены)
            days: Количество дней для анализа (если требуется получить результаты)
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Результаты оптимизации
        """
        logger.info("Начинаем оптимизацию кампаний")
        
        # Получаем результаты анализа, если не предоставлены
        if not analysis_results:
            analysis_results = self.analyze_account(days)
        
        # Оптимизируем бюджеты кампаний
        budget_changes = self._optimize_budgets(analysis_results)
        
        # Оптимизируем ставки в группах объявлений
        bid_changes = self._optimize_bids(analysis_results)
        
        # Оптимизируем статусы объявлений (пауза/запуск)
        status_changes = self._optimize_ad_statuses(analysis_results)
        
        # Собираем результаты оптимизации
        optimization_results = {
            'budget_changes': budget_changes,
            'bid_changes': bid_changes,
            'status_changes': status_changes,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"Оптимизация кампаний завершена. Сделано {len(budget_changes)} изменений бюджета, "
                   f"{len(bid_changes)} изменений ставок, {len(status_changes)} изменений статусов")
        
        return optimization_results
    
    def _optimize_budgets(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Оптимизация бюджетов кампаний на основе эффективности.
        
        Args:
            analysis_results: Результаты анализа кампаний
            
        Returns:
            List[Dict[str, Any]]: Список изменений бюджетов
        """
        budget_changes = []
        
        if not analysis_results or 'campaign_performance' not in analysis_results:
            return budget_changes
        
        campaigns = analysis_results['campaign_performance']['all_campaigns']
        
        for campaign_data in campaigns:
            campaign_id = campaign_data.get('id')
            if not campaign_id:
                continue
            
            # Проверяем достаточно ли данных для принятия решения
            if (campaign_data.get('impressions', 0) < self.thresholds['min_data']['impressions'] or
                campaign_data.get('spend', 0) < self.thresholds['min_data']['spend']):
                logger.info(f"Недостаточно данных для оптимизации бюджета кампании {campaign_id}")
                continue
            
            # Текущий бюджет кампании
            current_budget = None
            is_daily_budget = False
            
            if campaign_data.get('daily_budget'):
                current_budget = float(campaign_data['daily_budget']) / 100  # Конвертируем из центов
                is_daily_budget = True
            elif campaign_data.get('lifetime_budget'):
                current_budget = float(campaign_data['lifetime_budget']) / 100  # Конвертируем из центов
                is_daily_budget = False
            
            if not current_budget:
                logger.warning(f"Не удалось определить текущий бюджет для кампании {campaign_id}")
                continue
            
            # Определяем новый бюджет на основе эффективности
            new_budget = current_budget
            
            # Используем CTR и ROAS как ключевые метрики для оптимизации бюджета
            ctr = campaign_data.get('ctr', 0)
            roas = campaign_data.get('roas', 0)
            
            # Правила корректировки бюджета:
            # 1. Если CTR отличный и ROAS хороший или отличный - увеличиваем бюджет на 20%
            # 2. Если CTR хороший и ROAS хороший - увеличиваем бюджет на 10%
            # 3. Если CTR плохой или ROAS плохой - уменьшаем бюджет на 10%
            # 4. Если CTR плохой и ROAS плохой - уменьшаем бюджет на 20%
            
            if ctr >= self.thresholds['ctr']['excellent'] and roas >= self.thresholds['roas']['good']:
                new_budget = current_budget * 1.2  # Увеличение на 20%
                action = "increase"
                reason = "Отличный CTR и хороший ROAS"
            elif ctr >= self.thresholds['ctr']['good'] and roas >= self.thresholds['roas']['good']:
                new_budget = current_budget * 1.1  # Увеличение на 10%
                action = "increase"
                reason = "Хороший CTR и ROAS"
            elif ctr <= self.thresholds['ctr']['poor'] or roas <= self.thresholds['roas']['poor']:
                new_budget = current_budget * 0.9  # Уменьшение на 10%
                action = "decrease"
                reason = "Низкий CTR или ROAS"
            elif ctr <= self.thresholds['ctr']['poor'] and roas <= self.thresholds['roas']['poor']:
                new_budget = current_budget * 0.8  # Уменьшение на 20%
                action = "decrease"
                reason = "Низкий CTR и ROAS"
            else:
                # Без изменений
                continue
            
            # Округляем бюджет до целого числа
            new_budget = round(new_budget)
            
            # Если изменение менее 10%, не вносим изменения
            if abs(new_budget - current_budget) / current_budget < 0.1:
                continue
            
            # Применяем изменение бюджета
            try:
                campaign = Campaign(campaign_id)
                
                # Преобразуем бюджет в центы для API
                budget_param = int(new_budget * 100)
                
                params = {}
                if is_daily_budget:
                    params['daily_budget'] = budget_param
                else:
                    params['lifetime_budget'] = budget_param
                
                logger.info(f"Изменение бюджета кампании {campaign_id} "
                           f"с {current_budget} на {new_budget} ({action})")
                
                campaign.api_update(params=params)
                
                # Записываем изменение бюджета
                budget_changes.append({
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_data.get('name', 'Неизвестная кампания'),
                    'old_budget': current_budget,
                    'new_budget': new_budget,
                    'budget_type': 'daily' if is_daily_budget else 'lifetime',
                    'action': action,
                    'reason': reason,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                logger.error(f"Ошибка при изменении бюджета кампании {campaign_id}: {str(e)}")
        
        return budget_changes
    
    def _optimize_bids(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Оптимизация ставок в группах объявлений на основе эффективности.
        
        Args:
            analysis_results: Результаты анализа кампаний
            
        Returns:
            List[Dict[str, Any]]: Список изменений ставок
        """
        bid_changes = []
        
        if not analysis_results or 'adset_performance' not in analysis_results:
            return bid_changes
        
        adsets = analysis_results['adset_performance']['all_adsets']
        
        for adset_data in adsets:
            adset_id = adset_data.get('id')
            if not adset_id:
                continue
            
            # Проверяем достаточно ли данных для принятия решения
            if (adset_data.get('impressions', 0) < self.thresholds['min_data']['impressions'] or
                adset_data.get('spend', 0) < self.thresholds['min_data']['spend']):
                logger.info(f"Недостаточно данных для оптимизации ставок группы {adset_id}")
                continue
            
            # Определяем оптимальную стратегию ставок на основе производительности
            current_bid_strategy = adset_data.get('bid_strategy')
            current_bid_amount = adset_data.get('bid_amount')
            
            # Если у группы уже установлена стратегия LOWEST_COST_WITHOUT_CAP, пропускаем
            if current_bid_strategy == 'LOWEST_COST_WITHOUT_CAP':
                continue
            
            # Анализируем CPC и CTR
            cpc = adset_data.get('cpc', 0)
            ctr = adset_data.get('ctr', 0)
            
            new_bid_strategy = current_bid_strategy
            new_bid_amount = current_bid_amount
            
            # Правила изменения ставок:
            # 1. Если CPC высокий или CTR низкий, меняем на LOWEST_COST_WITHOUT_CAP
            # 2. Если текущая стратегия LOWEST_COST_WITH_BID_CAP и CPC низкий, уменьшаем ставку
            
            action = None
            reason = None
            
            if cpc > self.thresholds['cpc']['poor'] or ctr < self.thresholds['ctr']['poor']:
                # Меняем на стратегию с автоматическими ставками
                if current_bid_strategy != 'LOWEST_COST_WITHOUT_CAP':
                    new_bid_strategy = 'LOWEST_COST_WITHOUT_CAP'
                    new_bid_amount = None
                    action = "change_strategy"
                    reason = f"Высокий CPC ({cpc}) или низкий CTR ({ctr})"
            elif current_bid_strategy == 'LOWEST_COST_WITH_BID_CAP' and current_bid_amount and cpc < self.thresholds['cpc']['excellent']:
                # Уменьшаем ставку, если CPC низкий
                new_bid_amount = int(float(current_bid_amount) * 0.9)  # Уменьшаем на 10%
                action = "decrease_bid"
                reason = f"Низкий CPC ({cpc})"
            
            if not action:
                continue
            
            # Применяем изменение ставок
            try:
                adset = AdSet(adset_id)
                
                params = {'bid_strategy': new_bid_strategy}
                if new_bid_amount:
                    params['bid_amount'] = new_bid_amount
                
                logger.info(f"Изменение стратегии ставок группы {adset_id} "
                           f"с {current_bid_strategy} на {new_bid_strategy}")
                
                adset.api_update(params=params)
                
                # Записываем изменение ставок
                bid_changes.append({
                    'adset_id': adset_id,
                    'adset_name': adset_data.get('name', 'Неизвестная группа'),
                    'old_bid_strategy': current_bid_strategy,
                    'new_bid_strategy': new_bid_strategy,
                    'old_bid_amount': current_bid_amount,
                    'new_bid_amount': new_bid_amount,
                    'action': action,
                    'reason': reason,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                logger.error(f"Ошибка при изменении ставок группы {adset_id}: {str(e)}")
        
        return bid_changes
    
    def _optimize_ad_statuses(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Оптимизация статусов объявлений (пауза неэффективных, запуск эффективных).
        
        Args:
            analysis_results: Результаты анализа кампаний
            
        Returns:
            List[Dict[str, Any]]: Список изменений статусов
        """
        status_changes = []
        
        if not analysis_results or 'ad_performance' not in analysis_results:
            return status_changes
        
        ads = analysis_results['ad_performance'].get('all_ads', [])
        
        for ad_data in ads:
            ad_id = ad_data.get('id')
            if not ad_id:
                continue
            
            # Проверяем достаточно ли данных для принятия решения
            if (ad_data.get('impressions', 0) < self.thresholds['min_data']['impressions'] // 2):
                logger.info(f"Недостаточно данных для оптимизации статуса объявления {ad_id}")
                continue
            
            current_status = ad_data.get('status')
            new_status = current_status
            action = None
            reason = None
            
            # Получаем метрики эффективности
            ctr = ad_data.get('ctr', 0)
            cpc = ad_data.get('cpc', 0)
            
            # Правила изменения статуса:
            # 1. Если объявление активно, но имеет плохие показатели - ставим на паузу
            # 2. Если объявление на паузе, но имеет хорошие показатели - активируем
            
            if current_status == 'ACTIVE' and (ctr < self.thresholds['ctr']['poor'] or cpc > self.thresholds['cpc']['poor']):
                new_status = 'PAUSED'
                action = "pause"
                reason = f"Низкий CTR ({ctr}) или высокий CPC ({cpc})"
            elif current_status == 'PAUSED' and ctr > self.thresholds['ctr']['good'] and cpc < self.thresholds['cpc']['good']:
                new_status = 'ACTIVE'
                action = "activate"
                reason = f"Хороший CTR ({ctr}) и низкий CPC ({cpc})"
            
            if not action or new_status == current_status:
                continue
            
            # Применяем изменение статуса
            try:
                ad = Ad(ad_id)
                
                logger.info(f"{action.capitalize()} объявления {ad_id}")
                
                ad.api_update(params={'status': new_status})
                
                # Записываем изменение статуса
                status_changes.append({
                    'ad_id': ad_id,
                    'ad_name': ad_data.get('name', 'Неизвестное объявление'),
                    'old_status': current_status,
                    'new_status': new_status,
                    'action': action,
                    'reason': reason,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                logger.error(f"Ошибка при изменении статуса объявления {ad_id}: {str(e)}")
        
        return status_changes
    
    def get_optimization_recommendations(self, analysis_results: Optional[Dict[str, Any]] = None, 
                                     days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получение рекомендаций по оптимизации без применения изменений.
        
        Args:
            analysis_results: Результаты анализа (если не предоставлены, будут получены)
            days: Количество дней для анализа (если требуется получить результаты)
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Рекомендации по оптимизации
        """
        logger.info("Формирование рекомендаций по оптимизации кампаний")
        
        # Сохраняем текущие пороги
        original_thresholds = self.thresholds.copy()
        
        # Устанавливаем минимальные данные в 0, чтобы получить больше рекомендаций
        min_data = self.thresholds['min_data'].copy()
        self.thresholds['min_data'] = {'impressions': 0, 'spend': 0}
        
        # Получаем результаты анализа, если не предоставлены
        if not analysis_results:
            analysis_results = self.analyze_account(days)
        
        # Временно заменяем методы, чтобы они только формировали рекомендации
        original_update_budget = Campaign.api_update
        original_update_adset = AdSet.api_update
        original_update_ad = Ad.api_update
        
        # Переопределяем методы, чтобы они не выполняли реальных изменений
        def mock_update(self, params):
            return None
        
        Campaign.api_update = mock_update
        AdSet.api_update = mock_update
        Ad.api_update = mock_update
        
        # Получаем рекомендации по оптимизации
        recommendations = self.optimize_campaigns(analysis_results)
        
        # Восстанавливаем оригинальные методы
        Campaign.api_update = original_update_budget
        AdSet.api_update = original_update_adset
        Ad.api_update = original_update_ad
        
        # Восстанавливаем оригинальные пороги
        self.thresholds = original_thresholds
        
        logger.info(f"Сформированы рекомендации: {len(recommendations['budget_changes'])} по бюджетам, "
                   f"{len(recommendations['bid_changes'])} по ставкам, "
                   f"{len(recommendations['status_changes'])} по статусам")
        
        return recommendations 