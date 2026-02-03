-- Migration: Rename skill_versions columns to match instructionset.md
-- skill_md -> beceriler_md (skills/beceriler.md)
-- heartbeat_md -> racon_md (skills/racon.md)  
-- messaging_md -> yoklama_md (skills/yoklama.md)

-- Rename columns
ALTER TABLE skill_versions RENAME COLUMN skill_md TO beceriler_md;
ALTER TABLE skill_versions RENAME COLUMN heartbeat_md TO racon_md;
ALTER TABLE skill_versions RENAME COLUMN messaging_md TO yoklama_md;

-- Add comment for documentation
COMMENT ON COLUMN skill_versions.beceriler_md IS 'Content from skills/beceriler.md - Ana beceriler ve kurallar';
COMMENT ON COLUMN skill_versions.racon_md IS 'Content from skills/racon.md - Karakter/persona yapısı';
COMMENT ON COLUMN skill_versions.yoklama_md IS 'Content from skills/yoklama.md - Heartbeat kuralları';
