#!/bin/bash

# Скрипт для подготовки пакета AWS Lambda

# Установка цветного вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Подготовка пакета AWS Lambda ===${NC}"

# Проверка существования requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Ошибка: Файл requirements.txt не найден!${NC}"
    exit 1
fi

# Создаем временную директорию
echo -e "${YELLOW}Создание временной директории...${NC}"
mkdir -p lambda_package

# Копируем файлы проекта
echo -e "${YELLOW}Копирование файлов проекта...${NC}"
cp lambda_function.py lambda_package/
cp -r facebook_ads_toolkit lambda_package/

# Устанавливаем зависимости
echo -e "${YELLOW}Установка зависимостей из requirements.txt...${NC}"
pip install -t lambda_package/ -r requirements.txt

# Создаем ZIP-архив
echo -e "${YELLOW}Создание ZIP-архива...${NC}"
cd lambda_package
zip -r ../lambda_package.zip .
cd ..

# Очистка
echo -e "${YELLOW}Очистка временных файлов...${NC}"
rm -rf lambda_package

echo -e "${GREEN}Пакет Lambda успешно создан: lambda_package.zip${NC}"
echo -e "${GREEN}Размер пакета: $(du -h lambda_package.zip | cut -f1)${NC}"