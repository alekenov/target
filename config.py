"""
Configuration settings for Facebook Ads reporting system.
Contains all necessary parameters and settings for:
- Facebook Marketing API credentials
- Database connection settings
- Logging configuration
- Report parameters
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Facebook API Settings
FB_APP_ID = os.getenv('FB_APP_ID') or os.getenv('FACEBOOK_APP_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
FB_ACCOUNT_ID = os.getenv('FB_ACCOUNT_ID') or os.getenv('FACEBOOK_AD_ACCOUNT_ID')

if not all([FB_APP_ID, FB_ACCESS_TOKEN, FB_ACCOUNT_ID]):
    raise ValueError("Missing required Facebook API credentials in environment variables")

# Database Settings
DB_CONFIG = {
    'host': os.getenv('AURORA_HOST'),
    'user': os.getenv('AURORA_MASTER_USERNAME'),
    'password': os.getenv('AURORA_MASTER_PASSWORD'),
    'database': os.getenv('AURORA_DATABASE_NAME'),
    'port': int(os.getenv('AURORA_PORT', 3306))
}

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Logging Configuration
LOG_CONFIG = {
    'filename': BASE_DIR / 'fb_ad_report.log',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'level': 'INFO'
}

# Report Settings
REPORT_CONFIG = {
    'default_date_range': 7,  # Days
    'metrics': [
        'spend',
        'impressions',
        'clicks',
        'ctr',
        'cpc',
        'reach',
        'frequency'
    ],
    'currency': 'USD',
    'time_increment': 1,  # Daily reports
}

# API Request Settings
API_CONFIG = {
    'max_retries': 3,
    'retry_delay': 5,  # seconds
    'timeout': 300,    # seconds
    'batch_size': 100  # Number of objects per request
}

# Cache Settings
CACHE_CONFIG = {
    'enabled': True,
    'expire_time': 3600,  # 1 hour in seconds
    'directory': BASE_DIR / '.cache'
}

# Campaign Management Settings
CAMPAIGN_CONFIG = {
    'budget_threshold': 1000,  # Maximum daily budget
    'performance_metrics': {
        'min_ctr': 0.1,
        'max_cpc': 2.0,
        'min_roas': 2.0
    }
}

def get_date_range(days=None):
    """Get start and end dates for report generation"""
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days or REPORT_CONFIG['default_date_range'])
    return start_date, end_date
