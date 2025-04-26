#!/bin/bash

# Скрипт для подготовки пакета AWS Lambda для Facebook Ads Dashboard

# Установка цветного вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Подготовка пакета AWS Lambda для Facebook Ads Dashboard ===${NC}"

# Проверка существования requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Ошибка: Файл requirements.txt не найден!${NC}"
    exit 1
fi

# Проверка существования необходимых файлов
if [ ! -f "simple_dashboard.py" ]; then
    echo -e "${RED}Ошибка: Файл simple_dashboard.py не найден!${NC}"
    exit 1
fi

if [ ! -f "lambda_handler.py" ]; then
    echo -e "${RED}Ошибка: Файл lambda_handler.py не найден!${NC}"
    exit 1
fi

# Создаем временную директорию
echo -e "${YELLOW}Создание временной директории...${NC}"
mkdir -p lambda_package

# Копируем файлы проекта
echo -e "${YELLOW}Копирование файлов проекта...${NC}"
cp lambda_handler.py lambda_package/
cp simple_dashboard.py lambda_package/
cp show_data.py lambda_package/
cp -r templates lambda_package/

# Устанавливаем зависимости
echo -e "${YELLOW}Установка зависимостей из requirements.txt...${NC}"
pip install -t lambda_package/ -r requirements.txt

# Создаем ZIP-архив
echo -e "${YELLOW}Создание ZIP-архива...${NC}"
cd lambda_package
zip -r ../dashboard_lambda_package.zip .
cd ..

# Очистка
echo -e "${YELLOW}Очистка временных файлов...${NC}"
rm -rf lambda_package

echo -e "${GREEN}Пакет Lambda успешно создан: dashboard_lambda_package.zip${NC}"
echo -e "${GREEN}Размер пакета: $(du -h dashboard_lambda_package.zip | cut -f1)${NC}"
echo -e "${YELLOW}Примечание: Загрузите этот ZIP-файл в AWS Lambda и установите обработчик: lambda_handler.lambda_handler${NC}"