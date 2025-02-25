#!/usr/bin/env python
"""
Скрипт для настройки новой структуры проекта Facebook Ads Toolkit.
"""

import os
import sys
import shutil
import json
import subprocess
from datetime import datetime

def create_directory_structure():
    """Создание структуры директорий проекта."""
    print("Создание структуры директорий проекта...")
    
    directories = [
        'facebook_ads_toolkit',
        'facebook_ads_toolkit/auth',
        'facebook_ads_toolkit/analysis',
        'facebook_ads_toolkit/campaign',
        'facebook_ads_toolkit/utils',
        'facebook_ads_toolkit/reports',
        'facebook_ads_toolkit/config',
        'facebook_ads_toolkit/tests',
        'facebook_ads_toolkit/data',
        'facebook_ads_toolkit/cli',
        'logs',
        'reports',
        'backup'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Создана директория: {directory}")
    
    return True

def create_init_files():
    """Создание __init__.py файлов во всех пакетах."""
    print("Создание __init__.py файлов...")
    
    # Список директорий, где нужно создать __init__.py
    package_dirs = [
        'facebook_ads_toolkit',
        'facebook_ads_toolkit/auth',
        'facebook_ads_toolkit/analysis',
        'facebook_ads_toolkit/campaign',
        'facebook_ads_toolkit/utils',
        'facebook_ads_toolkit/reports',
        'facebook_ads_toolkit/config',
        'facebook_ads_toolkit/tests',
        'facebook_ads_toolkit/cli'
    ]
    
    for directory in package_dirs:
        init_file = os.path.join(directory, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(f'"""\n{os.path.basename(directory)} module.\n"""\n')
            print(f"Создан файл: {init_file}")
    
    return True

def copy_old_files():
    """Копирование и архивирование старых файлов."""
    print("Копирование старых файлов в резервную копию...")
    
    # Создаем timestamped директорию для архива
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_dir = os.path.join('backup', f'archive_{timestamp}')
    
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
    
    # Копируем все .py и .json файлы в архив
    py_files = [f for f in os.listdir('.') if f.endswith('.py')]
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]
    md_files = [f for f in os.listdir('.') if f.endswith('.md')]
    env_files = ['.env'] if os.path.exists('.env') else []
    
    all_files = py_files + json_files + md_files + env_files
    
    for file in all_files:
        if os.path.isfile(file):
            shutil.copy2(file, os.path.join(archive_dir, file))
            print(f"Скопирован файл в архив: {file}")
    
    print(f"Все файлы скопированы в {archive_dir}")
    
    # Копируем .env в config директорию
    if os.path.exists('.env'):
        shutil.copy2('.env', os.path.join('facebook_ads_toolkit', 'config', '.env'))
        print("Файл .env скопирован в config директорию")
    
    # Копируем шаблон кампании
    if os.path.exists('campaign_config.json'):
        shutil.copy2('campaign_config.json', 
                    os.path.join('facebook_ads_toolkit', 'config', 'campaign_template.json'))
        print("Шаблон кампании скопирован в config директорию")
    
    return True

def create_main_script():
    """Создание основного скрипта для запуска."""
    print("Создание основного скрипта для запуска...")
    
    script_content = '''#!/usr/bin/env python
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
'''
    
    main_script_path = 'facebook_ads_tool.py'
    
    with open(main_script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Делаем исполняемым на Unix-подобных системах
    if sys.platform != 'win32':
        os.chmod(main_script_path, 0o755)
    
    print(f"Создан основной скрипт: {main_script_path}")
    
    return True

def setup_project():
    """Основная функция настройки проекта."""
    print("Начало настройки проекта Facebook Ads Toolkit...")
    
    # Создаем структуру директорий
    if not create_directory_structure():
        print("Ошибка при создании структуры директорий")
        return 1
    
    # Создаем __init__.py файлы
    if not create_init_files():
        print("Ошибка при создании __init__.py файлов")
        return 1
    
    # Копируем старые файлы
    if not copy_old_files():
        print("Ошибка при копировании старых файлов")
        return 1
    
    # Создаем основной скрипт для запуска
    if not create_main_script():
        print("Ошибка при создании основного скрипта")
        return 1
    
    print("\nНастройка проекта Facebook Ads Toolkit успешно завершена!")
    print("\nДля запуска используйте: python facebook_ads_tool.py [команда] [опции]")
    print("Доступные команды:")
    print("  analyze - Анализ рекламы")
    print("  campaign - Управление кампаниями")
    
    return 0

if __name__ == "__main__":
    sys.exit(setup_project()) 