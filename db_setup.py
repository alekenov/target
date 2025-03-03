"""
Database setup script for Facebook Ads reporting system.
Creates all necessary tables and indexes for storing Facebook Ads data.
"""
import logging
import pymysql
import os
import sys
from config import DB_CONFIG, LOG_CONFIG

# Configure logging
logging.basicConfig(
    filename=LOG_CONFIG['filename'],
    format=LOG_CONFIG['format'],
    level=getattr(logging, LOG_CONFIG['level'])
)
logger = logging.getLogger('db_setup')

def create_connection():
    """Create a connection to the database"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        logger.info("Database connection established")
        return connection
    except pymysql.MySQLError as e:
        logger.error(f"Error connecting to the database: {e}")
        sys.exit(1)

def create_database(connection, database_name):
    """Create the database if it doesn't exist"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
            cursor.execute(f"USE {database_name}")
            logger.info(f"Database '{database_name}' created or already exists")
    except pymysql.MySQLError as e:
        logger.error(f"Error creating database: {e}")
        sys.exit(1)

def create_tables(connection):
    """Create all necessary tables for the Facebook Ads data"""
    try:
        with connection.cursor() as cursor:
            # Create campaigns table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                daily_budget DECIMAL(10, 2),
                lifetime_budget DECIMAL(10, 2),
                start_time DATETIME,
                stop_time DATETIME,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_status (status),
                INDEX idx_start_time (start_time),
                INDEX idx_updated_time (updated_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("Table 'campaigns' created or already exists")
            
            # Create ad_sets table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ad_sets (
                id VARCHAR(50) PRIMARY KEY,
                campaign_id VARCHAR(50) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                daily_budget DECIMAL(10, 2),
                lifetime_budget DECIMAL(10, 2),
                targeting JSON,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_campaign_id (campaign_id),
                INDEX idx_status (status),
                INDEX idx_updated_time (updated_time),
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("Table 'ad_sets' created or already exists")
            
            # Create ads table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id VARCHAR(50) PRIMARY KEY,
                ad_set_id VARCHAR(50) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                creative JSON,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_ad_set_id (ad_set_id),
                INDEX idx_status (status),
                INDEX idx_updated_time (updated_time),
                FOREIGN KEY (ad_set_id) REFERENCES ad_sets(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("Table 'ads' created or already exists")
            
            # Create ad_insights table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ad_insights (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                ad_id VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                impressions INT UNSIGNED DEFAULT 0,
                clicks INT UNSIGNED DEFAULT 0,
                spend DECIMAL(10, 2) DEFAULT 0.00,
                ctr DECIMAL(5, 4) DEFAULT 0.0000,
                cpc DECIMAL(10, 2) DEFAULT 0.00,
                conversions INT UNSIGNED DEFAULT 0,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ad_id (ad_id),
                INDEX idx_date (date),
                INDEX idx_created_time (created_time),
                UNIQUE KEY unique_ad_date (ad_id, date),
                FOREIGN KEY (ad_id) REFERENCES ads(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("Table 'ad_insights' created or already exists")
            
            # Create config table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                config_key VARCHAR(100) PRIMARY KEY,
                config_value TEXT,
                updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            logger.info("Table 'config' created or already exists")
            
        connection.commit()
        logger.info("All tables created successfully")
    except pymysql.MySQLError as e:
        logger.error(f"Error creating tables: {e}")
        connection.rollback()
        sys.exit(1)

def initialize_config(connection):
    """Initialize default configuration values"""
    try:
        with connection.cursor() as cursor:
            # Check if config table has entries
            cursor.execute("SELECT COUNT(*) FROM config")
            count = cursor.fetchone()[0]
            
            # Only insert default values if table is empty
            if count == 0:
                default_configs = [
                    ('last_data_fetch', None),
                    ('daily_budget_threshold', '1000.00'),
                    ('min_acceptable_ctr', '0.01'),
                    ('max_acceptable_cpc', '2.00'),
                    ('report_recipients', '[]'),
                    ('api_request_limit', '100')
                ]
                
                cursor.executemany(
                    "INSERT INTO config (config_key, config_value) VALUES (%s, %s)",
                    default_configs
                )
                connection.commit()
                logger.info("Default configuration values initialized")
    except pymysql.MySQLError as e:
        logger.error(f"Error initializing config: {e}")
        connection.rollback()

def main():
    """Main function to set up the database"""
    logger.info("Starting database setup")
    
    # Create connection
    connection = create_connection()
    
    try:
        # Create database if it doesn't exist
        create_database(connection, DB_CONFIG['database'])
        
        # Create tables
        create_tables(connection)
        
        # Initialize default configuration
        initialize_config(connection)
        
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Unexpected error during database setup: {e}")
    finally:
        connection.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    main()
