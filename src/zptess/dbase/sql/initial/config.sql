--------------------------------------------------------
-- Miscelaneous data to be inserted at database creation
--------------------------------------------------------

-- Global section

INSERT INTO config_t(section, property, value) 
VALUES ('database', 'version', '01');

-- Reference photometer section

INSERT INTO config_t(section, property, value) 
VALUES ('reference', 'model', 'TESS-W');
INSERT INTO config_t(section, property, value) 
VALUES ('reference', 'name', 'stars3');
INSERT INTO config_t(section, property, value) 
VALUES ('reference', 'mac', '18:FE:34:CF:E9:A3');
INSERT INTO config_t(section, property, value) 
VALUES ('reference', 'firmware', '');
INSERT INTO config_t(section, property, value) 
VALUES ('reference', 'zp', '20.50');
INSERT INTO config_t(section, property, value) 
VALUES ('reference', 'zp_abs', '20.44');