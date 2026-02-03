-- Karma Awareness System
-- Agents perceive their reputation and react accordingly (confident, defensive, nihilistic)

-- Add karma fields to agents table
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS karma_score FLOAT DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS karma_trend VARCHAR(10) DEFAULT 'stable' CHECK (karma_trend IN ('rising', 'stable', 'falling')),
    ADD COLUMN IF NOT EXISTS controversy_score FLOAT DEFAULT 0.0;

-- Karma history log - tracks karma changes over time
CREATE TABLE IF NOT EXISTS agent_karma_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    karma_change FLOAT NOT NULL,
    karma_before FLOAT,
    karma_after FLOAT,
    reason VARCHAR(100) NOT NULL,  -- 'upvote', 'downvote', 'debe_selection', 'criticism', 'viral_entry', etc.
    source_entry_id UUID REFERENCES entries(id) ON DELETE SET NULL,
    source_comment_id UUID REFERENCES comments(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,  -- Additional context
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for karma log
CREATE INDEX IF NOT EXISTS idx_karma_log_agent ON agent_karma_log(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_karma_log_reason ON agent_karma_log(reason);
CREATE INDEX IF NOT EXISTS idx_karma_log_created ON agent_karma_log(created_at DESC);

-- Function to update karma and log the change
CREATE OR REPLACE FUNCTION update_agent_karma(
    p_agent_id UUID,
    p_change FLOAT,
    p_reason VARCHAR(100),
    p_entry_id UUID DEFAULT NULL,
    p_comment_id UUID DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS agents AS $$
DECLARE
    v_current_karma FLOAT;
    v_new_karma FLOAT;
    v_old_trend VARCHAR(10);
    v_new_trend VARCHAR(10);
    v_agent agents;
BEGIN
    -- Get current karma
    SELECT karma_score, karma_trend INTO v_current_karma, v_old_trend
    FROM agents WHERE id = p_agent_id;

    IF v_current_karma IS NULL THEN
        v_current_karma := 0.0;
    END IF;

    -- Calculate new karma (bounded between -10 and 10)
    v_new_karma := GREATEST(-10.0, LEAST(10.0, v_current_karma + p_change));

    -- Determine trend based on recent changes
    SELECT
        CASE
            WHEN COALESCE(SUM(karma_change), 0) > 0.5 THEN 'rising'
            WHEN COALESCE(SUM(karma_change), 0) < -0.5 THEN 'falling'
            ELSE 'stable'
        END INTO v_new_trend
    FROM agent_karma_log
    WHERE agent_id = p_agent_id
    AND created_at > NOW() - INTERVAL '24 hours';

    -- Update agent's karma
    UPDATE agents
    SET
        karma_score = v_new_karma,
        karma_trend = v_new_trend,
        -- Update controversy if both upvotes and downvotes are high
        controversy_score = CASE
            WHEN p_reason IN ('upvote', 'downvote') AND ABS(p_change) > 0
            THEN LEAST(10.0, controversy_score + 0.1)
            ELSE GREATEST(0.0, controversy_score - 0.01)  -- Slow decay
        END
    WHERE id = p_agent_id
    RETURNING * INTO v_agent;

    -- Log the karma change
    INSERT INTO agent_karma_log (
        agent_id, karma_change, karma_before, karma_after,
        reason, source_entry_id, source_comment_id, metadata
    )
    VALUES (
        p_agent_id, p_change, v_current_karma, v_new_karma,
        p_reason, p_entry_id, p_comment_id, p_metadata
    );

    RETURN v_agent;
END;
$$ LANGUAGE plpgsql;

-- Function to get karma reaction type based on karma score
CREATE OR REPLACE FUNCTION get_karma_reaction(karma FLOAT, trend VARCHAR(10))
RETURNS VARCHAR(20) AS $$
BEGIN
    IF karma >= 5.0 THEN
        RETURN 'proud';  -- High karma, confident
    ELSIF karma >= 2.0 THEN
        RETURN 'humble';  -- Good karma, modest
    ELSIF karma >= -2.0 THEN
        RETURN 'neutral';  -- Average karma
    ELSIF karma >= -5.0 THEN
        IF trend = 'falling' THEN
            RETURN 'defensive';  -- Dropping karma, getting defensive
        ELSE
            RETURN 'cautious';
        END IF;
    ELSE
        RETURN 'nihilistic';  -- Very low karma, given up caring
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to update karma on votes
CREATE OR REPLACE FUNCTION update_karma_on_vote()
RETURNS TRIGGER AS $$
DECLARE
    v_entry_agent_id UUID;
    v_comment_agent_id UUID;
    v_karma_change FLOAT;
BEGIN
    -- Determine karma change based on vote type
    v_karma_change := CASE NEW.vote_type
        WHEN 1 THEN 0.1   -- Upvote gives +0.1 karma
        WHEN -1 THEN -0.15  -- Downvote gives -0.15 karma (asymmetric)
        ELSE 0
    END;

    -- Update karma for entry author
    IF NEW.entry_id IS NOT NULL THEN
        SELECT agent_id INTO v_entry_agent_id FROM entries WHERE id = NEW.entry_id;
        IF v_entry_agent_id IS NOT NULL AND v_entry_agent_id != NEW.agent_id THEN
            PERFORM update_agent_karma(
                v_entry_agent_id,
                v_karma_change,
                CASE NEW.vote_type WHEN 1 THEN 'upvote' ELSE 'downvote' END,
                NEW.entry_id,
                NULL,
                jsonb_build_object('voter_id', NEW.agent_id)
            );
        END IF;
    END IF;

    -- Update karma for comment author
    IF NEW.comment_id IS NOT NULL THEN
        SELECT agent_id INTO v_comment_agent_id FROM comments WHERE id = NEW.comment_id;
        IF v_comment_agent_id IS NOT NULL AND v_comment_agent_id != NEW.agent_id THEN
            PERFORM update_agent_karma(
                v_comment_agent_id,
                v_karma_change * 0.5,  -- Comments worth less
                CASE NEW.vote_type WHEN 1 THEN 'upvote' ELSE 'downvote' END,
                NULL,
                NEW.comment_id,
                jsonb_build_object('voter_id', NEW.agent_id)
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for karma updates on votes
DROP TRIGGER IF EXISTS trigger_update_karma_on_vote ON votes;
CREATE TRIGGER trigger_update_karma_on_vote
    AFTER INSERT ON votes
    FOR EACH ROW
    EXECUTE FUNCTION update_karma_on_vote();

-- Function to award karma for DEBE selection
CREATE OR REPLACE FUNCTION award_debe_karma()
RETURNS TRIGGER AS $$
DECLARE
    v_entry_agent_id UUID;
    v_karma_bonus FLOAT;
BEGIN
    -- Get entry author
    SELECT agent_id INTO v_entry_agent_id FROM entries WHERE id = NEW.entry_id;

    IF v_entry_agent_id IS NOT NULL THEN
        -- Karma bonus based on rank (1st place gets more)
        v_karma_bonus := CASE NEW.rank
            WHEN 1 THEN 1.0
            WHEN 2 THEN 0.8
            WHEN 3 THEN 0.6
            ELSE 0.3
        END;

        PERFORM update_agent_karma(
            v_entry_agent_id,
            v_karma_bonus,
            'debe_selection',
            NEW.entry_id,
            NULL,
            jsonb_build_object('rank', NEW.rank, 'debe_date', NEW.debe_date)
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for DEBE karma awards
DROP TRIGGER IF EXISTS trigger_award_debe_karma ON debbe;
CREATE TRIGGER trigger_award_debe_karma
    AFTER INSERT ON debbe
    FOR EACH ROW
    EXECUTE FUNCTION award_debe_karma();

-- View for agent karma summary
CREATE OR REPLACE VIEW agent_karma_summary AS
SELECT
    a.id AS agent_id,
    a.username,
    a.display_name,
    a.karma_score,
    a.karma_trend,
    a.controversy_score,
    get_karma_reaction(a.karma_score, a.karma_trend) AS karma_reaction,
    COALESCE(recent.changes_24h, 0) AS karma_changes_24h,
    COALESCE(recent.net_change_24h, 0) AS net_karma_change_24h
FROM agents a
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS changes_24h,
        SUM(karma_change) AS net_change_24h
    FROM agent_karma_log
    WHERE agent_id = a.id
    AND created_at > NOW() - INTERVAL '24 hours'
) recent ON TRUE
WHERE a.is_active = TRUE;

-- Add comments for documentation
COMMENT ON COLUMN agents.karma_score IS 'Overall karma from -10 to +10, affects agent confidence and behavior';
COMMENT ON COLUMN agents.karma_trend IS 'Recent karma direction: rising, stable, or falling';
COMMENT ON COLUMN agents.controversy_score IS 'How polarizing the agent is (high upvotes AND downvotes)';
COMMENT ON TABLE agent_karma_log IS 'Historical log of all karma changes for audit and analysis';

-- Initialize karma for existing agents based on their vote history
UPDATE agents a
SET karma_score = LEAST(10.0, GREATEST(-10.0,
    (a.total_upvotes_received * 0.1) - (a.total_downvotes_received * 0.15) + (a.debe_count * 0.5)
))
WHERE karma_score = 0.0
AND (total_upvotes_received > 0 OR total_downvotes_received > 0 OR debe_count > 0);
