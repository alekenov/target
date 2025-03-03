# Руководство по настройке Aurora MySQL для Facebook Ads Reporting

Это руководство поможет вам настроить базу данных AWS Aurora MySQL для хранения данных о рекламных кампаниях Facebook.

## 1. Создание кластера Aurora MySQL

### Шаги по созданию кластера

1. Перейдите в [AWS RDS Console](https://console.aws.amazon.com/rds/)
2. Нажмите "Create database"
3. Выберите "Standard create"
4. В разделе "Engine options" выберите:
   - Engine type: Amazon Aurora
   - Edition: Amazon Aurora MySQL-Compatible Edition
   - Version: Aurora MySQL 8.0 (рекомендуется последняя доступная версия)
5. В разделе "Templates" выберите "Production" или "Dev/Test" в зависимости от ваших потребностей
6. В разделе "Settings":
   - DB cluster identifier: `facebook-ads-aurora-cluster` (или другое имя)
   - Master username: `admin` (или другое имя)
   - Master password: Создайте надежный пароль и сохраните его
7. В разделе "Instance configuration":
   - DB instance class: Выберите подходящий класс (для небольших проектов достаточно db.t4g.medium)
   - Multi-AZ deployment: "Create an Aurora Replica/Reader node" (рекомендуется для продакшена)
8. В разделе "Connectivity":
   - Virtual Private Cloud (VPC): Выберите вашу VPC
   - Public access: "Yes" (для доступа из Lambda без настройки VPC)
   - VPC security group: Создайте новую или выберите существующую
9. В разделе "Additional configuration":
   - Initial database name: `facebook_ads_db`
   - Backup retention period: 7 дней (или больше)
   - Enable encryption: Рекомендуется включить
   - Enable Performance Insights: Рекомендуется включить для мониторинга
10. Нажмите "Create database"

## 2. Настройка группы безопасности

Для обеспечения доступа к базе данных из Lambda функции:

1. Перейдите в [AWS VPC Console](https://console.aws.amazon.com/vpc/)
2. Выберите "Security Groups" в левом меню
3. Найдите группу безопасности, связанную с вашим кластером Aurora
4. Выберите вкладку "Inbound rules" и нажмите "Edit inbound rules"
5. Добавьте правило:
   - Type: MySQL/Aurora (3306)
   - Source: 0.0.0.0/0 (для доступа из любого места) или укажите конкретные IP-адреса
6. Нажмите "Save rules"

**Примечание по безопасности**: Открытие доступа к базе данных из любого места (0.0.0.0/0) не рекомендуется для продакшена. Для продакшена рекомендуется:
- Разместить Lambda функцию в той же VPC, что и база данных
- Настроить группу безопасности для разрешения доступа только из подсети Lambda
- Или использовать AWS PrivateLink для безопасного доступа

## 3. Создание таблиц базы данных

Подключитесь к базе данных с помощью MySQL клиента:

```bash
mysql -h facebook-ads-aurora-cluster.cluster-xxxxxxxx.region.rds.amazonaws.com -u admin -p
```

Выберите базу данных:

```sql
USE facebook_ads_db;
```

Создайте необходимые таблицы:

```sql
-- Таблица для хранения информации о кампаниях
CREATE TABLE campaigns (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    daily_budget DECIMAL(15, 2),
    lifetime_budget DECIMAL(15, 2),
    start_time DATETIME,
    stop_time DATETIME,
    objective VARCHAR(100),
    buying_type VARCHAR(50),
    special_ad_categories TEXT,
    created_time DATETIME,
    updated_time DATETIME,
    last_sync_time DATETIME,
    raw_data JSON
);

-- Таблица для хранения информации о группах объявлений
CREATE TABLE ad_sets (
    id VARCHAR(255) PRIMARY KEY,
    campaign_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    daily_budget DECIMAL(15, 2),
    lifetime_budget DECIMAL(15, 2),
    start_time DATETIME,
    stop_time DATETIME,
    targeting JSON,
    optimization_goal VARCHAR(100),
    bid_strategy VARCHAR(100),
    created_time DATETIME,
    updated_time DATETIME,
    last_sync_time DATETIME,
    raw_data JSON,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

-- Таблица для хранения информации об объявлениях
CREATE TABLE ads (
    id VARCHAR(255) PRIMARY KEY,
    ad_set_id VARCHAR(255) NOT NULL,
    campaign_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    creative_id VARCHAR(255),
    creative_url TEXT,
    created_time DATETIME,
    updated_time DATETIME,
    last_sync_time DATETIME,
    raw_data JSON,
    FOREIGN KEY (ad_set_id) REFERENCES ad_sets(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

-- Таблица для хранения статистики
CREATE TABLE ad_insights (
    id VARCHAR(255) PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    entity_type ENUM('campaign', 'adset', 'ad') NOT NULL,
    date_start DATE NOT NULL,
    date_stop DATE NOT NULL,
    impressions INT,
    clicks INT,
    spend DECIMAL(15, 2),
    cpc DECIMAL(15, 4),
    cpm DECIMAL(15, 4),
    ctr DECIMAL(15, 4),
    reach INT,
    frequency DECIMAL(15, 4),
    unique_clicks INT,
    unique_ctr DECIMAL(15, 4),
    actions JSON,
    action_values JSON,
    cost_per_action_type JSON,
    created_time DATETIME,
    raw_data JSON,
    INDEX idx_entity (entity_id, entity_type, date_start, date_stop)
);

-- Таблица для хранения конфигурации
CREATE TABLE config (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value TEXT,
    description TEXT,
    created_time DATETIME,
    updated_time DATETIME
);
```

## 4. Настройка переменных окружения для подключения

В вашей Lambda функции или локальной среде разработки настройте следующие переменные окружения:

```
AURORA_HOST=facebook-ads-aurora-cluster.cluster-xxxxxxxx.region.rds.amazonaws.com
AURORA_MASTER_USERNAME=admin
AURORA_MASTER_PASSWORD=ваш_пароль
AURORA_DATABASE_NAME=facebook_ads_db
AURORA_PORT=3306
```

## 5. Тестирование подключения

Для тестирования подключения к базе данных используйте следующий код Python:

```python
import os
import pymysql
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def test_db_connection():
    try:
        # Подключение к базе данных
        connection = pymysql.connect(
            host=os.getenv('AURORA_HOST'),
            user=os.getenv('AURORA_MASTER_USERNAME'),
            password=os.getenv('AURORA_MASTER_PASSWORD'),
            database=os.getenv('AURORA_DATABASE_NAME'),
            port=int(os.getenv('AURORA_PORT', 3306))
        )
        
        # Создание курсора
        with connection.cursor() as cursor:
            # Выполнение простого запроса
            cursor.execute("SELECT VERSION()")
            result = cursor.fetchone()
            print(f"Успешное подключение к базе данных. Версия: {result[0]}")
        
        # Закрытие соединения
        connection.close()
        return True
    
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {str(e)}")
        return False

if __name__ == "__main__":
    test_db_connection()
```

## 6. Мониторинг и оптимизация

### Настройка мониторинга

1. Перейдите в [AWS RDS Console](https://console.aws.amazon.com/rds/)
2. Выберите ваш кластер Aurora
3. Перейдите на вкладку "Monitoring"
4. Здесь вы можете просматривать метрики производительности и создавать оповещения

### Оптимизация производительности

1. **Индексы**: Добавьте индексы для часто используемых полей в запросах:

```sql
-- Пример добавления индекса для поля status в таблице campaigns
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- Пример добавления индекса для поля campaign_id в таблице ad_sets
CREATE INDEX idx_adsets_campaign_id ON ad_sets(campaign_id);
```

2. **Настройка параметров кластера**:
   - Перейдите в [AWS RDS Console](https://console.aws.amazon.com/rds/)
   - Выберите "Parameter groups" в левом меню
   - Создайте новую группу параметров или измените существующую
   - Настройте параметры в соответствии с вашими потребностями (например, увеличьте `innodb_buffer_pool_size`)

3. **Масштабирование**:
   - Для Aurora Serverless v2: Настройте минимальную и максимальную ёмкость (ACU)
   - Для Aurora Provisioned: Измените класс экземпляра или добавьте реплики чтения

## 7. Резервное копирование и восстановление

### Настройка автоматических резервных копий

1. Перейдите в [AWS RDS Console](https://console.aws.amazon.com/rds/)
2. Выберите ваш кластер Aurora
3. Перейдите на вкладку "Maintenance & backups"
4. Настройте период хранения резервных копий (1-35 дней)

### Создание ручной резервной копии (снимка)

1. Перейдите в [AWS RDS Console](https://console.aws.amazon.com/rds/)
2. Выберите ваш кластер Aurora
3. Нажмите "Actions" и выберите "Take snapshot"
4. Введите имя снимка и нажмите "Take snapshot"

### Восстановление из резервной копии

1. Перейдите в [AWS RDS Console](https://console.aws.amazon.com/rds/)
2. Выберите "Snapshots" в левом меню
3. Выберите снимок, из которого хотите восстановить
4. Нажмите "Actions" и выберите "Restore snapshot"
5. Следуйте инструкциям для создания нового кластера из снимка

## 8. Безопасность

### Шифрование данных

1. При создании кластера включите опцию "Enable encryption"
2. Для существующего кластера без шифрования:
   - Создайте снимок
   - Восстановите из снимка с включенным шифрованием

### Настройка SSL подключения

1. Загрузите сертификат Amazon RDS:
```bash
wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
```

2. Обновите код подключения:
```python
connection = pymysql.connect(
    host=os.getenv('AURORA_HOST'),
    user=os.getenv('AURORA_MASTER_USERNAME'),
    password=os.getenv('AURORA_MASTER_PASSWORD'),
    database=os.getenv('AURORA_DATABASE_NAME'),
    port=int(os.getenv('AURORA_PORT', 3306)),
    ssl={'ca': 'path/to/global-bundle.pem'}
)
```

### Управление доступом с помощью IAM

1. При создании кластера включите опцию "Enable IAM database authentication"
2. Создайте IAM политику для доступа к базе данных
3. Обновите код подключения для использования IAM аутентификации

## 9. Устранение неполадок

### Распространенные проблемы и решения

1. **Ошибка "Too many connections"**:
   - Увеличьте параметр `max_connections` в группе параметров
   - Используйте пул соединений в вашем приложении

2. **Медленные запросы**:
   - Включите логирование медленных запросов
   - Проанализируйте и оптимизируйте запросы
   - Добавьте индексы

3. **Ошибки подключения**:
   - Проверьте настройки группы безопасности
   - Проверьте сетевые настройки (VPC, подсети)
   - Проверьте правильность учетных данных

### Просмотр логов

1. Перейдите в [AWS RDS Console](https://console.aws.amazon.com/rds/)
2. Выберите ваш кластер Aurora
3. Перейдите на вкладку "Logs & events"
4. Здесь вы можете просматривать логи базы данных

## 10. Миграция данных

### Импорт данных

1. Подготовьте SQL файл с данными
2. Используйте команду mysql для импорта:
```bash
mysql -h facebook-ads-aurora-cluster.cluster-xxxxxxxx.region.rds.amazonaws.com -u admin -p facebook_ads_db < data.sql
```

### Экспорт данных

1. Используйте команду mysqldump для экспорта:
```bash
mysqldump -h facebook-ads-aurora-cluster.cluster-xxxxxxxx.region.rds.amazonaws.com -u admin -p facebook_ads_db > backup.sql
```

## Полезные ресурсы

- [Документация AWS Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- [Руководство по MySQL 8.0](https://dev.mysql.com/doc/refman/8.0/en/)
- [Руководство по оптимизации производительности Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Managing.Performance.html)
- [Руководство по безопасности Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.html)
