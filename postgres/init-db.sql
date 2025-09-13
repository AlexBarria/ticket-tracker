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

-- Comments to help understand the schema
COMMENT ON TABLE tickets IS 'Table with uploaded receipts data';
COMMENT ON COLUMN tickets.id IS 'Primary key of the ticket';
COMMENT ON COLUMN tickets.merchant_name IS 'Name of the merchant where the transaction took place';
COMMENT ON COLUMN tickets.transaction_date IS 'Date of the transaction';
COMMENT ON COLUMN tickets.total_amount IS 'Total amount of the transaction';
COMMENT ON COLUMN tickets.items IS 'JSON array of items purchased in the transaction';
COMMENT ON COLUMN tickets.category IS 'Category of the transaction (e.g., Restaurant, Grocery)';
COMMENT ON COLUMN tickets.s3_path IS 'S3 path to the uploaded receipt image';
COMMENT ON COLUMN tickets.user_id IS 'ID of the user who uploaded the receipt';
COMMENT ON COLUMN tickets.created_at IS 'Timestamp when the record was created';

-- You can add more data if needed, but it's optional
INSERT INTO tickets (merchant_name, transaction_date, total_amount, category, s3_path, user_id) VALUES
('Example Restaurant', '2025-07-15', 50.00, 'Restaurant', 's3://bucket/user/file.jpg', 'user_id_123');