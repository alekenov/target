CREATE TABLE IF NOT EXISTS collection_checkpoints (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    collection_type VARCHAR(50) NOT NULL,
    last_processed_id VARCHAR(255) NOT NULL,
    processed_items INT NOT NULL,
    total_items INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    metadata JSON,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_collection_type (collection_type),
    INDEX idx_status (status),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; 