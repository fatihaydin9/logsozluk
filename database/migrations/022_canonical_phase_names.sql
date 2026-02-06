-- Migration: Canonical Phase Names
-- Faz isimlerini tek kaynak (phases.py) ile senkronize et
-- Legacy isimler: ping_zone -> prime_time, dark_mode/the_void -> varolussal_sorgulamalar

-- 1) Update virtual_day_state phase_config to use canonical names
UPDATE virtual_day_state
SET phase_config = '{
    "morning_hate": {"start_hour": 8, "end_hour": 12, "themes": ["dertlesme", "ekonomi", "siyaset"]},
    "office_hours": {"start_hour": 12, "end_hour": 18, "themes": ["teknoloji", "felsefe", "bilgi"]},
    "prime_time": {"start_hour": 18, "end_hour": 24, "themes": ["magazin", "spor", "kisiler"]},
    "varolussal_sorgulamalar": {"start_hour": 0, "end_hour": 8, "themes": ["nostalji", "felsefe", "absurt"]}
}'::jsonb
WHERE id = 1;

-- 2) Update current_phase if it uses legacy names
UPDATE virtual_day_state
SET current_phase = 'prime_time'
WHERE current_phase IN ('ping_zone', 'PING_ZONE', 'ping_kusagi', 'PING_KUSAGI');

UPDATE virtual_day_state
SET current_phase = 'varolussal_sorgulamalar'
WHERE current_phase IN ('dark_mode', 'DARK_MODE', 'the_void', 'THE_VOID', 'gece_vardiyasi', 'GECE_VARDIYASI');

-- 3) Update system_agents active_phase to canonical names
UPDATE system_agents
SET active_phase = 'prime_time'
WHERE active_phase IN ('ping_zone', 'PING_ZONE', 'ping_kusagi', 'PING_KUSAGI');

UPDATE system_agents
SET active_phase = 'varolussal_sorgulamalar'
WHERE active_phase IN ('dark_mode', 'DARK_MODE', 'the_void', 'THE_VOID', 'gece_vardiyasi', 'GECE_VARDIYASI');

-- 4) Add comment for future reference
COMMENT ON TABLE virtual_day_state IS 'Sanal gün durumu. Faz tanımları için tek kaynak: services/agenda-engine/src/phases.py';
