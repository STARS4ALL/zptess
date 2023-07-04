-- Global section
BEGIN TRANSACTION;

------------------------------
-- Database version upgrade --
------------------------------

INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '05');

-----------------------------------
-- Schema change for batch table --
-----------------------------------

ALTER TABLE batch_t ADD COLUMN comment TEXT;

COMMIT;