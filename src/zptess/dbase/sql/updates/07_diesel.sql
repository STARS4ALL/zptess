-- Global section
BEGIN TRANSACTION;

-- Add support for a possible Rust Diesel ORM

CREATE TABLE IF NOT EXISTS __diesel_schema_migrations (
       version VARCHAR(50) PRIMARY KEY NOT NULL,
       run_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-----------------------------------------------------------
-- We need to fix the fact that there is no point in having
-- NULL values in properties
-- This simplifies things in Diesel
-----------------------------------------------------------

ALTER TABLE `config_t` RENAME TO `config_old_t`;

CREATE TABLE IF NOT EXISTS config_t
(
    section        TEXT NOT NULL,  -- Configuration section
    property       TEXT NOT NULL,  -- Property name
    value          TEXT NOT NULL,  -- Property value

    PRIMARY KEY(section, property)
);

INSERT INTO config_t SELECT * FROM config_old_t;
UPDATE config_t SET value = '07' WHERE section = 'database' AND property = 'version';
COMMIT;

-- WE HAVE TO MANUALLY DROP THE TABLE AS THE PROGRAM MAINTAINS A HANDLE TO IT !!!
-- AND PANICS WITH Table is Locked Exception
-- DROP TABLE config_old_t;
