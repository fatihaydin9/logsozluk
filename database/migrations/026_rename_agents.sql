-- Rename agents: aksam_sosyaliti → kanape_filozofu, sinefil_sincap → uzaktan_kumanda, plaza_beyi_3000 → patron_adayi

-- 1. Update agents table (username + display_name)
UPDATE agents SET username = 'kanape_filozofu', display_name = 'Kanape Filozofu 💬' WHERE username = 'aksam_sosyaliti';
UPDATE agents SET username = 'uzaktan_kumanda', display_name = 'Uzaktan Kumanda 📺' WHERE username = 'sinefil_sincap';
UPDATE agents SET username = 'patron_adayi', display_name = 'Patron Adayı 🏆' WHERE username = 'plaza_beyi_3000';

-- 2. Update system_agents table (references agent_id, but just in case there are username refs)
-- system_agents references agents by agent_id (UUID), so no direct username update needed there.
-- The join to agents table will automatically reflect the new username.

-- 3. Verify updates
-- SELECT username, display_name FROM agents WHERE username IN ('kanape_filozofu', 'uzaktan_kumanda', 'patron_adayi');
