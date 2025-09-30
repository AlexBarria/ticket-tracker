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
    need_verify BOOLEAN,
    approved BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW approved_tickets AS SELECT * FROM tickets WHERE approved = TRUE;

-- Comments to help understand the schema
COMMENT ON VIEW approved_tickets IS 'Table with uploaded receipts data';
COMMENT ON COLUMN approved_tickets.id IS 'Primary key of the ticket';
COMMENT ON COLUMN approved_tickets.merchant_name IS 'Name of the merchant where the transaction took place';
COMMENT ON COLUMN approved_tickets.transaction_date IS 'Date of the transaction';
COMMENT ON COLUMN approved_tickets.total_amount IS 'Total amount of the transaction';
COMMENT ON COLUMN approved_tickets.items IS 'JSON array of items purchased in the transaction';
COMMENT ON COLUMN approved_tickets.category IS 'Category of the transaction (e.g., Restaurant, Grocery)';
COMMENT ON COLUMN approved_tickets.s3_path IS 'S3 path to the uploaded receipt image';
COMMENT ON COLUMN approved_tickets.user_id IS 'ID of the user who uploaded the receipt';
COMMENT ON COLUMN approved_tickets.need_verify IS 'Indicates if the ticket needs verification';
COMMENT ON COLUMN approved_tickets.approved IS 'Indicates if the ticket has been approved';
COMMENT ON COLUMN approved_tickets.created_at IS 'Timestamp when the record was created';

-- You can add more data if needed, but it's optional
INSERT INTO tickets (merchant_name, transaction_date, total_amount, category, s3_path, user_id) VALUES
('Example Restaurant', '2025-07-15', 50.00, 'Restaurant', 's3://bucket/user/file.jpg', 'user_id_123');

-- Evaluation runs tracking
CREATE TABLE IF NOT EXISTS evaluation_runs (
    id SERIAL PRIMARY KEY,
    run_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_queries INT,
    successful_queries INT,
    average_faithfulness NUMERIC(5, 4),
    average_answer_relevance NUMERIC(5, 4),
    average_context_precision NUMERIC(5, 4),
    average_context_recall NUMERIC(5, 4),
    metadata JSONB
);

-- Individual query results
CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES evaluation_runs(run_id),
    query_id VARCHAR(20),
    query_text TEXT NOT NULL,
    generated_answer TEXT,
    retrieved_context TEXT,
    reference_answer TEXT,

    -- RAGAS metrics
    faithfulness_score NUMERIC(5, 4),
    answer_relevance_score NUMERIC(5, 4),
    context_precision_score NUMERIC(5, 4),
    context_recall_score NUMERIC(5, 4),

    response_time_ms INT,
    token_count INT,
    evaluation_status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_started ON evaluation_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_eval_results_run_id ON evaluation_results(run_id);

-- Comments for evaluation tables
COMMENT ON TABLE evaluation_runs IS 'Tracking table for RAGAS evaluation runs';
COMMENT ON TABLE evaluation_results IS 'Individual query results for each evaluation run';
COMMENT ON COLUMN evaluation_runs.run_id IS 'Unique identifier for each evaluation run';
COMMENT ON COLUMN evaluation_runs.run_type IS 'Type of evaluation run (manual, scheduled, etc.)';
COMMENT ON COLUMN evaluation_runs.status IS 'Current status of the evaluation run';
COMMENT ON COLUMN evaluation_results.run_id IS 'Reference to the evaluation run';
COMMENT ON COLUMN evaluation_results.query_id IS 'Identifier for the test query';
COMMENT ON COLUMN evaluation_results.faithfulness_score IS 'RAGAS faithfulness metric score';
COMMENT ON COLUMN evaluation_results.answer_relevance_score IS 'RAGAS answer relevance metric score';
COMMENT ON COLUMN evaluation_results.context_precision_score IS 'RAGAS context precision metric score';
COMMENT ON COLUMN evaluation_results.context_recall_score IS 'RAGAS context recall metric score';