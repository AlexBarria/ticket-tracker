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
    has_ground_truth BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Ground truth table for corrected ticket values
CREATE TABLE IF NOT EXISTS ticket_ground_truth (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER UNIQUE REFERENCES tickets(id) ON DELETE CASCADE,
    corrected_merchant VARCHAR(255),
    corrected_date DATE,
    corrected_amount NUMERIC(10, 2),
    corrected_items JSONB,
    corrected_by VARCHAR(255),
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

-- Agent 1 (OCR/Formatter) Evaluation Tables
CREATE TABLE IF NOT EXISTS agent1_evaluation_runs (
    id SERIAL PRIMARY KEY,
    run_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_tickets INT,
    successful_tickets INT,

    -- Deterministic metrics (averages)
    average_merchant_match NUMERIC(5, 4),
    average_date_match NUMERIC(5, 4),
    average_amount_match NUMERIC(5, 4),
    average_item_precision NUMERIC(5, 4),
    average_item_recall NUMERIC(5, 4),
    average_item_f1 NUMERIC(5, 4),

    -- LLM-as-Judge metrics (averages)
    average_merchant_similarity NUMERIC(5, 4),
    average_items_similarity NUMERIC(5, 4),
    average_overall_quality NUMERIC(5, 4),

    run_metadata JSONB
);

-- Individual Agent 1 evaluation results
CREATE TABLE IF NOT EXISTS agent1_evaluation_results (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES agent1_evaluation_runs(run_id),
    test_id VARCHAR(50),
    filename VARCHAR(255),

    -- Ground truth data
    expected_merchant VARCHAR(255),
    expected_date DATE,
    expected_amount NUMERIC(10, 2),
    expected_items JSONB,

    -- Agent 1 output
    actual_merchant VARCHAR(255),
    actual_date DATE,
    actual_amount NUMERIC(10, 2),
    actual_items JSONB,

    -- Deterministic metrics
    merchant_exact_match BOOLEAN,
    date_exact_match BOOLEAN,
    amount_exact_match BOOLEAN,
    item_precision NUMERIC(5, 4),
    item_recall NUMERIC(5, 4),
    item_f1 NUMERIC(5, 4),

    -- LLM-as-Judge metrics
    merchant_similarity_score NUMERIC(5, 4),
    items_similarity_score NUMERIC(5, 4),
    overall_quality_score NUMERIC(5, 4),
    llm_feedback TEXT,

    processing_time_ms INT,
    evaluation_status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent1_eval_runs_started ON agent1_evaluation_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent1_eval_results_run_id ON agent1_evaluation_results(run_id);

-- Comments for Agent 1 evaluation tables
COMMENT ON TABLE agent1_evaluation_runs IS 'Tracking table for Agent 1 (OCR/Formatter) evaluation runs';
COMMENT ON TABLE agent1_evaluation_results IS 'Individual ticket results for each Agent 1 evaluation run';
COMMENT ON COLUMN agent1_evaluation_runs.run_id IS 'Unique identifier for each evaluation run';
COMMENT ON COLUMN agent1_evaluation_runs.run_type IS 'Type of evaluation run (sample, manual, realtime)';
COMMENT ON COLUMN agent1_evaluation_runs.average_merchant_match IS 'Average exact match rate for merchant names';
COMMENT ON COLUMN agent1_evaluation_runs.average_item_f1 IS 'Average F1 score for item extraction';
COMMENT ON COLUMN agent1_evaluation_runs.average_merchant_similarity IS 'Average LLM-judged similarity for merchant names';
COMMENT ON COLUMN agent1_evaluation_results.merchant_exact_match IS 'Whether merchant name matches exactly';
COMMENT ON COLUMN agent1_evaluation_results.item_precision IS 'Precision score for extracted items';
COMMENT ON COLUMN agent1_evaluation_results.item_recall IS 'Recall score for extracted items';
COMMENT ON COLUMN agent1_evaluation_results.merchant_similarity_score IS 'LLM-judged semantic similarity for merchant name';
COMMENT ON COLUMN agent1_evaluation_results.overall_quality_score IS 'LLM-judged overall extraction quality';