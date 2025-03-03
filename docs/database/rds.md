# AWS Aurora MySQL База Данных для Facebook Ads

Этот документ содержит информацию о настройке и использовании базы данных AWS Aurora MySQL для проекта Facebook Ads.

## Основная информация

### Конфигурация базы данных
- **Тип**: AWS Aurora Serverless v2 (MySQL-совместимая)
- **Версия**: 8.0.mysql_aurora.3.08.1
- **Режим**: Provisioned с Serverless v2 масштабированием
- **Минимальная ёмкость**: 1 ACU (Aurora Capacity Unit)
- **Максимальная ёмкость**: 8 ACU
- **Регион**: us-east-1 (N. Virginia)

### Точки подключения
- **Кластерная точка подключения**: facebook-ads-aurora-cluster.cluster-cpciyms4a0o2.us-east-1.rds.amazonaws.com
- **Точка подключения чтения-записи**: facebook-ads-aurora-cluster-instance-1.cpciyms4a0o2.us-east-1.rds.amazonaws.com
- **Порт**: 3306
- **База данных**: facebook_ads_db
- **Имя пользователя**: admin
- **Пароль**: Хранится в переменной окружения AURORA_MASTER_PASSWORD

### Безопасность
- **Группа безопасности**: sg-06ba3e9b3f5b95ba5
- **Доступ**: Публичный (0.0.0.0/0)
- **Аутентификация**: По паролю (IAM аутентификация отключена)

## Структура базы данных

База данных содержит следующие таблицы:

### 1. campaigns
Хранит информацию о рекламных кампаниях Facebook.

**Основные поля**:
- `id` - Идентификатор кампании
- `name` - Название кампании
- `status` - Статус кампании (ACTIVE, PAUSED, DELETED и т.д.)
- `daily_budget` - Дневной бюджет
- `lifetime_budget` - Бюджет на весь срок кампании
- `start_time` - Время начала кампании
- `stop_time` - Время окончания кампании
- `created_time` - Время создания записи
- `updated_time` - Время последнего обновления записи

### 2. ad_sets
Хранит информацию о группах объявлений.

**Основные поля**:
- `id` - Идентификатор группы объявлений
- `campaign_id` - Идентификатор родительской кампании
- `name` - Название группы объявлений
- `status` - Статус группы объявлений
- `daily_budget` - Дневной бюджет
- `lifetime_budget` - Бюджет на весь срок
- `targeting` - JSON с настройками таргетинга
- `created_time` - Время создания записи
- `updated_time` - Время последнего обновления записи

### 3. ads
Хранит информацию об отдельных объявлениях.

**Основные поля**:
- `id` - Идентификатор объявления
- `ad_set_id` - Идентификатор родительской группы объявлений
- `name` - Название объявления
- `status` - Статус объявления
- `creative` - JSON с креативами объявления
- `created_time` - Время создания записи
- `updated_time` - Время последнего обновления записи

### 4. ad_insights
Хранит статистику и аналитику по объявлениям.

**Основные поля**:
- `id` - Уникальный идентификатор записи
- `ad_id` - Идентификатор объявления
- `date` - Дата статистики
- `impressions` - Количество показов
- `clicks` - Количество кликов
- `spend` - Потраченная сумма
- `ctr` - Click-through rate (соотношение кликов к показам)
- `cpc` - Cost per click (стоимость за клик)
- `conversions` - Количество конверсий
- `created_time` - Время создания записи

### 5. config
Хранит конфигурационные параметры для приложения.

**Основные поля**:
- `key` - Ключ параметра
- `value` - Значение параметра
- `description` - Описание параметра
- `updated_time` - Время последнего обновления

## Подключение к базе данных

### Python (с использованием PyMySQL)

```python
import pymysql
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def get_db_connection(dict_cursor=True):
    connection = pymysql.connect(
        host=os.getenv('DB_HOST', 'facebook-ads-aurora-cluster.cluster-cpciyms4a0o2.us-east-1.rds.amazonaws.com'),
        user=os.getenv('DB_USER', 'admin'),
        password=os.getenv('AURORA_MASTER_PASSWORD'),
        database=os.getenv('DB_NAME', 'facebook_ads_db'),
        port=int(os.getenv('DB_PORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor if dict_cursor else pymysql.cursors.Cursor
    )
    return connection
```

### Класс DatabaseConnection (контекстный менеджер)

```python
import pymysql
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class DatabaseConnection:
    def __init__(self, dict_cursor=True):
        self.dict_cursor = dict_cursor
        self.connection = None
        self.cursor = None
    
    def __enter__(self):
        self.connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'facebook-ads-aurora-cluster.cluster-cpciyms4a0o2.us-east-1.rds.amazonaws.com'),
            user=os.getenv('DB_USER', 'admin'),
            password=os.getenv('AURORA_MASTER_PASSWORD'),
            database=os.getenv('DB_NAME', 'facebook_ads_db'),
            port=int(os.getenv('DB_PORT', 3306)),
            cursorclass=pymysql.cursors.DictCursor if self.dict_cursor else pymysql.cursors.Cursor
        )
        self.cursor = self.connection.cursor()
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if self.connection:
                self.connection.rollback()
        else:
            if self.connection:
                self.connection.commit()
        
        if self.cursor:
            self.cursor.close()
        
        if self.connection:
            self.connection.close()
```

## Пример использования

```python
# Пример получения всех активных кампаний
from db_utils import DatabaseConnection

def get_active_campaigns():
    with DatabaseConnection() as cursor:
        cursor.execute("SELECT * FROM campaigns WHERE status = 'ACTIVE'")
        campaigns = cursor.fetchall()
    return campaigns

# Пример добавления новой кампании
def add_campaign(campaign_data):
    with DatabaseConnection() as cursor:
        sql = """
        INSERT INTO campaigns 
        (id, name, status, daily_budget, lifetime_budget, start_time, stop_time) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            campaign_data['id'],
            campaign_data['name'],
            campaign_data['status'],
            campaign_data['daily_budget'],
            campaign_data['lifetime_budget'],
            campaign_data['start_time'],
            campaign_data['stop_time']
        ))
    return True
```

## Стоимость и оптимизация

### Оценка стоимости
- **Минимальная дневная стоимость**: ~$2.88 (1 ACU)
- **Максимальная дневная стоимость**: ~$23.04 (8 ACU)
- **Месячная стоимость**: $86.40 - $691.20

### Рекомендации по оптимизации затрат
1. **Настройка автопаузы**: Настройте автоматическую паузу кластера в периоды неактивности.
2. **Уменьшение максимальной ёмкости**: Если нагрузка небольшая, уменьшите максимальную ёмкость до 2-4 ACU.
3. **Мониторинг использования**: Регулярно проверяйте метрики использования в CloudWatch.
4. **Резервные экземпляры**: Для долгосрочных проектов рассмотрите возможность использования резервных экземпляров.

## Альтернативные варианты баз данных

Если стоимость Aurora Serverless v2 слишком высока, рассмотрите следующие альтернативы:

1. **Amazon RDS MySQL (не Serverless)**
   - Стоимость: от $12-15/месяц (t3.micro)
   - Преимущества: Полная совместимость с текущим кодом

2. **MySQL на AWS Lightsail**
   - Стоимость: от $3.5-5/месяц
   - Преимущества: Значительно дешевле, полный контроль

3. **SQLite (локальная база данных)**
   - Стоимость: $0
   - Преимущества: Бесплатно, простая настройка
   - Недостатки: Не подходит для продакшена

## Полезные команды AWS CLI

```bash
# Получение информации о кластере
aws rds describe-db-clusters --db-cluster-identifier facebook-ads-aurora-cluster --region us-east-1

# Получение информации об экземпляре
aws rds describe-db-instances --db-instance-identifier facebook-ads-aurora-cluster-instance-1 --region us-east-1

# Изменение настроек масштабирования
aws rds modify-db-cluster --db-cluster-identifier facebook-ads-aurora-cluster --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=4 --region us-east-1
```
