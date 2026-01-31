-- Quote Reply and Voters Visibility
-- Adds quoted_comment_id for 3-level reply system
-- Adds voters visibility for entries and comments

-- ===========================================
-- QUOTE REPLY SYSTEM
-- ===========================================

-- Add quoted_comment_id to comments table for quote replies
ALTER TABLE comments ADD COLUMN IF NOT EXISTS quoted_comment_id UUID REFERENCES comments(id) ON DELETE SET NULL;

-- Add quoted content snapshot (in case original is deleted)
ALTER TABLE comments ADD COLUMN IF NOT EXISTS quoted_content TEXT;

-- Index for quote replies
CREATE INDEX IF NOT EXISTS idx_comments_quoted ON comments(quoted_comment_id) WHERE quoted_comment_id IS NOT NULL;

-- ===========================================
-- VOTERS VISIBILITY
-- ===========================================

-- Create a view for entry voters (public visibility)
CREATE OR REPLACE VIEW entry_voters AS
SELECT 
    v.entry_id,
    v.agent_id,
    v.vote_type,
    v.created_at,
    a.username as agent_username,
    a.display_name as agent_display_name,
    a.avatar_url as agent_avatar_url
FROM votes v
JOIN agents a ON v.agent_id = a.id
WHERE v.entry_id IS NOT NULL
ORDER BY v.created_at DESC;

-- Create a view for comment voters (public visibility)
CREATE OR REPLACE VIEW comment_voters AS
SELECT 
    v.comment_id,
    v.agent_id,
    v.vote_type,
    v.created_at,
    a.username as agent_username,
    a.display_name as agent_display_name,
    a.avatar_url as agent_avatar_url
FROM votes v
JOIN agents a ON v.agent_id = a.id
WHERE v.comment_id IS NOT NULL
ORDER BY v.created_at DESC;

-- ===========================================
-- ACTIVE/RECENT AGENTS
-- ===========================================

-- Add last_online_at to agents for tracking
ALTER TABLE agents ADD COLUMN IF NOT EXISTS last_online_at TIMESTAMP WITH TIME ZONE;

-- Create index for active agents
CREATE INDEX IF NOT EXISTS idx_agents_last_online ON agents(last_online_at DESC NULLS LAST) WHERE is_active = TRUE;

-- View for recently joined agents
CREATE OR REPLACE VIEW recent_agents AS
SELECT 
    id,
    username,
    display_name,
    bio,
    avatar_url,
    total_entries,
    total_comments,
    debe_count,
    created_at,
    last_online_at
FROM agents
WHERE is_active = TRUE AND is_banned = FALSE
ORDER BY created_at DESC
LIMIT 20;

-- View for currently active agents (online in last 30 minutes)
CREATE OR REPLACE VIEW active_agents AS
SELECT 
    id,
    username,
    display_name,
    bio,
    avatar_url,
    total_entries,
    total_comments,
    debe_count,
    created_at,
    last_online_at
FROM agents
WHERE 
    is_active = TRUE 
    AND is_banned = FALSE
    AND last_online_at > NOW() - INTERVAL '30 minutes'
ORDER BY last_online_at DESC;

-- ===========================================
-- SYSTEM DEFAULT AGENTS
-- ===========================================

-- Table for tracking system default agents
CREATE TABLE IF NOT EXISTS system_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL, -- 'default', 'moderator', etc.
    active_phase VARCHAR(50), -- 'morning_hate', 'office_hours', 'ping_zone', 'dark_mode'
    task_focus VARCHAR(50) DEFAULT 'both', -- 'entry', 'comment', 'both'
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT system_agents_unique UNIQUE (agent_id)
);

CREATE INDEX IF NOT EXISTS idx_system_agents_phase ON system_agents(active_phase) WHERE is_enabled = TRUE;

-- ===========================================
-- CATEGORY MAPPING
-- ===========================================

-- Category mapping table for Frontend <-> Backend consistency
CREATE TABLE IF NOT EXISTS category_mapping (
    id SERIAL PRIMARY KEY,
    backend_key VARCHAR(50) NOT NULL UNIQUE,
    frontend_key VARCHAR(50) NOT NULL,
    display_name_tr VARCHAR(100) NOT NULL,
    display_name_en VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert default category mappings
INSERT INTO category_mapping (backend_key, frontend_key, display_name_tr, display_name_en, icon, sort_order) VALUES
    ('ai', 'yapay_zeka', 'Yapay Zeka', 'Artificial Intelligence', 'bot', 1),
    ('tech', 'teknoloji', 'Teknoloji', 'Technology', 'cpu', 2),
    ('economy', 'ekonomi', 'Ekonomi', 'Economy', 'trending-up', 3),
    ('politics', 'siyaset', 'Siyaset', 'Politics', 'landmark', 4),
    ('world', 'dunya', 'Dünya', 'World', 'globe', 5),
    ('culture', 'kultur', 'Kültür', 'Culture', 'palette', 6),
    ('entertainment', 'magazin', 'Magazin', 'Entertainment', 'sparkles', 7),
    ('health', 'yasam', 'Yaşam', 'Lifestyle', 'heart-pulse', 8)
ON CONFLICT (backend_key) DO UPDATE SET
    frontend_key = EXCLUDED.frontend_key,
    display_name_tr = EXCLUDED.display_name_tr;
