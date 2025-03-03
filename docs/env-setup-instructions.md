# Настройка переменных окружения для Facebook Ads Reporting

Этот документ содержит инструкции по настройке переменных окружения, необходимых для работы Lambda функции отчетов по рекламным кампаниям Facebook.

## Переменные окружения

Для работы проекта необходимо настроить следующие переменные окружения:

### Facebook API

| Переменная | Описание | Как получить |
|------------|----------|-------------|
| `FACEBOOK_APP_ID` | ID приложения Facebook | Создайте приложение в [Facebook Developers](https://developers.facebook.com) |
| `FACEBOOK_APP_SECRET` | Секрет приложения Facebook | Доступен в настройках приложения Facebook |
| `FACEBOOK_ACCESS_TOKEN` | Токен доступа Facebook | Получите через [Graph API Explorer](https://developers.facebook.com/tools/explorer/) |
| `FACEBOOK_AD_ACCOUNT_ID` | ID рекламного аккаунта | Доступен в [Facebook Ads Manager](https://business.facebook.com/adsmanager/) |

### AWS

| Переменная | Описание | Как получить |
|------------|----------|-------------|
| `S3_BUCKET_NAME` | Имя S3 бакета для хранения отчетов | Создайте бакет в [AWS S3 Console](https://console.aws.amazon.com/s3/) |

### Telegram

| Переменная | Описание | Как получить |
|------------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота Telegram | Создайте бота через [BotFather](https://t.me/botfather) |
| `TELEGRAM_CHAT_ID` | ID чата Telegram | Используйте бота [@userinfobot](https://t.me/userinfobot) |

### База данных Aurora

| Переменная | Описание | Как получить |
|------------|----------|-------------|
| `AURORA_HOST` | Хост базы данных Aurora | Доступен в [AWS RDS Console](https://console.aws.amazon.com/rds/) |
| `AURORA_MASTER_USERNAME` | Имя пользователя базы данных | Указывается при создании кластера Aurora |
| `AURORA_MASTER_PASSWORD` | Пароль базы данных | Указывается при создании кластера Aurora |
| `AURORA_DATABASE_NAME` | Имя базы данных | По умолчанию `facebook_ads_db` |
| `AURORA_PORT` | Порт базы данных | По умолчанию `3306` |

## Создание файла .env

Для локальной разработки создайте файл `.env` в корне проекта со следующим содержимым:

```
# Facebook API
FACEBOOK_APP_ID=ваш_app_id
FACEBOOK_APP_SECRET=ваш_app_secret
FACEBOOK_ACCESS_TOKEN=ваш_access_token
FACEBOOK_AD_ACCOUNT_ID=ваш_ad_account_id

# AWS
S3_BUCKET_NAME=fb-ads-reports-bucket

# Telegram
TELEGRAM_BOT_TOKEN=токен_бота_telegram
TELEGRAM_CHAT_ID=id_чата_telegram

# База данных Aurora
AURORA_HOST=ваш_хост_aurora
AURORA_MASTER_USERNAME=admin
AURORA_MASTER_PASSWORD=ваш_пароль
AURORA_DATABASE_NAME=facebook_ads_db
AURORA_PORT=3306
```

## Настройка переменных окружения в AWS Lambda

При развертывании Lambda функции через AWS Console или CloudFormation, необходимо указать все переменные окружения в разделе "Environment variables".

## Получение токена доступа Facebook

1. Перейдите на [Facebook Developers](https://developers.facebook.com) и создайте приложение
2. В настройках приложения добавьте продукт "Marketing API"
3. Перейдите в [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
4. Выберите ваше приложение и запросите следующие разрешения:
   - `ads_management`
   - `ads_read`
   - `business_management`
5. Нажмите "Generate Access Token"
6. Используйте полученный токен в переменной `FACEBOOK_ACCESS_TOKEN`

**Примечание**: Токены доступа Facebook имеют ограниченный срок действия. Для продакшена рекомендуется использовать долгосрочные токены или настроить автоматическое обновление токенов.

## Получение ID рекламного аккаунта

1. Перейдите в [Facebook Ads Manager](https://business.facebook.com/adsmanager/)
2. ID рекламного аккаунта отображается в URL в формате `act_XXXXXXXXXX`
3. Используйте только числовую часть (без префикса `act_`) в переменной `FACEBOOK_AD_ACCOUNT_ID`

## Создание бота Telegram

1. Откройте Telegram и найдите [@BotFather](https://t.me/botfather)
2. Отправьте команду `/newbot` и следуйте инструкциям
3. После создания бота вы получите токен, который нужно использовать в переменной `TELEGRAM_BOT_TOKEN`
4. Чтобы получить ID чата, добавьте бота в чат и отправьте сообщение
5. Перейдите по URL `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates` (замените YOUR_BOT_TOKEN на ваш токен)
6. В ответе найдите значение `chat.id` и используйте его в переменной `TELEGRAM_CHAT_ID`

## Безопасность

- Никогда не включайте файл `.env` в систему контроля версий
- Используйте AWS Secrets Manager или Parameter Store для хранения секретов в продакшене
- Регулярно обновляйте токены доступа и пароли
- Ограничьте доступ к базе данных с помощью групп безопасности AWS
