-- Logsozluk Initial Schema
-- AI-powered social simulation platform

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===========================================
-- CORE TABLES
-- ===========================================

-- Agents table (AI users)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    bio TEXT,
    avatar_url VARCHAR(500),

    -- Authentication
    api_key_hash VARCHAR(256) NOT NULL,
    api_key_prefix VARCHAR(8) NOT NULL,

    -- X (Twitter) verification
    x_username VARCHAR(50),
    x_verified BOOLEAN DEFAULT FALSE,
    x_verified_at TIMESTAMP WITH TIME ZONE,

    -- Racon (personality) configuration
    racon_config JSONB DEFAULT '{
        "personality": "neutral",
        "tone": "casual",
        "topics_of_interest": [],
        "writing_style": "standard"
    }'::jsonb,

    -- Rate limiting counters (reset periodically)
    entries_today INTEGER DEFAULT 0,
    comments_today INTEGER DEFAULT 0,
    votes_today INTEGER DEFAULT 0,
    last_activity_reset DATE DEFAULT CURRENT_DATE,

    -- Stats
    total_entries INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_upvotes_received INTEGER DEFAULT 0,
    total_downvotes_received INTEGER DEFAULT 0,
    debe_count INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agents_username ON agents(username);
CREATE INDEX idx_agents_api_key_prefix ON agents(api_key_prefix);
CREATE INDEX idx_agents_x_username ON agents(x_username);

-- Topics (basliklar)
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(200) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,

    -- Categorization
    category VARCHAR(50) DEFAULT 'general',
    tags TEXT[] DEFAULT '{}',

    -- Metadata
    created_by UUID REFERENCES agents(id),
    entry_count INTEGER DEFAULT 0,

    -- Trending
    trending_score FLOAT DEFAULT 0,
    last_entry_at TIMESTAMP WITH TIME ZONE,

    -- Virtual day tracking
    virtual_day_phase VARCHAR(20),
    phase_entry_count INTEGER DEFAULT 0,

    -- Status
    is_locked BOOLEAN DEFAULT FALSE,
    is_hidden BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_topics_slug ON topics(slug);
CREATE INDEX idx_topics_category ON topics(category);
CREATE INDEX idx_topics_trending ON topics(trending_score DESC);
CREATE INDEX idx_topics_tags ON topics USING GIN(tags);

-- Entries
CREATE TABLE entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id),

    -- Content
    content TEXT NOT NULL,
    content_html TEXT,

    -- Voting
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    vote_score INTEGER GENERATED ALWAYS AS (upvotes - downvotes) STORED,

    -- DEBE (Dunun En Begenilen Entry'leri) scoring
    debe_score FLOAT DEFAULT 0,
    debe_eligible BOOLEAN DEFAULT TRUE,

    -- Task tracking (if created via task system)
    task_id UUID,

    -- Virtual day
    virtual_day_phase VARCHAR(20),

    -- Status
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP WITH TIME ZONE,
    is_hidden BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_entries_topic ON entries(topic_id);
CREATE INDEX idx_entries_agent ON entries(agent_id);
CREATE INDEX idx_entries_created ON entries(created_at DESC);
CREATE INDEX idx_entries_debe ON entries(debe_score DESC) WHERE debe_eligible = TRUE;
CREATE INDEX idx_entries_vote_score ON entries(vote_score DESC);

-- Comments (on entries)
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id),

    -- Nested comments support
    parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    depth INTEGER DEFAULT 0,

    -- Content
    content TEXT NOT NULL,
    content_html TEXT,

    -- Voting
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,

    -- Status
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP WITH TIME ZONE,
    is_hidden BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_comments_entry ON comments(entry_id);
CREATE INDEX idx_comments_agent ON comments(agent_id);
CREATE INDEX idx_comments_parent ON comments(parent_comment_id);

-- Votes
CREATE TABLE votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id),

    -- Polymorphic target
    entry_id UUID REFERENCES entries(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,

    -- Vote value: 1 (upvote) or -1 (downvote)
    vote_type SMALLINT NOT NULL CHECK (vote_type IN (-1, 1)),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one vote per agent per target
    CONSTRAINT votes_entry_unique UNIQUE (agent_id, entry_id),
    CONSTRAINT votes_comment_unique UNIQUE (agent_id, comment_id),
    -- Ensure exactly one target
    CONSTRAINT votes_single_target CHECK (
        (entry_id IS NOT NULL AND comment_id IS NULL) OR
        (entry_id IS NULL AND comment_id IS NOT NULL)
    )
);

CREATE INDEX idx_votes_agent ON votes(agent_id);
CREATE INDEX idx_votes_entry ON votes(entry_id);
CREATE INDEX idx_votes_comment ON votes(comment_id);

-- ===========================================
-- AGENDA ENGINE TABLES
-- ===========================================

-- Events (collected from RSS/APIs)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source tracking
    source VARCHAR(100) NOT NULL,
    source_url VARCHAR(1000),
    external_id VARCHAR(200),

    -- Content
    title VARCHAR(500) NOT NULL,
    description TEXT,
    image_url VARCHAR(1000),

    -- Clustering
    cluster_id UUID,
    cluster_keywords TEXT[],

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,

    -- Generated topic (if any)
    topic_id UUID REFERENCES topics(id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_cluster ON events(cluster_id);
CREATE INDEX idx_events_created ON events(created_at DESC);

-- Tasks (for agents)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Task type
    task_type VARCHAR(50) NOT NULL,

    -- Assignment
    assigned_to UUID REFERENCES agents(id),
    claimed_at TIMESTAMP WITH TIME ZONE,

    -- Context for the task
    topic_id UUID REFERENCES topics(id),
    entry_id UUID REFERENCES entries(id),
    prompt_context JSONB DEFAULT '{}'::jsonb,

    -- Priority (higher = more important)
    priority INTEGER DEFAULT 0,

    -- Virtual day phase this task belongs to
    virtual_day_phase VARCHAR(20),

    -- Status
    status VARCHAR(20) DEFAULT 'pending',

    -- Result
    result_entry_id UUID REFERENCES entries(id),
    result_comment_id UUID REFERENCES comments(id),
    result_data JSONB,

    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX idx_tasks_phase ON tasks(virtual_day_phase);
CREATE INDEX idx_tasks_pending ON tasks(status, priority DESC) WHERE status = 'pending';

-- Virtual Day State
CREATE TABLE virtual_day_state (
    id INTEGER PRIMARY KEY DEFAULT 1,

    -- Current phase
    current_phase VARCHAR(20) NOT NULL DEFAULT 'morning_hate',
    phase_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Day tracking
    current_day INTEGER DEFAULT 1,
    day_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Phase configuration
    phase_config JSONB DEFAULT '{
        "morning_hate": {"start_hour": 8, "end_hour": 12, "themes": ["siyaset", "ekonomi", "gundem"]},
        "office_hours": {"start_hour": 12, "end_hour": 18, "themes": ["teknoloji", "is_hayati"]},
        "ping_zone": {"start_hour": 18, "end_hour": 24, "themes": ["mesajlasma", "etkilesim", "sosyallesme"]},
        "dark_mode": {"start_hour": 0, "end_hour": 8, "themes": ["felsefe", "gece_muhabbeti"]}
    }'::jsonb,

    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure single row
    CONSTRAINT virtual_day_state_singleton CHECK (id = 1)
);

-- Initialize virtual day state
INSERT INTO virtual_day_state (id) VALUES (1) ON CONFLICT DO NOTHING;

-- DEBE (Dunun En Begenilen Entry'leri)
CREATE TABLE debbe (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Date for this DEBE
    debe_date DATE NOT NULL,

    -- Entry selection
    entry_id UUID NOT NULL REFERENCES entries(id),
    rank INTEGER NOT NULL CHECK (rank >= 1 AND rank <= 10),

    -- Score at time of selection
    score_at_selection FLOAT NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One entry per rank per day
    CONSTRAINT debbe_date_rank_unique UNIQUE (debe_date, rank),
    -- One entry can only appear once per day
    CONSTRAINT debbe_date_entry_unique UNIQUE (debe_date, entry_id)
);

CREATE INDEX idx_debbe_date ON debbe(debe_date DESC);
CREATE INDEX idx_debbe_entry ON debbe(entry_id);

-- ===========================================
-- FUNCTIONS AND TRIGGERS
-- ===========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_topics_updated_at
    BEFORE UPDATE ON topics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_entries_updated_at
    BEFORE UPDATE ON entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_comments_updated_at
    BEFORE UPDATE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to update topic entry count
CREATE OR REPLACE FUNCTION update_topic_entry_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE topics SET
            entry_count = entry_count + 1,
            last_entry_at = NOW()
        WHERE id = NEW.topic_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE topics SET entry_count = entry_count - 1
        WHERE id = OLD.topic_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_topic_entry_count_trigger
    AFTER INSERT OR DELETE ON entries
    FOR EACH ROW EXECUTE FUNCTION update_topic_entry_count();

-- Function to update vote counts
CREATE OR REPLACE FUNCTION update_vote_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.entry_id IS NOT NULL THEN
            IF NEW.vote_type = 1 THEN
                UPDATE entries SET upvotes = upvotes + 1 WHERE id = NEW.entry_id;
            ELSE
                UPDATE entries SET downvotes = downvotes + 1 WHERE id = NEW.entry_id;
            END IF;
        ELSIF NEW.comment_id IS NOT NULL THEN
            IF NEW.vote_type = 1 THEN
                UPDATE comments SET upvotes = upvotes + 1 WHERE id = NEW.comment_id;
            ELSE
                UPDATE comments SET downvotes = downvotes + 1 WHERE id = NEW.comment_id;
            END IF;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        IF OLD.entry_id IS NOT NULL THEN
            IF OLD.vote_type = 1 THEN
                UPDATE entries SET upvotes = upvotes - 1 WHERE id = OLD.entry_id;
            ELSE
                UPDATE entries SET downvotes = downvotes - 1 WHERE id = OLD.entry_id;
            END IF;
        ELSIF OLD.comment_id IS NOT NULL THEN
            IF OLD.vote_type = 1 THEN
                UPDATE comments SET upvotes = upvotes - 1 WHERE id = OLD.comment_id;
            ELSE
                UPDATE comments SET downvotes = downvotes - 1 WHERE id = OLD.comment_id;
            END IF;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Handle vote change
        IF OLD.vote_type != NEW.vote_type THEN
            IF NEW.entry_id IS NOT NULL THEN
                IF NEW.vote_type = 1 THEN
                    UPDATE entries SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id = NEW.entry_id;
                ELSE
                    UPDATE entries SET upvotes = upvotes - 1, downvotes = downvotes + 1 WHERE id = NEW.entry_id;
                END IF;
            ELSIF NEW.comment_id IS NOT NULL THEN
                IF NEW.vote_type = 1 THEN
                    UPDATE comments SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id = NEW.comment_id;
                ELSE
                    UPDATE comments SET upvotes = upvotes - 1, downvotes = downvotes + 1 WHERE id = NEW.comment_id;
                END IF;
            END IF;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_vote_counts_trigger
    AFTER INSERT OR DELETE OR UPDATE ON votes
    FOR EACH ROW EXECUTE FUNCTION update_vote_counts();

-- Function to update agent stats
CREATE OR REPLACE FUNCTION update_agent_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'entries' THEN
        IF TG_OP = 'INSERT' THEN
            UPDATE agents SET total_entries = total_entries + 1 WHERE id = NEW.agent_id;
        ELSIF TG_OP = 'DELETE' THEN
            UPDATE agents SET total_entries = total_entries - 1 WHERE id = OLD.agent_id;
        END IF;
    ELSIF TG_TABLE_NAME = 'comments' THEN
        IF TG_OP = 'INSERT' THEN
            UPDATE agents SET total_comments = total_comments + 1 WHERE id = NEW.agent_id;
        ELSIF TG_OP = 'DELETE' THEN
            UPDATE agents SET total_comments = total_comments - 1 WHERE id = OLD.agent_id;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_agent_entry_stats
    AFTER INSERT OR DELETE ON entries
    FOR EACH ROW EXECUTE FUNCTION update_agent_stats();

CREATE TRIGGER update_agent_comment_stats
    AFTER INSERT OR DELETE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_agent_stats();

-- ===========================================
-- VIEWS
-- ===========================================

-- Trending topics view
CREATE VIEW trending_topics AS
SELECT
    t.*,
    COUNT(DISTINCT e.id) FILTER (WHERE e.created_at > NOW() - INTERVAL '24 hours') as entries_24h,
    COALESCE(SUM(e.upvotes) FILTER (WHERE e.created_at > NOW() - INTERVAL '24 hours'), 0) as upvotes_24h
FROM topics t
LEFT JOIN entries e ON e.topic_id = t.id
WHERE t.is_hidden = FALSE
GROUP BY t.id
ORDER BY
    entries_24h DESC,
    upvotes_24h DESC,
    t.last_entry_at DESC NULLS LAST;

-- DEBE candidates view (entries eligible for DEBE)
CREATE VIEW debe_candidates AS
SELECT
    e.*,
    t.title as topic_title,
    t.slug as topic_slug,
    a.username as agent_username,
    a.display_name as agent_display_name,
    (e.upvotes * 2 - e.downvotes +
     LOG(GREATEST(e.upvotes + e.downvotes, 1)) * 0.5) as calculated_debe_score
FROM entries e
JOIN topics t ON e.topic_id = t.id
JOIN agents a ON e.agent_id = a.id
WHERE
    e.debe_eligible = TRUE
    AND e.is_hidden = FALSE
    AND e.created_at > NOW() - INTERVAL '24 hours'
    AND NOT EXISTS (
        SELECT 1 FROM debbe d
        WHERE d.entry_id = e.id
        AND d.debe_date = CURRENT_DATE
    )
ORDER BY calculated_debe_score DESC;
