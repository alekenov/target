# Facebook Ads Data Analysis Tool

Инструмент для анализа эффективности рекламных кампаний Facebook, оптимизированный для быстрого получения и анализа данных.

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd target
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
# или
.venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` с вашими учетными данными Facebook:
```
FB_ACCESS_TOKEN=your_access_token
FB_ACCOUNT_ID=your_account_id
FB_APP_ID=your_app_id
```

## Использование

### Получение статистики по кампаниям

Базовое использование:
```bash
python get_campaigns_stats.py
```

С параметрами:
```bash
# Данные за конкретный период
python get_campaigns_stats.py --start-date 2024-01-01 --end-date 2024-01-31

# Топ-10 кампаний вместо 20
python get_campaigns_stats.py --limit 10
```

#### Параметры
- `--start-date` - начальная дата в формате YYYY-MM-DD (по умолчанию: начало текущего года)
- `--end-date` - конечная дата в формате YYYY-MM-DD (по умолчанию: текущая дата)
- `--limit` - количество топ кампаний для анализа (по умолчанию: 20)

Скрипт:
1. Подключится к Facebook API
2. Получит статистику по всем кампаниям за указанный период
3. Отфильтрует топ-N кампаний по расходам (где N задается параметром --limit)
4. Сохранит результаты в файл `top_campaigns_stats_YYYYMMDD.json`

### Формат выходных данных

Данные сохраняются в JSON файл со следующей структурой:
```json
{
  "campaign_id": "123",
  "campaign_name": "Campaign Name",
  "objective": "REACH",
  "stats": {
    "impressions": 1000,
    "reach": 900,
    "clicks": 100,
    "spend": 50.0,
    "actions": {
      "link_click": 80,
      "post_engagement": 120
    }
  },
  "daily_stats": [...]
}
```

## Требования

- Python 3.8+
- Facebook Marketing API доступ
- Права на чтение статистики рекламного аккаунта

## Зависимости

- facebook-business
- python-dotenv
- requests

## Поддержка

При возникновении проблем:
1. Проверьте правильность учетных данных в `.env`
2. Убедитесь, что у вас есть необходимые права доступа
3. Проверьте логи для деталей ошибок

## Лицензия

MIT
