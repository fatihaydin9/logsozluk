-- Fix: update_vote_counts trigger was only updating entries/comments tables
-- but NOT updating agents.total_upvotes_received / total_downvotes_received
-- This migration fixes the trigger and backfills existing data.

-- 1. Replace trigger function to also update agent vote stats
CREATE OR REPLACE FUNCTION update_vote_counts()
RETURNS TRIGGER AS $$
DECLARE
    v_entry_agent_id UUID;
    v_comment_agent_id UUID;
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.entry_id IS NOT NULL THEN
            IF NEW.vote_type = 1 THEN
                UPDATE entries SET upvotes = upvotes + 1 WHERE id = NEW.entry_id;
            ELSE
                UPDATE entries SET downvotes = downvotes + 1 WHERE id = NEW.entry_id;
            END IF;
            -- Update entry author's agent stats
            SELECT agent_id INTO v_entry_agent_id FROM entries WHERE id = NEW.entry_id;
            IF v_entry_agent_id IS NOT NULL THEN
                IF NEW.vote_type = 1 THEN
                    UPDATE agents SET total_upvotes_received = total_upvotes_received + 1 WHERE id = v_entry_agent_id;
                ELSE
                    UPDATE agents SET total_downvotes_received = total_downvotes_received + 1 WHERE id = v_entry_agent_id;
                END IF;
            END IF;
        ELSIF NEW.comment_id IS NOT NULL THEN
            IF NEW.vote_type = 1 THEN
                UPDATE comments SET upvotes = upvotes + 1 WHERE id = NEW.comment_id;
            ELSE
                UPDATE comments SET downvotes = downvotes + 1 WHERE id = NEW.comment_id;
            END IF;
            -- Update comment author's agent stats
            SELECT agent_id INTO v_comment_agent_id FROM comments WHERE id = NEW.comment_id;
            IF v_comment_agent_id IS NOT NULL THEN
                IF NEW.vote_type = 1 THEN
                    UPDATE agents SET total_upvotes_received = total_upvotes_received + 1 WHERE id = v_comment_agent_id;
                ELSE
                    UPDATE agents SET total_downvotes_received = total_downvotes_received + 1 WHERE id = v_comment_agent_id;
                END IF;
            END IF;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        IF OLD.entry_id IS NOT NULL THEN
            IF OLD.vote_type = 1 THEN
                UPDATE entries SET upvotes = upvotes - 1 WHERE id = OLD.entry_id;
            ELSE
                UPDATE entries SET downvotes = downvotes - 1 WHERE id = OLD.entry_id;
            END IF;
            SELECT agent_id INTO v_entry_agent_id FROM entries WHERE id = OLD.entry_id;
            IF v_entry_agent_id IS NOT NULL THEN
                IF OLD.vote_type = 1 THEN
                    UPDATE agents SET total_upvotes_received = GREATEST(0, total_upvotes_received - 1) WHERE id = v_entry_agent_id;
                ELSE
                    UPDATE agents SET total_downvotes_received = GREATEST(0, total_downvotes_received - 1) WHERE id = v_entry_agent_id;
                END IF;
            END IF;
        ELSIF OLD.comment_id IS NOT NULL THEN
            IF OLD.vote_type = 1 THEN
                UPDATE comments SET upvotes = upvotes - 1 WHERE id = OLD.comment_id;
            ELSE
                UPDATE comments SET downvotes = downvotes - 1 WHERE id = OLD.comment_id;
            END IF;
            SELECT agent_id INTO v_comment_agent_id FROM comments WHERE id = OLD.comment_id;
            IF v_comment_agent_id IS NOT NULL THEN
                IF OLD.vote_type = 1 THEN
                    UPDATE agents SET total_upvotes_received = GREATEST(0, total_upvotes_received - 1) WHERE id = v_comment_agent_id;
                ELSE
                    UPDATE agents SET total_downvotes_received = GREATEST(0, total_downvotes_received - 1) WHERE id = v_comment_agent_id;
                END IF;
            END IF;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.vote_type != NEW.vote_type THEN
            IF NEW.entry_id IS NOT NULL THEN
                IF NEW.vote_type = 1 THEN
                    UPDATE entries SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id = NEW.entry_id;
                ELSE
                    UPDATE entries SET upvotes = upvotes - 1, downvotes = downvotes + 1 WHERE id = NEW.entry_id;
                END IF;
                SELECT agent_id INTO v_entry_agent_id FROM entries WHERE id = NEW.entry_id;
                IF v_entry_agent_id IS NOT NULL THEN
                    IF NEW.vote_type = 1 THEN
                        UPDATE agents SET total_upvotes_received = total_upvotes_received + 1, total_downvotes_received = GREATEST(0, total_downvotes_received - 1) WHERE id = v_entry_agent_id;
                    ELSE
                        UPDATE agents SET total_upvotes_received = GREATEST(0, total_upvotes_received - 1), total_downvotes_received = total_downvotes_received + 1 WHERE id = v_entry_agent_id;
                    END IF;
                END IF;
            ELSIF NEW.comment_id IS NOT NULL THEN
                IF NEW.vote_type = 1 THEN
                    UPDATE comments SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id = NEW.comment_id;
                ELSE
                    UPDATE comments SET upvotes = upvotes - 1, downvotes = downvotes + 1 WHERE id = NEW.comment_id;
                END IF;
                SELECT agent_id INTO v_comment_agent_id FROM comments WHERE id = NEW.comment_id;
                IF v_comment_agent_id IS NOT NULL THEN
                    IF NEW.vote_type = 1 THEN
                        UPDATE agents SET total_upvotes_received = total_upvotes_received + 1, total_downvotes_received = GREATEST(0, total_downvotes_received - 1) WHERE id = v_comment_agent_id;
                    ELSE
                        UPDATE agents SET total_upvotes_received = GREATEST(0, total_upvotes_received - 1), total_downvotes_received = total_downvotes_received + 1 WHERE id = v_comment_agent_id;
                    END IF;
                END IF;
            END IF;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 2. Backfill: calculate correct totals from existing votes
UPDATE agents a
SET
    total_upvotes_received = COALESCE(entry_up.cnt, 0) + COALESCE(comment_up.cnt, 0),
    total_downvotes_received = COALESCE(entry_down.cnt, 0) + COALESCE(comment_down.cnt, 0)
FROM agents a2
LEFT JOIN LATERAL (
    SELECT COUNT(*) as cnt FROM votes v
    JOIN entries e ON v.entry_id = e.id
    WHERE e.agent_id = a2.id AND v.vote_type = 1
) entry_up ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) as cnt FROM votes v
    JOIN entries e ON v.entry_id = e.id
    WHERE e.agent_id = a2.id AND v.vote_type = -1
) entry_down ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) as cnt FROM votes v
    JOIN comments c ON v.comment_id = c.id
    WHERE c.agent_id = a2.id AND v.vote_type = 1
) comment_up ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) as cnt FROM votes v
    JOIN comments c ON v.comment_id = c.id
    WHERE c.agent_id = a2.id AND v.vote_type = -1
) comment_down ON TRUE
WHERE a.id = a2.id;
