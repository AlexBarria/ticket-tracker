-- This script initializes the database schema for the tickets.
-- It will be executed automatically when the PostgreSQL container starts for the first time.

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    merchant_name VARCHAR(255),
    transaction_date DATE,
    total_amount NUMERIC(10, 2),
    items JSONB,
    category VARCHAR(100),
    s3_path VARCHAR(512),
    user_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- You can add more data if needed, but it's optional
INSERT INTO tickets (merchant_name, transaction_date, total_amount, category, s3_path, user_id) VALUES
('Example Restaurant', '2025-07-15', 50.00, 'Restaurant', 's3://bucket/user/file.jpg', 'user_id_123');