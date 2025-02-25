"""
Модуль с командами CLI для генерации и управления отчетами.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..reports.report_generator import ReportManager
from ..reports.visualization import ChartGenerator
from ..analysis.ad_analyzer import AdAnalyzer
from ..analysis.data_fetchers import AdDataFetcher
from ..auth.facebook_auth import FacebookAuth

logger = logging.getLogger(__name__)

def setup_report_parser(subparsers):
    """
    Настройка парсера команд для работы с отчетами.
    
    Args:
        subparsers: Объект subparsers основного парсера аргументов
    """
    # Создаем парсер для команды report
    report_parser = subparsers.add_parser('report', help='Управление отчетами')
    report_subparsers = report_parser.add_subparsers(dest='report_command', help='Подкоманды управления отчетами')
    
    # Команда generate - генерация отчета
    generate_parser = report_subparsers.add_parser('generate', help='Генерация отчета')
    generate_parser.add_argument('--type', choices=['performance', 'comparison'], default='performance', 
                               help='Тип отчета (performance - производительность, comparison - сравнение)')
    generate_parser.add_argument('--days', type=int, default=30, 
                               help='Количество дней для анализа (по умолчанию 30)')
    generate_parser.add_argument('--format', nargs='+', choices=['json', 'txt', 'csv'], default=['json'], 
                               help='Форматы для экспорта отчета (по умолчанию json)')
    generate_parser.add_argument('--ads', nargs='+', 
                               help='ID объявлений для сравнения (только для типа "comparison")')
    generate_parser.add_argument('--campaigns', nargs='+', 
                               help='ID кампаний для анализа (только для типа "performance")')
    generate_parser.add_argument('--charts', action='store_true', default=False, 
                               help='Создавать графики к отчету')
    generate_parser.add_argument('--filename', 
                               help='Пользовательское имя файла для отчета')
    
    # Команда list - список отчетов
    list_parser = report_subparsers.add_parser('list', help='Список доступных отчетов')
    list_parser.add_argument('--days', type=int, default=30, 
                           help='Отчеты за указанное количество дней (по умолчанию 30)')
    
    # Команда view - просмотр отчета
    view_parser = report_subparsers.add_parser('view', help='Просмотр отчета')
    view_parser.add_argument('report_path', help='Путь к файлу отчета для просмотра')
    
    # Команда export - экспорт отчета в другой формат
    export_parser = report_subparsers.add_parser('export', help='Экспорт отчета в другой формат')
    export_parser.add_argument('report_path', help='Путь к файлу отчета для экспорта')
    export_parser.add_argument('--format', choices=['json', 'txt', 'csv'], required=True, 
                             help='Формат для экспорта')
    export_parser.add_argument('--output', help='Путь для сохранения экспортированного отчета')
    
    # Установка функции-обработчика
    report_parser.set_defaults(func=handle_report_command)

def handle_report_command(args, auth_client=None):
    """
    Обработка команд для работы с отчетами.
    
    Args:
        args: Аргументы командной строки
        auth_client: Клиент авторизации Facebook (опционально)
    """
    # Проверяем наличие подкоманды
    if not hasattr(args, 'report_command') or not args.report_command:
        logger.error("Не указана подкоманда для работы с отчетами")
        return
    
    # Инициализируем менеджер отчетов
    report_manager = ReportManager(output_dir="reports")
    
    # Обрабатываем подкоманды
    if args.report_command == 'generate':
        generate_report(args, auth_client, report_manager)
    elif args.report_command == 'list':
        list_reports(args)
    elif args.report_command == 'view':
        view_report(args)
    elif args.report_command == 'export':
        export_report(args, report_manager)
    else:
        logger.error(f"Неизвестная подкоманда: {args.report_command}")
        
def generate_report(args, auth_client, report_manager):
    """
    Генерация отчета на основе указанных параметров.
    
    Args:
        args: Аргументы командной строки
        auth_client: Клиент авторизации Facebook
        report_manager: Менеджер отчетов
    """
    try:
        # Если клиент авторизации не предоставлен, создаем новый
        if not auth_client:
            auth_client = FacebookAuth.from_env()
        
        # Определяем временной диапазон
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        
        date_format = '%Y-%m-%d'
        time_range = {
            'since': start_date.strftime(date_format),
            'until': end_date.strftime(date_format)
        }
        
        # Создаем средства для получения и анализа данных
        data_fetcher = AdDataFetcher(auth_client)
        ad_analyzer = AdAnalyzer(data_fetcher)
        
        # Формируем данные для отчета в зависимости от типа
        if args.type == 'performance':
            # Получаем данные о производительности кампаний
            campaign_ids = args.campaigns if hasattr(args, 'campaigns') and args.campaigns else None
            
            # Анализируем данные
            analysis_results = ad_analyzer.analyze_campaign_performance(time_range, campaign_ids)
            
            # Генерируем отчет
            template_name = 'campaign_performance'
            
            logger.info(f"Данные для отчета о производительности получены: "
                      f"{len(analysis_results.get('campaign_performance', {}).get('top_campaigns_by_ctr', []))} кампаний")
            
        elif args.type == 'comparison':
            # Проверяем наличие ID объявлений для сравнения
            if not hasattr(args, 'ads') or not args.ads or len(args.ads) < 2:
                logger.error("Для сравнительного отчета необходимо указать минимум два ID объявлений")
                return
            
            # Получаем данные об объявлениях
            ad_ids = args.ads
            
            # Получаем и анализируем данные для каждого объявления
            ads_data = []
            for ad_id in ad_ids:
                ad_data = data_fetcher.fetch_ad_details(ad_id, time_range)
                if ad_data:
                    # Получаем данные о производительности по времени суток и дням недели
                    hourly_data = data_fetcher.fetch_ad_hourly_stats(ad_id, time_range)
                    daily_data = data_fetcher.fetch_ad_daily_stats(ad_id, time_range)
                    
                    # Добавляем эти данные к основным данным объявления
                    ad_data['hourly_performance'] = hourly_data
                    ad_data['daily_performance'] = daily_data
                    
                    ads_data.append(ad_data)
            
            # Формируем данные для отчета
            analysis_results = {
                'time_range': time_range,
                'ads': ads_data
            }
            
            # Генерируем отчет
            template_name = 'ad_comparison'
            
            logger.info(f"Данные для сравнительного отчета получены: {len(ads_data)} объявлений")
        
        else:
            logger.error(f"Неизвестный тип отчета: {args.type}")
            return
        
        # Определяем имя файла для отчета
        custom_filename = args.filename if hasattr(args, 'filename') and args.filename else None
        
        # Генерируем отчет
        formats = args.format if hasattr(args, 'format') and args.format else ['json']
        exported_files = report_manager.generate_report(
            template_name, 
            analysis_results,
            export_formats=formats,
            custom_filename=custom_filename
        )
        
        # Выводим информацию о созданных файлах
        print("Отчет успешно сгенерирован:")
        for format_name, file_path in exported_files.items():
            print(f" - {format_name}: {file_path}")
        
        # Если нужно создать графики
        if hasattr(args, 'charts') and args.charts:
            # Создаем генератор графиков
            chart_generator = ChartGenerator(output_dir="reports")
            
            # Генерируем графики
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_id = custom_filename if custom_filename else f"{args.type}_report_{timestamp}"
            
            charts = chart_generator.generate_all_charts(analysis_results, report_id)
            
            # Выводим информацию о созданных графиках
            if charts:
                print("\nСозданы графики:")
                for chart_name, chart_path in charts.items():
                    print(f" - {chart_name}: {chart_path}")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {str(e)}")
        raise

def list_reports(args):
    """
    Вывод списка доступных отчетов.
    
    Args:
        args: Аргументы командной строки
    """
    try:
        # Определяем период для поиска отчетов
        days = args.days if hasattr(args, 'days') and args.days else 30
        date_threshold = datetime.now() - timedelta(days=days)
        
        # Проверяем наличие директории с отчетами
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            print(f"Директория с отчетами ({reports_dir}) не найдена")
            return
        
        # Получаем список файлов в директории
        report_files = []
        for filename in os.listdir(reports_dir):
            file_path = os.path.join(reports_dir, filename)
            
            # Проверяем, что это файл и он имеет подходящее расширение
            if os.path.isfile(file_path) and filename.endswith(('.json', '.txt', '.csv')):
                # Получаем время создания файла
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                
                # Проверяем, что файл создан в указанный период
                if file_time >= date_threshold:
                    # Определяем тип отчета по имени файла
                    report_type = "Неизвестный"
                    if "performance" in filename:
                        report_type = "Производительность кампаний"
                    elif "comparison" in filename:
                        report_type = "Сравнение объявлений"
                    elif "campaign" in filename:
                        report_type = "Кампании"
                    elif "ad" in filename:
                        report_type = "Объявления"
                    
                    # Добавляем информацию о файле
                    report_files.append({
                        'filename': filename,
                        'path': file_path,
                        'type': report_type,
                        'size': os.path.getsize(file_path),
                        'created': file_time
                    })
        
        # Сортируем файлы по времени создания (от новых к старым)
        report_files.sort(key=lambda x: x['created'], reverse=True)
        
        # Выводим список отчетов
        if not report_files:
            print(f"Не найдено отчетов за последние {days} дней")
            return
        
        print(f"Список отчетов за последние {days} дней:")
        print("-" * 100)
        print(f"{'Имя файла':<50} {'Тип':<25} {'Размер':<10} {'Дата создания':<20}")
        print("-" * 100)
        
        for report in report_files:
            # Форматируем размер файла
            size_str = f"{report['size'] / 1024:.1f} КБ"
            
            # Форматируем время создания
            created_str = report['created'].strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"{report['filename']:<50} {report['type']:<25} {size_str:<10} {created_str:<20}")
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка отчетов: {str(e)}")
        raise

def view_report(args):
    """
    Просмотр отчета.
    
    Args:
        args: Аргументы командной строки
    """
    try:
        # Получаем путь к файлу отчета
        report_path = args.report_path
        
        # Проверяем существование файла
        if not os.path.exists(report_path):
            print(f"Файл отчета не найден: {report_path}")
            return
        
        # Определяем формат файла по расширению
        file_ext = os.path.splitext(report_path)[1].lower()
        
        if file_ext == '.json':
            # Читаем JSON-файл
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # Выводим основную информацию из отчета
            print("\n" + "=" * 80)
            if 'title' in report_data:
                print(f"ОТЧЕТ: {report_data['title']}")
            else:
                print(f"ОТЧЕТ: {os.path.basename(report_path)}")
            print("=" * 80)
            
            if 'description' in report_data:
                print(f"\n{report_data['description']}")
            
            if 'generated_at' in report_data:
                try:
                    gen_time = datetime.fromisoformat(report_data['generated_at'])
                    print(f"\nДата генерации: {gen_time.strftime('%Y-%m-%d %H:%M:%S')}")
                except ValueError:
                    print(f"\nДата генерации: {report_data['generated_at']}")
            
            if 'time_range' in report_data:
                time_range = report_data['time_range']
                print(f"Период анализа: {time_range.get('since', 'н/д')} - {time_range.get('until', 'н/д')}")
            
            # Выводим секции отчета
            if 'sections' in report_data:
                sections = report_data['sections']
                print("\n" + "-" * 80)
                
                for section_title, section_content in sections.items():
                    print(f"\n== {section_title} ==\n")
                    
                    # Различная обработка в зависимости от типа содержимого
                    if isinstance(section_content, dict):
                        # Для словарей выводим ключи и значения
                        for key, value in section_content.items():
                            if isinstance(value, dict):
                                print(f"{key}:")
                                for k, v in value.items():
                                    print(f"  {k}: {v}")
                            elif isinstance(value, list):
                                print(f"{key}: {len(value)} элементов")
                                if len(value) > 0 and isinstance(value[0], dict) and 'name' in value[0]:
                                    for i, item in enumerate(value[:3], 1):  # Показываем только первые 3
                                        print(f"  {i}. {item.get('name', f'Элемент {i}')}")
                                    if len(value) > 3:
                                        print(f"  ...и еще {len(value) - 3}")
                            else:
                                print(f"{key}: {value}")
                            
                    elif isinstance(section_content, list):
                        # Для списков выводим элементы
                        for i, item in enumerate(section_content, 1):
                            if isinstance(item, str):
                                print(f"{i}. {item}")
                            elif isinstance(item, dict):
                                print(f"{i}. {item.get('name', f'Элемент {i}')}")
                                
                    else:
                        # Для других типов просто выводим значение
                        print(section_content)
            
            print("\n" + "=" * 80)
                    
        elif file_ext == '.txt':
            # Читаем и выводим содержимое текстового файла
            with open(report_path, 'r', encoding='utf-8') as f:
                print(f.read())
                
        elif file_ext == '.csv':
            # Читаем и выводим содержимое CSV-файла
            import csv
            with open(report_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    print(','.join(row))
        
        else:
            print(f"Неподдерживаемый формат файла: {file_ext}")
            
    except Exception as e:
        logger.error(f"Ошибка при просмотре отчета: {str(e)}")
        raise

def export_report(args, report_manager):
    """
    Экспорт отчета в другой формат.
    
    Args:
        args: Аргументы командной строки
        report_manager: Менеджер отчетов
    """
    try:
        # Получаем параметры
        report_path = args.report_path
        export_format = args.format
        output_path = args.output if hasattr(args, 'output') and args.output else None
        
        # Проверяем существование файла
        if not os.path.exists(report_path):
            print(f"Файл отчета не найден: {report_path}")
            return
        
        # Определяем формат исходного файла по расширению
        src_ext = os.path.splitext(report_path)[1].lower()
        
        # Пока поддерживаем только преобразование из JSON
        if src_ext != '.json':
            print(f"Экспорт поддерживается только для отчетов в формате JSON")
            return
        
        # Читаем данные отчета
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # Определяем имя выходного файла
        if not output_path:
            base_name = os.path.splitext(report_path)[0]
            output_path = f"{base_name}.{export_format}"
        
        # Выбираем класс экспортера
        export_format_obj = report_manager.export_formats.get(export_format)
        if not export_format_obj:
            print(f"Формат экспорта '{export_format}' не поддерживается")
            return
        
        # Экспортируем отчет
        exported_file = export_format_obj.export(report_data, output_path)
        
        if exported_file:
            print(f"Отчет успешно экспортирован в формат {export_format}: {exported_file}")
        else:
            print(f"Ошибка при экспорте отчета в формат {export_format}")
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте отчета: {str(e)}")
        raise 