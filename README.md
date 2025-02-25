# Facebook Ads Toolkit

Инструмент для управления и анализа рекламных кампаний Facebook с использованием Facebook Marketing API.

## Возможности

- Управление рекламными кампаниями, группами объявлений и объявлениями
- Анализ эффективности рекламы с расчетом ключевых метрик
- Автоматическая оптимизация рекламных кампаний
- Генерация отчетов в различных форматах
- Интеграция с Telegram для отправки отчетов и уведомлений
- CLI-интерфейс для удобного управления
- Автоматизация отчетов через GitHub Actions

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/facebook-ads-toolkit.git
cd facebook-ads-toolkit

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp examples/.env.example .env
# Отредактируйте файл .env, добавив свои учетные данные
```

## Настройка

1. Создайте приложение в [Facebook Developers](https://developers.facebook.com/)
2. Получите токен доступа с необходимыми разрешениями
3. Укажите ID рекламного аккаунта
4. Заполните файл `.env` полученными данными

### Настройка Telegram-бота

1. Создайте нового бота через [@BotFather](https://t.me/BotFather) в Telegram
2. Получите токен бота и добавьте его в файл `.env`
3. Создайте канал для логов и добавьте бота в него как администратора
4. Получите ID канала и добавьте его в файл `.env`

## Использование

### Управление кампаниями

```python
from facebook_ads_toolkit.campaign.manager import CampaignManager

# Инициализация менеджера кампаний
campaign_manager = CampaignManager()

# Получение списка активных кампаний
active_campaigns = campaign_manager.get_campaigns(status='ACTIVE')

# Создание новой кампании
new_campaign = campaign_manager.create_campaign(
    name="Тестовая кампания",
    objective="CONVERSIONS",
    status="PAUSED",
    special_ad_categories=[],
    daily_budget=1000
)

# Обновление параметров кампании
campaign_manager.update_campaign(
    campaign_id=new_campaign['id'],
    name="Обновленная тестовая кампания",
    daily_budget=2000
)

# Остановка кампании
campaign_manager.update_campaign_status(
    campaign_id=new_campaign['id'],
    status="PAUSED"
)
```

### Анализ эффективности

```python
from facebook_ads_toolkit.analysis.ad_analyzer import AdAnalyzer

# Инициализация анализатора
analyzer = AdAnalyzer()

# Анализ эффективности кампании
performance = analyzer.analyze_campaign(
    campaign_id="123456789",
    date_preset="LAST_30_DAYS"
)

# Выявление неэффективных объявлений
underperforming_ads = analyzer.find_underperforming_ads(
    account_id="act_123456789",
    metrics=["ctr", "cpc"],
    threshold=0.5
)
```

### Генерация отчетов

```python
from facebook_ads_toolkit.reports.report_generator import ReportManager

# Инициализация менеджера отчетов
report_manager = ReportManager(output_dir="reports")

# Генерация отчета о производительности кампаний
report_files = report_manager.generate_report(
    template_name="campaign_performance",
    data=performance_data,
    export_formats=["json", "csv", "txt"]
)
```

### Использование Telegram-бота

```python
from facebook_ads_toolkit.telegram_integration import run_bot

# Запуск Telegram-бота
run_bot()
```

Или запустите пример из директории examples:

```bash
python examples/telegram_bot_example.py
```

#### Команды Telegram-бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку по командам
- `/list` - Показать список активных кампаний
- `/daily` - Получить ежедневный отчет
- `/weekly` - Получить еженедельный отчет
- `/campaign [ID]` - Информация о конкретной кампании
- `/alerts` - Проверить наличие предупреждений

## Автоматизация отчетов в облаке

Проект настроен для автоматического запуска ежедневных отчетов с использованием GitHub Actions.

### Настройка GitHub Actions

1. Разместите проект в репозитории GitHub
2. Добавьте следующие секреты в настройках репозитория (Settings > Secrets and variables > Actions):
   - `FB_APP_ID` - ID приложения Facebook
   - `FB_APP_SECRET` - Секрет приложения Facebook
   - `FB_ACCESS_TOKEN` - Токен доступа Facebook
   - `FB_AD_ACCOUNT_ID` - ID рекламного аккаунта
   - `TELEGRAM_BOT_TOKEN` - Токен Telegram-бота
   - `TELEGRAM_CHAT_ID` - ID чата или канала Telegram

### Расписание запуска

По умолчанию отчет запускается каждый день в 8:00 UTC (11:00 МСК). Вы можете изменить расписание, отредактировав файл `.github/workflows/daily_report.yml`.

### Ручной запуск

Вы также можете запустить генерацию отчета вручную через интерфейс GitHub:
1. Перейдите в раздел Actions вашего репозитория
2. Выберите workflow "Ежедневный отчет по рекламным кампаниям Facebook"
3. Нажмите "Run workflow"

### Доступ к отчетам

После выполнения workflow отчеты будут доступны как артефакты в GitHub Actions и отправлены в настроенный Telegram-канал.

## Структура проекта

```
facebook_ads_toolkit/
├── auth/                  # Аутентификация с Facebook API
├── campaign/              # Управление кампаниями
├── analysis/              # Анализ эффективности
├── reports/               # Генерация отчетов
├── telegram_integration/  # Интеграция с Telegram
├── cli/                   # CLI-интерфейс
├── utils/                 # Вспомогательные функции
└── config/                # Конфигурационные файлы
```

## Требования

- Python 3.8+
- facebook-business SDK
- python-telegram-bot
- pandas
- matplotlib
- pyyaml
- python-dotenv

## Лицензия

MIT

## Автор

Ваше имя - [ваш email](mailto:your.email@example.com)
