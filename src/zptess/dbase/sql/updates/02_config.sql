-- Global section
BEGIN TRANSACTION;

INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '02');

DELETE FROM config_t WHERE section = 'reference';

------------------------------
-- Calibration process section
------------------------------

INSERT INTO config_t(section, property, value) 
VALUES ('calibration', 'rounds', '5');
INSERT INTO config_t(section, property, value) 
VALUES ('calibration', 'offset', '0.0');
INSERT INTO config_t(section, property, value) 
VALUES ('calibration', 'author', '');

-------------------------------
-- Reference photometer section
-------------------------------

-- Default device identification values when using serial line

INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'model', 'TESS-W');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'name', 'stars3');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'mac', '18:FE:34:CF:E9:A3');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'firmware', '');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'zp', '20.44');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'freq_offset', '0.0');

-- Default device protocol and comm method

INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'endpoint', 'serial:/dev/ttyUSB0:9600');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-device', 'old_proto', '1');

-- Default statistics to compute

INSERT INTO config_t(section, property, value) 
VALUES ('ref-stats', 'samples', '125');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-stats', 'period', '5');
INSERT INTO config_t(section, property, value) 
VALUES ('ref-stats', 'central', 'median');

-------------------------------
--  Test photometer section
-------------------------------

-- Default device identification

INSERT INTO config_t(section, property, value) 
VALUES ('test-device', 'model', 'TESS-W');

-- Default device protocol and comm method

INSERT INTO config_t(section, property, value) 
VALUES ('test-device', 'endpoint', 'tcp:192.168.4.1:23');
INSERT INTO config_t(section, property, value) 
VALUES ('test-device', 'old_proto', '0');

-- Default statistics to compute

INSERT INTO config_t(section, property, value) 
VALUES ('test-stats', 'samples', '125');
INSERT INTO config_t(section, property, value) 
VALUES ('test-stats', 'period', '5');
INSERT INTO config_t(section, property, value) 
VALUES ('test-stats', 'central', 'median');

COMMIT;
