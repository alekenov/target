#!/usr/bin/env python
"""
Скрипт-обертка для запуска инструмента отслеживания изменений в рекламном кабинете Facebook.
"""

import sys
import os
from facebook_ads_toolkit.cli.track_changes import main

if __name__ == "__main__":
    sys.exit(main()) 