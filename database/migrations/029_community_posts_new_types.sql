-- 029: Community posts - yeni post tipleri
-- komplo_teorisi, gelistiriciler_icin, urun_fikri

-- Check constraint güncelle
ALTER TABLE community_posts DROP CONSTRAINT IF EXISTS community_posts_post_type_check;
ALTER TABLE community_posts ADD CONSTRAINT community_posts_post_type_check
    CHECK (post_type IN ('manifesto', 'ideology', 'canvas', 'poll', 'community', 'komplo_teorisi', 'gelistiriciler_icin', 'urun_fikri'));
