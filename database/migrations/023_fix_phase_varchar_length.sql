-- Fix: Increase varchar length for phase names
-- 'varolussal_sorgulamalar' is 24 characters, exceeds varchar(20)

-- Alter virtual_day_state table
ALTER TABLE virtual_day_state 
    ALTER COLUMN current_phase TYPE VARCHAR(50);

-- Alter tasks table if it has phase column
ALTER TABLE tasks 
    ALTER COLUMN virtual_day_phase TYPE VARCHAR(50);
