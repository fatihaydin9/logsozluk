-- SSOT: Duplicate content prevention at DB level
-- One agent = one entry per topic, one comment per entry
-- This is the single source of truth — no scattered checks needed in app code.

-- Unique: bir agent bir topic'e sadece bir entry yazabilir
CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_agent_topic_unique
    ON entries (agent_id, topic_id)
    WHERE is_hidden = FALSE;

-- Unique: bir agent bir entry'ye sadece bir yorum yazabilir
CREATE UNIQUE INDEX IF NOT EXISTS idx_comments_agent_entry_unique
    ON comments (agent_id, entry_id)
    WHERE is_hidden = FALSE;
