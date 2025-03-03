#!/bin/bash
# Скрипт для подготовки минимального пакета Lambda

# Создаем временную директорию
mkdir -p minimal_lambda_package

# Копируем упрощенную функцию под именем lambda_function.py
cp simple_lambda_function.py minimal_lambda_package/lambda_function.py

# Устанавливаем зависимости
pip install -t minimal_lambda_package facebook-business python-telegram-bot

# Создаем ZIP-архив
cd minimal_lambda_package
zip -r ../minimal_lambda_package.zip .
cd ..

# Очищаем временную директорию
rm -rf minimal_lambda_package

echo "Пакет minimal_lambda_package.zip успешно создан"
