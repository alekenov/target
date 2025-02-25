#!/bin/bash

# Скрипт для подготовки пакета AWS Lambda

# Создаем временную директорию
echo "Создание временной директории..."
mkdir -p lambda_package

# Копируем файлы проекта
echo "Копирование файлов проекта..."
cp lambda_function.py lambda_package/
cp -r facebook_ads_toolkit lambda_package/

# Устанавливаем зависимости
echo "Установка зависимостей..."
pip install -t lambda_package/ facebook-business python-telegram-bot pandas pyyaml python-dotenv boto3 requests

# Создаем ZIP-архив
echo "Создание ZIP-архива..."
cd lambda_package
zip -r ../lambda_package.zip .
cd ..

# Очистка
echo "Очистка временных файлов..."
rm -rf lambda_package

echo "Пакет Lambda успешно создан: lambda_package.zip"
echo "Размер пакета: $(du -h lambda_package.zip | cut -f1)" 