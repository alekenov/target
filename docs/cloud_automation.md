# Автоматизация отчетов в облаке

В этом документе описаны шаги по настройке автоматического запуска ежедневных отчетов о рекламных кампаниях Facebook с использованием GitHub Actions.

## Преимущества использования GitHub Actions

- Бесплатно для публичных репозиториев и ограниченное количество минут для приватных
- Не требует настройки отдельного сервера
- Интеграция с GitHub для удобного управления кодом
- Возможность запуска по расписанию или вручную
- Хранение отчетов в виде артефактов

## Шаги по настройке

### 1. Подготовка репозитория

1. Создайте репозиторий на GitHub или используйте существующий
2. Убедитесь, что в репозитории есть следующие файлы:
   - `daily_ad_report.py` - скрипт для генерации отчетов
   - `requirements.txt` - список зависимостей
   - `.github/workflows/daily_report.yml` - конфигурация GitHub Actions

### 2. Настройка секретов

Для безопасного хранения учетных данных используйте секреты GitHub:

1. Перейдите в настройки репозитория: `Settings > Secrets and variables > Actions`
2. Нажмите `New repository secret`
3. Добавьте следующие секреты:
   - `FB_APP_ID` - ID приложения Facebook
   - `FB_APP_SECRET` - Секрет приложения Facebook
   - `FB_ACCESS_TOKEN` - Токен доступа Facebook
   - `FB_AD_ACCOUNT_ID` - ID рекламного аккаунта
   - `TELEGRAM_BOT_TOKEN` - Токен Telegram-бота
   - `TELEGRAM_CHAT_ID` - ID чата или канала Telegram

### 3. Конфигурация GitHub Actions

Файл `.github/workflows/daily_report.yml` содержит настройки для автоматического запуска:

```yaml
name: Ежедневный отчет по рекламным кампаниям Facebook

on:
  schedule:
    # Запуск каждый день в 8:00 UTC (это соответствует 11:00 МСК)
    - cron: '0 8 * * *'
  workflow_dispatch:  # Позволяет запускать workflow вручную из интерфейса GitHub

jobs:
  generate_report:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -e .
          
      - name: Create directories
        run: |
          mkdir -p reports
          mkdir -p cache
          mkdir -p logs
          
      - name: Set up environment variables
        run: |
          echo "APP_ID=${{ secrets.FB_APP_ID }}" >> $GITHUB_ENV
          echo "APP_SECRET=${{ secrets.FB_APP_SECRET }}" >> $GITHUB_ENV
          echo "ACCESS_TOKEN=${{ secrets.FB_ACCESS_TOKEN }}" >> $GITHUB_ENV
          echo "AD_ACCOUNT_ID=${{ secrets.FB_AD_ACCOUNT_ID }}" >> $GITHUB_ENV
          echo "TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }}" >> $GITHUB_ENV
          echo "TELEGRAM_CHAT_ID=${{ secrets.TELEGRAM_CHAT_ID }}" >> $GITHUB_ENV
          echo "LOG_LEVEL=INFO" >> $GITHUB_ENV
          echo "CACHE_ENABLED=true" >> $GITHUB_ENV
          echo "CACHE_DIR=./cache" >> $GITHUB_ENV
          echo "REPORTS_DIR=./reports" >> $GITHUB_ENV
          
      - name: Run daily report script
        run: python daily_ad_report.py
        
      - name: Upload report as artifact
        uses: actions/upload-artifact@v3
        with:
          name: fb-ads-report
          path: reports/
          retention-days: 7
```

### 4. Настройка расписания

По умолчанию отчет запускается каждый день в 8:00 UTC (11:00 МСК). Вы можете изменить расписание, отредактировав строку с cron-выражением:

```yaml
on:
  schedule:
    - cron: '0 8 * * *'  # Формат: минуты часы день_месяца месяц день_недели
```

Примеры cron-выражений:
- `0 8 * * *` - каждый день в 8:00 UTC
- `0 */6 * * *` - каждые 6 часов
- `0 8 * * 1-5` - каждый будний день в 8:00 UTC

### 5. Ручной запуск

Вы можете запустить генерацию отчета вручную:

1. Перейдите в раздел Actions вашего репозитория
2. Выберите workflow "Ежедневный отчет по рекламным кампаниям Facebook"
3. Нажмите "Run workflow"
4. Выберите ветку и нажмите "Run workflow"

### 6. Просмотр результатов

После выполнения workflow:

1. Отчет будет отправлен в настроенный Telegram-канал
2. Файлы отчетов будут доступны как артефакты:
   - Перейдите в раздел Actions
   - Выберите последний выполненный workflow
   - Прокрутите вниз до раздела "Artifacts"
   - Скачайте артефакт "fb-ads-report"

## Устранение неполадок

### Ошибка аутентификации Facebook

Если возникают ошибки с аутентификацией Facebook:
1. Проверьте правильность секретов `FB_APP_ID`, `FB_APP_SECRET`, `FB_ACCESS_TOKEN`
2. Убедитесь, что токен доступа не истек (долгосрочные токены действуют 60 дней)
3. Проверьте права доступа приложения к рекламному аккаунту

### Ошибка отправки в Telegram

Если отчет не отправляется в Telegram:
1. Проверьте правильность секретов `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`
2. Убедитесь, что бот добавлен в канал/группу и имеет права на отправку сообщений
3. Проверьте формат ID канала (для публичных каналов: `@channel_name`, для приватных: `-100xxxxxxxxxx`)

### Workflow не запускается по расписанию

Если workflow не запускается автоматически:
1. Убедитесь, что в репозитории была активность за последние 60 дней
2. Проверьте правильность cron-выражения
3. Учтите, что GitHub не гарантирует точное время запуска (возможны задержки) 