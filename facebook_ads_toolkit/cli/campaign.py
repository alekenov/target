#!/usr/bin/env python
"""
Командный интерфейс для работы с рекламными кампаниями Facebook.
"""

import argparse
import logging
import sys
import os
import json

# Добавляем родительскую директорию в sys.path, чтобы можно было импортировать модули
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.campaign.campaign_manager import CampaignManager
from facebook_ads_toolkit.utils.logging_utils import setup_logging

def main():
    """Основная функция командного интерфейса для работы с кампаниями."""
    # Настраиваем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Управление рекламными кампаниями Facebook.')
    
    # Добавляем подпарсеры для различных команд
    subparsers = parser.add_subparsers(dest='command', help='Команда')
    
    # Команда создания тестовой кампании
    create_parser = subparsers.add_parser('create', help='Создать тестовую кампанию')
    create_parser.add_argument('--config', type=str, default='campaign_config.json',
                            help='Путь к файлу конфигурации (по умолчанию: campaign_config.json)')
    create_parser.add_argument('--env-path', type=str,
                            help='Путь к файлу .env с параметрами авторизации')
    
    # Команда просмотра кампаний
    list_parser = subparsers.add_parser('list', help='Просмотр списка кампаний')
    list_parser.add_argument('--limit', type=int, default=10,
                            help='Максимальное количество кампаний для отображения (по умолчанию: 10)')
    list_parser.add_argument('--status', type=str, choices=['ACTIVE', 'PAUSED', 'DELETED', 'ALL'], 
                            default='ACTIVE',
                            help='Статус кампаний для отображения (по умолчанию: ACTIVE)')
    list_parser.add_argument('--output', type=str, 
                            help='Путь к файлу для сохранения результатов в JSON')
    list_parser.add_argument('--env-path', type=str,
                            help='Путь к файлу .env с параметрами авторизации')
    
    # Общие параметры
    parser.add_argument('--debug', action='store_true', 
                      help='Включить режим отладки (увеличивает детализацию логов)')
    
    # Разбираем аргументы
    args = parser.parse_args()
    
    # Проверяем, была ли указана команда
    if not args.command:
        parser.print_help()
        return 1
    
    # Настраиваем логирование
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(log_level=log_level, log_dir='logs')
    
    try:
        # Инициализируем авторизацию
        auth = FacebookAuth(args.env_path if hasattr(args, 'env_path') else None)
        account, api = auth.initialize()
        
        if not account or not api:
            logger.error("Не удалось инициализировать авторизацию Facebook")
            return 1
        
        # Инициализируем менеджер кампаний
        campaign_manager = CampaignManager(account, api)
        
        # Обрабатываем команды
        if args.command == 'create':
            # Создание тестовой кампании
            logger.info(f"Создание тестовой кампании из файла {args.config}")
            
            if not os.path.exists(args.config):
                logger.error(f"Файл конфигурации не найден: {args.config}")
                return 1
            
            result = campaign_manager.create_test_campaign(args.config)
            
            # Выводим результаты
            print(f"\nКампания успешно создана!")
            print(f"ID кампании: {result['campaign']['id']}")
            
            print(f"\nСозданные группы объявлений:")
            for i, ad_set in enumerate(result['ad_sets'], 1):
                print(f"{i}. {ad_set.get('name', 'Без имени')} (ID: {ad_set['id']})")
            
            print(f"\nСозданные объявления:")
            for i, ad in enumerate(result['ads'], 1):
                print(f"{i}. {ad.get('name', 'Без имени')} (ID: {ad['id']})")
            
            logger.info("Тестовая кампания успешно создана")
            
        elif args.command == 'list':
            # Просмотр списка кампаний
            logger.info(f"Получение списка кампаний (статус: {args.status}, лимит: {args.limit})")
            
            # Определяем параметры запроса
            params = {
                'limit': args.limit,
                'fields': [
                    'id',
                    'name',
                    'objective',
                    'status',
                    'daily_budget',
                    'lifetime_budget',
                    'created_time',
                    'updated_time',
                    'start_time',
                    'stop_time'
                ]
            }
            
            # Добавляем фильтр по статусу, если нужно
            if args.status != 'ALL':
                params['effective_status'] = [args.status]
            
            # Получаем кампании
            campaigns = account.get_campaigns(params=params)
            
            # Выводим результаты
            print(f"\nСписок кампаний (статус: {args.status}, всего: {len(campaigns)}):")
            print("-" * 80)
            
            # Собираем данные для вывода и сохранения
            campaign_data = []
            
            for i, campaign in enumerate(campaigns, 1):
                # Экспортируем данные кампании
                campaign_info = campaign.export_all_data()
                campaign_data.append(campaign_info)
                
                # Выводим основную информацию
                print(f"{i}. {campaign_info.get('name', 'Без имени')} (ID: {campaign_info['id']})")
                print(f"   Статус: {campaign_info.get('status', 'н/д')}")
                print(f"   Цель: {campaign_info.get('objective', 'н/д')}")
                
                # Выводим информацию о бюджете
                if 'daily_budget' in campaign_info and campaign_info['daily_budget']:
                    print(f"   Дневной бюджет: ${int(campaign_info['daily_budget'])/100:.2f}")
                elif 'lifetime_budget' in campaign_info and campaign_info['lifetime_budget']:
                    print(f"   Бюджет на весь период: ${int(campaign_info['lifetime_budget'])/100:.2f}")
                
                # Выводим информацию о датах
                if 'start_time' in campaign_info and campaign_info['start_time']:
                    print(f"   Дата запуска: {campaign_info['start_time']}")
                
                if 'created_time' in campaign_info and campaign_info['created_time']:
                    print(f"   Дата создания: {campaign_info['created_time']}")
                
                print("-" * 80)
            
            # Сохраняем результаты в файл, если указан параметр --output
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(campaign_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Список кампаний сохранен в файл: {args.output}")
                    print(f"\nСписок кампаний сохранен в файл: {args.output}")
                except Exception as e:
                    logger.error(f"Ошибка при сохранении списка кампаний в файл: {str(e)}")
            
            logger.info(f"Получено {len(campaigns)} кампаний")
        
        return 0
        
    except Exception as e:
        logger.exception(f"Произошла ошибка при выполнении команды: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 