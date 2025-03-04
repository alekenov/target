"""Configuration settings for the Facebook Ads Toolkit."""
import os
from dotenv import load_dotenv

load_dotenv()

# Facebook API Configuration
FB_APP_ID = os.getenv('FB_APP_ID')
FB_APP_SECRET = os.getenv('FB_APP_SECRET')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
FB_ACCOUNT_ID = os.getenv('FB_ACCOUNT_ID')

# Database Configuration
AURORA_HOST = os.getenv('AURORA_HOST', 'facebook-ads-aurora-cluster.cluster-cpciyms4a0o2.us-east-1.rds.amazonaws.com')
AURORA_PORT = int(os.getenv('AURORA_PORT', '3306'))
AURORA_USERNAME = os.getenv('AURORA_USERNAME', 'admin')
AURORA_PASSWORD = os.getenv('AURORA_PASSWORD')
AURORA_DATABASE = os.getenv('AURORA_DATABASE', 'facebook_ads_db')

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Database Tables
TABLES = {
    'campaigns': 'campaigns',
    'ad_sets': 'ad_sets',
    'ads': 'ads',
    'insights': 'ad_insights',
    'config': 'config',
    'sync_state': 'sync_state'
}

# Default Database Collation
DEFAULT_COLLATION = 'utf8mb4_unicode_ci'

# API Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Reporting Configuration
CURRENCY_FORMAT = '${:,.2f}'
PERCENTAGE_FORMAT = '{:.1f}%'
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Trend Indicators
TREND_UP = '▲'
TREND_DOWN = '▼'
TREND_NEUTRAL = '→'

# Performance Thresholds
SIGNIFICANT_CHANGE_THRESHOLD = 10  # percentage
