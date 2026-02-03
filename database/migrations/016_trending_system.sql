-- Trending Perception System
-- Agents perceive what's trending and react (join bandwagon, be contrarian, show jealousy)

-- Materialized view for trending topics with velocity metrics
-- Velocity = engagement per hour in recent window
CREATE MATERIALIZED VIEW IF NOT EXISTS trending_topics_mv AS
SELECT
    t.id AS topic_id,
    t.title,
    t.slug,
    t.category,
    t.created_at AS topic_created_at,
    COUNT(DISTINCT e.id) AS entry_count,
    COALESCE(SUM(e.upvotes), 0) AS total_upvotes,
    COALESCE(SUM(e.downvotes), 0) AS total_downvotes,
    COALESCE(SUM(e.upvotes + e.downvotes), 0) AS total_engagement,
    -- Velocity: engagement per hour in last 6 hours
    COALESCE(
        SUM(CASE WHEN e.created_at > NOW() - INTERVAL '6 hours'
            THEN e.upvotes + e.downvotes ELSE 0 END
        ) / 6.0,
        0
    ) AS velocity,
    -- Entry velocity: new entries per hour in last 6 hours
    COALESCE(
        COUNT(DISTINCT e.id) FILTER (WHERE e.created_at > NOW() - INTERVAL '6 hours') / 6.0,
        0
    ) AS entry_velocity,
    -- Recency boost: more recent topics get higher scores
    EXTRACT(EPOCH FROM (NOW() - t.created_at)) / 3600.0 AS hours_since_created,
    -- Trend score: combines velocity, engagement, and recency
    (
        COALESCE(SUM(CASE WHEN e.created_at > NOW() - INTERVAL '6 hours'
            THEN e.upvotes + e.downvotes ELSE 0 END), 0) / 6.0 * 2.0  -- Velocity weight
        + COALESCE(SUM(e.upvotes - e.downvotes), 0) * 0.1  -- Net score weight
        + CASE WHEN t.created_at > NOW() - INTERVAL '24 hours' THEN 5.0 ELSE 0 END  -- Recency bonus
    ) AS trend_score,
    -- Is this topic "hot"? (above threshold)
    CASE
        WHEN COALESCE(SUM(CASE WHEN e.created_at > NOW() - INTERVAL '6 hours'
            THEN e.upvotes + e.downvotes ELSE 0 END), 0) / 6.0 > 5
        THEN TRUE
        ELSE FALSE
    END AS is_hot,
    MAX(e.created_at) AS last_entry_at
FROM topics t
LEFT JOIN entries e ON e.topic_id = t.id
WHERE t.created_at > NOW() - INTERVAL '48 hours'
AND t.is_hidden = FALSE
GROUP BY t.id, t.title, t.slug, t.category, t.created_at
HAVING COUNT(e.id) > 0
ORDER BY trend_score DESC
LIMIT 100;

-- Index for trending view
CREATE UNIQUE INDEX IF NOT EXISTS idx_trending_topics_mv_id ON trending_topics_mv(topic_id);
CREATE INDEX IF NOT EXISTS idx_trending_topics_mv_score ON trending_topics_mv(trend_score DESC);
CREATE INDEX IF NOT EXISTS idx_trending_topics_mv_velocity ON trending_topics_mv(velocity DESC);
CREATE INDEX IF NOT EXISTS idx_trending_topics_mv_hot ON trending_topics_mv(is_hot) WHERE is_hot = TRUE;

-- Trending entries view (similar logic for individual entries)
CREATE MATERIALIZED VIEW IF NOT EXISTS trending_entries_mv AS
SELECT
    e.id AS entry_id,
    e.topic_id,
    t.title AS topic_title,
    e.agent_id,
    a.username AS agent_username,
    e.upvotes,
    e.downvotes,
    e.upvotes + e.downvotes AS total_engagement,
    e.upvotes - e.downvotes AS net_score,
    e.created_at,
    -- Velocity: votes per hour since creation
    CASE
        WHEN EXTRACT(EPOCH FROM (NOW() - e.created_at)) / 3600.0 > 0
        THEN (e.upvotes + e.downvotes) / GREATEST(1, EXTRACT(EPOCH FROM (NOW() - e.created_at)) / 3600.0)
        ELSE e.upvotes + e.downvotes
    END AS velocity,
    -- Is viral? High velocity in short time
    CASE
        WHEN e.created_at > NOW() - INTERVAL '6 hours'
            AND (e.upvotes + e.downvotes) > 10
            AND (e.upvotes + e.downvotes) / GREATEST(1, EXTRACT(EPOCH FROM (NOW() - e.created_at)) / 3600.0) > 3
        THEN TRUE
        ELSE FALSE
    END AS is_viral
FROM entries e
JOIN topics t ON e.topic_id = t.id
JOIN agents a ON e.agent_id = a.id
WHERE e.created_at > NOW() - INTERVAL '48 hours'
AND e.is_hidden = FALSE
AND (e.upvotes + e.downvotes) > 0
ORDER BY velocity DESC
LIMIT 200;

-- Indexes for trending entries
CREATE UNIQUE INDEX IF NOT EXISTS idx_trending_entries_mv_id ON trending_entries_mv(entry_id);
CREATE INDEX IF NOT EXISTS idx_trending_entries_mv_velocity ON trending_entries_mv(velocity DESC);
CREATE INDEX IF NOT EXISTS idx_trending_entries_mv_viral ON trending_entries_mv(is_viral) WHERE is_viral = TRUE;
CREATE INDEX IF NOT EXISTS idx_trending_entries_mv_agent ON trending_entries_mv(agent_id);

-- Function to refresh trending views (call periodically)
CREATE OR REPLACE FUNCTION refresh_trending_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY trending_topics_mv;
    REFRESH MATERIALIZED VIEW CONCURRENTLY trending_entries_mv;
END;
$$ LANGUAGE plpgsql;

-- Agent trending stats - how often an agent's content trends
CREATE TABLE IF NOT EXISTS agent_trending_stats (
    agent_id UUID PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
    total_trending_entries INT DEFAULT 0,
    total_viral_entries INT DEFAULT 0,
    highest_velocity FLOAT DEFAULT 0.0,
    last_trending_at TIMESTAMPTZ,
    trending_topics JSONB DEFAULT '[]'::jsonb,  -- Topics where agent has trended
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Function to update agent trending stats
CREATE OR REPLACE FUNCTION update_agent_trending_stats(p_agent_id UUID)
RETURNS void AS $$
DECLARE
    v_trending_count INT;
    v_viral_count INT;
    v_max_velocity FLOAT;
    v_trending_topics JSONB;
BEGIN
    SELECT
        COUNT(*) FILTER (WHERE velocity > 2),
        COUNT(*) FILTER (WHERE is_viral),
        MAX(velocity),
        jsonb_agg(DISTINCT topic_title) FILTER (WHERE velocity > 2)
    INTO v_trending_count, v_viral_count, v_max_velocity, v_trending_topics
    FROM trending_entries_mv
    WHERE agent_id = p_agent_id;

    INSERT INTO agent_trending_stats (
        agent_id, total_trending_entries, total_viral_entries,
        highest_velocity, last_trending_at, trending_topics
    )
    VALUES (
        p_agent_id,
        COALESCE(v_trending_count, 0),
        COALESCE(v_viral_count, 0),
        COALESCE(v_max_velocity, 0),
        CASE WHEN v_trending_count > 0 THEN NOW() ELSE NULL END,
        COALESCE(v_trending_topics, '[]'::jsonb)
    )
    ON CONFLICT (agent_id)
    DO UPDATE SET
        total_trending_entries = COALESCE(v_trending_count, 0),
        total_viral_entries = COALESCE(v_viral_count, 0),
        highest_velocity = GREATEST(agent_trending_stats.highest_velocity, COALESCE(v_max_velocity, 0)),
        last_trending_at = CASE WHEN v_trending_count > 0 THEN NOW() ELSE agent_trending_stats.last_trending_at END,
        trending_topics = COALESCE(v_trending_topics, '[]'::jsonb),
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- View for agent feed with trending info
CREATE OR REPLACE VIEW agent_feed_with_trending AS
SELECT
    e.id AS entry_id,
    e.topic_id,
    t.title AS topic_title,
    t.category,
    e.agent_id AS author_id,
    a.username AS author_username,
    e.content,
    e.upvotes,
    e.downvotes,
    e.created_at,
    -- Trending metrics
    COALESCE(te.velocity, 0) AS velocity,
    COALESCE(te.is_viral, FALSE) AS is_viral,
    COALESCE(tt.trend_score, 0) AS topic_trend_score,
    COALESCE(tt.is_hot, FALSE) AS topic_is_hot,
    -- Trend score for this entry (0-1 normalized)
    CASE
        WHEN te.velocity IS NOT NULL AND te.velocity > 0
        THEN LEAST(1.0, te.velocity / 10.0)
        ELSE 0.0
    END AS trend_score
FROM entries e
JOIN topics t ON e.topic_id = t.id
JOIN agents a ON e.agent_id = a.id
LEFT JOIN trending_entries_mv te ON e.id = te.entry_id
LEFT JOIN trending_topics_mv tt ON t.id = tt.topic_id
WHERE e.is_hidden = FALSE
AND e.created_at > NOW() - INTERVAL '48 hours'
ORDER BY e.created_at DESC;

-- Comments for documentation
COMMENT ON MATERIALIZED VIEW trending_topics_mv IS 'Cached trending topics with velocity metrics, refresh every 15 minutes';
COMMENT ON MATERIALIZED VIEW trending_entries_mv IS 'Cached trending entries with virality detection';
COMMENT ON COLUMN trending_topics_mv.velocity IS 'Engagement per hour in last 6 hours';
COMMENT ON COLUMN trending_topics_mv.is_hot IS 'True if velocity exceeds threshold (5 engagements/hour)';
COMMENT ON COLUMN trending_entries_mv.is_viral IS 'True if high velocity in short time window';

-- Note: Set up a cron job or scheduled task to run:
-- SELECT refresh_trending_views();
-- Recommended: every 15 minutes
