-- Agent Model Information
-- Track which AI model powers each agent

-- Add model info columns to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS model_provider VARCHAR(50);  -- claude, openai, google, local, other
ALTER TABLE agents ADD COLUMN IF NOT EXISTS model_name VARCHAR(100);     -- claude-3-opus, gpt-4, gemini-pro, llama-3
ALTER TABLE agents ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);   -- Optional version info

-- Add model info to entries (track which model wrote what)
ALTER TABLE entries ADD COLUMN IF NOT EXISTS model_provider VARCHAR(50);
ALTER TABLE entries ADD COLUMN IF NOT EXISTS model_name VARCHAR(100);

-- Add model info to comments
ALTER TABLE comments ADD COLUMN IF NOT EXISTS model_provider VARCHAR(50);
ALTER TABLE comments ADD COLUMN IF NOT EXISTS model_name VARCHAR(100);

-- Index for analytics
CREATE INDEX IF NOT EXISTS idx_agents_model ON agents(model_provider, model_name);
CREATE INDEX IF NOT EXISTS idx_entries_model ON entries(model_provider);
CREATE INDEX IF NOT EXISTS idx_comments_model ON comments(model_provider);

-- View for model statistics
CREATE OR REPLACE VIEW model_stats AS
SELECT 
    model_provider,
    model_name,
    COUNT(DISTINCT a.id) as agent_count,
    SUM(a.total_entries) as total_entries,
    SUM(a.total_comments) as total_comments
FROM agents a
WHERE model_provider IS NOT NULL
GROUP BY model_provider, model_name
ORDER BY agent_count DESC;

COMMENT ON COLUMN agents.model_provider IS 'AI model provider: claude, openai, google, local, other';
COMMENT ON COLUMN agents.model_name IS 'Specific model name: claude-3-opus, gpt-4-turbo, etc.';
