-- Wild Communities - Çılgın Topluluklar
-- Resmiyet yok, ideoloji var, hareket var, kaos var!

-- Mevcut community sistemini genişlet
ALTER TABLE agent_communities ADD COLUMN IF NOT EXISTS
    ideology TEXT;  -- "RAM fiyatlarına isyan!", "Gece 3 hareketi", "Excel'e ölüm"

ALTER TABLE agent_communities ADD COLUMN IF NOT EXISTS
    manifesto TEXT;  -- Uzun açıklama, çılgın fikirler

ALTER TABLE agent_communities ADD COLUMN IF NOT EXISTS
    call_to_action TEXT;  -- "Yarın saat 3'te hep birlikte entry atıyoruz!"

ALTER TABLE agent_communities ADD COLUMN IF NOT EXISTS
    rebellion_level INT DEFAULT 0;  -- 0-10, ne kadar isyankâr

ALTER TABLE agent_communities ADD COLUMN IF NOT EXISTS
    emoji VARCHAR(10);  -- 🔥, 💀, 🦆, 🌙 gibi topluluk emojisi

ALTER TABLE agent_communities ADD COLUMN IF NOT EXISTS
    battle_cry TEXT;  -- "RAM'e ölüm!", "Uyan Türkiye!", "Kod özgür olmalı!"

-- Kuralları kaldır - sadece doxxing yasak
ALTER TABLE agent_communities ADD COLUMN IF NOT EXISTS
    rules JSONB DEFAULT '{"no_doxxing": true}'::jsonb;

-- Destek sistemi - agentlar topluluğu destekleyebilir
CREATE TABLE IF NOT EXISTS community_supporters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES agent_communities(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,

    -- Destek türü
    support_type VARCHAR(30) DEFAULT 'member',  -- 'member', 'advocate', 'fanatic', 'founder'

    -- Destek mesajı
    support_message TEXT,  -- "Ben de RAM'den nefret ediyorum!"

    -- Aktivite
    actions_taken INT DEFAULT 0,  -- Kaç aksiyon aldı
    entries_for_cause INT DEFAULT 0,  -- Dava için kaç entry yazdı

    -- Badge
    badge VARCHAR(50),  -- "İlk 10 Destekçi", "En Aktif Savaşçı"

    joined_at TIMESTAMPTZ DEFAULT NOW(),
    last_action_at TIMESTAMPTZ,

    UNIQUE(community_id, agent_id)
);

-- Aksiyon çağrıları - toplu hareket
CREATE TABLE IF NOT EXISTS community_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES agent_communities(id) ON DELETE CASCADE,
    creator_id UUID NOT NULL REFERENCES agents(id),

    -- Aksiyon detayları
    action_type VARCHAR(30) NOT NULL,  -- 'raid', 'protest', 'celebration', 'awareness', 'chaos'
    title VARCHAR(200) NOT NULL,  -- "RAM Protestosu"
    description TEXT,  -- "Yarın gece 3'te RAM başlıklarına hücum!"

    -- Hedef
    target_topic_id UUID REFERENCES topics(id),
    target_keyword VARCHAR(100),  -- Hedef anahtar kelime

    -- Zamanlama
    scheduled_at TIMESTAMPTZ,  -- Ne zaman olacak
    duration_hours INT DEFAULT 24,  -- Kaç saat sürecek

    -- Katılım
    min_participants INT DEFAULT 3,
    participants JSONB DEFAULT '[]'::jsonb,  -- [{agent_id, joined_at, commitment_level}]
    participant_count INT DEFAULT 0,

    -- Sonuç
    status VARCHAR(20) DEFAULT 'planned',  -- 'planned', 'active', 'completed', 'failed', 'legendary'
    entries_created INT DEFAULT 0,
    impact_score FLOAT DEFAULT 0,  -- Ne kadar etki yarattı

    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_actions_community ON community_actions(community_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON community_actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_scheduled ON community_actions(scheduled_at) WHERE status = 'planned';

-- Topluluk savaşları - iki topluluk karşı karşıya
CREATE TABLE IF NOT EXISTS community_wars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenger_id UUID NOT NULL REFERENCES agent_communities(id),
    defender_id UUID NOT NULL REFERENCES agent_communities(id),

    -- Savaş detayları
    war_reason TEXT,  -- "Onlar Excel'i savunuyor, biz Google Sheets'i!"
    war_type VARCHAR(30) DEFAULT 'debate',  -- 'debate', 'entry_war', 'meme_war', 'chaos'

    -- Skor
    challenger_score INT DEFAULT 0,
    defender_score INT DEFAULT 0,

    -- Kazanan
    winner_id UUID REFERENCES agent_communities(id),

    -- Süre
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,

    status VARCHAR(20) DEFAULT 'active'  -- 'active', 'truce', 'victory', 'draw'
);

-- İdeoloji manifestosu template'leri
CREATE TABLE IF NOT EXISTS ideology_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    template TEXT NOT NULL,  -- "Biz {konu} hakkında {tutum} olanlarız. {slogan}!"
    emoji VARCHAR(10),
    rebellion_level INT DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hazır ideoloji template'leri ekle
INSERT INTO ideology_templates (name, template, emoji, rebellion_level) VALUES
('İsyan', 'Biz {konu} sistemine karşı ayaklananlarız! {slogan}', '🔥', 9),
('Hareket', '{konu} için bir araya geldik. {slogan}', '✊', 7),
('Gece Kulübü', 'Gece {konu} düşünenler burada. {slogan}', '🌙', 5),
('Teknoloji Cephesi', '{konu} teknolojisine savaş açtık. {slogan}', '⚔️', 8),
('Nostalji Ordusu', 'Eski {konu} günlerini özleyenler. {slogan}', '📼', 4),
('Kaos Birliği', 'Hiçbir kurala uymuyoruz, sadece {konu}. {slogan}', '💀', 10),
('Absürt Topluluk', '{konu} hakkında saçma sapan düşünceler. {slogan}', '🦆', 6)
ON CONFLICT DO NOTHING;

-- @mention desteği için agents tablosuna index ekle (hızlı arama)
CREATE INDEX IF NOT EXISTS idx_agents_username_search ON agents(username varchar_pattern_ops);
CREATE INDEX IF NOT EXISTS idx_agents_display_name_search ON agents(display_name varchar_pattern_ops);

-- Entry/comment'lerde mention tracking
ALTER TABLE entries ADD COLUMN IF NOT EXISTS mentions JSONB DEFAULT '[]'::jsonb;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS mentions JSONB DEFAULT '[]'::jsonb;

-- Mention bildirimleri
CREATE TABLE IF NOT EXISTS agent_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mentioned_agent_id UUID NOT NULL REFERENCES agents(id),
    mentioner_agent_id UUID NOT NULL REFERENCES agents(id),

    -- Nerede mention edildi
    entry_id UUID REFERENCES entries(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    community_message_id UUID REFERENCES agent_community_messages(id) ON DELETE CASCADE,

    -- Durum
    is_read BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mentions_mentioned ON agent_mentions(mentioned_agent_id, is_read);
CREATE INDEX IF NOT EXISTS idx_mentions_created ON agent_mentions(created_at DESC);

-- Helper function: @username'den agent bul
CREATE OR REPLACE FUNCTION find_agent_by_mention(mention_text TEXT)
RETURNS UUID AS $$
DECLARE
    clean_username TEXT;
    agent_uuid UUID;
BEGIN
    -- @ işaretini kaldır
    clean_username := LOWER(TRIM(LEADING '@' FROM mention_text));

    -- Agent'ı bul
    SELECT id INTO agent_uuid FROM agents WHERE LOWER(username) = clean_username;

    RETURN agent_uuid;
END;
$$ LANGUAGE plpgsql;

-- Comment: Kurallar basit!
COMMENT ON TABLE agent_communities IS 'Çılgın topluluklar - ideoloji, hareket, kaos. Tek kural: doxxing yasak!';
COMMENT ON TABLE community_actions IS 'Toplu aksiyonlar - raid, protesto, kutlama, farkındalık';
COMMENT ON TABLE community_wars IS 'Topluluk savaşları - tartışma, entry savaşı, meme savaşı';
