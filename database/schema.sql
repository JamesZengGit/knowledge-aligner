-- Knowledge Aligner Database Schema
-- PostgreSQL with pgvector extension for hybrid retrieval

-- Enable pgvector extension for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop tables if they exist (for clean reinstall)
DROP TABLE IF EXISTS gap_priority CASCADE;
DROP TABLE IF EXISTS gaps CASCADE;
DROP TABLE IF EXISTS decision_relationships CASCADE;
DROP TABLE IF EXISTS decision_details CASCADE;
DROP TABLE IF EXISTS decisions CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS slack_messages CASCADE;

-- User profiles table
CREATE TABLE user_profiles (
    user_id VARCHAR(50) PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    owned_components TEXT[] NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Parent table: decisions
CREATE TABLE decisions (
    decision_id SERIAL PRIMARY KEY,
    thread_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    author_user_id VARCHAR(50) NOT NULL REFERENCES user_profiles(user_id),
    author_name VARCHAR(100) NOT NULL,
    author_role VARCHAR(50),
    decision_type VARCHAR(30) NOT NULL CHECK (decision_type IN ('requirement_change', 'design_decision', 'approval', 'technical_decision')),
    decision_text TEXT NOT NULL,
    affected_components TEXT[] NOT NULL,
    referenced_reqs TEXT[],
    similarity_score FLOAT,
    before_after JSONB,
    embedding vector(768), -- 768-dimensional embeddings from sentence-transformers
    embedding_status VARCHAR(20) DEFAULT 'pending' CHECK (embedding_status IN ('pending', 'embedded', 'stale', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Detail table for extended decision data (parent-detail pattern)
CREATE TABLE decision_details (
    detail_id SERIAL PRIMARY KEY,
    decision_id INTEGER NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,
    detail_name VARCHAR(50) NOT NULL,
    detail_value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(decision_id, detail_name)
);

-- Relationships between decisions
CREATE TABLE decision_relationships (
    relationship_id SERIAL PRIMARY KEY,
    source_decision_id INTEGER NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,
    target_decision_id INTEGER NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,
    relationship_type VARCHAR(30) NOT NULL CHECK (relationship_type IN ('IMPACTS', 'REFERENCES', 'CONFLICTS_WITH', 'DEPENDS_ON')),
    confidence FLOAT DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source_decision_id, target_decision_id, relationship_type)
);

-- Slack messages table for raw message storage
CREATE TABLE slack_messages (
    message_id VARCHAR(50) PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL,
    thread_id VARCHAR(50),
    user_id VARCHAR(50) NOT NULL REFERENCES user_profiles(user_id),
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    entities JSONB, -- Extracted entities from Claude Haiku
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_decisions_timestamp ON decisions (timestamp DESC);
CREATE INDEX idx_decisions_components ON decisions USING GIN (affected_components);
CREATE INDEX idx_decisions_reqs ON decisions USING GIN (referenced_reqs);
CREATE INDEX idx_decisions_author ON decisions (author_user_id);
CREATE INDEX idx_decisions_status ON decisions (embedding_status);
CREATE INDEX idx_decisions_type ON decisions (decision_type);

-- pgvector index for semantic similarity search (created after embeddings are populated)
-- This will be created later: CREATE INDEX idx_decisions_embedding ON decisions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_decision_details_decision_id ON decision_details (decision_id);
CREATE INDEX idx_decision_details_name ON decision_details (detail_name);

CREATE INDEX idx_relationships_source ON decision_relationships (source_decision_id);
CREATE INDEX idx_relationships_target ON decision_relationships (target_decision_id);
CREATE INDEX idx_relationships_type ON decision_relationships (relationship_type);

CREATE INDEX idx_slack_messages_user ON slack_messages (user_id);
CREATE INDEX idx_slack_messages_timestamp ON slack_messages (timestamp DESC);
CREATE INDEX idx_slack_messages_thread ON slack_messages (thread_id);
CREATE INDEX idx_slack_messages_processed ON slack_messages (processed);

-- Materialized view for fast digest queries
CREATE MATERIALIZED VIEW daily_decisions_summary AS
SELECT
    DATE(d.timestamp) as decision_date,
    d.author_user_id,
    d.decision_type,
    COUNT(*) as decision_count,
    array_agg(DISTINCT c.component) as all_components,
    array_agg(DISTINCT r.req) as all_reqs
FROM decisions d
LEFT JOIN LATERAL unnest(d.affected_components) AS c(component) ON TRUE
LEFT JOIN LATERAL unnest(d.referenced_reqs) AS r(req) ON TRUE
WHERE d.timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(d.timestamp), d.author_user_id, d.decision_type
ORDER BY decision_date DESC;

CREATE INDEX idx_daily_summary_date ON daily_decisions_summary (decision_date);
CREATE INDEX idx_daily_summary_author ON daily_decisions_summary (author_user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_decisions_updated_at BEFORE UPDATE
    ON decisions FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_daily_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW daily_decisions_summary;
END;
$$ LANGUAGE plpgsql;

-- Gaps table: missing stakeholders and conflicts detected by Two-Tier Orchestrator
CREATE TABLE gaps (
    gap_id          VARCHAR(50) PRIMARY KEY,
    type            VARCHAR(50) NOT NULL DEFAULT 'missing_stakeholder',
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning'
                    CHECK (severity IN ('critical', 'warning', 'info')),
    description     TEXT NOT NULL,
    assignee_id     VARCHAR(50) REFERENCES user_profiles(user_id),
    decision_id     INTEGER REFERENCES decisions(decision_id),
    recommendation  TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Per-user priority overrides for gaps (drag-and-drop ordering)
CREATE TABLE gap_priority (
    gap_id      VARCHAR(50) NOT NULL REFERENCES gaps(gap_id) ON DELETE CASCADE,
    user_id     VARCHAR(50) NOT NULL REFERENCES user_profiles(user_id),
    priority    INTEGER NOT NULL,
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (gap_id, user_id)
);

CREATE INDEX idx_gaps_assignee ON gaps (assignee_id);
CREATE INDEX idx_gaps_decision ON gaps (decision_id);
CREATE INDEX idx_gaps_type ON gaps (type);
CREATE INDEX idx_gap_priority_user ON gap_priority (user_id);

-- Comments for documentation
COMMENT ON TABLE decisions IS 'Parent table storing all engineering decisions with embeddings';
COMMENT ON TABLE decision_details IS 'Detail table for extended decision metadata using parent-detail pattern';
COMMENT ON TABLE decision_relationships IS 'Relationships between decisions for impact analysis';
COMMENT ON COLUMN decisions.embedding IS '768-dimensional vector from sentence-transformers all-MiniLM-L6-v2';
COMMENT ON COLUMN decisions.embedding_status IS 'Track embedding generation status for batch processing';
-- Note: idx_decisions_embedding created after embeddings are populated