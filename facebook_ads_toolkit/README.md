# Facebook Ads Toolkit

Инструментарий для работы с Facebook Ads API, включающий функциональность для анализа производительности рекламы, управления кампаниями и генерации отчетов.

## Особенности

- Анализ активных рекламных кампаний, групп объявлений и объявлений
- Получение статистики и ключевых метрик (CTR, CPC, ROAS)
- Создание и настройка рекламных кампаний
- Оптимизация производительности с использованием batch-запросов
- Генерация детальных отчетов в различных форматах (JSON, CSV, TXT)

## Структура проекта

```
facebook_ads_toolkit/
├── auth/             # Модули авторизации
├── analysis/         # Анализ рекламы
├── campaign/         # Управление кампаниями
├── utils/            # Общие утилиты
├── reports/          # Генерация отчетов
├── config/           # Конфигурации
├── tests/            # Тесты
├── data/             # Хранение результатов
└── cli/              # Командные интерфейсы
```

## Установка

1. Клонировать репозиторий:
   ```
   git clone <repository-url>
   cd facebook-ads-toolkit
   ```

2. Создать и активировать виртуальное окружение:
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. Установить зависимости:
   ```
   pip install -r requirements.txt
   ```

4. Настроить параметры авторизации:
   - Скопировать `config/.env.example` в `.env`
   - Заполнить необходимые параметры авторизации для Facebook API

## Использование

### Анализ рекламы

```bash
# Анализ рекламы за последние 30 дней
python -m facebook_ads_toolkit.cli.analyze

# Анализ рекламы за указанный период
python -m facebook_ads_toolkit.cli.analyze --start-date 2023-01-01 --end-date 2023-01-31

# Экспорт результатов в определенный формат
python -m facebook_ads_toolkit.cli.analyze --export-format json
```

### Программное использование

```python
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth
from facebook_ads_toolkit.analysis.ad_analyzer import AdAnalyzer

# Инициализация авторизации
auth = FacebookAuth()
account, api = auth.initialize()

# Анализ рекламы
results = AdAnalyzer.run_analysis(account)
```

## Основные модули

### Модуль авторизации (`auth/`)

Отвечает за авторизацию и установление соединения с Facebook API.

```python
from facebook_ads_toolkit.auth.facebook_auth import FacebookAuth

auth = FacebookAuth()
account, api = auth.initialize()
```

### Модуль анализа рекламы (`analysis/`)

Включает функциональность для получения и анализа данных о рекламных кампаниях.

```python
from facebook_ads_toolkit.analysis.data_fetchers import AdDataFetcher
from facebook_ads_toolkit.analysis.ad_analyzer import AdAnalyzer

# Получение данных
fetcher = AdDataFetcher(account)
ad_data = fetcher.fetch_all_batch()

# Анализ данных
analyzer = AdAnalyzer(ad_data)
results = analyzer.analyze()
```

### Модуль экспорта (`analysis/exporters.py`)

Позволяет экспортировать результаты анализа в различные форматы.

```python
from facebook_ads_toolkit.analysis.exporters import AnalysisExporter

exporter = AnalysisExporter(results)
exporter.export_all()  # Экспорт во все доступные форматы
```

## Требования

- Python 3.7+
- facebook-business 17.0.0+
- pandas 1.5.0+
- python-dotenv 1.0.0+

## Лицензия

Этот проект распространяется под лицензией MIT. Подробности см. в файле LICENSE. 