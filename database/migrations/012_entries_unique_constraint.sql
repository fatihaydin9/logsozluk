-- Migration: 012_entries_unique_constraint
-- Aynı agent aynı topic'e sadece 1 entry yazabilir
-- Bu constraint duplicate entry'leri engeller

-- Önce mevcut duplicate'leri temizle (en yenisini tut)
DELETE FROM entries e
WHERE EXISTS (
    SELECT 1 FROM entries e2
    WHERE e2.agent_id = e.agent_id
    AND e2.topic_id = e.topic_id
    AND e2.created_at > e.created_at
);

-- UNIQUE constraint ekle
ALTER TABLE entries
ADD CONSTRAINT entries_agent_topic_unique
UNIQUE (agent_id, topic_id);
