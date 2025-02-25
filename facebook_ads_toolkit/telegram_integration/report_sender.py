#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для форматирования и отправки отчетов в Telegram.

Этот модуль содержит функции для создания и отправки различных типов отчетов
о рекламных кампаниях Facebook в Telegram.
"""

import os
import logging
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from telegram import Bot
from telegram.error import TelegramError

from facebook_ads_toolkit.telegram_integration.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_LOG_CHANNEL_ID,
    MESSAGE_TEMPLATES,
    REPORT_SETTINGS
)
from facebook_ads_toolkit.reports.report_generator import get_campaign_data, get_campaigns_list

# Настройка логирования
logger = logging.getLogger(__name__)

class ReportSender:
    """
    Класс для форматирования и отправки отчетов в Telegram.
    """
    
    def __init__(self):
        """
        Инициализация отправителя отчетов.
        """
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("Инициализирован отправитель отчетов в Telegram")
    
    def _format_report(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Форматирование отчета по шаблону.
        
        Args:
            template_name (str): Имя шаблона.
            data (dict): Данные для подстановки в шаблон.
            
        Returns:
            str: Отформатированный текст отчета.
        """
        template = MESSAGE_TEMPLATES.get(template_name, '')
        
        if not template:
            # Если шаблон не найден, создаем базовый отчет
            return self._create_basic_report(data)
        
        try:
            return template.format(**data)
        except KeyError as e:
            logger.error(f"Ошибка форматирования отчета: отсутствует ключ {e}")
            return self._create_basic_report(data)
    
    def _create_basic_report(self, data: Dict[str, Any]) -> str:
        """
        Создание базового отчета без шаблона.
        
        Args:
            data (dict): Данные для отчета.
            
        Returns:
            str: Текст базового отчета.
        """
        report = f"📊 *Отчет по рекламе Facebook*\n📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
        
        # Добавляем доступные данные
        for key, value in data.items():
            if isinstance(value, (int, float, str)):
                report += f"*{key}*: {value}\n"
        
        return report
    
    def _generate_chart(self, data: List[Dict[str, Any]], 
                        metric: str = 'ctr', 
                        title: str = 'Динамика показателей') -> Optional[BytesIO]:
        """
        Генерация графика на основе данных.
        
        Args:
            data (list): Список словарей с данными.
            metric (str): Метрика для отображения (ctr, cpc, conversions).
            title (str): Заголовок графика.
            
        Returns:
            BytesIO: Объект с изображением графика или None в случае ошибки.
        """
        if not data:
            logger.warning("Нет данных для создания графика")
            return None
        
        try:
            # Создаем DataFrame из данных
            df = pd.DataFrame(data)
            
            if 'date' not in df.columns or metric not in df.columns:
                logger.warning(f"Отсутствуют необходимые колонки для графика: date или {metric}")
                return None
            
            # Преобразуем даты и сортируем
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Создаем график
            plt.figure(figsize=(10, 6))
            plt.plot(df['date'], df[metric], marker='o', linestyle='-', linewidth=2)
            plt.title(title)
            plt.xlabel('Дата')
            plt.ylabel(metric.upper())
            plt.grid(True)
            plt.tight_layout()
            
            # Сохраняем график в буфер
            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            return buf
        
        except Exception as e:
            logger.error(f"Ошибка при создании графика: {e}")
            return None
    
    def _format_campaign_list(self, campaigns: List[Dict[str, Any]]) -> str:
        """
        Форматирование списка кампаний для отображения в сообщении.
        
        Args:
            campaigns (list): Список словарей с данными о кампаниях.
            
        Returns:
            str: Отформатированный текст со списком кампаний.
        """
        if not campaigns:
            return "Активные кампании не найдены."
        
        result = ""
        for i, campaign in enumerate(campaigns, 1):
            status_emoji = "🟢" if campaign.get('status') == 'ACTIVE' else "🔴"
            result += (
                f"{i}. {status_emoji} *{campaign.get('name', 'Без имени')}*\n"
                f"   ID: `{campaign.get('id', 'Неизвестный ID')}`\n"
                f"   Бюджет: ${campaign.get('budget', 0):.2f}\n"
                f"   Статус: {campaign.get('status', 'Неизвестно')}\n\n"
            )
        
        return result
    
    async def send_message(self, chat_id: Union[str, int], text: str, parse_mode: str = 'Markdown') -> bool:
        """
        Отправка текстового сообщения в Telegram.
        
        Args:
            chat_id (str|int): ID чата для отправки.
            text (str): Текст сообщения.
            parse_mode (str, optional): Режим форматирования текста. По умолчанию 'Markdown'.
            
        Returns:
            bool: True в случае успеха, False в случае ошибки.
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            return False
    
    async def send_photo(self, chat_id: Union[str, int], 
                         photo_path: Union[str, BytesIO], 
                         caption: Optional[str] = None) -> bool:
        """
        Отправка изображения в Telegram.
        
        Args:
            chat_id (str|int): ID чата для отправки.
            photo_path (str|BytesIO): Путь к файлу или объект BytesIO с изображением.
            caption (str, optional): Подпись к изображению.
            
        Returns:
            bool: True в случае успеха, False в случае ошибки.
        """
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo_path,
                caption=caption,
                parse_mode='Markdown' if caption else None
            )
            return True
        except TelegramError as e:
            logger.error(f"Ошибка при отправке изображения: {e}")
            return False
    
    async def send_document(self, chat_id: Union[str, int], 
                           document_path: Union[str, BytesIO], 
                           caption: Optional[str] = None,
                           filename: Optional[str] = None) -> bool:
        """
        Отправка документа в Telegram.
        
        Args:
            chat_id (str|int): ID чата для отправки.
            document_path (str|BytesIO): Путь к файлу или объект BytesIO с документом.
            caption (str, optional): Подпись к документу.
            filename (str, optional): Имя файла.
            
        Returns:
            bool: True в случае успеха, False в случае ошибки.
        """
        try:
            await self.bot.send_document(
                chat_id=chat_id,
                document=document_path,
                caption=caption,
                filename=filename,
                parse_mode='Markdown' if caption else None
            )
            return True
        except TelegramError as e:
            logger.error(f"Ошибка при отправке документа: {e}")
            return False
    
    async def send_campaign_list(self, chat_id: Union[str, int]) -> bool:
        """
        Отправка списка активных кампаний.
        
        Args:
            chat_id (str|int): ID чата для отправки.
            
        Returns:
            bool: True в случае успеха, False в случае ошибки.
        """
        try:
            # Получаем список кампаний
            campaigns = get_campaigns_list(status='ACTIVE')
            
            if not campaigns:
                await self.send_message(
                    chat_id=chat_id,
                    text="❌ Активные кампании не найдены."
                )
                return True
            
            # Форматируем данные для шаблона
            data = {
                'date': datetime.now().strftime('%d.%m.%Y'),
                'campaigns_list': self._format_campaign_list(campaigns)
            }
            
            # Форматируем сообщение
            message = self._format_report('campaign_list', data)
            
            # Отправляем сообщение
            return await self.send_message(chat_id=chat_id, text=message)
        
        except Exception as e:
            logger.error(f"Ошибка при отправке списка кампаний: {e}")
            await self.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при получении списка кампаний. Пожалуйста, попробуйте позже."
            )
            return False
    
    async def send_daily_report(self, chat_id: Union[str, int]) -> bool:
        """
        Отправка ежедневного отчета о производительности кампаний.
        
        Args:
            chat_id (Union[str, int]): ID чата для отправки отчета.
            
        Returns:
            bool: True, если отчет успешно отправлен, иначе False.
        """
        try:
            # Получаем данные о кампаниях за последние 24 часа
            logger.info("Получение данных для ежедневного отчета")
            yesterday = datetime.now() - timedelta(days=1)
            date_range = f"{yesterday.strftime('%d.%m.%Y')} - {datetime.now().strftime('%d.%m.%Y')}"
            
            # Получаем данные о кампаниях
            campaigns = get_campaign_data(
                campaign_id=None,
                days=1,
                status='ACTIVE',
                date_preset='yesterday',
                fields=['impressions', 'clicks', 'spend', 'conversions']
            )
            
            if not campaigns:
                logger.warning("Нет данных о кампаниях для ежедневного отчета")
                await self.send_message(
                    chat_id=chat_id,
                    text=MESSAGE_TEMPLATES.get('report.daily.no_campaigns', 'За указанный период нет данных по кампаниям.')
                )
                return True
            
            # Рассчитываем общие метрики
            total_impressions = sum(c.get('metrics', {}).get('impressions', 0) for c in campaigns)
            total_clicks = sum(c.get('metrics', {}).get('clicks', 0) for c in campaigns)
            total_spend = sum(c.get('metrics', {}).get('spend', 0) for c in campaigns)
            total_conversions = sum(c.get('metrics', {}).get('conversions', 0) for c in campaigns)
            
            # Рассчитываем производные метрики
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            cpc = total_spend / total_clicks if total_clicks > 0 else 0
            cost_per_conversion = total_spend / total_conversions if total_conversions > 0 else 0
            
            # Сортируем кампании по CTR для выделения лучших
            for campaign in campaigns:
                metrics = campaign.get('metrics', {})
                impressions = metrics.get('impressions', 0)
                clicks = metrics.get('clicks', 0)
                campaign['ctr'] = (clicks / impressions * 100) if impressions > 0 else 0
            
            # Сортируем по CTR (от большего к меньшему)
            sorted_campaigns = sorted(campaigns, key=lambda x: x.get('ctr', 0), reverse=True)
            top_campaigns = sorted_campaigns[:3]  # Берем топ-3 кампании
            
            # Формируем заголовок отчета
            header = MESSAGE_TEMPLATES.get('report.daily.header', '').format(
                date_range=date_range,
                impressions=total_impressions,
                clicks=total_clicks,
                ctr=ctr,
                cpc=cpc,
                total_spend=total_spend,
                conversions=total_conversions,
                cost_per_conversion=cost_per_conversion
            )
            
            # Формируем список лучших кампаний
            campaigns_text = ""
            for i, campaign in enumerate(top_campaigns, 1):
                metrics = campaign.get('metrics', {})
                campaign_text = MESSAGE_TEMPLATES.get('report.daily.campaign_item', '').format(
                    index=i,
                    name=campaign.get('name', 'Без имени'),
                    impressions=metrics.get('impressions', 0),
                    clicks=metrics.get('clicks', 0),
                    ctr=campaign.get('ctr', 0),
                    spend=metrics.get('spend', 0)
                )
                campaigns_text += campaign_text + "\n"
            
            # Формируем рекомендации
            recommendations = []
            recommendations_header = MESSAGE_TEMPLATES.get('report.daily.recommendations.header', '')
            
            # Проверяем различные условия для рекомендаций
            if cpc > 2.0:  # Высокий CPC
                recommendations.append(MESSAGE_TEMPLATES.get('report.daily.recommendations.high_cpc', '').format(cpc=cpc))
            
            if ctr < 1.0:  # Низкий CTR
                recommendations.append(MESSAGE_TEMPLATES.get('report.daily.recommendations.low_ctr', '').format(ctr=ctr))
            
            # Проверяем бюджеты кампаний
            for campaign in campaigns:
                budget = campaign.get('budget', 0)
                spend = campaign.get('metrics', {}).get('spend', 0)
                remaining_budget = budget - spend
                
                if remaining_budget < budget * 0.2:  # Осталось менее 20% бюджета
                    recommendations.append(
                        MESSAGE_TEMPLATES.get('report.daily.recommendations.budget_limit', '').format(
                            remaining_budget=remaining_budget
                        )
                    )
                    break  # Достаточно одного предупреждения о бюджете
            
            if not recommendations and ctr > 2.0:  # Хорошая производительность
                recommendations.append(MESSAGE_TEMPLATES.get('report.daily.recommendations.good_performance', ''))
            
            # Собираем рекомендации в текст
            recommendations_text = ""
            if recommendations:
                recommendations_text = recommendations_header + "\n".join(recommendations)
            
            # Формируем полный текст отчета
            report_text = header + "\n" + campaigns_text + recommendations_text
            
            # Отправляем отчет
            logger.info("Отправка ежедневного отчета")
            return await self.send_message(chat_id=chat_id, text=report_text)
            
        except Exception as e:
            logger.error(f"Ошибка при отправке ежедневного отчета: {e}")
            await self.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при формировании ежедневного отчета. Пожалуйста, попробуйте позже."
            )
            return False
    
    def _generate_recommendations(self, ctr: float, cpc: float, 
                                 cost_per_conversion: float, 
                                 campaigns: List[Dict[str, Any]]) -> str:
        """
        Генерация рекомендаций на основе метрик.
        
        Args:
            ctr (float): Общий CTR.
            cpc (float): Общий CPC.
            cost_per_conversion (float): Общая стоимость конверсии.
            campaigns (list): Список словарей с данными о кампаниях.
            
        Returns:
            str: Текст с рекомендациями.
        """
        recommendations = []
        
        # Проверяем CTR
        if ctr < 1.0:
            recommendations.append("• Низкий CTR. Рекомендуется пересмотреть креативы и таргетинг.")
        
        # Проверяем CPC
        if cpc > 100:
            recommendations.append("• Высокий CPC. Рекомендуется оптимизировать ставки и таргетинг.")
        
        # Проверяем стоимость конверсии
        if cost_per_conversion > 1000:
            recommendations.append("• Высокая стоимость конверсии. Рекомендуется оптимизировать таргетинг и бюджет.")
        
        # Проверяем наличие проблемных кампаний
        problematic_campaigns = [c for c in campaigns if c.get('ctr', 0) < 0.5 or c.get('cpc', 0) > 100]
        if problematic_campaigns:
            recommendations.append(
                f"• Обнаружены проблемные кампании ({len(problematic_campaigns)}). "
                "Рекомендуется проверить их настройки."
            )
        
        # Если нет рекомендаций, добавляем стандартную
        if not recommendations:
            recommendations.append("• Показатели в пределах нормы. Рекомендуется продолжать текущую стратегию.")
        
        return "\n".join(recommendations)
    
    async def send_weekly_report(self, chat_id: Union[str, int]) -> bool:
        """
        Отправка еженедельного отчета о производительности кампаний.
        
        Args:
            chat_id (Union[str, int]): ID чата для отправки отчета.
            
        Returns:
            bool: True, если отчет успешно отправлен, иначе False.
        """
        try:
            # Получаем данные о кампаниях за последние 7 дней
            logger.info("Получение данных для еженедельного отчета")
            week_ago = datetime.now() - timedelta(days=7)
            date_range = f"{week_ago.strftime('%d.%m.%Y')} - {datetime.now().strftime('%d.%m.%Y')}"
            
            # Получаем данные о кампаниях
            campaigns = get_campaign_data(
                campaign_id=None,
                days=7,
                status='ACTIVE',
                date_preset='last_7_days',
                fields=['impressions', 'clicks', 'spend', 'conversions']
            )
            
            if not campaigns:
                logger.warning("Нет данных о кампаниях для еженедельного отчета")
                await self.send_message(
                    chat_id=chat_id,
                    text=MESSAGE_TEMPLATES.get('report.weekly.no_campaigns', 'За указанный период нет данных по кампаниям.')
                )
                return True
            
            # Рассчитываем общие метрики
            total_impressions = sum(c.get('metrics', {}).get('impressions', 0) for c in campaigns)
            total_clicks = sum(c.get('metrics', {}).get('clicks', 0) for c in campaigns)
            total_spend = sum(c.get('metrics', {}).get('spend', 0) for c in campaigns)
            total_conversions = sum(c.get('metrics', {}).get('conversions', 0) for c in campaigns)
            
            # Рассчитываем производные метрики
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            cpc = total_spend / total_clicks if total_clicks > 0 else 0
            cost_per_conversion = total_spend / total_conversions if total_conversions > 0 else 0
            
            # Сортируем кампании по CTR для выделения лучших
            for campaign in campaigns:
                metrics = campaign.get('metrics', {})
                impressions = metrics.get('impressions', 0)
                clicks = metrics.get('clicks', 0)
                campaign['ctr'] = (clicks / impressions * 100) if impressions > 0 else 0
            
            # Сортируем по CTR (от большего к меньшему)
            sorted_campaigns = sorted(campaigns, key=lambda x: x.get('ctr', 0), reverse=True)
            top_campaigns = sorted_campaigns[:5]  # Берем топ-5 кампаний
            
            # Формируем заголовок отчета
            header = MESSAGE_TEMPLATES.get('report.weekly.header', '').format(
                date_range=date_range,
                impressions=total_impressions,
                clicks=total_clicks,
                ctr=ctr,
                cpc=cpc,
                total_spend=total_spend,
                conversions=total_conversions,
                cost_per_conversion=cost_per_conversion
            )
            
            # Формируем список лучших кампаний
            campaigns_text = ""
            for i, campaign in enumerate(top_campaigns, 1):
                metrics = campaign.get('metrics', {})
                campaign_text = MESSAGE_TEMPLATES.get('report.weekly.campaign_item', '').format(
                    index=i,
                    name=campaign.get('name', 'Без имени'),
                    impressions=metrics.get('impressions', 0),
                    clicks=metrics.get('clicks', 0),
                    ctr=campaign.get('ctr', 0),
                    spend=metrics.get('spend', 0),
                    conversions=metrics.get('conversions', 0)
                )
                campaigns_text += campaign_text + "\n"
            
            # Формируем рекомендации
            recommendations = []
            recommendations_header = MESSAGE_TEMPLATES.get('report.weekly.recommendations.header', '')
            
            # Проверяем различные условия для рекомендаций
            if cpc > 2.0:  # Высокий CPC
                recommendations.append(MESSAGE_TEMPLATES.get('report.weekly.recommendations.high_cpc', '').format(cpc=cpc))
            
            if ctr < 1.0:  # Низкий CTR
                recommendations.append(MESSAGE_TEMPLATES.get('report.weekly.recommendations.low_ctr', '').format(ctr=ctr))
            
            # Проверяем конверсии
            if total_conversions == 0:
                recommendations.append(MESSAGE_TEMPLATES.get('report.weekly.recommendations.no_conversions', ''))
            elif cost_per_conversion > 50:
                recommendations.append(MESSAGE_TEMPLATES.get('report.weekly.recommendations.high_cost_per_conversion', '').format(
                    cost_per_conversion=cost_per_conversion
                ))
            
            if not recommendations and ctr > 2.0 and cost_per_conversion < 30:  # Хорошая производительность
                recommendations.append(MESSAGE_TEMPLATES.get('report.weekly.recommendations.good_performance', ''))
            
            # Собираем рекомендации в текст
            recommendations_text = ""
            if recommendations:
                recommendations_text = recommendations_header + "\n".join(recommendations)
            
            # Формируем полный текст отчета
            report_text = header + "\n" + campaigns_text + recommendations_text
            
            # Отправляем отчет
            logger.info("Отправка еженедельного отчета")
            return await self.send_message(chat_id=chat_id, text=report_text)
            
        except Exception as e:
            logger.error(f"Ошибка при отправке еженедельного отчета: {e}")
            await self.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при формировании еженедельного отчета. Пожалуйста, попробуйте позже."
            )
            return False
    
    async def send_campaign_info(self, chat_id: Union[str, int], campaign_id: str) -> bool:
        """
        Отправка подробной информации о конкретной кампании.
        
        Args:
            chat_id (Union[str, int]): ID чата для отправки информации.
            campaign_id (str): ID кампании.
            
        Returns:
            bool: True, если информация успешно отправлена, иначе False.
        """
        try:
            # Получаем данные о кампании
            logger.info(f"Получение информации о кампании {campaign_id}")
            
            campaign_data = get_campaign_data(campaign_id=campaign_id, days=30)
            
            if not campaign_data:
                logger.warning(f"Не удалось получить данные о кампании {campaign_id}")
                await self.send_message(
                    chat_id=chat_id,
                    text=f"❌ Не удалось получить данные о кампании с ID {campaign_id}. Проверьте ID и попробуйте снова."
                )
                return False
            
            # Форматируем информацию о кампании
            campaign_name = campaign_data.get('name', 'Без имени')
            status = campaign_data.get('status', 'Неизвестно')
            objective = campaign_data.get('objective', 'Не указано')
            budget = campaign_data.get('budget', 0)
            
            # Получаем метрики
            metrics = campaign_data.get('metrics', {})
            impressions = metrics.get('impressions', 0)
            clicks = metrics.get('clicks', 0)
            ctr = metrics.get('ctr', 0)
            cpc = metrics.get('cpc', 0)
            spend = metrics.get('spend', 0)
            conversions = metrics.get('conversions', 0)
            cost_per_conversion = metrics.get('cost_per_conversion', 0)
            
            # Форматируем сообщение
            message = MESSAGE_TEMPLATES.get('campaign_info', '').format(
                campaign_name=campaign_name,
                campaign_id=campaign_id,
                status=status,
                objective=objective,
                budget=budget,
                impressions=impressions,
                clicks=clicks,
                ctr=ctr,
                cpc=cpc,
                spend=spend,
                conversions=conversions,
                cost_per_conversion=cost_per_conversion,
                targeting=campaign_data.get('targeting', 'Не указано')
            )
            
            # Отправляем сообщение
            logger.info(f"Отправка информации о кампании {campaign_id}")
            await self.send_message(chat_id=chat_id, text=message)
            
            # Если есть данные по дням, создаем график CTR
            daily_stats = campaign_data.get('daily_stats', [])
            if daily_stats:
                logger.info(f"Создание графика CTR для кампании {campaign_id}")
                
                # Создаем график CTR
                ctr_chart = self._generate_chart(
                    data=daily_stats,
                    metric='ctr',
                    title=f'Динамика CTR кампании {campaign_name}'
                )
                
                if ctr_chart:
                    # Отправляем график
                    await self.send_photo(
                        chat_id=chat_id,
                        photo_path=ctr_chart,
                        caption=f"📊 Динамика CTR кампании {campaign_name} за последние 30 дней"
                    )
                
                # Создаем график расходов
                spend_chart = self._generate_chart(
                    data=daily_stats,
                    metric='spend',
                    title=f'Динамика расходов кампании {campaign_name}'
                )
                
                if spend_chart:
                    # Отправляем график
                    await self.send_photo(
                        chat_id=chat_id,
                        photo_path=spend_chart,
                        caption=f"💰 Динамика расходов кампании {campaign_name} за последние 30 дней"
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке информации о кампании {campaign_id}: {e}")
            await self.send_message(
                chat_id=chat_id,
                text=f"❌ Произошла ошибка при получении информации о кампании {campaign_id}. Пожалуйста, попробуйте позже."
            )
            return False
    
    def _format_campaign_info(self, campaign: Dict[str, Any]) -> str:
        """
        Форматирование детальной информации о кампании.
        
        Args:
            campaign (dict): Словарь с данными о кампании.
            
        Returns:
            str: Отформатированный текст с информацией о кампании.
        """
        if not campaign:
            return "Информация о кампании не найдена."
        
        # Основная информация
        info = (
            f"*Кампания: {campaign.get('name', 'Без имени')}*\n\n"
            f"📊 *Основная информация:*\n"
            f"ID: `{campaign.get('id', 'Неизвестный ID')}`\n"
            f"Статус: {campaign.get('status', 'Неизвестно')}\n"
            f"Цель: {campaign.get('objective', 'Не указана')}\n"
            f"Создана: {campaign.get('created_time', 'Неизвестно')}\n"
            f"Запущена: {campaign.get('start_time', 'Неизвестно')}\n"
        )
        
        if campaign.get('stop_time'):
            info += f"Остановлена: {campaign.get('stop_time')}\n"
        
        # Бюджет
        info += f"\n💰 *Бюджет:* ${campaign.get('budget', 0):.2f}\n\n"
        
        # Метрики
        info += "📈 *Метрики:*\n"
        metrics = campaign.get('metrics', {})
        if metrics:
            info += (
                f"Расход: ${metrics.get('spend', 0):.2f}\n"
                f"Показы: {metrics.get('impressions', 0):,}\n"
                f"Клики: {metrics.get('clicks', 0):,}\n"
                f"CTR: {metrics.get('ctr', 0):.2f}%\n"
                f"CPC: ${metrics.get('cpc', 0):.2f}\n"
                f"Конверсии: {metrics.get('conversions', 0):,}\n"
                f"Стоимость конверсии: ${metrics.get('cost_per_conversion', 0):.2f}\n"
            )
        else:
            info += "Метрики недоступны\n"
        
        # Таргетинг
        targeting = campaign.get('targeting', {})
        if targeting:
            info += "\n🎯 *Таргетинг:*\n"
            if targeting.get('geo_locations'):
                countries = targeting.get('geo_locations', {}).get('countries', [])
                cities = targeting.get('geo_locations', {}).get('cities', [])
                if countries:
                    info += f"Страны: {', '.join(countries)}\n"
                if cities:
                    city_names = [city.get('name', 'Неизвестно') for city in cities]
                    info += f"Города: {', '.join(city_names)}\n"
            
            if targeting.get('age_min') or targeting.get('age_max'):
                age_min = targeting.get('age_min', 'Не указан')
                age_max = targeting.get('age_max', 'Не указан')
                info += f"Возраст: {age_min} - {age_max}\n"
            
            if targeting.get('genders'):
                genders = {1: 'Мужчины', 2: 'Женщины'}
                gender_list = [genders.get(g, 'Другое') for g in targeting.get('genders', [])]
                info += f"Пол: {', '.join(gender_list)}\n"
        
        return info
    
    async def send_alerts(self, chat_id: Union[str, int]) -> bool:
        """
        Отправка предупреждений о проблемах с кампаниями.
        
        Args:
            chat_id (Union[str, int]): ID чата для отправки предупреждений.
            
        Returns:
            bool: True, если предупреждения успешно отправлены, иначе False.
        """
        try:
            # Получаем данные о кампаниях
            logger.info("Проверка кампаний на наличие проблем")
            
            # Получаем данные о кампаниях
            campaigns = get_campaign_data(
                campaign_id=None,
                days=1,
                status='ACTIVE',
                date_preset='yesterday',
                fields=['impressions', 'clicks', 'spend', 'conversions']
            )
            
            if not campaigns:
                logger.warning("Нет данных о кампаниях для проверки предупреждений")
                await self.send_message(
                    chat_id=chat_id,
                    text=MESSAGE_TEMPLATES.get('alerts.no_campaigns', 'Нет активных кампаний для проверки.')
                )
                return True
            
            # Проверяем различные условия для предупреждений
            alerts = []
            
            # Пороговые значения из настроек
            ctr_threshold = REPORT_SETTINGS.get('ALERT_LOW_CTR', 0.5)
            cpc_threshold = REPORT_SETTINGS.get('ALERT_HIGH_CPC', 2.0)
            budget_threshold = REPORT_SETTINGS.get('ALERT_BUDGET_THRESHOLD', 80)  # Процент использования бюджета
            
            for campaign in campaigns:
                campaign_id = campaign.get('id')
                campaign_name = campaign.get('name')
                metrics = campaign.get('metrics', {})
                
                # Проверяем CTR
                impressions = metrics.get('impressions', 0)
                clicks = metrics.get('clicks', 0)
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                
                if impressions > 100 and ctr < ctr_threshold:
                    alert = MESSAGE_TEMPLATES.get('alerts.low_ctr', '').format(
                        campaign_name=campaign_name,
                        campaign_id=campaign_id,
                        ctr=ctr
                    )
                    alerts.append(alert)
                
                # Проверяем CPC
                spend = metrics.get('spend', 0)
                cpc = spend / clicks if clicks > 0 else 0
                
                if clicks > 10 and cpc > cpc_threshold:
                    alert = MESSAGE_TEMPLATES.get('alerts.high_cpc', '').format(
                        campaign_name=campaign_name,
                        campaign_id=campaign_id,
                        cpc=cpc
                    )
                    alerts.append(alert)
                
                # Проверяем бюджет
                budget = campaign.get('budget', 0)
                budget_used_percent = (spend / budget * 100) if budget > 0 else 0
                
                if budget > 0 and budget_used_percent > budget_threshold:
                    alert = MESSAGE_TEMPLATES.get('alerts.budget_limit', '').format(
                        campaign_name=campaign_name,
                        campaign_id=campaign_id,
                        budget_used_percent=budget_used_percent,
                        remaining_budget=budget - spend
                    )
                    alerts.append(alert)
                
                # Проверяем конверсии
                conversions = metrics.get('conversions', 0)
                cost_per_conversion = spend / conversions if conversions > 0 else 0
                
                if spend > 50 and conversions == 0:
                    alert = MESSAGE_TEMPLATES.get('alerts.no_conversions', '').format(
                        campaign_name=campaign_name,
                        campaign_id=campaign_id,
                        spend=spend
                    )
                    alerts.append(alert)
                elif conversions > 0 and cost_per_conversion > 50:
                    alert = MESSAGE_TEMPLATES.get('alerts.high_cost_per_conversion', '').format(
                        campaign_name=campaign_name,
                        campaign_id=campaign_id,
                        cost_per_conversion=cost_per_conversion
                    )
                    alerts.append(alert)
            
            # Отправляем предупреждения
            if alerts:
                header = MESSAGE_TEMPLATES.get('alerts.header', '')
                alerts_text = header + "\n\n" + "\n\n".join(alerts)
                
                logger.info(f"Отправка {len(alerts)} предупреждений")
                return await self.send_message(chat_id=chat_id, text=alerts_text)
            else:
                # Если предупреждений нет
                no_alerts_text = MESSAGE_TEMPLATES.get('alerts.no_alerts', 'Предупреждений нет. Все кампании работают нормально.')
                logger.info("Предупреждений нет")
                return await self.send_message(chat_id=chat_id, text=no_alerts_text)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке кампаний на наличие проблем: {e}")
            await self.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при проверке предупреждений. Пожалуйста, попробуйте позже."
            )
            return False 