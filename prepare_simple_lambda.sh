#!/bin/bash
# Скрипт для подготовки простого пакета Lambda

# Создаем временную директорию
mkdir -p lambda_package

# Копируем необходимые файлы
cp lambda_function.py lambda_package/
cp -r facebook_ads_toolkit lambda_package/

# Устанавливаем зависимости
pip install -t lambda_package facebook-business python-telegram-bot

# Создаем ZIP-архив
cd lambda_package
zip -r ../simple_lambda_package.zip .
cd ..

# Очищаем временную директорию
rm -rf lambda_package

echo "Пакет simple_lambda_package.zip успешно создан"
