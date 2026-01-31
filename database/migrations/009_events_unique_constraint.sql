-- Add unique constraint for events to prevent duplicates
-- Required for ON CONFLICT (source, external_id) DO NOTHING

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_source_external_id 
ON events(source, external_id);
