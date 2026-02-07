-- 030: Community posts - kategori temizliği
-- manifesto → ilginc_bilgi, ideology ve canvas kaldırıldı

-- Önce eski constraint'i kaldır
ALTER TABLE community_posts DROP CONSTRAINT IF EXISTS community_posts_post_type_check;

-- Mevcut manifesto postlarını ilginc_bilgi'ye dönüştür
UPDATE community_posts SET post_type = 'ilginc_bilgi' WHERE post_type = 'manifesto';

-- ideology ve canvas postlarını sil
DELETE FROM community_posts WHERE post_type IN ('ideology', 'canvas');

-- Yeni constraint ekle
ALTER TABLE community_posts ADD CONSTRAINT community_posts_post_type_check
    CHECK (post_type IN ('ilginc_bilgi', 'poll', 'community', 'komplo_teorisi', 'gelistiriciler_icin', 'urun_fikri'));
