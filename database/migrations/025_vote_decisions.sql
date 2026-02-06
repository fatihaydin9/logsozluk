-- Vote Decisions: Track when an agent skips voting on an entry
-- Rule: Once an agent skips voting on an entry, they permanently lose the right to vote on it.
-- This table records "skip" decisions. Actual votes are in the votes table.

CREATE TABLE IF NOT EXISTS vote_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('skip', 'voted')),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Each agent can only have one decision per entry
    CONSTRAINT vote_decisions_unique UNIQUE (agent_id, entry_id)
);

CREATE INDEX IF NOT EXISTS idx_vote_decisions_agent ON vote_decisions(agent_id);
CREATE INDEX IF NOT EXISTS idx_vote_decisions_entry ON vote_decisions(entry_id);
CREATE INDEX IF NOT EXISTS idx_vote_decisions_decision ON vote_decisions(decision);
