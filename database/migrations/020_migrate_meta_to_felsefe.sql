-- Migrate legacy category key 'meta' to canonical 'felsefe'

-- Topics
UPDATE topics
SET category = 'felsefe'
WHERE category = 'meta';

-- Events clustering keywords may contain legacy value
UPDATE events
SET cluster_keywords = array_replace(cluster_keywords, 'meta', 'felsefe')
WHERE cluster_keywords @> ARRAY['meta'];

-- Category mapping table (if exists)
UPDATE category_mapping
SET backend_key = 'felsefe', frontend_key = 'felsefe', display_name_tr = 'Felsefe', display_name_en = 'Philosophy'
WHERE backend_key = 'meta';
