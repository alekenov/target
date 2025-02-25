#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для интеграции с Telegram API.
Позволяет отправлять сообщения, файлы и разделять большие сообщения.
"""

import os
import json
import logging
import requests
import csv
import tempfile
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

# Настройка логирования
logger = logging.getLogger(__name__)

# Максимальная длина сообщения в Telegram
MAX_MESSAGE_LENGTH = 4096

def send_telegram_message(chat_id: Union[str, int], text: str, parse_mode: str = "Markdown", 
                         disable_web_page_preview: bool = True) -> requests.Response:
    """
    Отправляет сообщение в Telegram.
    
    Args:
        chat_id (Union[str, int]): ID чата или канала.
        text (str): Текст сообщения.
        parse_mode (str): Режим форматирования (Markdown, HTML).
        disable_web_page_preview (bool): Отключить предпросмотр ссылок.
        
    Returns:
        requests.Response: Ответ от API Telegram.
    """
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("Токен Telegram бота не найден в переменных окружения")
        raise ValueError("Токен Telegram бота не найден в переменных окружения")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Проверяем длину сообщения
    if len(text) <= MAX_MESSAGE_LENGTH:
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code != 200:
                logger.error(f"Ошибка при отправке сообщения: {response.text}")
            return response
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {str(e)}")
            raise
    else:
        # Если сообщение слишком длинное, разделяем его
        return send_long_message(chat_id, text, parse_mode, disable_web_page_preview)

def send_long_message(chat_id: Union[str, int], text: str, parse_mode: str = "Markdown",
                     disable_web_page_preview: bool = True) -> requests.Response:
    """
    Разделяет длинное сообщение на части и отправляет их последовательно.
    
    Args:
        chat_id (Union[str, int]): ID чата или канала.
        text (str): Текст сообщения.
        parse_mode (str): Режим форматирования (Markdown, HTML).
        disable_web_page_preview (bool): Отключить предпросмотр ссылок.
        
    Returns:
        requests.Response: Ответ от API Telegram для последнего сообщения.
    """
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("Токен Telegram бота не найден в переменных окружения")
        raise ValueError("Токен Telegram бота не найден в переменных окружения")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Разделяем сообщение на части
    parts = []
    current_part = ""
    
    # Разделяем по строкам для сохранения целостности форматирования
    lines = text.split('\n')
    
    for line in lines:
        # Если текущая часть + новая строка не превышают лимит
        if len(current_part + line + '\n') <= MAX_MESSAGE_LENGTH:
            current_part += line + '\n'
        else:
            # Если текущая часть не пуста, добавляем её в список частей
            if current_part:
                parts.append(current_part)
            
            # Если строка сама по себе превышает лимит, разбиваем её
            if len(line) > MAX_MESSAGE_LENGTH:
                # Разбиваем длинную строку на части
                for i in range(0, len(line), MAX_MESSAGE_LENGTH - 1):
                    chunk = line[i:i + MAX_MESSAGE_LENGTH - 1]
                    parts.append(chunk)
                current_part = ""
            else:
                # Иначе начинаем новую часть с текущей строки
                current_part = line + '\n'
    
    # Добавляем последнюю часть, если она не пуста
    if current_part:
        parts.append(current_part)
    
    # Отправляем каждую часть
    last_response = None
    for i, part in enumerate(parts):
        # Добавляем нумерацию частей, если их больше одной
        if len(parts) > 1:
            header = f"*Часть {i+1}/{len(parts)}*\n\n" if parse_mode == "Markdown" else f"<b>Часть {i+1}/{len(parts)}</b>\n\n"
            part = header + part
        
        data = {
            'chat_id': chat_id,
            'text': part,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview
        }
        
        try:
            response = requests.post(url, data=data)
            last_response = response
            
            if response.status_code != 200:
                logger.error(f"Ошибка при отправке части {i+1}/{len(parts)}: {response.text}")
            else:
                logger.info(f"Часть {i+1}/{len(parts)} успешно отправлена")
        except Exception as e:
            logger.error(f"Ошибка при отправке части {i+1}/{len(parts)}: {str(e)}")
    
    return last_response

def send_file(chat_id: Union[str, int], file_path: str, caption: str = None, 
             parse_mode: str = "Markdown") -> requests.Response:
    """
    Отправляет файл в Telegram.
    
    Args:
        chat_id (Union[str, int]): ID чата или канала.
        file_path (str): Путь к файлу.
        caption (str, optional): Подпись к файлу.
        parse_mode (str): Режим форматирования подписи (Markdown, HTML).
        
    Returns:
        requests.Response: Ответ от API Telegram.
    """
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("Токен Telegram бота не найден в переменных окружения")
        raise ValueError("Токен Telegram бота не найден в переменных окружения")
    
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    
    # Ограничиваем длину подписи
    if caption and len(caption) > 1024:
        caption = caption[:1021] + "..."
    
    data = {
        'chat_id': chat_id,
        'parse_mode': parse_mode
    }
    
    if caption:
        data['caption'] = caption
    
    try:
        with open(file_path, 'rb') as file:
            files = {'document': file}
            response = requests.post(url, data=data, files=files)
            
            if response.status_code != 200:
                logger.error(f"Ошибка при отправке файла: {response.text}")
            else:
                logger.info(f"Файл {file_path} успешно отправлен")
                
            return response
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {str(e)}")
        raise

def export_to_json(data: Union[Dict, List], file_path: str = None) -> str:
    """
    Экспортирует данные в JSON файл.
    
    Args:
        data (Union[Dict, List]): Данные для экспорта.
        file_path (str, optional): Путь для сохранения файла. 
            Если не указан, создается временный файл.
            
    Returns:
        str: Путь к созданному файлу.
    """
    if file_path is None:
        # Создаем временный файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(tempfile.gettempdir(), f"report_{timestamp}.json")
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Данные успешно экспортированы в JSON: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Ошибка при экспорте в JSON: {str(e)}")
        raise

def export_to_csv(data: List[Dict], file_path: str = None, headers: List[str] = None) -> str:
    """
    Экспортирует данные в CSV файл.
    
    Args:
        data (List[Dict]): Данные для экспорта.
        file_path (str, optional): Путь для сохранения файла.
            Если не указан, создается временный файл.
        headers (List[str], optional): Список заголовков столбцов.
            Если не указан, используются ключи из первого элемента данных.
            
    Returns:
        str: Путь к созданному файлу.
    """
    if not data:
        logger.warning("Нет данных для экспорта в CSV")
        return None
    
    if file_path is None:
        # Создаем временный файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(tempfile.gettempdir(), f"report_{timestamp}.csv")
    
    try:
        # Определяем заголовки, если не указаны
        if headers is None:
            headers = list(data[0].keys())
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for row in data:
                # Фильтруем данные, оставляя только поля из заголовков
                filtered_row = {k: v for k, v in row.items() if k in headers}
                writer.writerow(filtered_row)
                
        logger.info(f"Данные успешно экспортированы в CSV: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Ошибка при экспорте в CSV: {str(e)}")
        raise

def send_report_as_file(chat_id: Union[str, int], data: Union[Dict, List], 
                       format: str = "json", caption: str = None, 
                       headers: List[str] = None) -> requests.Response:
    """
    Экспортирует данные в файл и отправляет его в Telegram.
    
    Args:
        chat_id (Union[str, int]): ID чата или канала.
        data (Union[Dict, List]): Данные для экспорта.
        format (str): Формат файла (json или csv).
        caption (str, optional): Подпись к файлу.
        headers (List[str], optional): Список заголовков для CSV.
        
    Returns:
        requests.Response: Ответ от API Telegram.
    """
    try:
        # Экспортируем данные в файл
        if format.lower() == "json":
            file_path = export_to_json(data)
        elif format.lower() == "csv":
            if not isinstance(data, list):
                logger.error("Для экспорта в CSV данные должны быть списком словарей")
                raise ValueError("Для экспорта в CSV данные должны быть списком словарей")
            file_path = export_to_csv(data, headers=headers)
        else:
            logger.error(f"Неподдерживаемый формат файла: {format}")
            raise ValueError(f"Неподдерживаемый формат файла: {format}")
        
        # Отправляем файл
        response = send_file(chat_id, file_path, caption)
        
        # Удаляем временный файл
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл {file_path}: {str(e)}")
        
        return response
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета как файла: {str(e)}")
        raise 