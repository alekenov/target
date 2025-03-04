from setuptools import setup, find_packages

setup(
    name="facebook_ads_toolkit",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "facebook-business>=17.0.0",
        "python-dotenv>=1.0.0",
        "PyMySQL>=1.1.0",
        "requests>=2.31.0",
        "typing-extensions>=4.8.0"
    ],
    author="Chingis Alekenov",
    author_email="alekenov@gmail.com",
    description="Инструменты для работы с Facebook Ads API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/alekenov/facebook-ads-toolkit",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 