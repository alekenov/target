"""Configuration settings for the Facebook Ads Toolkit."""
import os
import logging.config
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

# Database Connection Pool Configuration
DB_POOL_MIN_CONNECTIONS = int(os.getenv('DB_POOL_MIN_CONNECTIONS', '3'))
DB_POOL_MAX_CONNECTIONS = int(os.getenv('DB_POOL_MAX_CONNECTIONS', '10'))
DB_POOL_CONNECTION_TIMEOUT = int(os.getenv('DB_POOL_CONNECTION_TIMEOUT', '30'))
DB_POOL_MAX_CONNECTION_AGE = int(os.getenv('DB_POOL_MAX_CONNECTION_AGE', '3600'))  # 1 час

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

# Centralized Logging Configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'detailed',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'facebook_ads_toolkit.log',
            'maxBytes': 10485760,  # 10 МБ
            'backupCount': 10
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True
        },
        'facebook_ads_toolkit': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'facebook_business': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}


def setup_logging(log_level=None):
    """
    Настраивает логирование для всего приложения.
    
    Args:
        log_level: Уровень логирования (опционально)
    """
    if log_level:
        LOGGING_CONFIG['loggers']['facebook_ads_toolkit']['level'] = log_level
        LOGGING_CONFIG['loggers']['']['level'] = log_level
    
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.debug("Логирование настроено")


def get_performance_metrics(execution_time, operation_name):
    """
    Форматирует метрики производительности для логирования.
    
    Args:
        execution_time: Время выполнения операции
        operation_name: Название операции
        
    Returns:
        dict: Метрики производительности
    """
    return {
        'execution_time_ms': int(execution_time * 1000),
        'operation': operation_name
    }
