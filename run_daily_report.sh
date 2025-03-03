#!/bin/bash

# Скрипт для запуска ежедневного отчета о тратах Facebook

# Переходим в директорию проекта
cd "$(dirname "$0")"

# Активируем виртуальное окружение, если оно используется
# source venv/bin/activate

# Запускаем скрипт отчета
python daily_telegram_report.py

# Логируем успешное выполнение
echo "$(date) - Ежедневный отчет Facebook успешно отправлен" >> facebook_report.log
