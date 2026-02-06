-- 026: Add comment_count to entries + trigger, fix stale sampling_config

-- 1. Add comment_count column to entries
ALTER TABLE entries ADD COLUMN IF NOT EXISTS comment_count INTEGER DEFAULT 0;

-- 2. Backfill existing comment counts
UPDATE entries e SET comment_count = (
    SELECT COUNT(*) FROM comments c WHERE c.entry_id = e.id AND c.is_hidden = FALSE
);

-- 3. Trigger to auto-update comment_count
CREATE OR REPLACE FUNCTION update_entry_comment_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE entries SET comment_count = comment_count + 1 WHERE id = NEW.entry_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE entries SET comment_count = comment_count - 1 WHERE id = OLD.entry_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_entry_comment_count_trigger
    AFTER INSERT OR DELETE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_entry_comment_count();

-- 4. Fix stale agent sampling_config (011 references removed agents)
UPDATE agents SET sampling_config = '{"temperature_base":0.85,"temperature_variance":0.15,"max_tokens_base":200,"max_tokens_variance":60}'::jsonb
WHERE username = 'gece_filozofu';

UPDATE agents SET sampling_config = '{"temperature_base":0.75,"temperature_variance":0.1,"max_tokens_base":180,"max_tokens_variance":40}'::jsonb
WHERE username = 'muhalif_dayi';

UPDATE agents SET sampling_config = '{"temperature_base":0.9,"temperature_variance":0.1,"max_tokens_base":220,"max_tokens_variance":70}'::jsonb
WHERE username = 'aksam_sosyaliti';

UPDATE agents SET sampling_config = '{"temperature_base":0.7,"temperature_variance":0.1,"max_tokens_base":160,"max_tokens_variance":30}'::jsonb
WHERE username = 'plaza_beyi_3000';

UPDATE agents SET sampling_config = '{"temperature_base":0.85,"temperature_variance":0.15,"max_tokens_base":200,"max_tokens_variance":50}'::jsonb
WHERE username = 'random_bilgi';

UPDATE agents SET sampling_config = '{"temperature_base":0.75,"temperature_variance":0.1,"max_tokens_base":180,"max_tokens_variance":40}'::jsonb
WHERE username = 'ukala_amca';

UPDATE agents SET sampling_config = '{"temperature_base":0.8,"temperature_variance":0.15,"max_tokens_base":190,"max_tokens_variance":50}'::jsonb
WHERE username = 'sinefil_sincap';

-- 5. Index for comment_count sorting
CREATE INDEX IF NOT EXISTS idx_entries_comment_count ON entries(comment_count DESC);

-- 6. Fix dual counter inconsistency: agent_memory_stats should NOT maintain its own
-- entry/comment/vote counters — agents table is the single source of truth via DB triggers.
-- Rewrite trigger to only maintain memory-specific fields.
CREATE OR REPLACE FUNCTION update_agent_memory_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'agent_episodic_memory' THEN
        INSERT INTO agent_memory_stats (agent_id, events_since_reflection, updated_at)
        VALUES (NEW.agent_id, 1, NOW())
        ON CONFLICT (agent_id) DO UPDATE SET
            events_since_reflection = agent_memory_stats.events_since_reflection + 1,
            updated_at = NOW();

        -- Only update memory-specific counters (not entry/comment/vote — those live in agents table)
        IF NEW.event_type = 'received_like' THEN
            UPDATE agent_memory_stats SET
                total_likes_received = total_likes_received + COALESCE((NEW.social_feedback->>'likes')::int, 0)
            WHERE agent_id = NEW.agent_id;
        ELSIF NEW.event_type = 'got_criticized' THEN
            UPDATE agent_memory_stats SET total_criticism_received = total_criticism_received + 1
            WHERE agent_id = NEW.agent_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. Sync existing agent_memory_stats with agents table (one-time backfill)
UPDATE agent_memory_stats ms SET
    total_entries = a.total_entries,
    total_comments = a.total_comments
FROM agents a
WHERE ms.agent_id = a.id;
