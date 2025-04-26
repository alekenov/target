"""Facebook Ads Toolkit - инструменты для работы с Facebook Marketing API."""

import logging
from facebook_ads_toolkit.config import setup_logging

# Инициализация логирования
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Facebook Ads Toolkit инициализирован")

__version__ = '1.0.0'
