#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тесты для инкрементального сборщика данных.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from facebook_business.adobjects.adaccount import AdAccount
from facebook_ads_toolkit.core.incremental_collector import (
    IncrementalCollector,
    CollectionError,
    APILimitError,
    NetworkError,
    CollectionStatus
)

class TestIncrementalCollector(unittest.TestCase):
    """Тесты для инкрементального сборщика данных."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        self.mock_account = Mock(spec=AdAccount)
        self.mock_db_manager = Mock()
        self.collector = IncrementalCollector(self.mock_account, self.mock_db_manager)
        
        # Подготовка тестовых данных
        self.test_campaign = {
            'id': '123456789',
            'name': 'Test Campaign',
            'status': 'ACTIVE',
            'objective': 'LINK_CLICKS',
            'daily_budget': '1000',
            'updated_time': datetime.now().isoformat()
        }
        
        self.test_ad_set = {
            'id': '987654321',
            'campaign_id': '123456789',
            'name': 'Test Ad Set',
            'status': 'ACTIVE',
            'daily_budget': '500',
            'updated_time': datetime.now().isoformat()
        }
        
        self.test_ad = {
            'id': '456789123',
            'ad_set_id': '987654321',
            'name': 'Test Ad',
            'status': 'ACTIVE',
            'updated_time': datetime.now().isoformat()
        }
    
    def test_successful_collection_with_checkpoints(self):
        """Тест успешного сбора данных с контрольными точками."""
        # Настройка моков
        self.mock_db_manager.get_last_checkpoint.return_value = None
        self.mock_db_manager.get_last_sync_state.return_value = {
            'last_sync_time': datetime.now() - timedelta(days=1)
        }
        
        # Настройка возвращаемых данных
        mock_campaign = MagicMock()
        mock_campaign.export_all_data.return_value = self.test_campaign
        self.mock_account.get_campaigns.return_value = [mock_campaign]
        
        mock_ad_set = MagicMock()
        mock_ad_set.export_all_data.return_value = self.test_ad_set
        mock_campaign.get_ad_sets.return_value = [mock_ad_set]
        
        mock_ad = MagicMock()
        mock_ad.export_all_data.return_value = self.test_ad
        mock_ad_set.get_ads.return_value = [mock_ad]
        
        # Выполнение сбора данных
        result = self.collector.collect_incremental_data()
        
        # Проверки
        self.assertEqual(len(result['campaigns']), 1)
        self.assertEqual(len(result['ad_sets']), 1)
        self.assertEqual(len(result['ads']), 1)
        
        # Проверка создания контрольных точек
        self.mock_db_manager.save_checkpoint.assert_called()
        
        # Проверка обновления состояния синхронизации
        self.mock_db_manager.update_last_sync.assert_called()
        
        # Проверка статуса
        self.assertEqual(self.collector.progress.status, CollectionStatus.COMPLETED)
    
    def test_collection_with_api_limit_error(self):
        """Тест обработки ошибки превышения лимита API."""
        # Настройка мока для имитации ошибки
        self.mock_account.get_campaigns.side_effect = Exception(
            "User request limit reached"
        )
        
        # Проверка вызова исключения
        with self.assertRaises(APILimitError):
            self.collector.collect_incremental_data()
        
        # Проверка статуса
        self.assertEqual(self.collector.progress.status, CollectionStatus.FAILED)
    
    def test_collection_with_network_error(self):
        """Тест обработки сетевой ошибки."""
        # Настройка мока для имитации ошибки
        self.mock_account.get_campaigns.side_effect = Exception(
            "Network error occurred"
        )
        
        # Проверка вызова исключения
        with self.assertRaises(NetworkError):
            self.collector.collect_incremental_data()
        
        # Проверка статуса
        self.assertEqual(self.collector.progress.status, CollectionStatus.FAILED)
    
    def test_resume_from_checkpoint(self):
        """Тест возобновления сбора с последней контрольной точки."""
        # Настройка мока контрольной точки
        checkpoint = {
            'collection_type': 'campaigns',
            'last_processed_id': '123456789',
            'processed_items': 1,
            'total_items': 2,
            'status': CollectionStatus.INTERRUPTED.value,
            'metadata': json.dumps({
                'since_time': datetime.now().isoformat()
            })
        }
        self.mock_db_manager.get_last_checkpoint.return_value = checkpoint
        
        # Настройка возвращаемых данных
        mock_campaign = MagicMock()
        mock_campaign.export_all_data.return_value = {
            'id': '987654321',  # Новый ID после последней точки
            'name': 'New Campaign',
            'status': 'ACTIVE'
        }
        self.mock_account.get_campaigns.return_value = [mock_campaign]
        
        # Выполнение сбора данных
        result = self.collector.collect_incremental_data()
        
        # Проверка, что обработан только новый элемент
        self.assertEqual(len(result['campaigns']), 1)
        self.assertEqual(result['campaigns'][0]['id'], '987654321')
    
    def test_checkpoint_interval(self):
        """Тест интервала создания контрольных точек."""
        # Создаем много тестовых кампаний
        test_campaigns = []
        for i in range(150):  # Больше чем CHECKPOINT_INTERVAL
            mock_campaign = MagicMock()
            mock_campaign.export_all_data.return_value = {
                'id': str(i),
                'name': f'Campaign {i}',
                'status': 'ACTIVE'
            }
            test_campaigns.append(mock_campaign)
        
        # Настройка возвращаемых данных
        self.mock_account.get_campaigns.return_value = test_campaigns
        self.mock_db_manager.get_last_checkpoint.return_value = None
        
        # Выполнение сбора данных
        self.collector.collect_incremental_data()
        
        # Проверка количества вызовов save_checkpoint
        # Должно быть как минимум 1 вызов на каждые CHECKPOINT_INTERVAL элементов
        expected_calls = len(test_campaigns) // self.collector.CHECKPOINT_INTERVAL
        self.assertGreaterEqual(
            self.mock_db_manager.save_checkpoint.call_count,
            expected_calls
        )
    
    def test_cleanup_old_checkpoints(self):
        """Тест очистки старых контрольных точек."""
        # Выполняем очистку
        self.collector.db_manager.cleanup_old_checkpoints(days_to_keep=7)
        
        # Проверяем вызов метода очистки
        self.mock_db_manager.cleanup_old_checkpoints.assert_called_once_with(
            days_to_keep=7
        )

if __name__ == '__main__':
    unittest.main() 