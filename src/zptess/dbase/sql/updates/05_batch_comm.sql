-- Global section
BEGIN TRANSACTION;

------------------------------
-- Database version upgrade --
------------------------------

UPDATE config_t SET value = '05' WHERE section = 'database' AND property = 'version';

-----------------------------------
-- Schema change for batch table --
-----------------------------------

ALTER TABLE batch_t ADD COLUMN comment TEXT;

COMMIT;