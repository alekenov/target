# Руководство по настройке Facebook Marketing API

Это руководство поможет вам настроить доступ к Facebook Marketing API для использования в проекте AWS Lambda Facebook Ads Reporting.

## 1. Создание приложения Facebook

1. Перейдите на [Facebook Developers](https://developers.facebook.com)
2. Нажмите "Мои приложения" в правом верхнем углу
3. Нажмите "Создать приложение"
4. Выберите тип приложения "Бизнес"
5. Введите название приложения и контактный email
6. Нажмите "Создать приложение"

## 2. Настройка приложения

1. В панели навигации приложения выберите "Добавить продукты"
2. Найдите "Marketing API" и нажмите "Настроить"
3. Перейдите в раздел "Инструменты" -> "Graph API Explorer"

## 3. Получение токена доступа

### Краткосрочный токен (для тестирования)

1. В Graph API Explorer выберите ваше приложение из выпадающего списка
2. Нажмите "Создать токен доступа"
3. Выберите разрешения:
   - `ads_management`
   - `ads_read`
   - `business_management`
4. Нажмите "Создать токен доступа"
5. Скопируйте полученный токен (срок действия - 1-2 часа)

### Долгосрочный токен (для продакшена)

1. Получите краткосрочный токен как описано выше
2. Используйте следующий запрос для обмена краткосрочного токена на долгосрочный:

```
curl -X GET "https://graph.facebook.com/v17.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

Замените:
- `YOUR_APP_ID` на ID вашего приложения
- `YOUR_APP_SECRET` на секрет вашего приложения
- `SHORT_LIVED_TOKEN` на краткосрочный токен

3. В ответе вы получите долгосрочный токен (срок действия - 60 дней)

## 4. Получение ID рекламного аккаунта

1. Перейдите в [Facebook Ads Manager](https://business.facebook.com/adsmanager/)
2. ID рекламного аккаунта отображается в URL в формате `act_XXXXXXXXXX`
3. Для использования в API вам нужна только числовая часть (без префикса `act_`)

## 5. Тестирование доступа к API

Проверьте доступ к API с помощью следующей команды:

```
curl -X GET "https://graph.facebook.com/v17.0/act_YOUR_AD_ACCOUNT_ID/campaigns?fields=name,status&access_token=YOUR_ACCESS_TOKEN"
```

Замените:
- `YOUR_AD_ACCOUNT_ID` на ID вашего рекламного аккаунта (без префикса `act_`)
- `YOUR_ACCESS_TOKEN` на полученный токен доступа

Если запрос успешен, вы получите JSON с информацией о кампаниях.

## 6. Управление разрешениями системных пользователей

Для продакшена рекомендуется настроить системного пользователя:

1. Перейдите в [Business Manager](https://business.facebook.com/settings/)
2. Выберите "Пользователи" -> "Системные пользователи"
3. Нажмите "Добавить" и создайте системного пользователя
4. Назначьте роль "Разработчик" или "Администратор"
5. В разделе "Добавить активы" предоставьте доступ к рекламному аккаунту
6. Выберите разрешения:
   - Управление кампаниями
   - Просмотр статистики
   - Управление рекламными аккаунтами

## 7. Обновление токенов

Долгосрочные токены действуют 60 дней. Для автоматического обновления:

1. Создайте функцию для обновления токена за 1-2 недели до истечения срока
2. Используйте тот же запрос для обмена, что и при получении долгосрочного токена
3. Сохраните новый токен в безопасном месте (AWS Secrets Manager, Parameter Store)

## 8. Лимиты API и оптимизация запросов

Facebook Marketing API имеет следующие ограничения:

- 200 запросов в час на пользователя
- Более высокие лимиты для приложений с расширенным доступом

Для оптимизации:

1. Используйте пакетные запросы (batch requests)
2. Запрашивайте только необходимые поля
3. Кэшируйте данные, которые меняются редко
4. Используйте инкрементальный подход для получения данных

## 9. Обработка ошибок

Общие ошибки и их решения:

- `(#17) User request limit reached`: Превышен лимит запросов. Добавьте задержку и повторите позже.
- `(#100) Unsupported get request`: Неверный формат запроса или отсутствуют разрешения.
- `(#200) Access to this data is temporarily disabled`: Временное ограничение доступа.
- `(#2635) You are calling a deprecated version of the Ads API`: Используйте актуальную версию API.

## 10. Версионирование API

Facebook Marketing API использует версионирование в формате `v{major}.{minor}`:

- Новые версии выпускаются ежеквартально
- Каждая версия поддерживается 2 года
- Рекомендуется обновлять версию API каждые 6-12 месяцев

## Полезные ресурсы

- [Документация Facebook Marketing API](https://developers.facebook.com/docs/marketing-apis/)
- [Руководство по токенам доступа](https://developers.facebook.com/docs/facebook-login/access-tokens/)
- [Инструмент Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- [Руководство по системным пользователям](https://developers.facebook.com/docs/marketing-api/system-users/)
- [Лимиты и ограничения API](https://developers.facebook.com/docs/marketing-api/rate-limiting/)
