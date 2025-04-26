-- Set default character set and collation
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

-- Create campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id VARCHAR(255) PRIMARY KEY COLLATE utf8mb4_unicode_ci,
    name VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
    daily_budget DECIMAL(15,2),
    lifetime_budget DECIMAL(15,2),
    start_time DATETIME,
    stop_time DATETIME,
    created_time DATETIME,
    updated_time DATETIME,
    last_sync DATETIME,
    INDEX status_idx (status),
    INDEX created_time_idx (created_time),
    INDEX start_time_idx (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add last_sync column if it doesn't exist
SET @dbname = DATABASE();
SET @tablename = "campaigns";
SET @columnname = "last_sync";
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  "SELECT 1",
  "ALTER TABLE campaigns ADD COLUMN last_sync DATETIME"
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Create ad_sets table
CREATE TABLE IF NOT EXISTS ad_sets (
    id VARCHAR(255) PRIMARY KEY COLLATE utf8mb4_unicode_ci,
    campaign_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    name VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
    daily_budget DECIMAL(15,2),
    lifetime_budget DECIMAL(15,2),
    targeting JSON,
    created_time DATETIME,
    updated_time DATETIME,
    last_sync_time DATETIME,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    INDEX campaign_id_idx (campaign_id),
    INDEX status_idx (status),
    INDEX created_time_idx (created_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create ads table
CREATE TABLE IF NOT EXISTS ads (
    id VARCHAR(255) PRIMARY KEY COLLATE utf8mb4_unicode_ci,
    ad_set_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    name VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
    creative JSON,
    created_time DATETIME,
    updated_time DATETIME,
    last_sync_time DATETIME,
    FOREIGN KEY (ad_set_id) REFERENCES ad_sets(id),
    INDEX ad_set_id_idx (ad_set_id),
    INDEX status_idx (status),
    INDEX created_time_idx (created_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create ad_insights table
CREATE TABLE IF NOT EXISTS ad_insights (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ad_id VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    date DATE,
    impressions INT,
    clicks INT,
    spend DECIMAL(15,2),
    ctr DECIMAL(10,4),
    cpc DECIMAL(10,2),
    conversions INT,
    created_time DATETIME,
    last_sync_time DATETIME,
    FOREIGN KEY (ad_id) REFERENCES ads(id),
    UNIQUE KEY ad_date_idx (ad_id, date),
    INDEX date_idx (date),
    INDEX spend_idx (spend),
    INDEX ad_id_date_idx (ad_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create config table
CREATE TABLE IF NOT EXISTS config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(255) UNIQUE COLLATE utf8mb4_unicode_ci,
    value TEXT COLLATE utf8mb4_unicode_ci,
    description TEXT COLLATE utf8mb4_unicode_ci,
    updated_time DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create sync_state table
CREATE TABLE IF NOT EXISTS sync_state (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(50) COLLATE utf8mb4_unicode_ci,
    last_sync DATETIME,
    status VARCHAR(50) COLLATE utf8mb4_unicode_ci,
    error_message TEXT COLLATE utf8mb4_unicode_ci,
    updated_at DATETIME,
    UNIQUE KEY `entity_type_idx` (entity_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert initial sync states
INSERT IGNORE INTO sync_state (entity_type, status, updated_at) VALUES
('campaigns', 'PENDING', NOW()),
('ad_sets', 'PENDING', NOW()),
('ads', 'PENDING', NOW()),
('insights', 'PENDING', NOW());
