#!/usr/bin/env python
"""
Основной скрипт для запуска функций Facebook Ads Toolkit.
"""

import os
import sys
import argparse

from facebook_ads_toolkit.cli.analyze import main as analyze_main
from facebook_ads_toolkit.cli.campaign import main as campaign_main

def main():
    """Основная функция для запуска."""
    parser = argparse.ArgumentParser(description='Facebook Ads Toolkit')
    
    # Создаем подпарсеры для различных команд
    subparsers = parser.add_subparsers(dest='command', help='Команда')
    
    # Команда анализа
    analyze_parser = subparsers.add_parser('analyze', help='Анализ рекламы')
    analyze_parser.add_argument('--days', type=int, default=30,
                             help='Количество дней для анализа (по умолчанию: 30)')
    analyze_parser.add_argument('--start-date', type=str,
                             help='Начальная дата анализа (YYYY-MM-DD)')
    analyze_parser.add_argument('--end-date', type=str,
                             help='Конечная дата анализа (YYYY-MM-DD)')
    analyze_parser.add_argument('--output-dir', type=str, default='reports',
                             help='Директория для сохранения отчетов (по умолчанию: "reports")')
    analyze_parser.add_argument('--debug', action='store_true',
                             help='Включить режим отладки')
    
    # Команда управления кампаниями
    campaign_parser = subparsers.add_parser('campaign', help='Управление кампаниями')
    
    # Подкоманды для campaign
    campaign_subparsers = campaign_parser.add_subparsers(dest='subcommand')
    
    # Подкоманда create
    create_parser = campaign_subparsers.add_parser('create', help='Создать тестовую кампанию')
    create_parser.add_argument('--config', type=str, 
                            default='facebook_ads_toolkit/config/campaign_template.json',
                            help='Путь к файлу конфигурации')
    create_parser.add_argument('--debug', action='store_true',
                            help='Включить режим отладки')
    
    # Подкоманда list
    list_parser = campaign_subparsers.add_parser('list', help='Просмотр списка кампаний')
    list_parser.add_argument('--limit', type=int, default=10,
                          help='Максимальное количество кампаний для отображения')
    list_parser.add_argument('--status', type=str, 
                          choices=['ACTIVE', 'PAUSED', 'DELETED', 'ALL'],
                          default='ACTIVE',
                          help='Статус кампаний для отображения')
    list_parser.add_argument('--output', type=str,
                          help='Путь к файлу для сохранения результатов в JSON')
    list_parser.add_argument('--debug', action='store_true',
                          help='Включить режим отладки')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Обрабатываем команды
    if args.command == 'analyze':
        # Формируем аргументы для анализа
        sys.argv = [sys.argv[0]]
        
        if args.days:
            sys.argv.extend(['--days', str(args.days)])
        
        if args.start_date and args.end_date:
            sys.argv.extend(['--start-date', args.start_date, '--end-date', args.end_date])
        
        if args.output_dir:
            sys.argv.extend(['--output-dir', args.output_dir])
        
        if args.debug:
            sys.argv.append('--debug')
        
        # Запускаем анализ
        return analyze_main()
    
    elif args.command == 'campaign':
        if not args.subcommand:
            campaign_parser.print_help()
            return 1
        
        # Формируем аргументы для campaign
        sys.argv = [sys.argv[0]]
        
        if args.subcommand == 'create':
            sys.argv.append('create')
            
            if hasattr(args, 'config'):
                sys.argv.extend(['--config', args.config])
            
            if hasattr(args, 'debug') and args.debug:
                sys.argv.append('--debug')
                
        elif args.subcommand == 'list':
            sys.argv.append('list')
            
            if hasattr(args, 'limit'):
                sys.argv.extend(['--limit', str(args.limit)])
            
            if hasattr(args, 'status'):
                sys.argv.extend(['--status', args.status])
            
            if hasattr(args, 'output') and args.output:
                sys.argv.extend(['--output', args.output])
            
            if hasattr(args, 'debug') and args.debug:
                sys.argv.append('--debug')
        
        # Запускаем управление кампаниями
        return campaign_main()

if __name__ == "__main__":
    sys.exit(main())
