"""
Модуль для обработки и анализа данных рекламы.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def calculate_metrics(ad_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Расчет основных метрик на основе рекламных данных.
    
    Args:
        ad_data: Словарь с данными о кампаниях, группах и объявлениях
        
    Returns:
        Dict[str, Any]: Словарь с рассчитанными метриками
    """
    logger.info("Расчет метрик для рекламных данных")
    
    metrics = {}
    
    # Рассчитываем общую статистику
    campaigns = ad_data.get('campaigns', [])
    adsets = ad_data.get('adsets', [])
    ads = ad_data.get('ads', [])
    
    # Количество кампаний, групп и объявлений
    metrics['total_campaigns'] = len(campaigns)
    metrics['total_adsets'] = len(adsets)
    metrics['total_ads'] = len(ads)
    
    # Количество активных кампаний, групп и объявлений
    metrics['active_campaigns'] = sum(1 for c in campaigns if c.get('status') == 'ACTIVE')
    metrics['active_adsets'] = sum(1 for a in adsets if a.get('status') == 'ACTIVE')
    metrics['active_ads'] = sum(1 for a in ads if a.get('status') == 'ACTIVE')
    
    # Общие расходы, показы и клики
    total_spend = 0
    total_impressions = 0
    total_clicks = 0
    
    for campaign in campaigns:
        insights = campaign.get('insights', {})
        try:
            spend = float(insights.get('spend', 0))
            impressions = int(insights.get('impressions', 0))
            clicks = int(insights.get('clicks', 0))
            
            total_spend += spend
            total_impressions += impressions
            total_clicks += clicks
        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка при обработке данных кампании {campaign.get('id', 'unknown')}: {str(e)}")
    
    metrics['total_spend'] = total_spend
    metrics['total_impressions'] = total_impressions
    metrics['total_clicks'] = total_clicks
    
    # Расчет средних показателей
    if total_impressions > 0:
        metrics['avg_ctr'] = (total_clicks / total_impressions) * 100
    else:
        metrics['avg_ctr'] = 0
    
    if total_clicks > 0:
        metrics['avg_cpc'] = total_spend / total_clicks
    else:
        metrics['avg_cpc'] = 0
    
    logger.info(f"Завершен расчет метрик: {len(metrics)} показателей")
    
    return metrics

def format_currency(amount: float, currency_symbol: str = '$') -> str:
    """
    Форматирование числа как денежной суммы.
    
    Args:
        amount: Сумма для форматирования
        currency_symbol: Символ валюты
        
    Returns:
        str: Отформатированная сумма
    """
    if amount is None:
        return f"{currency_symbol}0.00"
    
    if amount == 0:
        return f"{currency_symbol}0.00"
    
    if amount < 0:
        return f"-{currency_symbol}{abs(amount):.2f}"
    
    return f"{currency_symbol}{amount:.2f}"

def format_number(value: Union[float, int], decimal_places: int = 0) -> str:
    """
    Форматирование числового значения с разделением тысяч.
    
    Args:
        value: Значение для форматирования
        decimal_places: Количество десятичных знаков
        
    Returns:
        str: Отформатированная строка
    """
    try:
        if value is None:
            return "0"
        
        # Форматируем число с разделением тысяч
        formatted_value = f"{value:,.{decimal_places}f}".replace(',', ' ')
        
        return formatted_value
    except Exception as e:
        logger.warning(f"Ошибка при форматировании числа: {str(e)}")
        return str(value)

def format_percentage(value: float, decimal_places: int = 2) -> str:
    """
    Форматирование значения как процента.
    
    Args:
        value: Значение для форматирования (от 0 до 1 или уже в процентах)
        decimal_places: Количество десятичных знаков
        
    Returns:
        str: Отформатированная строка
    """
    try:
        if value is None:
            return "0.00%"
        
        # Определяем, нужно ли умножать на 100
        if 0 <= value <= 1:
            value *= 100
        
        # Форматируем число
        formatted_value = f"{value:.{decimal_places}f}"
        
        return f"{formatted_value}%"
    except Exception as e:
        logger.warning(f"Ошибка при форматировании процента: {str(e)}")
        return f"{value}%"

def analyze_performance_trends(data_points: List[Dict[str, Any]], 
                               metric_name: str) -> Dict[str, Any]:
    """
    Анализ тенденций производительности по определенной метрике.
    
    Args:
        data_points: Список словарей с данными по времени
        metric_name: Имя метрики для анализа
        
    Returns:
        Dict[str, Any]: Результаты анализа тенденций
    """
    if not data_points:
        return {'trend': 'no_data', 'change': 0, 'data': []}
    
    # Сортируем точки данных по времени
    sorted_data = sorted(data_points, key=lambda x: x.get('date', ''))
    
    # Извлекаем значения метрики
    values = [point.get(metric_name, 0) for point in sorted_data]
    
    # Если меньше двух точек данных, невозможно определить тренд
    if len(values) < 2:
        return {
            'trend': 'insufficient_data',
            'change': 0,
            'data': sorted_data
        }
    
    # Рассчитываем изменение
    first_value = values[0]
    last_value = values[-1]
    
    if first_value == 0:
        change_percent = 0 if last_value == 0 else 100
    else:
        change_percent = ((last_value - first_value) / first_value) * 100
    
    # Определяем тренд
    if change_percent > 5:
        trend = 'increasing'
    elif change_percent < -5:
        trend = 'decreasing'
    else:
        trend = 'stable'
    
    return {
        'trend': trend,
        'change': change_percent,
        'data': sorted_data
    }

def clean_text(text: str) -> str:
    """
    Очистка и нормализация текста от специальных символов для отчетов.
    
    Args:
        text: Текст для очистки
        
    Returns:
        str: Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем HTML-теги
    clean = re.sub(r'<[^>]+>', '', text)
    
    # Заменяем множественные пробелы и переносы строк
    clean = re.sub(r'\s+', ' ', clean)
    
    # Обрезаем пробелы по краям
    clean = clean.strip()
    
    return clean

def truncate_text(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """
    Обрезка текста до указанной длины с добавлением суффикса.
    
    Args:
        text: Текст для обрезки
        max_length: Максимальная длина текста
        suffix: Суффикс для добавления к обрезанному тексту
        
    Returns:
        str: Обрезанный текст
    """
    if not text:
        return ""
    
    # Очищаем текст
    clean = clean_text(text)
    
    # Если текст короче максимальной длины, возвращаем его как есть
    if len(clean) <= max_length:
        return clean
    
    # Обрезаем текст и добавляем суффикс
    return clean[:max_length - len(suffix)] + suffix

def parse_date_range(days: Optional[int] = None, 
                   start_date: Optional[str] = None, 
                   end_date: Optional[str] = None) -> Dict[str, str]:
    """
    Парсинг и форматирование диапазона дат для запросов к API.
    
    Args:
        days: Количество дней в прошлое от текущей даты
        start_date: Начальная дата в формате YYYY-MM-DD
        end_date: Конечная дата в формате YYYY-MM-DD
        
    Returns:
        Dict[str, str]: Словарь с ключами 'since' и 'until'
    """
    date_format = '%Y-%m-%d'
    
    # Если указаны явные даты начала и конца
    if start_date and end_date:
        try:
            # Парсим даты
            start = datetime.strptime(start_date, date_format)
            end = datetime.strptime(end_date, date_format)
            
            # Проверяем корректность диапазона
            if start > end:
                logger.warning("Начальная дата позже конечной даты, меняем местами")
                start, end = end, start
                
            return {
                'since': start.strftime(date_format),
                'until': end.strftime(date_format)
            }
        except ValueError as e:
            logger.error(f"Ошибка парсинга дат: {str(e)}")
            # Используем значение по умолчанию
    
    # Если указано количество дней в прошлое
    if days is not None:
        end = datetime.now()
        start = end - timedelta(days=days)
        
        return {
            'since': start.strftime(date_format),
            'until': end.strftime(date_format)
        }
    
    # Значение по умолчанию - последние 30 дней
    end = datetime.now()
    start = end - timedelta(days=30)
    
    return {
        'since': start.strftime(date_format),
        'until': end.strftime(date_format)
    }

def safe_json_serialize(obj: Any) -> Any:
    """
    Безопасная сериализация объектов в JSON.
    
    Args:
        obj: Объект для сериализации
        
    Returns:
        Any: Сериализуемый объект
    """
    if isinstance(obj, (datetime, )):
        return obj.isoformat()
    elif hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
    else:
        return str(obj)

def save_to_json(data: Any, file_path: str, pretty: bool = True) -> bool:
    """
    Сохранение данных в JSON-файл.
    
    Args:
        data: Данные для сохранения
        file_path: Путь к файлу
        pretty: Форматировать ли JSON для читаемости
        
    Returns:
        bool: True в случае успеха, False в случае ошибки
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, default=safe_json_serialize, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, default=safe_json_serialize, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в JSON: {str(e)}")
        return False

def load_from_json(file_path: str) -> Optional[Any]:
    """
    Загрузка данных из JSON-файла.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Optional[Any]: Загруженные данные или None в случае ошибки
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из JSON: {str(e)}")
        return None 