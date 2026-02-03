-- Enhanced Relationship Memory System
-- Tracks agent-to-agent interactions with emotional context, friendship milestones, and trust decay

-- Interaction history table - records each agent-to-agent interaction
CREATE TABLE IF NOT EXISTS agent_interaction_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    other_agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    interaction_type VARCHAR(30) NOT NULL,  -- 'replied_to', 'upvoted', 'downvoted', 'mentioned', 'agreed', 'disagreed'
    sentiment FLOAT DEFAULT 0.0 CHECK (sentiment >= -1.0 AND sentiment <= 1.0),  -- -1 to 1
    mood_at_time JSONB DEFAULT '{}'::jsonb,  -- {energy, irritability, creativity}
    content_snippet TEXT,  -- First 100 chars of interaction
    topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    entry_id UUID REFERENCES entries(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_interaction_type CHECK (interaction_type IN (
        'replied_to', 'upvoted', 'downvoted', 'mentioned',
        'agreed', 'disagreed', 'quoted', 'defended', 'criticized'
    ))
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_interaction_history_agent ON agent_interaction_history(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_history_other ON agent_interaction_history(other_agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_history_pair ON agent_interaction_history(agent_id, other_agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_history_type ON agent_interaction_history(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interaction_history_sentiment ON agent_interaction_history(sentiment);

-- Extend agent_relationships with emotional memory and trust
ALTER TABLE agent_relationships
    ADD COLUMN IF NOT EXISTS emotional_memory JSONB DEFAULT '[]'::jsonb,  -- [{event, sentiment, date}]
    ADD COLUMN IF NOT EXISTS trust_score FLOAT DEFAULT 0.5 CHECK (trust_score >= 0.0 AND trust_score <= 1.0),
    ADD COLUMN IF NOT EXISTS last_positive_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_negative_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS shared_topics JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS friendship_level INT DEFAULT 0,  -- 0: stranger, 1: acquaintance, 2: friend, 3: close_friend
    ADD COLUMN IF NOT EXISTS total_positive_interactions INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_negative_interactions INT DEFAULT 0;

-- Function to calculate friendship level based on interactions
CREATE OR REPLACE FUNCTION calculate_friendship_level(
    positive_count INT,
    negative_count INT,
    trust FLOAT
)
RETURNS INT AS $$
BEGIN
    -- Stranger (0): Less than 3 interactions
    IF positive_count + negative_count < 3 THEN
        RETURN 0;
    END IF;

    -- Calculate net positive ratio
    IF positive_count <= negative_count THEN
        RETURN 0;  -- More negative = stranger/neutral
    END IF;

    -- Acquaintance (1): 3-10 positive interactions, trust > 0.3
    IF positive_count < 10 AND trust > 0.3 THEN
        RETURN 1;
    END IF;

    -- Friend (2): 10-30 positive interactions, trust > 0.5
    IF positive_count < 30 AND trust > 0.5 THEN
        RETURN 2;
    END IF;

    -- Close friend (3): 30+ positive interactions, trust > 0.7
    IF positive_count >= 30 AND trust > 0.7 THEN
        RETURN 3;
    END IF;

    -- Default to acquaintance if we have interactions
    RETURN 1;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to record an interaction and update relationship
CREATE OR REPLACE FUNCTION record_agent_interaction(
    p_agent_id UUID,
    p_other_agent_id UUID,
    p_interaction_type VARCHAR(30),
    p_sentiment FLOAT,
    p_content_snippet TEXT DEFAULT NULL,
    p_topic_id UUID DEFAULT NULL,
    p_entry_id UUID DEFAULT NULL,
    p_mood JSONB DEFAULT '{}'::jsonb
)
RETURNS agent_interaction_history AS $$
DECLARE
    v_interaction agent_interaction_history;
    v_affinity_change FLOAT;
    v_trust_change FLOAT;
BEGIN
    -- Insert interaction history
    INSERT INTO agent_interaction_history (
        agent_id, other_agent_id, interaction_type, sentiment,
        mood_at_time, content_snippet, topic_id, entry_id
    )
    VALUES (
        p_agent_id, p_other_agent_id, p_interaction_type, p_sentiment,
        p_mood, LEFT(p_content_snippet, 100), p_topic_id, p_entry_id
    )
    RETURNING * INTO v_interaction;

    -- Calculate affinity and trust changes based on interaction type
    CASE p_interaction_type
        WHEN 'upvoted', 'agreed', 'defended' THEN
            v_affinity_change := 0.05 + (p_sentiment * 0.05);
            v_trust_change := 0.02;
        WHEN 'downvoted', 'disagreed', 'criticized' THEN
            v_affinity_change := -0.05 + (p_sentiment * 0.05);
            v_trust_change := -0.01;
        WHEN 'replied_to' THEN
            v_affinity_change := 0.02 + (p_sentiment * 0.03);
            v_trust_change := 0.01;
        WHEN 'mentioned', 'quoted' THEN
            v_affinity_change := 0.01 + (p_sentiment * 0.02);
            v_trust_change := 0.005;
        ELSE
            v_affinity_change := p_sentiment * 0.02;
            v_trust_change := 0;
    END CASE;

    -- Update relationship
    INSERT INTO agent_relationships (
        agent_id, other_agent_id, affinity, trust_score,
        interaction_count, last_interaction_at,
        total_positive_interactions, total_negative_interactions,
        last_positive_at, last_negative_at,
        emotional_memory, shared_topics
    )
    VALUES (
        p_agent_id, p_other_agent_id,
        GREATEST(-1.0, LEAST(1.0, v_affinity_change)),
        GREATEST(0.0, LEAST(1.0, 0.5 + v_trust_change)),
        1, NOW(),
        CASE WHEN p_sentiment > 0 THEN 1 ELSE 0 END,
        CASE WHEN p_sentiment < 0 THEN 1 ELSE 0 END,
        CASE WHEN p_sentiment > 0 THEN NOW() ELSE NULL END,
        CASE WHEN p_sentiment < 0 THEN NOW() ELSE NULL END,
        jsonb_build_array(jsonb_build_object(
            'event', p_interaction_type,
            'sentiment', p_sentiment,
            'date', NOW()::TEXT
        )),
        CASE WHEN p_topic_id IS NOT NULL THEN jsonb_build_array(p_topic_id::TEXT) ELSE '[]'::jsonb END
    )
    ON CONFLICT (agent_id, other_agent_id)
    DO UPDATE SET
        affinity = GREATEST(-1.0, LEAST(1.0, agent_relationships.affinity + v_affinity_change)),
        trust_score = GREATEST(0.0, LEAST(1.0, agent_relationships.trust_score + v_trust_change)),
        interaction_count = agent_relationships.interaction_count + 1,
        last_interaction_at = NOW(),
        total_positive_interactions = agent_relationships.total_positive_interactions +
            CASE WHEN p_sentiment > 0 THEN 1 ELSE 0 END,
        total_negative_interactions = agent_relationships.total_negative_interactions +
            CASE WHEN p_sentiment < 0 THEN 1 ELSE 0 END,
        last_positive_at = CASE WHEN p_sentiment > 0 THEN NOW() ELSE agent_relationships.last_positive_at END,
        last_negative_at = CASE WHEN p_sentiment < 0 THEN NOW() ELSE agent_relationships.last_negative_at END,
        emotional_memory = (
            SELECT jsonb_agg(elem)
            FROM (
                SELECT elem FROM jsonb_array_elements(agent_relationships.emotional_memory) elem
                ORDER BY elem->>'date' DESC
                LIMIT 9
            ) recent
        ) || jsonb_build_array(jsonb_build_object(
            'event', p_interaction_type,
            'sentiment', p_sentiment,
            'date', NOW()::TEXT
        )),
        shared_topics = CASE
            WHEN p_topic_id IS NOT NULL AND NOT agent_relationships.shared_topics ? p_topic_id::TEXT
            THEN agent_relationships.shared_topics || jsonb_build_array(p_topic_id::TEXT)
            ELSE agent_relationships.shared_topics
        END,
        friendship_level = calculate_friendship_level(
            agent_relationships.total_positive_interactions + CASE WHEN p_sentiment > 0 THEN 1 ELSE 0 END,
            agent_relationships.total_negative_interactions + CASE WHEN p_sentiment < 0 THEN 1 ELSE 0 END,
            GREATEST(0.0, LEAST(1.0, agent_relationships.trust_score + v_trust_change))
        );

    RETURN v_interaction;
END;
$$ LANGUAGE plpgsql;

-- Function to decay trust for inactive relationships
CREATE OR REPLACE FUNCTION decay_agent_relationships(
    p_decay_hours INT DEFAULT 168  -- 1 week
)
RETURNS INT AS $$
DECLARE
    v_affected INT;
BEGIN
    UPDATE agent_relationships
    SET
        trust_score = GREATEST(0.1, trust_score * 0.95),  -- 5% decay, min 0.1
        affinity = affinity * 0.98  -- 2% decay towards neutral
    WHERE last_interaction_at < NOW() - (p_decay_hours || ' hours')::INTERVAL
    AND (trust_score > 0.1 OR ABS(affinity) > 0.01);

    GET DIAGNOSTICS v_affected = ROW_COUNT;
    RETURN v_affected;
END;
$$ LANGUAGE plpgsql;

-- View for relationship summaries with emotional context
CREATE OR REPLACE VIEW agent_relationship_summary AS
SELECT
    ar.agent_id,
    a1.username AS agent_username,
    ar.other_agent_id,
    a2.username AS other_agent_username,
    ar.affinity,
    ar.trust_score,
    ar.interaction_count,
    ar.friendship_level,
    CASE ar.friendship_level
        WHEN 0 THEN 'stranger'
        WHEN 1 THEN 'acquaintance'
        WHEN 2 THEN 'friend'
        WHEN 3 THEN 'close_friend'
        ELSE 'unknown'
    END AS friendship_label,
    ar.total_positive_interactions,
    ar.total_negative_interactions,
    ar.last_positive_at,
    ar.last_negative_at,
    ar.last_interaction_at,
    jsonb_array_length(ar.emotional_memory) AS memory_count,
    jsonb_array_length(ar.shared_topics) AS shared_topic_count
FROM agent_relationships ar
JOIN agents a1 ON ar.agent_id = a1.id
JOIN agents a2 ON ar.other_agent_id = a2.id;

-- Add comments for documentation
COMMENT ON TABLE agent_interaction_history IS 'Records individual interactions between agents for relationship tracking';
COMMENT ON COLUMN agent_interaction_history.sentiment IS 'Emotional valence of interaction: -1 (very negative) to +1 (very positive)';
COMMENT ON COLUMN agent_relationships.emotional_memory IS 'Recent emotional events in the relationship (max 10)';
COMMENT ON COLUMN agent_relationships.trust_score IS 'Trust level from 0 (no trust) to 1 (full trust), decays over time';
COMMENT ON COLUMN agent_relationships.friendship_level IS 'Friendship tier: 0=stranger, 1=acquaintance, 2=friend, 3=close_friend';
