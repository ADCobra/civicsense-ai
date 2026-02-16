-- CivicSense AI - Complete Database Schema
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- =====================================
-- Core Tables
-- =====================================

-- Opportunities table (main data)
CREATE TABLE IF NOT EXISTS opportunities (
    id VARCHAR(16) PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    
    -- Basic information
    title TEXT NOT NULL,
    description TEXT,
    opportunity_type VARCHAR(50) NOT NULL,
    
    -- Government metadata
    issuing_authority VARCHAR(200),
    authority_level VARCHAR(20),
    scheme_code VARCHAR(100),
    
    -- Temporal information
    published_date TIMESTAMP NOT NULL,
    application_start TIMESTAMP,
    application_end TIMESTAMP,
    last_updated TIMESTAMP DEFAULT NOW(),
    
    -- Eligibility (JSONB for flexibility)
    eligibility JSONB NOT NULL DEFAULT '{}',
    
    -- Financial information
    benefit_amount DECIMAL(15,2),
    benefit_description TEXT,
    
    -- Application process
    application_url TEXT,
    required_documents JSONB DEFAULT '[]',
    application_mode VARCHAR(20) DEFAULT 'online',
    
    -- AI-generated content
    ai_summary TEXT,
    ai_eligibility_explanation JSONB,
    common_mistakes JSONB DEFAULT '[]',
    
    -- Trust & quality
    trust_score DECIMAL(3,2) CHECK (trust_score BETWEEN 0 AND 1),
    verification_status VARCHAR(20) DEFAULT 'pending',
    ai_quality_score DECIMAL(3,2),
    
    -- Multilingual support
    translations JSONB DEFAULT '{}',
    
    -- Analytics
    view_count INTEGER DEFAULT 0,
    application_count INTEGER DEFAULT 0,
    save_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_verification_status CHECK (
        verification_status IN ('pending', 'verified', 'flagged', 'rejected')
    ),
    CONSTRAINT valid_opportunity_type CHECK (
        opportunity_type IN (
            'scholarship', 'welfare_scheme', 'competitive_exam', 
            'job_notification', 'skill_training', 'financial_aid',
            'subsidy', 'pension', 'certificate'
        )
    )
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_opp_type ON opportunities(opportunity_type);
CREATE INDEX IF NOT EXISTS idx_opp_dates ON opportunities(application_start, application_end);
CREATE INDEX IF NOT EXISTS idx_opp_authority ON opportunities(issuing_authority);
CREATE INDEX IF NOT EXISTS idx_opp_published ON opportunities(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(verification_status);
CREATE INDEX IF NOT EXISTS idx_opp_source ON opportunities(source_id);

-- GIN indexes for JSONB queries (eligibility, translations)
CREATE INDEX IF NOT EXISTS idx_opp_eligibility ON opportunities USING GIN (eligibility);
CREATE INDEX IF NOT EXISTS idx_opp_translations ON opportunities USING GIN (translations);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_opp_search ON opportunities USING GIN (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '') || ' ' || COALESCE(ai_summary, ''))
);

-- =====================================
-- Data Source Management
-- =====================================

CREATE TABLE IF NOT EXISTS sources (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    
    -- Configuration
    config JSONB NOT NULL,
    schedule JSONB NOT NULL,
    
    -- Health metrics
    last_run TIMESTAMP,
    last_success TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    total_successes INTEGER DEFAULT 0,
    total_failures INTEGER DEFAULT 0,
    avg_items_per_run DECIMAL(10,2),
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,  -- 1-10, higher = more important
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_source_type CHECK (
        source_type IN ('api', 'rss', 'sitemap', 'pdf', 'manual')
    )
);

-- Index for active sources
CREATE INDEX IF NOT EXISTS idx_sources_active ON sources(is_active, priority DESC);

-- =====================================
-- Collection Logs
-- =====================================

CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) REFERENCES sources(id),
    
    -- Run details
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Results
    status VARCHAR(20) NOT NULL,  -- success, partial, failed
    items_fetched INTEGER DEFAULT 0,
    items_processed INTEGER DEFAULT 0,
    items_saved INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB,
    
    -- Metadata
    worker_id VARCHAR(100),
    
    CONSTRAINT valid_log_status CHECK (
        status IN ('success', 'partial', 'failed', 'running')
    )
);

-- Indexes for log queries
CREATE INDEX IF NOT EXISTS idx_logs_source ON collection_logs(source_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_status ON collection_logs(status, started_at DESC);

-- =====================================
-- Raw Data Storage (before normalization)
-- =====================================

CREATE TABLE IF NOT EXISTS raw_data (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,
    collection_log_id INTEGER REFERENCES collection_logs(id),
    
    -- Raw data
    data JSONB NOT NULL,
    url TEXT,
    
    -- Processing status
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP,
    opportunity_id VARCHAR(16) REFERENCES opportunities(id),
    
    -- Error tracking
    processing_error TEXT,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for unprocessed items
CREATE INDEX IF NOT EXISTS idx_raw_unprocessed ON raw_data(processed, source_id) WHERE NOT processed;

-- =====================================
-- Opportunity Versions (change tracking)
-- =====================================

CREATE TABLE IF NOT EXISTS opportunity_versions (
    id SERIAL PRIMARY KEY,
    opportunity_id VARCHAR(16) REFERENCES opportunities(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    
    -- Snapshot of data
    data JSONB NOT NULL,
    
    -- Change tracking
    changed_fields JSONB,
    change_reason VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(opportunity_id, version_number)
);

-- Index for version queries
CREATE INDEX IF NOT EXISTS idx_versions_opp ON opportunity_versions(opportunity_id, version_number DESC);

-- =====================================
-- Deduplication Tracking
-- =====================================

CREATE TABLE IF NOT EXISTS duplicate_groups (
    id SERIAL PRIMARY KEY,
    master_opportunity_id VARCHAR(16) REFERENCES opportunities(id),
    duplicate_opportunity_ids JSONB NOT NULL,
    similarity_score DECIMAL(3,2),
    
    -- Review status
    reviewed BOOLEAN DEFAULT false,
    review_action VARCHAR(20),  -- merged, separate, pending
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_review_action CHECK (
        review_action IS NULL OR review_action IN ('merged', 'separate', 'pending')
    )
);

-- =====================================
-- Analytics & Aggregation
-- =====================================

CREATE TABLE IF NOT EXISTS analytics_daily (
    date DATE PRIMARY KEY,
    
    -- Opportunity metrics
    new_opportunities INTEGER DEFAULT 0,
    active_opportunities INTEGER DEFAULT 0,
    expired_opportunities INTEGER DEFAULT 0,
    
    -- Engagement (if you add user tracking later)
    total_views INTEGER DEFAULT 0,
    total_applications INTEGER DEFAULT 0,
    total_saves INTEGER DEFAULT 0,
    
    -- By category
    metrics_by_type JSONB DEFAULT '{}',
    metrics_by_state JSONB DEFAULT '{}',
    metrics_by_authority JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================
-- Helper Functions
-- =====================================

-- Function to update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for sources table
CREATE TRIGGER update_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to create opportunity version on update
CREATE OR REPLACE FUNCTION create_opportunity_version()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create version if data actually changed
    IF OLD.* IS DISTINCT FROM NEW.* THEN
        INSERT INTO opportunity_versions (
            opportunity_id,
            version_number,
            data,
            changed_fields
        )
        SELECT
            OLD.id,
            COALESCE(MAX(version_number), 0) + 1,
            row_to_json(OLD.*),
            jsonb_object_agg(
                key,
                jsonb_build_object('old', OLD_json->>key, 'new', NEW_json->>key)
            )
        FROM
            opportunity_versions
            CROSS JOIN LATERAL (SELECT row_to_json(OLD.*) AS OLD_json, row_to_json(NEW.*) AS NEW_json) AS jsons
            CROSS JOIN LATERAL jsonb_each_text(OLD_json) AS fields(key, value)
        WHERE
            opportunity_id = OLD.id
            AND (OLD_json->>key) IS DISTINCT FROM (NEW_json->>key)
        GROUP BY OLD.id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for opportunity versioning
CREATE TRIGGER track_opportunity_versions
    BEFORE UPDATE ON opportunities
    FOR EACH ROW
    EXECUTE FUNCTION create_opportunity_version();

-- =====================================
-- Initial Data
-- =====================================

-- Insert default sources (will be managed via config/sources.yaml)
INSERT INTO sources (id, name, source_type, config, schedule, priority) VALUES
('pib_releases', 'Press Information Bureau', 'rss', 
 '{"feed_url": "https://pib.gov.in/allRss.aspx"}'::jsonb,
 '{"type": "interval", "interval_minutes": 60}'::jsonb,
 8),
('upsc_notifications', 'UPSC Notifications', 'rss',
 '{"feed_url": "https://upsc.gov.in/rss/latest-notifications.xml"}'::jsonb,
 '{"type": "interval", "interval_minutes": 180}'::jsonb,
 9)
ON CONFLICT (id) DO NOTHING;

-- =====================================
-- Views for Common Queries
-- =====================================

-- Active opportunities view
CREATE OR REPLACE VIEW active_opportunities AS
SELECT *
FROM opportunities
WHERE 
    verification_status = 'verified'
    AND (application_end IS NULL OR application_end >= NOW())
ORDER BY published_date DESC;

-- Opportunities needing review
CREATE OR REPLACE VIEW pending_review AS
SELECT *
FROM opportunities
WHERE verification_status = 'pending'
ORDER BY created_at ASC;

-- Collection health dashboard
CREATE OR REPLACE VIEW collection_health AS
SELECT 
    s.id,
    s.name,
    s.is_active,
    s.last_success,
    s.consecutive_failures,
    s.total_runs,
    s.total_successes,
    ROUND(100.0 * s.total_successes / NULLIF(s.total_runs, 0), 2) AS success_rate,
    l.status AS last_run_status,
    l.items_saved AS last_run_items
FROM sources s
LEFT JOIN LATERAL (
    SELECT * FROM collection_logs
    WHERE source_id = s.id
    ORDER BY started_at DESC
    LIMIT 1
) l ON true
ORDER BY s.priority DESC, s.last_success DESC NULLS LAST;

-- =====================================
-- Maintenance
-- =====================================

-- Cleanup old raw data (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_raw_data(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM raw_data
    WHERE processed = true
      AND created_at < NOW() - (days_old || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Refresh analytics
CREATE OR REPLACE FUNCTION refresh_daily_analytics(for_date DATE DEFAULT CURRENT_DATE)
RETURNS VOID AS $$
BEGIN
    INSERT INTO analytics_daily (date, new_opportunities, active_opportunities, expired_opportunities)
    SELECT
        for_date,
        COUNT(*) FILTER (WHERE DATE(created_at) = for_date),
        COUNT(*) FILTER (WHERE application_end IS NULL OR application_end >= for_date),
        COUNT(*) FILTER (WHERE application_end < for_date)
    FROM opportunities
    ON CONFLICT (date) DO UPDATE SET
        new_opportunities = EXCLUDED.new_opportunities,
        active_opportunities = EXCLUDED.active_opportunities,
        expired_opportunities = EXCLUDED.expired_opportunities;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust for your setup)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO civicsense;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO civicsense;