#!/bin/bash

# Скрипт для подготовки облегченного пакета AWS Lambda

# Установка цветного вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Подготовка облегченного пакета AWS Lambda ===${NC}"

# Создаем временную директорию
echo -e "${YELLOW}Создание временной директории...${NC}"
mkdir -p slim_lambda

# Копируем только необходимые файлы
echo -e "${YELLOW}Копирование необходимых файлов...${NC}"
cp lambda_daily_report.py slim_lambda/lambda_function.py
cp -r facebook_ads_toolkit/auth slim_lambda/
cp -r facebook_ads_toolkit/utils slim_lambda/
mkdir -p slim_lambda/facebook_ads_toolkit
touch slim_lambda/facebook_ads_toolkit/__init__.py

# Создаем файл с минимальными зависимостями
cat > slim_lambda/requirements.txt << EOF
facebook-business==17.0.0
python-telegram-bot==20.7
python-dotenv==1.0.0
EOF

# Устанавливаем зависимости
echo -e "${YELLOW}Установка зависимостей...${NC}"
pip install -t slim_lambda/ -r slim_lambda/requirements.txt

# Удаляем ненужные файлы для уменьшения размера
echo -e "${YELLOW}Оптимизация размера пакета...${NC}"
find slim_lambda -name "*.pyc" -delete
find slim_lambda -name "__pycache__" -type d -exec rm -rf {} +
find slim_lambda -name "*.dist-info" -type d -exec rm -rf {} +
find slim_lambda -name "*.egg-info" -type d -exec rm -rf {} +
find slim_lambda -name "tests" -type d -exec rm -rf {} +
find slim_lambda -name "test" -type d -exec rm -rf {} +
find slim_lambda -name "docs" -type d -exec rm -rf {} +
find slim_lambda -name "doc" -type d -exec rm -rf {} +
find slim_lambda -name "examples" -type d -exec rm -rf {} +

# Создаем ZIP-архив
echo -e "${YELLOW}Создание ZIP-архива...${NC}"
cd slim_lambda
zip -r ../slim_lambda_package.zip .
cd ..

# Очистка
echo -e "${YELLOW}Очистка временных файлов...${NC}"
rm -rf slim_lambda

echo -e "${GREEN}Пакет Lambda успешно создан: slim_lambda_package.zip${NC}"
echo -e "${GREEN}Размер пакета: $(du -h slim_lambda_package.zip | cut -f1)${NC}"
