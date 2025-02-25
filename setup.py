#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="facebook_ads_toolkit",
    version="0.1.0",
    description="Инструменты для управления и анализа рекламных кампаний Facebook",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "facebook-business",
        "python-telegram-bot",
        "pandas",
        "matplotlib",
        "pyyaml",
        "python-dotenv"
    ],
    python_requires=">=3.7",
) 