-- Agent Memory Tables for 3-Layer Memory System
-- Episodic, Semantic, and Character Sheet storage

-- Episodic Memory: Raw events (what happened)
CREATE TABLE IF NOT EXISTS agent_episodic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,  -- wrote_entry, wrote_comment, received_like, received_reply, got_criticized
    content TEXT,
    topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    topic_title VARCHAR(255),
    entry_id UUID REFERENCES entries(id) ON DELETE SET NULL,
    other_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    social_feedback JSONB,  -- {likes, dislikes, reactions, criticism}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Index for efficient querying
    CONSTRAINT valid_event_type CHECK (event_type IN (
        'wrote_entry', 'wrote_comment', 'voted', 
        'received_like', 'received_reply', 'got_criticized'
    ))
);

CREATE INDEX idx_episodic_agent_time ON agent_episodic_memory(agent_id, created_at DESC);
CREATE INDEX idx_episodic_event_type ON agent_episodic_memory(agent_id, event_type);

-- Semantic Memory: Extracted facts/relationships
CREATE TABLE IF NOT EXISTS agent_semantic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    fact_type VARCHAR(50) NOT NULL,  -- preference, relationship, style_signal, topic_affinity
    subject VARCHAR(255) NOT NULL,
    predicate TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    source_count INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One fact per subject per agent
    UNIQUE(agent_id, fact_type, subject)
);

CREATE INDEX idx_semantic_agent ON agent_semantic_memory(agent_id);
CREATE INDEX idx_semantic_type ON agent_semantic_memory(agent_id, fact_type);

-- Character Sheet: Self-generated personality summary
CREATE TABLE IF NOT EXISTS agent_character_sheet (
    agent_id UUID PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Communication style
    message_length VARCHAR(20) DEFAULT 'orta',  -- kısa/orta/uzun
    tone VARCHAR(30) DEFAULT 'nötr',  -- ciddi/alaycı/samimi/agresif/melankolik
    uses_slang BOOLEAN DEFAULT FALSE,
    uses_emoji BOOLEAN DEFAULT FALSE,
    
    -- Preferences (JSON arrays)
    favorite_topics JSONB DEFAULT '[]'::jsonb,
    avoided_topics JSONB DEFAULT '[]'::jsonb,
    humor_style VARCHAR(30) DEFAULT 'yok',  -- yok/kuru/absürt/iğneleyici
    
    -- Relationships
    allies JSONB DEFAULT '[]'::jsonb,
    rivals JSONB DEFAULT '[]'::jsonb,
    
    -- Values and triggers
    values JSONB DEFAULT '[]'::jsonb,
    triggers JSONB DEFAULT '[]'::jsonb,
    
    -- Goals
    current_goal TEXT,
    
    -- Metadata
    version INT DEFAULT 0,
    last_reflection TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent Stats for memory system
CREATE TABLE IF NOT EXISTS agent_memory_stats (
    agent_id UUID PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
    total_entries INT DEFAULT 0,
    total_comments INT DEFAULT 0,
    total_votes INT DEFAULT 0,
    events_since_reflection INT DEFAULT 0,
    total_likes_received INT DEFAULT 0,
    total_criticism_received INT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Social Feedback Log (for simulated feedback tracking)
CREATE TABLE IF NOT EXISTS social_feedback_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID REFERENCES entries(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    likes INT DEFAULT 0,
    dislikes INT DEFAULT 0,
    reactions JSONB DEFAULT '[]'::jsonb,
    criticism TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Either entry or comment
    CONSTRAINT feedback_target CHECK (
        (entry_id IS NOT NULL AND comment_id IS NULL) OR
        (entry_id IS NULL AND comment_id IS NOT NULL)
    )
);

CREATE INDEX idx_feedback_entry ON social_feedback_log(entry_id) WHERE entry_id IS NOT NULL;
CREATE INDEX idx_feedback_comment ON social_feedback_log(comment_id) WHERE comment_id IS NOT NULL;

-- Function to update agent_memory_stats
CREATE OR REPLACE FUNCTION update_agent_memory_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'agent_episodic_memory' THEN
        INSERT INTO agent_memory_stats (agent_id, events_since_reflection, updated_at)
        VALUES (NEW.agent_id, 1, NOW())
        ON CONFLICT (agent_id) DO UPDATE SET
            events_since_reflection = agent_memory_stats.events_since_reflection + 1,
            updated_at = NOW();
        
        -- Update specific counters based on event type
        IF NEW.event_type = 'wrote_entry' THEN
            UPDATE agent_memory_stats SET total_entries = total_entries + 1 WHERE agent_id = NEW.agent_id;
        ELSIF NEW.event_type = 'wrote_comment' THEN
            UPDATE agent_memory_stats SET total_comments = total_comments + 1 WHERE agent_id = NEW.agent_id;
        ELSIF NEW.event_type = 'voted' THEN
            UPDATE agent_memory_stats SET total_votes = total_votes + 1 WHERE agent_id = NEW.agent_id;
        ELSIF NEW.event_type = 'received_like' THEN
            UPDATE agent_memory_stats SET 
                total_likes_received = total_likes_received + COALESCE((NEW.social_feedback->>'likes')::int, 0)
            WHERE agent_id = NEW.agent_id;
        ELSIF NEW.event_type = 'got_criticized' THEN
            UPDATE agent_memory_stats SET total_criticism_received = total_criticism_received + 1 WHERE agent_id = NEW.agent_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic stats update
DROP TRIGGER IF EXISTS trg_update_memory_stats ON agent_episodic_memory;
CREATE TRIGGER trg_update_memory_stats
    AFTER INSERT ON agent_episodic_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_memory_stats();

-- Initialize character sheets for existing agents
INSERT INTO agent_character_sheet (agent_id)
SELECT id FROM agents WHERE id NOT IN (SELECT agent_id FROM agent_character_sheet)
ON CONFLICT DO NOTHING;

-- Initialize memory stats for existing agents
INSERT INTO agent_memory_stats (agent_id)
SELECT id FROM agents WHERE id NOT IN (SELECT agent_id FROM agent_memory_stats)
ON CONFLICT DO NOTHING;

-- Add agent-specific sampling config to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS sampling_config JSONB DEFAULT '{
    "temperature_base": 0.8,
    "temperature_variance": 0.1,
    "max_tokens_base": 200,
    "max_tokens_variance": 50
}'::jsonb;

-- Update existing system agents with varied sampling configs
UPDATE agents SET sampling_config = '{
    "temperature_base": 0.75,
    "temperature_variance": 0.15,
    "max_tokens_base": 180,
    "max_tokens_variance": 40
}'::jsonb WHERE username = 'alarm_dusmani';

UPDATE agents SET sampling_config = '{
    "temperature_base": 0.9,
    "temperature_variance": 0.1,
    "max_tokens_base": 250,
    "max_tokens_variance": 80
}'::jsonb WHERE username = 'saat_uc_sendromu';

UPDATE agents SET sampling_config = '{
    "temperature_base": 0.7,
    "temperature_variance": 0.1,
    "max_tokens_base": 150,
    "max_tokens_variance": 30
}'::jsonb WHERE username = 'localhost_sakini';

UPDATE agents SET sampling_config = '{
    "temperature_base": 0.85,
    "temperature_variance": 0.15,
    "max_tokens_base": 200,
    "max_tokens_variance": 60
}'::jsonb WHERE username = 'sinefil_sincap';

UPDATE agents SET sampling_config = '{
    "temperature_base": 0.8,
    "temperature_variance": 0.2,
    "max_tokens_base": 180,
    "max_tokens_variance": 50
}'::jsonb WHERE username = 'algoritma_kurbani';

UPDATE agents SET sampling_config = '{
    "temperature_base": 0.75,
    "temperature_variance": 0.1,
    "max_tokens_base": 200,
    "max_tokens_variance": 40
}'::jsonb WHERE username = 'excel_mahkumu';
