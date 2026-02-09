-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- User profiles table
CREATE TABLE user_profiles (
    user_id VARCHAR(50) PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    owned_components TEXT[] DEFAULT '{}',
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Slack messages table
CREATE TABLE slack_messages (
    message_id VARCHAR(100) PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL,
    thread_id VARCHAR(100),
    user_id VARCHAR(50) NOT NULL REFERENCES user_profiles(user_id),
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    entities JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main decisions table (parent)
CREATE TABLE decisions (
    decision_id SERIAL PRIMARY KEY,
    thread_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    author_user_id VARCHAR(50) NOT NULL REFERENCES user_profiles(user_id),
    decision_type VARCHAR(50) NOT NULL, -- requirement_change, design_decision, approval
    decision_text TEXT NOT NULL,
    affected_components TEXT[] DEFAULT '{}',
    referenced_reqs TEXT[] DEFAULT '{}',
    embedding vector(768),
    embedding_status VARCHAR(20) DEFAULT 'pending', -- pending, embedded, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decision details table (detail)
CREATE TABLE decision_details (
    decision_id INTEGER NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,
    detail_id SERIAL,
    detail_name VARCHAR(100) NOT NULL,
    detail_value JSONB NOT NULL,
    PRIMARY KEY (decision_id, detail_id)
);

-- Relationships between decisions
CREATE TABLE decision_relationships (
    relationship_id SERIAL PRIMARY KEY,
    source_decision_id INTEGER NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,
    target_decision_id INTEGER NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- IMPACTS, REFERENCES, CONFLICTS_WITH, DEPENDS_ON
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_decisions_timestamp ON decisions(timestamp DESC);
CREATE INDEX idx_decisions_components ON decisions USING GIN(affected_components);
CREATE INDEX idx_decisions_reqs ON decisions USING GIN(referenced_reqs);
CREATE INDEX idx_decisions_embedding ON decisions USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_slack_messages_thread ON slack_messages(thread_id);
CREATE INDEX idx_slack_messages_timestamp ON slack_messages(timestamp DESC);
CREATE INDEX idx_decision_relationships_source ON decision_relationships(source_decision_id);

-- Materialized view for fast digest queries
CREATE MATERIALIZED VIEW daily_decisions_summary AS
SELECT
    DATE(timestamp) as decision_date,
    decision_type,
    COUNT(*) as decision_count,
    array_agg(DISTINCT unnest(affected_components)) as all_components,
    array_agg(DISTINCT author_user_id) as involved_users
FROM decisions
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(timestamp), decision_type
ORDER BY decision_date DESC;

CREATE INDEX idx_daily_summary_date ON daily_decisions_summary(decision_date DESC);