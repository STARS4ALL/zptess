-- Global section
BEGIN TRANSACTION;

------------------------------
-- Database version upgrade --
------------------------------

INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '03');

------------------------------------
-- Schema change for summary data --
------------------------------------

ALTER TABLE summary_t ADD COLUMN calibration TEXT;
ALTER TABLE summary_t ADD COLUMN filter TEXT;
ALTER TABLE summary_t ADD COLUMN socket TEXT;
ALTER TABLE summary_t ADD COLUMN box TEXT;
ALTER TABLE summary_t ADD COLUMN collector TEXT;
ALTER TABLE summary_t ADD COLUMN comment TEXT;

DROP VIEW summary_v;

CREATE VIEW IF NOT EXISTS summary_v 
AS SELECT
    test_t.session,
    test_t.role,
    test_t.calibration,
    test_t.model,
    test_t.name,
    test_t.mac,
    test_t.firmware,
    test_t.prev_zp,
    test_t.author,
    test_t.nrounds,
    test_t.offset,
    test_t.upd_flag,
    ROUND(test_t.zero_point, 2) AS zero_point,
    test_t.zero_point_method,
    ROUND(test_t.freq,3)        AS test_freq,
    test_t.freq_method          AS test_freq_method,
    ROUND(test_t.mag, 2)        AS test_mag,
    ROUND(ref_t.freq, 3)        AS ref_freq,
    ref_t.freq_method           AS ref_freq_method,
    ROUND(ref_t.mag, 2)         AS ref_mag,
    ROUND(ref_t.mag - test_t.mag, 2) AS mag_diff,
    ROUND(test_t.zero_point, 2) - test_t.offset as raw_zero_point,
    test_t.filter,
    test_t.socket,
    test_t.box,
    test_t.collector,
    test_t.comment

FROM summary_t AS ref_t
JOIN summary_t AS test_t USING (session)
WHERE test_t.role = 'test' AND ref_t.role = 'ref';

-- ------------------
-- Filtro por defecto
--- -----------------

UPDATE summary_t SET calibration = 'AUTO' WHERE role = 'test';

-- la excepcion es ahora mismo stars1
UPDATE summary_t SET filter = 'UV/IR-740' 
WHERE name NOT IN (SELECT * FROM (VALUES ('stars1')));

-- ----------------
-- Caja por defecto
-- ----------------

--------------------------------------------------
-- CAJA PARA LOS TESS4C
-- Aunque no apareczan en la BD lo pogo aqui para que no se pierda
-- 700 a 710 reservado para los primeros redondos.
-- 850 a 859  con caja cuadrada FS716.
--------------------------------------------------

-- Cajas antiguas chinas de plastico
UPDATE summary_t SET box  = 'Caja plastico antigua' 
WHERE CAST(substr(name, 6) AS INT) < 610
AND name NOT IN
(SELECT * FROM (VALUES ('stars532'),('stars604'),('stars605'),('stars606'),('stars607')));


-- Nueva caja FSH714
UPDATE summary_t SET box  = 'Caja FSH714' 
WHERE CAST(substr(name, 6) AS INT) >= 610
AND name NOT IN
(SELECT * FROM (VALUES ('stars532'),('stars604'),('stars605'),('stars606'),('stars607')));


-- Caja de aluminio
UPDATE summary_t SET box  = 'Caja aluminio' 
WHERE name IN
(SELECT * FROM (VALUES ('stars532'),('stars604'),('stars605'),('stars606'),('stars607')));

-- -----------------------
-- Clavija de alimentacion
-- -----------------------

-- Las excepciones estan en fotómetros que ahora mismo no estan en la BD
UPDATE summary_t SET socket  = 'USB-A' WHERE name != 'stars3';
UPDATE summary_t SET socket  = 'USB-A+serial' WHERE name = 'stars3';

-- --------
-- Colector
-- --------

-- REVISAR LA HOJA PARA VER EXCEPCIONES
UPDATE summary_t SET collector  = 'standard'
WHERE name NOT IN
(SELECT * FROM (VALUES ('stars611'),('stars612'),('stars613'),('stars614'),
  ('stars615'),('stars616'),('stars619'),('stars620'),('stars621'),('stars622'),
  ('stars623'),('stars625'),('stars626'),('stars656'),('stars660'),('stars669'),
  ('stars670'),('stars671'),('stars673'),('stars676'))
);


-- REVISAR LA HOJA PARA VER EXCEPCIONES
UPDATE summary_t SET collector  = '1mm adicional'
WHERE name IN
(SELECT * FROM (VALUES ('stars611'),('stars612'),('stars613'),('stars614'),
  ('stars615'),('stars616'),('stars619'),('stars620'),('stars621'),('stars622'),
  ('stars623'),('stars625'),('stars626'),('stars656'),('stars660'),('stars669'),
  ('stars670'),('stars671'),('stars673'),('stars676'))
);

----------------------------
-- Toques diversos a la BBDD
----------------------------

UPDATE summary_t SET author = 'Rafael Gonzalez' where author = 'Rafael_Gonzalez';

UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars23';
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars29';
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars30';
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars31';
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars87';
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars90';
UPDATE summary_t 
    SET comment = 'recalibrado, calibracion anterior manual' , socket = 'USB-A + serial'
WHERE name = 'stars58';

-- caso de stars382
UPDATE summary_t SET comment = 'reparado y recalibrado (nueva MAC)' WHERE mac = '5C:CF:7F:76:6A:33';
-- caso de stars422
UPDATE summary_t SET comment = 'reparado y recalibrado (nueva MAC)' WHERE mac = '98:F4:AB:B2:7C:3D';

-- NOTA: stars017 lo hemos tenido que renombrar porque el otro cascó
-- En realidad era stars624, para tenerlo en cuenta en la migracion
UPDATE summary_t SET comment = 'reparado y recalibrado (nueva MAC), renombrado de stars624 a stars17 porque éste se rompio' 
WHERE mac = '98:F4:AB:B2:7B:53';


-- ¿Este es el de la UCM con filtro especial?
--UPDATE summary_t SET socket = 'UK socket' WHERE name = 'stars85';

------------------------------------------------------
-- AÑADIR NUEVOS FOTOMETROS SIN CALIBRACION AUTOMATICA
------------------------------------------------------

-- stars3
INSERT INTO summary_t(model, name, mac, session, calibration, role, zero_point, mag, filter, socket, box, collector, comment)
VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3','0000-01-01T00:00:00','MANUAL','test',20.44, 20.44, 'UV/IR-740','USB-A+serial','Caja plastico antigua', 'standard', 'Fotometro de referencia. 20.44 es el ZP para que sus lecturas coincidan con un Unihedron SQM');
INSERT INTO summary_t(model,name,mac,session,calibration,role,zero_point,mag,filter,socket, box, collector, comment)
VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3','0000-01-01T00:00:00','MANUAL','ref',20.44, 20.44, 'UV/IR-740','USB-A+serial','Caja plastico antigua', 'standard', 'Fotometro de referencia. 20.44 es el ZP para que sus lecturas coincidan con un Unihedron SQM');


COMMIT;
