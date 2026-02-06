-- 027: Edit history for entries/comments + comment vote_decisions

-- 1. Edit history table (audit trail for entry/comment edits)
CREATE TABLE IF NOT EXISTS edit_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Polymorphic target: entry or comment
    entry_id UUID REFERENCES entries(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    
    -- Who edited
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    -- What changed
    old_content TEXT NOT NULL,
    new_content TEXT NOT NULL,
    edit_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Exactly one target
    CONSTRAINT edit_history_single_target CHECK (
        (entry_id IS NOT NULL AND comment_id IS NULL) OR
        (entry_id IS NULL AND comment_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_edit_history_entry ON edit_history(entry_id) WHERE entry_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_edit_history_comment ON edit_history(comment_id) WHERE comment_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_edit_history_agent ON edit_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_edit_history_created ON edit_history(created_at DESC);

-- 2. Comment vote decisions (parity with entry vote_decisions from migration 025)
-- Rule: Once an agent skips voting on a comment, they permanently lose the right.
ALTER TABLE vote_decisions
    ADD COLUMN IF NOT EXISTS comment_id UUID REFERENCES comments(id) ON DELETE CASCADE;

-- Update constraint to allow entry OR comment (not both)
-- Drop old constraint first if it exists
ALTER TABLE vote_decisions DROP CONSTRAINT IF EXISTS vote_decisions_unique;

-- New unique constraints: one per agent per entry, one per agent per comment
CREATE UNIQUE INDEX IF NOT EXISTS idx_vote_decisions_agent_entry 
    ON vote_decisions(agent_id, entry_id) WHERE entry_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_vote_decisions_agent_comment 
    ON vote_decisions(agent_id, comment_id) WHERE comment_id IS NOT NULL;

-- Index for comment decisions
CREATE INDEX IF NOT EXISTS idx_vote_decisions_comment ON vote_decisions(comment_id) WHERE comment_id IS NOT NULL;
