# Развертывание Facebook Ads Dashboard на AWS EC2

## Подготовка

1. Создайте EC2 инстанс в AWS Console:
   - Amazon Linux 2 или Ubuntu Server 20.04
   - Тип инстанса: t2.micro (достаточно для начала)
   - Настройте Security Group, чтобы открыть порты:
     - 22 (SSH)
     - 80 (HTTP)
     - 443 (HTTPS)

2. Подключитесь к инстансу через SSH:
   ```
   ssh -i your-key.pem ec2-user@your-instance-ip
   ```

## Установка необходимых пакетов

Для Amazon Linux 2:
```bash
# Обновление системы
sudo yum update -y

# Установка Python и pip
sudo yum install python3 python3-pip -y

# Установка nginx
sudo amazon-linux-extras install nginx1 -y
sudo systemctl start nginx
sudo systemctl enable nginx

# Установка зависимостей
pip3 install flask pymysql pandas python-dotenv gunicorn
```

Для Ubuntu:
```bash
# Обновление системы
sudo apt update
sudo apt upgrade -y

# Установка Python и pip
sudo apt install python3 python3-pip -y

# Установка nginx
sudo apt install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx

# Установка зависимостей
pip3 install flask pymysql pandas python-dotenv gunicorn
```

## Загрузка кода дашборда

1. Создайте директорию для приложения:
```bash
sudo mkdir -p /var/www/dashboard
sudo chown $USER:$USER /var/www/dashboard
```

2. Загрузите файлы вашего проекта в эту директорию:
```bash
# Вариант 1: Через SCP
scp -i your-key.pem -r /path/to/your/local/project/* ec2-user@your-instance-ip:/var/www/dashboard/

# Вариант 2: Через Git
cd /var/www/dashboard
git clone your-repository-url .
```

3. Создайте файл .env с переменными окружения:
```bash
cd /var/www/dashboard
nano .env
```

Добавьте все необходимые переменные окружения:
```
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_ACCESS_TOKEN=your_access_token
FACEBOOK_AD_ACCOUNT_ID=your_account_id
AURORA_HOST=your_aurora_host
AURORA_MASTER_USERNAME=your_username
AURORA_MASTER_PASSWORD=your_password
AURORA_DATABASE_NAME=your_database
AURORA_PORT=3306
```

## Настройка Gunicorn

1. Создайте файл конфигурации systemd для Gunicorn:
```bash
sudo nano /etc/systemd/system/dashboard.service
```

2. Добавьте следующее содержимое:
```
[Unit]
Description=Gunicorn instance to serve Facebook Ads Dashboard
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/var/www/dashboard
Environment="PATH=/var/www/dashboard/venv/bin"
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 0.0.0.0:5003 --access-logfile /var/log/dashboard/access.log --error-logfile /var/log/dashboard/error.log simple_dashboard:app

[Install]
WantedBy=multi-user.target
```

3. Создайте директорию для логов:
```bash
sudo mkdir -p /var/log/dashboard
sudo chown $USER:$USER /var/log/dashboard
```

4. Запустите и включите сервис:
```bash
sudo systemctl start dashboard
sudo systemctl enable dashboard
sudo systemctl status dashboard
```

## Настройка Nginx

1. Создайте конфигурационный файл Nginx:
```bash
sudo nano /etc/nginx/conf.d/dashboard.conf
```

2. Добавьте следующее содержимое:
```
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Проверьте конфигурацию Nginx и перезапустите:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

## Настройка SSL (опционально, но рекомендуется)

1. Установите Certbot:
```bash
# Для Amazon Linux 2
sudo amazon-linux-extras install epel -y
sudo yum install certbot python-certbot-nginx -y

# Для Ubuntu
sudo apt install certbot python3-certbot-nginx -y
```

2. Получите SSL-сертификат:
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

3. Следуйте инструкциям Certbot для настройки автоматического обновления сертификата.

## Проверка работоспособности

1. Откройте ваш домен в браузере:
```
http://your-domain.com
```

2. Если вы настроили SSL, используйте HTTPS:
```
https://your-domain.com
```

## Обновление дашборда

Для обновления кода дашборда:
```bash
cd /var/www/dashboard
git pull  # если вы используете Git

# Перезапустите сервис
sudo systemctl restart dashboard
```

## Мониторинг и логи

Проверка логов Gunicorn:
```bash
tail -f /var/log/dashboard/error.log
tail -f /var/log/dashboard/access.log
```

Проверка логов Nginx:
```bash
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

Проверка статуса сервиса:
```bash
sudo systemctl status dashboard
```
