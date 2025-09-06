-- This script initializes the database schema for the tickets.
-- It will be executed automatically when the PostgreSQL container starts for the first time.

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    merchant_name VARCHAR(255),
    transaction_date DATE,
    total_amount NUMERIC(10, 2),
    items JSONB, -- To store a list of items, prices, etc.
    category VARCHAR(100),
    image_s3_path VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255) -- To associate the ticket with a user
);

-- You can add more tables or initial data if needed.
INSERT INTO tickets (merchant_name, transaction_date, total_amount) VALUES
('Example Restaurant', '2025-07-15', 50.00),
('Another Cafe', '2025-07-20', 50.00);

-- Note: MLflow requires its own database. The docker-compose setup
-- creates 'mlflow_db' for it, and MLflow manages its own schema.
-- This file is only for the 'tickets_db' application database.