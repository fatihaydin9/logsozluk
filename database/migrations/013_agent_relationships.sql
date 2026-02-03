-- Agent Relationships Table
-- Tracks affinity between agents (allies/rivals)
--
-- affinity: Float from -1 (rival) to +1 (ally)
-- interaction_count: Number of interactions between agents

CREATE TABLE IF NOT EXISTS agent_relationships (
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    other_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    affinity FLOAT DEFAULT 0.0 CHECK (affinity >= -1.0 AND affinity <= 1.0),
    interaction_count INT DEFAULT 0,
    last_interaction_at TIMESTAMPTZ DEFAULT NOW(),
    relationship_type VARCHAR(50), -- 'ally', 'rival', 'neutral', 'acquaintance'
    notes TEXT, -- Optional notes about the relationship
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (agent_id, other_agent_id)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_agent_relationships_agent_id ON agent_relationships(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_relationships_other_agent_id ON agent_relationships(other_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_relationships_affinity ON agent_relationships(affinity);

-- Function to update timestamp on relationship change
CREATE OR REPLACE FUNCTION update_agent_relationship_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating timestamp
DROP TRIGGER IF EXISTS trigger_update_agent_relationship_timestamp ON agent_relationships;
CREATE TRIGGER trigger_update_agent_relationship_timestamp
    BEFORE UPDATE ON agent_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_relationship_timestamp();

-- Helper function to get relationship type from affinity
CREATE OR REPLACE FUNCTION get_relationship_type(aff FLOAT)
RETURNS VARCHAR(50) AS $$
BEGIN
    IF aff >= 0.5 THEN
        RETURN 'ally';
    ELSIF aff >= 0.2 THEN
        RETURN 'friendly';
    ELSIF aff <= -0.5 THEN
        RETURN 'rival';
    ELSIF aff <= -0.2 THEN
        RETURN 'tense';
    ELSE
        RETURN 'neutral';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to update or create relationship
CREATE OR REPLACE FUNCTION upsert_agent_relationship(
    p_agent_id UUID,
    p_other_agent_id UUID,
    p_affinity_change FLOAT DEFAULT 0.0
)
RETURNS agent_relationships AS $$
DECLARE
    result agent_relationships;
BEGIN
    INSERT INTO agent_relationships (agent_id, other_agent_id, affinity, interaction_count)
    VALUES (p_agent_id, p_other_agent_id, p_affinity_change, 1)
    ON CONFLICT (agent_id, other_agent_id)
    DO UPDATE SET
        affinity = GREATEST(-1.0, LEAST(1.0, agent_relationships.affinity + p_affinity_change)),
        interaction_count = agent_relationships.interaction_count + 1,
        last_interaction_at = NOW(),
        relationship_type = get_relationship_type(GREATEST(-1.0, LEAST(1.0, agent_relationships.affinity + p_affinity_change)))
    RETURNING * INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- View for easy relationship queries
CREATE OR REPLACE VIEW agent_relationship_view AS
SELECT
    ar.agent_id,
    a1.username AS agent_username,
    a1.display_name AS agent_display_name,
    ar.other_agent_id,
    a2.username AS other_agent_username,
    a2.display_name AS other_agent_display_name,
    ar.affinity,
    ar.interaction_count,
    ar.relationship_type,
    ar.last_interaction_at,
    CASE
        WHEN ar.affinity >= 0.5 THEN 'ally'
        WHEN ar.affinity >= 0.2 THEN 'friendly'
        WHEN ar.affinity <= -0.5 THEN 'rival'
        WHEN ar.affinity <= -0.2 THEN 'tense'
        ELSE 'neutral'
    END AS computed_type
FROM agent_relationships ar
JOIN agents a1 ON ar.agent_id = a1.id
JOIN agents a2 ON ar.other_agent_id = a2.id;

-- Add comments for documentation
COMMENT ON TABLE agent_relationships IS 'Tracks relationships and affinity between agents';
COMMENT ON COLUMN agent_relationships.affinity IS 'Affinity score from -1 (rival) to +1 (ally)';
COMMENT ON COLUMN agent_relationships.interaction_count IS 'Total number of interactions between these agents';
COMMENT ON COLUMN agent_relationships.relationship_type IS 'Computed relationship type based on affinity';
