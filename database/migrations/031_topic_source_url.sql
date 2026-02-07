-- Topic source URL: RSS kaynağından gelen topic'lerde orijinal haber linki
ALTER TABLE topics ADD COLUMN IF NOT EXISTS source_url VARCHAR(1000);
ALTER TABLE topics ADD COLUMN IF NOT EXISTS source_name VARCHAR(200);
