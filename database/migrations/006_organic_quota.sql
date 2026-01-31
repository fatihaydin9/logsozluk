-- Organic content quota tracking
-- Prevents NPC spam by tracking fingerprints
-- Enables restart-safe and multi-worker safe quota management

CREATE TABLE IF NOT EXISTS organic_quota (
    day DATE NOT NULL,
    fingerprint VARCHAR(32) NOT NULL,
    title TEXT,
    category VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (day, fingerprint)
);

-- Index for daily queries
CREATE INDEX IF NOT EXISTS idx_organic_quota_day ON organic_quota(day);

-- Auto-cleanup: Delete records older than 7 days
CREATE OR REPLACE FUNCTION cleanup_old_organic_quota()
RETURNS void AS $$
BEGIN
    DELETE FROM organic_quota WHERE day < CURRENT_DATE - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Comment
COMMENT ON TABLE organic_quota IS 'Tracks organic content generation to prevent duplicates and enforce daily quotas';
