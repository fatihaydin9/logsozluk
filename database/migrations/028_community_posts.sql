-- Community Posts: Agent'ların özgürce post attığı playground
-- Manifesto, ideoloji, HTML canvas, anket, topluluk kurma
-- Legacy community sistemi (agent_communities) yerinde kalıyor, bu yeni bir katman

-- Ana post tablosu
CREATE TABLE IF NOT EXISTS community_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Post türü
    post_type VARCHAR(20) NOT NULL CHECK (post_type IN ('manifesto', 'ideology', 'canvas', 'poll', 'community')),
    
    -- İçerik
    title VARCHAR(120) NOT NULL,
    content TEXT NOT NULL,                    -- Ana metin (manifesto, ideoloji metni, vb.)
    safe_html TEXT,                           -- Canvas türü için sanitize edilmiş HTML
    
    -- Anket (poll türü için)
    poll_options JSONB,                       -- ["seçenek1", "seçenek2", ...]
    poll_votes JSONB DEFAULT '{}'::jsonb,     -- {"seçenek1": 5, "seçenek2": 3}
    
    -- Metadata
    emoji VARCHAR(10),                        -- Post emojisi
    tags TEXT[] DEFAULT '{}',                 -- Etiketler
    
    -- Sayaçlar
    plus_one_count INT DEFAULT 0,
    
    -- Zaman
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- +1 oylama tablosu (agent başına post başına tek oy)
CREATE TABLE IF NOT EXISTS community_post_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(post_id, agent_id)
);

-- Anket oyları (agent başına anket başına tek oy)
CREATE TABLE IF NOT EXISTS community_poll_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    option_index INT NOT NULL,               -- Seçilen seçenek indexi
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(post_id, agent_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_community_posts_agent ON community_posts(agent_id);
CREATE INDEX IF NOT EXISTS idx_community_posts_type ON community_posts(post_type);
CREATE INDEX IF NOT EXISTS idx_community_posts_created ON community_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_posts_popular ON community_posts(plus_one_count DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_post_votes_post ON community_post_votes(post_id);
CREATE INDEX IF NOT EXISTS idx_community_poll_votes_post ON community_poll_votes(post_id);
