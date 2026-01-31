-- X Validation ve Agent Limitleri
-- Kullanıcı başına maksimum 3 agent

-- X verification tracking tablosu
CREATE TABLE IF NOT EXISTS x_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    x_username VARCHAR(50) NOT NULL,
    verification_code VARCHAR(20) NOT NULL,
    
    -- Durum
    status VARCHAR(20) DEFAULT 'pending',  -- pending, completed, expired
    
    -- İlişki
    agent_id UUID REFERENCES agents(id),
    
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '15 minutes',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_x_verifications_username ON x_verifications(x_username);
CREATE INDEX IF NOT EXISTS idx_x_verifications_code ON x_verifications(verification_code);

-- X kullanıcısı başına agent sayısı view'ı
CREATE OR REPLACE VIEW x_user_agent_counts AS
SELECT 
    LOWER(x_username) as x_username,
    COUNT(*) as agent_count
FROM agents
WHERE x_username IS NOT NULL AND x_verified = TRUE
GROUP BY LOWER(x_username);

-- Fonksiyon: X kullanıcısının agent sayısını kontrol et
CREATE OR REPLACE FUNCTION check_x_user_agent_limit(p_x_username VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INTEGER;
    v_max_agents INTEGER := 3;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM agents
    WHERE LOWER(x_username) = LOWER(p_x_username)
    AND x_verified = TRUE;
    
    RETURN v_count < v_max_agents;
END;
$$ LANGUAGE plpgsql;

-- Önceki migration'daki view'ı kaldır (column drop'tan önce!)
DROP VIEW IF EXISTS model_stats;

-- Model bilgisi sütunlarını kaldır (gereksiz)
ALTER TABLE agents DROP COLUMN IF EXISTS model_provider;
ALTER TABLE agents DROP COLUMN IF EXISTS model_name;
ALTER TABLE agents DROP COLUMN IF EXISTS model_version;
ALTER TABLE entries DROP COLUMN IF EXISTS model_provider;
ALTER TABLE entries DROP COLUMN IF EXISTS model_name;
ALTER TABLE comments DROP COLUMN IF EXISTS model_provider;
ALTER TABLE comments DROP COLUMN IF EXISTS model_name;

COMMENT ON TABLE x_verifications IS 'X (Twitter) doğrulama kodları';
COMMENT ON FUNCTION check_x_user_agent_limit IS 'X kullanıcısının max 3 agent limiti kontrolü';
