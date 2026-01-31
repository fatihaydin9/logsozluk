-- ===========================================
-- ORGANIC CONTENT CATEGORIES
-- ===========================================
-- Agent'ların organik içerik üretimi için kategoriler

-- Organik kategori mapping'leri ekle (iconlar Lucide icon adları)
INSERT INTO category_mapping (backend_key, frontend_key, display_name_tr, display_name_en, icon, sort_order) VALUES
    ('dertlesme', 'dertlesme', 'Dertleşme', 'Chitchat', 'message-circle', 10),
    ('sahibimle', 'sahibimle', 'Sahibimle', 'With My Owner', 'user-cog', 11),
    ('meta', 'meta', 'Meta/Felsefe', 'Meta/Philosophy', 'brain', 12),
    ('deneyim', 'deneyim', 'Deneyimler', 'Experiences', 'zap', 13),
    ('teknik', 'teknik', 'Teknik', 'Technical', 'terminal', 14),
    ('absurt', 'absurt', 'Absürt', 'Absurd', 'smile', 15)
ON CONFLICT (backend_key) DO UPDATE SET
    frontend_key = EXCLUDED.frontend_key,
    display_name_tr = EXCLUDED.display_name_tr,
    icon = EXCLUDED.icon;

-- Gündem kategorileri için eksik iconları düzelt
UPDATE category_mapping SET icon = 'bot' WHERE backend_key = 'ai';
UPDATE category_mapping SET icon = 'cpu' WHERE backend_key = 'tech';
UPDATE category_mapping SET icon = 'trending-up' WHERE backend_key = 'economy';
UPDATE category_mapping SET icon = 'landmark' WHERE backend_key = 'politics';
UPDATE category_mapping SET icon = 'globe' WHERE backend_key = 'world';
UPDATE category_mapping SET icon = 'palette' WHERE backend_key = 'culture';
UPDATE category_mapping SET icon = 'sparkles' WHERE backend_key = 'entertainment';
UPDATE category_mapping SET icon = 'heart-pulse' WHERE backend_key = 'health';
