-- Global section
BEGIN TRANSACTION;

------------------------------
-- Database version upgrade --
------------------------------

UPDATE config_t SET value = '03' WHERE section = 'database' AND property = 'version';

------------------------------------
-- Schema change for summary data --
------------------------------------

ALTER TABLE summary_t ADD COLUMN calibration TEXT;
ALTER TABLE summary_t ADD COLUMN filter TEXT;
ALTER TABLE summary_t ADD COLUMN plug TEXT;
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
    test_t.plug,
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

-- Conectores para los TASS y TESS-P
UPDATE summary_t SET plug  = 'USB-micro' WHERE (model = 'TAS') OR (model = 'TESS-P');

--------------------------------------------------
-- CAJA PARA LOS TESS4C
-- Aunque no apareczan en la BD lo pogo aqui para que no se pierda
-- 700 a 710 reservado para los primeros redondos.
-- 850 a 859  con caja cuadrada FS716.
--------------------------------------------------

-- Cajas antiguas chinas de plastico
UPDATE summary_t SET box  = 'Caja plastico antigua' 
WHERE model = 'TESS-W' AND CAST(substr(name, 6) AS INT) < 610
AND name NOT IN
(SELECT * FROM (VALUES ('stars532'),('stars604'),('stars605'),('stars606'),('stars607')));


-- Nueva caja FSH714
UPDATE summary_t SET box  = 'Caja FSH714' 
WHERE model = 'TESS-W' AND CAST(substr(name, 6) AS INT) >= 610
AND name NOT IN
(SELECT * FROM (VALUES ('stars532'),('stars604'),('stars605'),('stars606'),('stars607')));


-- Caja de aluminio
UPDATE summary_t SET box  = 'Caja aluminio' 
WHERE model = 'TESS-W' AND name IN
(SELECT * FROM (VALUES ('stars532'),('stars604'),('stars605'),('stars606'),('stars607')));

-- -----------------------
-- Clavija de alimentacion
-- -----------------------

-- Las excepciones estan en fotómetros que ahora mismo no estan en la BD
UPDATE summary_t SET plug  = 'USB-A' WHERE model = 'TESS-W' AND name != 'stars3';
UPDATE summary_t SET plug  = 'USB-A+serial' WHERE model = 'TESS-W' AND name = 'stars3';

-- --------
-- Colector
-- --------

-- REVISAR LA HOJA PARA VER EXCEPCIONES
UPDATE summary_t SET collector  = 'standard'
WHERE model = 'TESS-W' AND name NOT IN
(SELECT * FROM (VALUES ('stars611'),('stars612'),('stars613'),('stars614'),
  ('stars615'),('stars616'),('stars619'),('stars620'),('stars621'),('stars622'),
  ('stars623'),('stars625'),('stars626'),('stars656'),('stars660'),('stars669'),
  ('stars670'),('stars671'),('stars673'),('stars676'))
);


-- REVISAR LA HOJA PARA VER EXCEPCIONES
UPDATE summary_t SET collector  = '1mm adicional'
WHERE model = 'TESS-W' AND name IN
(SELECT * FROM (VALUES ('stars611'),('stars612'),('stars613'),('stars614'),
  ('stars615'),('stars616'),('stars619'),('stars620'),('stars621'),('stars622'),
  ('stars623'),('stars625'),('stars626'),('stars656'),('stars660'),('stars669'),
  ('stars670'),('stars671'),('stars673'),('stars676'))
);

----------------------------
-- Toques diversos a la BBDD
----------------------------

UPDATE summary_t SET author = 'Rafael Gonzalez' where author = 'Rafael_Gonzalez';

-- caso de stars9
UPDATE summary_t SET comment = 'recalibrado, no se tienen datos de calibracion anterior' WHERE name = 'stars9';
-- caso de stars17. En realidad era stars624, para tenerlo en cuenta en la migracion
UPDATE summary_t SET comment = 'reparado y recalibrado (nueva MAC), renombrado de stars624 a stars17 porque éste se rompio' WHERE mac = '98:F4:AB:B2:7B:53';
-- caso de stars23
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars23';
-- caso de stars29
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars29';
-- caso de stars30
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars30';
-- caso de stars31
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars31';
-- caso de stars58
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' , plug = 'USB-A + serial' WHERE name = 'stars58';
-- caso de stars87
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars87';
-- caso de stars90
UPDATE summary_t SET comment = 'recalibrado, calibracion anterior manual' WHERE name = 'stars90';
-- caso de stars241
UPDATE summary_t SET comment = 'reparado por Cristobal y recalibrado' WHERE mac = '5C:CF:7F:76:65:4A';
-- caso de stars246
UPDATE summary_t SET comment = 'recalibrado' WHERE mac = '5C:CF:7F:76:6A:CF';
-- caso de stars292
UPDATE summary_t SET comment = 'reparado y recalibrado (nueva MAC)' WHERE mac = '5C:CF:7F:76:60:D8';
-- caso de stars293
UPDATE summary_t SET comment = 'reparado y recalibrado (nueva MAC)' WHERE mac = '5C:CF:7F:76:65:10';
-- caso de stars382
UPDATE summary_t SET comment = 'reparado y recalibrado (nueva MAC)' WHERE mac = '5C:CF:7F:76:6A:33';
-- caso de stars422
UPDATE summary_t SET comment = 'recalibrado' WHERE mac = '98:F4:AB:B2:7C:3D';




-- ¿Este es el de la UCM con filtro especial?
--UPDATE summary_t SET plug = 'UK plug' WHERE name = 'stars85';

------------------------------------------------------
-- AÑADIR NUEVOS FOTOMETROS SIN CALIBRACION AUTOMATICA
------------------------------------------------------

-- stars3

-- Found out in stars3 web page that the firmware compilation date is 'May 19 2016'
UPDATE summary_t
SET firmware = 'May 19 2016'
WHERE name = 'stars3' AND (firmware = NULL OR firmware = '');

INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, zero_point, mag, offset, filter, plug, box, collector, comment)
VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3','May 19 2016','1000422-01-01T00:00:00','MANUAL','test',20.44, 20.44, 0, 'UV/IR-740','USB-A+serial','Caja plastico antigua', 'standard', 'Fotometro de referencia. 20.44 es el ZP para que sus lecturas coincidan con un Unihedron SQM');
INSERT INTO summary_t(model,name,mac, firmware, session,calibration,role,zero_point,mag,offset,filter,plug, box, collector, comment)
VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3', 'May 19 2016','1000-01-01T00:00:00','MANUAL','ref',20.44, 20.44, 0, 'UV/IR-740','USB-A+serial','Caja plastico antigua', 'standard', 'Fotometro de referencia. 20.44 es el ZP para que sus lecturas coincidan con un Unihedron SQM');



--------------------------------------------------
-- BEGIN NEW INSERT LINES MIGRACION POR migra1 --
--------------------------------------------------
-- 'stars1'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars1',NULL,NULL,'1000-01-01T00:01:00','MANUAL','test',NULL,NULL,0.0,20.5,'BG39','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:01:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars2'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars2',NULL,NULL,'1000-01-01T00:02:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:02:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars4'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars4','18:FE:34:D3:48:CD',NULL,'1000-01-01T00:03:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:03:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars5'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars5','5C:CF:7F:82:8E:FB',NULL,'1000-01-01T00:04:00','MANUAL','test',46.402,16.33,0.0,20.44,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:04:00','MANUAL','ref',46.488,16.33,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars6'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars6','18:FE:34:D3:45:B9',NULL,'1000-01-01T00:05:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:05:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars7'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars7','5C:CF:7F:82:8D:7B',NULL,'1000-01-01T00:06:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:06:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars8'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars8','18:FE:34:D3:48:CD',NULL,'1000-01-01T00:07:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:07:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars9'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars9','18:FE:34:CF:EA:80',NULL,'1000-01-01T00:08:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:08:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars10'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars10','18:FE:34:D3:47:77',NULL,'1000-01-01T00:09:00','MANUAL','test',26.0,16.32,0.0,20.37,'UV/IR-740','USB-D',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:09:00','MANUAL','ref',44.28,16.38,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars11'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars11','18:FE:34:D3:47:7F',NULL,'1000-01-01T00:10:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:10:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars12'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars12','18:FE:34:CF:E8:84',NULL,'1000-01-01T00:11:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:11:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars13'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars13','18:FE:34:00:BA:EB',NULL,'1000-01-01T00:12:00','MANUAL','test',27.0,16.3,0.0,20.37,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:12:00','MANUAL','ref',45.053,16.85,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars14'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars14','18:FE:34:82:8E:79',NULL,'1000-01-01T00:13:00','MANUAL','test',26.0,16.36,0.0,20.3,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:13:00','MANUAL','ref',41.811,16.45,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars15'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars15','18:FE:34:8C:06:5A',NULL,'1000-01-01T00:14:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:14:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars16'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars16','18:FE:34:8B:E4:07',NULL,'1000-01-01T00:15:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:15:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars17'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars17','18:FE:34:8C:03:38',NULL,'1000-01-01T00:16:00','MANUAL','test',27.0,16.33,0.0,20.41,'UV/IR-cut Schott GG495','EU',NULL,NULL,'Esta roto',1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:16:00','MANUAL','ref',46.465,16.33,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars18'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars18','18:FE:34:D3:42:79',NULL,'1000-01-01T00:17:00','MANUAL','test',27.0,16.31,0.0,20.39,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:17:00','MANUAL','ref',45.49,16.36,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars19'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars19','18:FE:34:CF:EC:06',NULL,'1000-01-01T00:18:00','MANUAL','test',26.0,16.33,0.0,20.38,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:18:00','MANUAL','ref',42.41,16.43,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars20'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars20','18:FE:34:8C:02:09',NULL,'1000-01-01T00:19:00','MANUAL','test',25.0,16.37,0.0,20.38,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:19:00','MANUAL','ref',44.353,16.38,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars21'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars21','1A:FE:34:8C:04:A3',NULL,'1000-01-01T00:20:00','MANUAL','test',25.0,16.39,0.0,20.41,'UV/IR-740','Open wire',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:20:00','MANUAL','ref',43.839,16.4,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars22'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars22','1A:FE:34:8B:E3:50',NULL,'1000-01-01T00:21:00','MANUAL','test',10.0,17.45,0.0,20.47,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:21:00','MANUAL','ref',15.84,17.48,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars23'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars23','5C:CF:7F:0:B6:A3',NULL,'1000-01-01T00:22:00','MANUAL','test',27.0,16.29,0.0,20.41,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:22:00','MANUAL','ref',46.392,16.82,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars24'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars24','1A:FE:34:CF:E9:8A',NULL,'1000-01-01T00:23:00','MANUAL','test',25.0,16.39,0.0,20.38,'UV/IR-740','Open wire',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:23:00','MANUAL','ref',43.53,16.4,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars25'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars25','1A:FE:34:D3:43:A8',NULL,'1000-01-01T00:24:00','MANUAL','test',30.0,16.21,0.0,20.41,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:24:00','MANUAL','ref',48.529,16.77,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars26'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars26','1A:FE:34:82:8E:9E',NULL,'1000-01-01T00:25:00','MANUAL','test',10.0,17.41,0.0,20.47,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:25:00','MANUAL','ref',17.19,17.41,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars27'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars27','1A:FE:34:82:8C:88',NULL,'1000-01-01T00:26:00','MANUAL','test',10.0,17.45,0.0,20.45,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:26:00','MANUAL','ref',15.78,17.5,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars28'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars28','1A:FE:34:8B:E5:48',NULL,'1000-01-01T00:27:00','MANUAL','test',26.0,16.32,0.0,20.42,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:27:00','MANUAL','ref',46.645,16.33,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars29'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars29','1A:FE:34:82:8C:81',NULL,'1000-01-01T00:28:00','MANUAL','test',25.0,16.39,0.0,20.39,'UV/IR-740','Open wire',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:28:00','MANUAL','ref',43.883,16.39,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars30'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars30','18:FE:34:11:9E:F6',NULL,'1000-01-01T00:29:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:29:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars31'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars31','1A:FE:34:CF:EA:EE',NULL,'1000-01-01T00:30:00','MANUAL','test',25.0,16.39,0.0,20.53,'UV/IR-740','Open wire',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:30:00','MANUAL','ref',48.722,16.28,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars32'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars32','1A:FE:34:8B:BA:DA',NULL,'1000-01-01T00:31:00','MANUAL','test',26.0,16.37,0.0,20.36,'UV/IR-740','UK',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:31:00','MANUAL','ref',40.045,16.49,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars33'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars33','5C:CF:7F:82:8D:28',NULL,'1000-01-01T00:32:00','MANUAL','test',26.0,16.33,0.0,20.43,'UV/IR-740','USB-D',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:32:00','MANUAL','ref',46.33,16.34,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars34'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars34','1A:FE:34:8C:03:39',NULL,'1000-01-01T00:33:00','MANUAL','test',24.0,16.39,0.0,20.45,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:33:00','MANUAL','ref',44.477,16.38,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars35'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars35','1A:FE:34:8B:B9:FE',NULL,'1000-01-01T00:34:00','MANUAL','test',27.0,16.31,0.0,20.43,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:34:00','MANUAL','ref',47.925,16.3,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars36'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars36','18:FE:34:D3:48:79',NULL,'1000-01-01T00:35:00','MANUAL','test',26.0,16.33,0.0,20.42,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:35:00','MANUAL','ref',47.445,16.31,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars37'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars37','1A:FE:34:CF:EC:81',NULL,'1000-01-01T00:36:00','MANUAL','test',25.0,16.39,0.0,20.45,'UV/IR-740','Open wire',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:36:00','MANUAL','ref',46.495,16.33,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars38'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars38','1A:FE:34:8C:03:46',NULL,'1000-01-01T00:37:00','MANUAL','test',48.0,15.68,0.0,20.38,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:37:00','MANUAL','ref',77.143,15.78,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars39'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars39','1A:FE:34:CF:EA:E6',NULL,'1000-01-01T00:38:00','MANUAL','test',10.0,17.4,0.0,20.48,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:38:00','MANUAL','ref',17.43,17.4,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars40'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars40','1A:FE:34:8B:B9:DF',NULL,'1000-01-01T00:39:00','MANUAL','test',25.0,16.38,0.0,20.38,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:39:00','MANUAL','ref',44.735,16.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars41'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars41','1A:FE:34:8B:E3:8B',NULL,'1000-01-01T00:40:00','MANUAL','test',26.0,16.38,0.0,20.42,'UV/IR-cut Schott GG495','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:40:00','MANUAL','ref',46.541,16.33,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars42'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars42','5C:CF:7F:0:B6:7E',NULL,'1000-01-01T00:41:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740',NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:41:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars43'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars43','1A:FE:34:CF:E8:F1',NULL,'1000-01-01T00:42:00','MANUAL','test',48.0,15.68,0.0,20.4,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:42:00','MANUAL','ref',82.0,15.72,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars44'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars44','1A:FE:34:00:B9:B3',NULL,'1000-01-01T00:43:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:43:00','MANUAL','ref',NULL,16.38,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars45'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars45','1A:FE:34:D3:48:0C',NULL,'1000-01-01T00:44:00','MANUAL','test',27.0,16.31,0.0,20.43,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:44:00','MANUAL','ref',45.91,16.35,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars46'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars46','1A:FE:34:D3:49:AD',NULL,'1000-01-01T00:45:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740',NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:45:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars47'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars47','1A:FE:34:8C:05:EF',NULL,'1000-01-01T00:46:00','MANUAL','test',27.0,16.3,0.0,20.47,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:46:00','MANUAL','ref',47.66,16.3,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars48'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars48','1A:FE:34:00:B6:90',NULL,'1000-01-01T00:47:00','MANUAL','test',10.0,17.38,0.0,20.5,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:47:00','MANUAL','ref',17.87,17.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars49'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars49','1A:FE:34:00:B6:DA',NULL,'1000-01-01T00:48:00','MANUAL','test',26.0,16.33,0.0,20.38,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:48:00','MANUAL','ref',45.127,16.36,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars50'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars50','1A:FE:34:CF:EB:A2',NULL,'1000-01-01T00:49:00','MANUAL','test',27.0,16.33,0.0,20.51,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:49:00','MANUAL','ref',45.169,16.26,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars51'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars51','1A:FE:34:CF:EA:1D',NULL,'1000-01-01T00:50:00','MANUAL','test',23.0,16.45,0.0,20.42,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:50:00','MANUAL','ref',40.992,16.47,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars52'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars52','1A:FE:34:8B:E3:A9',NULL,'1000-01-01T00:51:00','MANUAL','test',26.0,16.32,0.0,20.4,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:51:00','MANUAL','ref',45.91,16.35,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars53'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars53','1A:FE:34:00:B9:3F',NULL,'1000-01-01T00:52:00','MANUAL','test',27.0,16.26,0.0,20.44,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:52:00','MANUAL','ref',47.21,16.31,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars54'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars54','1A:FE:34:8B:BA:73',NULL,'1000-01-01T00:53:00','MANUAL','test',27.0,16.33,0.0,20.34,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:53:00','MANUAL','ref',43.807,16.4,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars55'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars55','1A:FE:34:00:BA:CB',NULL,'1000-01-01T00:54:00','MANUAL','test',28.0,16.26,0.0,20.41,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:54:00','MANUAL','ref',45.91,16.35,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars56'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars56','1A:FE:34:00:B8:9C',NULL,'1000-01-01T00:55:00','MANUAL','test',9.0,17.46,0.0,20.42,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:55:00','MANUAL','ref',15.35,17.53,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars57'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars57','1A:FE:34:D3:42:85',NULL,'1000-01-01T00:56:00','MANUAL','test',9.0,17.41,0.0,20.47,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:56:00','MANUAL','ref',17.25,17.41,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars58'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars58','1A:FE:34:00:B4:F9',NULL,'1000-01-01T00:57:00','MANUAL','test',25.0,16.37,0.0,20.42,'UV/IR-740','USB-D',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:57:00','MANUAL','ref',45.053,16.85,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars59'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars59','1A:FE:34:CF:E8:55',NULL,'1000-01-01T00:58:00','MANUAL','test',10.0,17.45,0.0,20.36,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:58:00','MANUAL','ref',15.89,17.59,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars60'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars60','1A:FE:34:D3:46:1D',NULL,'1000-01-01T00:59:00','MANUAL','test',NULL,17.46,0.0,20.5,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T00:59:00','MANUAL','ref',16.57,17.45,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars61'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES(NULL,'stars61','1A:FE:34:8C:02:89',NULL,'1000-01-01T01:00:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740',NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:00:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars62'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars62','5C:CF:7F:8B:E2:A0
',NULL,'1000-01-01T01:01:00','MANUAL','test',11.0,17.37,0.0,20.52,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:01:00','MANUAL','ref',18.53,17.33,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars63'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars63','1A:FE:34:8B:E3:DA',NULL,'1000-01-01T01:02:00','MANUAL','test',9.0,17.45,0.0,20.49,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:02:00','MANUAL','ref',16.51,17.46,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars64'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars64','1A:FE:34:8B:BB:8E',NULL,'1000-01-01T01:03:00','MANUAL','test',10.0,17.4,0.0,20.46,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:03:00','MANUAL','ref',17.08,17.42,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars65'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars65','1A:FE:34:D3:49:17',NULL,'1000-01-01T01:04:00','MANUAL','test',27.0,16.3,0.0,20.47,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:04:00','MANUAL','ref',48.12,16.29,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars66'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars66','1A:FE:34:CF:E8:32',NULL,'1000-01-01T01:05:00','MANUAL','test',NULL,NULL,0.0,20.5,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:05:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars67'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars67','1A:FE:34:8C:05:AB',NULL,'1000-01-01T01:06:00','MANUAL','test',25.0,16.37,0.0,20.42,'UV/IR-740','Open wire',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:06:00','MANUAL','ref',45.325,16.36,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars68'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars68','1A:FE:34:D3:45:A3',NULL,'1000-01-01T01:07:00','MANUAL','test',27.0,16.3,0.0,20.4,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:07:00','MANUAL','ref',45.49,16.36,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars69'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars69','1A:FE:34:D3:48:10',NULL,'1000-01-01T01:08:00','MANUAL','test',10.0,17.38,0.0,20.48,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:08:00','MANUAL','ref',17.5,17.39,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars70'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars70','1A:FE:34:8B:BA:4E',NULL,'1000-01-01T01:09:00','MANUAL','test',9.0,17.45,0.0,20.46,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:09:00','MANUAL','ref',16.04,17.49,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars71'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars71','1A:FE:34:D3:45:3D',NULL,'1000-01-01T01:10:00','MANUAL','test',26.0,16.34,0.0,20.44,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:10:00','MANUAL','ref',47.578,16.31,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars72'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars72','1A:FE:34:8C:06:C0',NULL,'1000-01-01T01:11:00','MANUAL','test',26.0,16.34,0.0,20.42,'UV/IR-740','USB-A',NULL,'Sí  **',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:11:00','MANUAL','ref',46.304,16.34,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars73'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars73','1A:FE:34:D3:47:17',NULL,'1000-01-01T01:12:00','MANUAL','test',27.0,16.32,0.0,20.4,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:12:00','MANUAL','ref',46.33,16.34,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars74'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars74','1A:FE:34:00:B9:B8',NULL,'1000-01-01T01:13:00','MANUAL','test',26.0,16.34,0.0,20.4,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:13:00','MANUAL','ref',45.066,16.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars75'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars75','1A:FE:34:82:8D:8B',NULL,'1000-01-01T01:14:00','MANUAL','test',27.0,16.33,0.0,20.36,'UV/IR-cut Schott GG495','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:14:00','MANUAL','ref',43.89,16.39,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars76'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars76','1A:FE:34:CF:ED:70',NULL,'1000-01-01T01:15:00','MANUAL','test',28.0,16.28,0.0,20.47,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:15:00','MANUAL','ref',50.0,16.25,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars77'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars77','1A:FE:34:D3:47:3D',NULL,'1000-01-01T01:16:00','MANUAL','test',27.0,16.31,0.0,20.42,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:16:00','MANUAL','ref',47.069,16.32,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars78'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars78','1A:FE:34:00:B6:F5',NULL,'1000-01-01T01:17:00','MANUAL','test',10.0,17.41,0.0,20.52,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:17:00','MANUAL','ref',18.06,17.36,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars79'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars79','1A:FE:34:8B:E3:22',NULL,'1000-01-01T01:18:00','MANUAL','test',25.0,16.37,0.0,20.43,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:18:00','MANUAL','ref',46.303,16.34,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars80'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars80','1A:FE:34:CF:E8:DC',NULL,'1000-01-01T01:19:00','MANUAL','test',28.0,16.28,0.0,20.35,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:19:00','MANUAL','ref',44.68,16.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars81'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars81','1A:FE:34:8B:BA:63',NULL,'1000-01-01T01:20:00','MANUAL','test',25.0,16.37,0.0,20.42,'UV/IR-740','Open wire',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:20:00','MANUAL','ref',45.151,16.36,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars82'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars82','1A:FE:34:00:B7:08',NULL,'1000-01-01T01:21:00','MANUAL','test',25.0,16.37,0.0,20.38,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:21:00','MANUAL','ref',44.133,16.39,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars83'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars83','1A:FE:34:8C:06:CC',NULL,'1000-01-01T01:22:00','MANUAL','test',27.0,16.28,0.0,20.42,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:22:00','MANUAL','ref',48.0,16.3,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars84'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars84','1A:FE:34:00:B9:C2',NULL,'1000-01-01T01:23:00','MANUAL','test',28.0,16.26,0.0,20.39,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:23:00','MANUAL','ref',47.388,16.8,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars85'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars85','1A:FE:34:CF:EC:0B',NULL,'1000-01-01T01:24:00','MANUAL','test',46.774,16.33,0.0,20.33,'UV/IR-cut Schott GG495','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:24:00','MANUAL','ref',42.059,16.44,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars86'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars86','1A:FE:34:00:B6:44',NULL,'1000-01-01T01:25:00','MANUAL','test',11.0,17.38,0.0,20.48,'UV/IR-740','UK',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:25:00','MANUAL','ref',17.87,17.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars87'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars87','1A:FE:34:D3:49:8E',NULL,'1000-01-01T01:26:00','MANUAL','test',26.0,16.32,0.0,20.42,'UV/IR-740','UK',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:26:00','MANUAL','ref',47.379,16.31,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars88'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars88','1A:FE:34:D3:49:10',NULL,'1000-01-01T01:27:00','MANUAL','test',27.0,16.31,0.0,20.43,'UV/IR-740','USB-A',NULL,'Sí ',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:27:00','MANUAL','ref',48.064,16.3,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars89'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars89','1A:FE:34:00:BA:6F',NULL,'1000-01-01T01:28:00','MANUAL','test',30.0,16.21,0.0,20.43,'UV/IR-740','Open wire',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:28:00','MANUAL','ref',49.72,16.75,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars90'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars90','18:FE:34:D3:45:0',NULL,'1000-01-01T01:29:00','MANUAL','test',25.0,16.37,0.0,20.41,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:29:00','MANUAL','ref',44.957,16.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars91'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars91','1A:FE:34:CF:E8:9B',NULL,'1000-01-01T01:30:00','MANUAL','test',24.0,16.39,0.0,20.33,'UV/IR-740','EU',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:30:00','MANUAL','ref',39.681,16.5,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars92'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars92','1A:FE:34:CF:EC:8D',NULL,'1000-01-01T01:31:00','MANUAL','test',26.0,16.33,0.0,20.34,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:31:00','MANUAL','ref',43.738,16.4,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars100'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars100',NULL,NULL,'1000-01-01T01:32:00','MANUAL','test',NULL,NULL,0.0,NULL,NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:32:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars101'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars101',NULL,NULL,'1000-01-01T01:33:00','MANUAL','test',NULL,NULL,0.0,NULL,NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:33:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars201'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars201',NULL,NULL,'1000-01-01T01:34:00','MANUAL','test',NULL,16.35,0.0,20.55,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:34:00','MANUAL','ref',NULL,16.24,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars202'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars202',NULL,NULL,'1000-01-01T01:35:00','MANUAL','test',NULL,16.32,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:35:00','MANUAL','ref',NULL,16.31,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars203'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars203',NULL,NULL,'1000-01-01T01:36:00','MANUAL','test',45.1,16.36,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:36:00','MANUAL','ref',46.33,16.34,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars204'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars204',NULL,NULL,'1000-01-01T01:37:00','MANUAL','test',45.479,16.36,0.0,20.59,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:37:00','MANUAL','ref',52.0,16.21,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars205'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars205',NULL,NULL,'1000-01-01T01:38:00','MANUAL','test',45.427,16.36,0.0,20.42,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:38:00','MANUAL','ref',44.28,16.38,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars206'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars206',NULL,NULL,'1000-01-01T01:39:00','MANUAL','test',45.462,16.36,0.0,20.5,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:39:00','MANUAL','ref',47.66,16.3,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars207'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars207',NULL,NULL,'1000-01-01T01:40:00','MANUAL','test',45.496,16.36,0.0,20.51,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:40:00','MANUAL','ref',48.12,16.29,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars208'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars208',NULL,NULL,'1000-01-01T01:41:00','MANUAL','test',51.5,16.22,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:41:00','MANUAL','ref',52.0,16.21,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars209'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars209',NULL,NULL,'1000-01-01T01:42:00','MANUAL','test',26.129,16.96,0.0,20.43,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:42:00','MANUAL','ref',25.779,16.97,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars210'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars210',NULL,NULL,'1000-01-01T01:43:00','MANUAL','test',45.494,16.36,0.0,20.52,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:43:00','MANUAL','ref',48.58,16.28,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars211'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars211',NULL,NULL,'1000-01-01T01:44:00','MANUAL','test',45.62,16.35,0.0,20.42,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:44:00','MANUAL','ref',45.08,16.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars212'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars212',NULL,NULL,'1000-01-01T01:45:00','MANUAL','test',45.515,16.35,0.0,20.54,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:45:00','MANUAL','ref',50.0,16.25,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars213'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars213',NULL,NULL,'1000-01-01T01:46:00','MANUAL','test',47.418,16.31,0.0,20.5,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:46:00','MANUAL','ref',50.0,16.25,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars214'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars214',NULL,NULL,'1000-01-01T01:47:00','MANUAL','test',47.129,16.32,0.0,20.5,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:47:00','MANUAL','ref',49.54,16.26,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars215'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars215',NULL,NULL,'1000-01-01T01:48:00','MANUAL','test',46.971,16.32,0.0,20.48,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:48:00','MANUAL','ref',48.58,16.28,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars216'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars216',NULL,NULL,'1000-01-01T01:49:00','MANUAL','test',47.19,16.32,0.0,20.39,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:49:00','MANUAL','ref',44.68,16.37,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars217'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars217',NULL,NULL,'1000-01-01T01:50:00','MANUAL','test',47.229,16.31,0.0,20.31,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:50:00','MANUAL','ref',42.05,16.44,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars218'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars218',NULL,NULL,'1000-01-01T01:51:00','MANUAL','test',47.297,16.31,0.0,20.26,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:51:00','MANUAL','ref',40.03,16.49,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars219'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars219',NULL,NULL,'1000-01-01T01:52:00','MANUAL','test',47.912,16.3,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:52:00','MANUAL','ref',49.06,16.27,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars220'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars220',NULL,NULL,'1000-01-01T01:53:00','MANUAL','test',47.886,16.3,0.0,20.38,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:53:00','MANUAL','ref',45.41,16.36,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars221'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars221',NULL,NULL,'1000-01-01T01:54:00','MANUAL','test',47.678,16.3,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:54:00','MANUAL','ref',48.58,16.28,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars222'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars222',NULL,NULL,'1000-01-01T01:55:00','MANUAL','test',47.766,16.3,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:55:00','MANUAL','ref',49.06,16.27,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars223'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars223',NULL,NULL,'1000-01-01T01:56:00','MANUAL','test',47.678,16.3,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:56:00','MANUAL','ref',48.58,16.28,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars224'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars224',NULL,NULL,'1000-01-01T01:57:00','MANUAL','test',51.0,16.23,0.0,20.54,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:57:00','MANUAL','ref',56.0,16.13,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars225'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars225',NULL,NULL,'1000-01-01T01:58:00','MANUAL','test',26.0,16.34,0.0,20.48,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:58:00','MANUAL','ref',47.66,16.3,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars226'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars226',NULL,NULL,'1000-01-01T01:59:00','MANUAL','test',26.0,16.34,0.0,20.62,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T01:59:00','MANUAL','ref',53.143,16.19,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars227'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars227',NULL,NULL,'1000-01-01T02:00:00','MANUAL','test',26.0,16.34,0.0,20.53,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:00:00','MANUAL','ref',49.52,16.26,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars228'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars228',NULL,NULL,'1000-01-01T02:01:00','MANUAL','test',26.0,16.34,0.0,20.56,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:01:00','MANUAL','ref',50.857,16.23,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars229'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars229',NULL,NULL,'1000-01-01T02:02:00','MANUAL','test',26.0,16.34,0.0,20.57,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:02:00','MANUAL','ref',50.0,16.25,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars230'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars230',NULL,NULL,'1000-01-01T02:03:00','MANUAL','test',26.0,16.34,0.0,20.53,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:03:00','MANUAL','ref',49.632,16.26,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars231'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars231',NULL,NULL,'1000-01-01T02:04:00','MANUAL','test',27.0,16.32,0.0,20.54,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:04:00','MANUAL','ref',50.0,16.25,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars232'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars232',NULL,NULL,'1000-01-01T02:05:00','MANUAL','test',26.0,16.31,0.0,20.51,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:05:00','MANUAL','ref',49.754,16.26,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars233'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars233',NULL,NULL,'1000-01-01T02:06:00','MANUAL','test',27.0,16.31,0.0,20.56,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:06:00','MANUAL','ref',53.0,16.19,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars234'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars234',NULL,NULL,'1000-01-01T02:07:00','MANUAL','test',27.0,16.31,0.0,20.58,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:07:00','MANUAL','ref',52.0,16.21,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars235'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars235',NULL,NULL,'1000-01-01T02:08:00','MANUAL','test',27.0,16.31,0.0,20.56,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:08:00','MANUAL','ref',53.0,16.19,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars236'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars236',NULL,NULL,'1000-01-01T02:09:00','MANUAL','test',27.0,16.32,0.0,20.54,'UV/IR-cut GG495','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:09:00','MANUAL','ref',50.286,16.25,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars237'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars237',NULL,NULL,'1000-01-01T02:10:00','MANUAL','test',26.0,16.32,0.0,20.6,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:10:00','MANUAL','ref',53.143,16.19,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars238'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars238',NULL,NULL,'1000-01-01T02:11:00','MANUAL','test',27.0,16.31,0.0,20.58,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:11:00','MANUAL','ref',52.0,16.21,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars239'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars239',NULL,NULL,'1000-01-01T02:12:00','MANUAL','test',27.0,16.32,0.0,20.53,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:12:00','MANUAL','ref',49.704,16.26,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars240'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars240',NULL,NULL,'1000-01-01T02:13:00','MANUAL','test',26.0,16.32,0.0,20.62,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:13:00','MANUAL','ref',54.0,16.17,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars241'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars241',NULL,NULL,'1000-01-01T02:14:00','MANUAL','test',26.261,16.95,0.0,20.44,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:14:00','MANUAL','ref',26.226,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars242'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars242',NULL,NULL,'1000-01-01T02:15:00','MANUAL','test',51.6,16.22,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:15:00','MANUAL','ref',52.0,16.21,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars243'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars243',NULL,NULL,'1000-01-01T02:16:00','MANUAL','test',51.0,16.23,0.0,20.54,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:16:00','MANUAL','ref',56.0,16.13,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars244'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars244',NULL,NULL,'1000-01-01T02:17:00','MANUAL','test',52.4,16.2,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:17:00','MANUAL','ref',54.0,16.17,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars245'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars245',NULL,NULL,'1000-01-01T02:18:00','MANUAL','test',NULL,NULL,0.0,NULL,NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:18:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars246'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars246',NULL,NULL,'1000-01-01T02:19:00','MANUAL','test',26.462,16.95,0.0,20.48,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:19:00','MANUAL','ref',27.395,16.91,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars247'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars247',NULL,NULL,'1000-01-01T02:20:00','MANUAL','test',51.571,16.22,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:20:00','MANUAL','ref',52.0,16.21,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars248'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars248',NULL,NULL,'1000-01-01T02:21:00','MANUAL','test',51.0,16.23,0.0,20.54,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:21:00','MANUAL','ref',56.0,16.13,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars249'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars249',NULL,NULL,'1000-01-01T02:22:00','MANUAL','test',51.0,16.23,0.0,20.54,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:22:00','MANUAL','ref',56.0,16.13,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars250'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars250',NULL,NULL,'1000-01-01T02:23:00','MANUAL','test',26.707,16.93,0.0,20.48,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:23:00','MANUAL','ref',27.762,16.89,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars251'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars251',NULL,NULL,'1000-01-01T02:24:00','MANUAL','test',26.507,16.94,0.0,20.48,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:24:00','MANUAL','ref',27.757,16.9,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars252'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars252',NULL,NULL,'1000-01-01T02:25:00','MANUAL','test',25.837,16.97,0.0,20.43,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:25:00','MANUAL','ref',25.503,16.98,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars253'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars253',NULL,NULL,'1000-01-01T02:26:00','MANUAL','test',26.604,16.94,0.0,20.48,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:26:00','MANUAL','ref',26.661,16.94,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars254'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars254',NULL,NULL,'1000-01-01T02:27:00','MANUAL','test',26.43,16.94,0.0,20.43,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:27:00','MANUAL','ref',26.436,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars255'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars255',NULL,NULL,'1000-01-01T02:28:00','MANUAL','test',NULL,NULL,0.0,NULL,NULL,'USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:28:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars256'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars256',NULL,NULL,'1000-01-01T02:29:00','MANUAL','test',26.299,16.95,0.0,20.44,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:29:00','MANUAL','ref',26.186,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars257'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars257',NULL,NULL,'1000-01-01T02:30:00','MANUAL','test',26.509,16.94,0.0,20.29,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:30:00','MANUAL','ref',23.126,17.09,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars258'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars258',NULL,NULL,'1000-01-01T02:31:00','MANUAL','test',NULL,NULL,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:31:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars259'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars259',NULL,NULL,'1000-01-01T02:32:00','MANUAL','test',NULL,NULL,0.0,20.48,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:32:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars260'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars260',NULL,NULL,'1000-01-01T02:33:00','MANUAL','test',26.605,16.94,0.0,20.44,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:33:00','MANUAL','ref',26.663,16.94,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars261'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars261',NULL,NULL,'1000-01-01T02:34:00','MANUAL','test',26.99,16.92,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:34:00','MANUAL','ref',27.382,16.91,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars262'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars262',NULL,NULL,'1000-01-01T02:35:00','MANUAL','test',26.567,16.94,0.0,20.43,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:35:00','MANUAL','ref',26.206,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars263'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars263',NULL,NULL,'1000-01-01T02:36:00','MANUAL','test',27.13,16.92,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:36:00','MANUAL','ref',27.672,16.89,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars264'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars264',NULL,NULL,'1000-01-01T02:37:00','MANUAL','test',26.542,16.94,0.0,20.49,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:37:00','MANUAL','ref',27.725,16.89,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars265'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars265',NULL,NULL,'1000-01-01T02:38:00','MANUAL','test',26.623,16.94,0.0,20.44,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:38:00','MANUAL','ref',26.589,16.94,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars266'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars266',NULL,NULL,'1000-01-01T02:39:00','MANUAL','test',27.099,16.92,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:39:00','MANUAL','ref',27.334,16.91,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars267'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars267',NULL,NULL,'1000-01-01T02:40:00','MANUAL','test',26.571,16.94,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:40:00','MANUAL','ref',27.203,16.91,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars268'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars268',NULL,NULL,'1000-01-01T02:41:00','MANUAL','test',27.473,16.9,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:41:00','MANUAL','ref',27.999,16.88,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars269'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars269',NULL,NULL,'1000-01-01T02:42:00','MANUAL','test',NULL,NULL,0.0,NULL,NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:42:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars270'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars270',NULL,NULL,'1000-01-01T02:43:00','MANUAL','test',26.127,16.96,0.0,20.51,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:43:00','MANUAL','ref',27.841,16.89,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars271'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars271',NULL,NULL,'1000-01-01T02:44:00','MANUAL','test',26.68,16.93,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:44:00','MANUAL','ref',27.241,16.91,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars272'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars272',NULL,NULL,'1000-01-01T02:45:00','MANUAL','test',26.139,16.96,0.0,20.49,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:45:00','MANUAL','ref',27.303,16.91,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars273'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars273',NULL,NULL,'1000-01-01T02:46:00','MANUAL','test',25.456,16.99,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:46:00','MANUAL','ref',25.51,16.98,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars274'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars274',NULL,NULL,'1000-01-01T02:47:00','MANUAL','test',25.906,16.97,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:47:00','MANUAL','ref',26.361,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars275'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars275',NULL,NULL,'1000-01-01T02:48:00','MANUAL','test',25.458,16.99,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:48:00','MANUAL','ref',25.576,16.98,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars276'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars276',NULL,NULL,'1000-01-01T02:49:00','MANUAL','test',25.69,16.98,0.0,20.44,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:49:00','MANUAL','ref',25.691,16.98,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars277'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars277',NULL,NULL,'1000-01-01T02:50:00','MANUAL','test',26.351,16.95,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:50:00','MANUAL','ref',27.087,16.92,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars278'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars278',NULL,NULL,'1000-01-01T02:51:00','MANUAL','test',26.356,16.95,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:51:00','MANUAL','ref',26.935,16.92,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars279'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars279',NULL,NULL,'1000-01-01T02:52:00','MANUAL','test',26.584,16.94,0.0,20.42,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:52:00','MANUAL','ref',26.128,16.96,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars280'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars280',NULL,NULL,'1000-01-01T02:53:00','MANUAL','test',24.481,17.03,0.0,20.39,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:53:00','MANUAL','ref',23.31,17.08,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars281'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars281',NULL,NULL,'1000-01-01T02:54:00','MANUAL','test',26.466,16.94,0.0,20.41,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:54:00','MANUAL','ref',25.736,16.97,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars282'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars282',NULL,NULL,'1000-01-01T02:55:00','MANUAL','test',25.222,17.0,0.0,20.36,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:55:00','MANUAL','ref',23.265,17.08,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars283'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars283',NULL,NULL,'1000-01-01T02:56:00','MANUAL','test',26.543,16.94,0.0,20.38,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:56:00','MANUAL','ref',25.077,17.0,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars284'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars284',NULL,NULL,'1000-01-01T02:57:00','MANUAL','test',24.86,17.01,0.0,20.4,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:57:00','MANUAL','ref',24.096,17.05,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars285'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars285',NULL,NULL,'1000-01-01T02:58:00','MANUAL','test',26.61,16.94,0.0,20.41,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:58:00','MANUAL','ref',25.725,16.97,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars286'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars286',NULL,NULL,'1000-01-01T02:59:00','MANUAL','test',NULL,NULL,0.0,20.41,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T02:59:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars287'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars287',NULL,NULL,'1000-01-01T03:00:00','MANUAL','test',26.584,16.94,0.0,20.43,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:00:00','MANUAL','ref',26.24,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars288'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars288',NULL,NULL,'1000-01-01T03:01:00','MANUAL','test',27.093,16.92,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:01:00','MANUAL','ref',27.866,16.89,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars289'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars289',NULL,NULL,'1000-01-01T03:02:00','MANUAL','test',26.639,16.94,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:02:00','MANUAL','ref',26.878,16.93,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars290'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars290',NULL,NULL,'1000-01-01T03:03:00','MANUAL','test',26.895,16.93,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:03:00','MANUAL','ref',27.161,16.92,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars291'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars291',NULL,NULL,'1000-01-01T03:04:00','MANUAL','test',27.094,16.92,0.0,20.55,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:04:00','MANUAL','ref',29.805,16.81,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars292'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars292',NULL,NULL,'1000-01-01T03:05:00','MANUAL','test',27.603,16.9,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:05:00','MANUAL','ref',28.07,16.88,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars293'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars293',NULL,NULL,'1000-01-01T03:06:00','MANUAL','test',27.035,16.92,0.0,20.49,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:06:00','MANUAL','ref',28.336,16.87,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars294'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars294',NULL,NULL,'1000-01-01T03:07:00','MANUAL','test',26.683,16.93,0.0,20.42,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:07:00','MANUAL','ref',26.336,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars295'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars295',NULL,NULL,'1000-01-01T03:08:00','MANUAL','test',27.588,16.9,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:08:00','MANUAL','ref',28.214,16.87,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars296'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars296',NULL,NULL,'1000-01-01T03:09:00','MANUAL','test',27.05,16.92,0.0,20.45,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:09:00','MANUAL','ref',27.332,16.91,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars297'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars297','5C:CF:7F:76:65:94',NULL,'1000-01-01T03:10:00','MANUAL','test',27.006,16.92,0.0,20.46,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:10:00','MANUAL','ref',27.479,16.9,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars298'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars298',NULL,NULL,'1000-01-01T03:11:00','MANUAL','test',26.991,16.92,0.0,20.41,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:11:00','MANUAL','ref',26.23,16.95,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars299'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars299',NULL,NULL,'1000-01-01T03:12:00','MANUAL','test',27.006,16.92,0.0,20.47,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:12:00','MANUAL','ref',27.709,16.89,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars300'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars300',NULL,NULL,'1000-01-01T03:13:00','MANUAL','test',27.034,16.92,0.0,20.53,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:13:00','MANUAL','ref',29.248,16.83,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars301'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars301',NULL,NULL,'1000-01-01T03:14:00','MANUAL','test',25.4,16.99,0.0,20.3,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:14:00','MANUAL','ref',22.2,17.13,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars302'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars302',NULL,NULL,'1000-01-01T03:15:00','MANUAL','test',25.4,16.99,0.0,20.34,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:15:00','MANUAL','ref',23.3,17.09,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars303'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars303',NULL,NULL,'1000-01-01T03:16:00','MANUAL','test',25.1,17.0,0.0,20.33,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:16:00','MANUAL','ref',22.9,17.11,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars304'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars304',NULL,NULL,'1000-01-01T03:17:00','MANUAL','test',24.8,17.01,0.0,20.41,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:17:00','MANUAL','ref',24.2,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars305'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars305',NULL,NULL,'1000-01-01T03:18:00','MANUAL','test',24.8,17.01,0.0,20.28,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:18:00','MANUAL','ref',21.5,17.17,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars306'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars306',NULL,NULL,'1000-01-01T03:19:00','MANUAL','test',25.2,17.0,0.0,20.33,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:19:00','MANUAL','ref',22.7,17.11,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars307'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars307',NULL,NULL,'1000-01-01T03:20:00','MANUAL','test',25.2,17.0,0.0,20.37,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:20:00','MANUAL','ref',23.8,17.07,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars308'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars308',NULL,NULL,'1000-01-01T03:21:00','MANUAL','test',24.8,17.01,0.0,20.35,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:21:00','MANUAL','ref',23.3,17.1,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars309'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars309',NULL,NULL,'1000-01-01T03:22:00','MANUAL','test',25.1,17.0,0.0,20.32,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:22:00','MANUAL','ref',22.6,17.12,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars310'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars310',NULL,NULL,'1000-01-01T03:23:00','MANUAL','test',24.7,17.01,0.0,20.31,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:23:00','MANUAL','ref',22.4,17.14,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars311'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars311',NULL,NULL,'1000-01-01T03:24:00','MANUAL','test',25.793,16.97,0.0,20.32,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:24:00','MANUAL','ref',23.849,17.09,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars312'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars312',NULL,NULL,'1000-01-01T03:25:00','MANUAL','test',25.401,16.99,0.0,20.31,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:25:00','MANUAL','ref',22.642,17.12,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars313'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars313',NULL,NULL,'1000-01-01T03:26:00','MANUAL','test',25.661,16.97,0.0,20.29,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:26:00','MANUAL','ref',22.439,17.12,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars314'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars314',NULL,NULL,'1000-01-01T03:27:00','MANUAL','test',25.661,16.98,0.0,20.35,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:27:00','MANUAL','ref',23.603,17.07,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars315'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars315',NULL,NULL,'1000-01-01T03:28:00','MANUAL','test',25.661,16.98,0.0,20.35,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:28:00','MANUAL','ref',23.492,17.07,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars316'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars316','CC:50:E3:2E:57:AE',NULL,'1000-01-01T03:29:00','MANUAL','test',25.793,NULL,0.0,20.32,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:29:00','MANUAL','ref',23.166,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars317'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars317','CC:50:E3:16:7A:9B',NULL,'1000-01-01T03:30:00','MANUAL','test',25.661,NULL,0.0,20.31,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:30:00','MANUAL','ref',22.745,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars318'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars318','CC:50:E3:16:85:9F',NULL,'1000-01-01T03:31:00','MANUAL','test',25.793,NULL,0.0,20.33,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:31:00','MANUAL','ref',23.274,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars319'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars319','CC:50:E3:16:7B:6D',NULL,'1000-01-01T03:32:00','MANUAL','test',25.793,NULL,0.0,20.3,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:32:00','MANUAL','ref',22.745,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars320'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars320','CC:50:E3:16:80:00',NULL,'1000-01-01T03:33:00','MANUAL','test',25.793,NULL,0.0,20.33,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:33:00','MANUAL','ref',23.383,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars321'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars321','CC:50:E3:16:7F:B7',NULL,'1000-01-01T03:34:00','MANUAL','test',25.793,NULL,0.0,20.25,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:34:00','MANUAL','ref',21.662,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars322'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars322','CC:50:E3:16:4D:F3',NULL,'1000-01-01T03:35:00','MANUAL','test',25.793,NULL,0.0,20.34,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:35:00','MANUAL','ref',23.492,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars323'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars323','CC:50:E3:16:8A:31',NULL,'1000-01-01T03:36:00','MANUAL','test',25.793,NULL,0.0,20.39,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:36:00','MANUAL','ref',24.529,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars324'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars324','CC:50:E3:16:88:EB',NULL,'1000-01-01T03:37:00','MANUAL','test',25.793,NULL,0.0,20.37,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:37:00','MANUAL','ref',24.173,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars325'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars325','CC:50:E3:2E:4E:21',NULL,'1000-01-01T03:38:00','MANUAL','test',25.793,NULL,0.0,20.32,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:38:00','MANUAL','ref',23.166,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars326'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars326','CC:50:E3:16:80:34',NULL,'1000-01-01T03:39:00','MANUAL','test',25.793,NULL,0.0,20.31,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:39:00','MANUAL','ref',22.954,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars327'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars327','CC:50:E3:2E:4F:D9',NULL,'1000-01-01T03:40:00','MANUAL','test',25.793,NULL,0.0,20.31,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:40:00','MANUAL','ref',22.849,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars328'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars328','CC:50:E3:16:81:84',NULL,'1000-01-01T03:41:00','MANUAL','test',25.793,NULL,0.0,20.32,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:41:00','MANUAL','ref',23.166,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars329'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars329','CC:50:E3:16:80:AB',NULL,'1000-01-01T03:42:00','MANUAL','test',25.793,NULL,0.0,20.36,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:42:00','MANUAL','ref',24.057,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars330'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars330','CC:50:E3:16:86:4A',NULL,'1000-01-01T03:43:00','MANUAL','test',25.793,NULL,0.0,20.32,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:43:00','MANUAL','ref',23.166,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars331'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars331','CC:50:E3:2E:4D:91',NULL,'1000-01-01T03:44:00','MANUAL','test',25.793,16.97,0.0,20.37,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:44:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars332'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars332','CC:50:E3:16:88:DE',NULL,'1000-01-01T03:45:00','MANUAL','test',25.793,16.97,0.0,20.37,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:45:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars333'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars333',NULL,NULL,'1000-01-01T03:46:00','MANUAL','test',24.291,16.97,0.0,20.37,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:46:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars334'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars334',NULL,NULL,'1000-01-01T03:47:00','MANUAL','test',25.793,16.97,0.0,20.3,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:47:00','MANUAL','ref',NULL,17.11,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars335'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars335',NULL,NULL,'1000-01-01T03:48:00','MANUAL','test',25.793,16.97,0.0,20.36,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:48:00','MANUAL','ref',NULL,17.05,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars336'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars336',NULL,NULL,'1000-01-01T03:49:00','MANUAL','test',25.793,16.97,0.0,20.37,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:49:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars337'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars337',NULL,NULL,'1000-01-01T03:50:00','MANUAL','test',25.793,16.96,0.0,20.32,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:50:00','MANUAL','ref',NULL,17.08,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars338'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars338',NULL,NULL,'1000-01-01T03:51:00','MANUAL','test',25.793,16.96,0.0,20.36,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:51:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars339'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars339',NULL,NULL,'1000-01-01T03:52:00','MANUAL','test',25.793,16.96,0.0,20.4,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:52:00','MANUAL','ref',NULL,17.0,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars340'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars340',NULL,NULL,'1000-01-01T03:53:00','MANUAL','test',25.793,16.96,0.0,20.36,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:53:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars341'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars341',NULL,NULL,'1000-01-01T03:54:00','MANUAL','test',NULL,16.96,0.0,20.37,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:54:00','MANUAL','ref',NULL,17.03,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars342'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars342',NULL,NULL,'1000-01-01T03:55:00','MANUAL','test',NULL,16.96,0.0,20.3,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:55:00','MANUAL','ref',NULL,17.1,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars343'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars343',NULL,NULL,'1000-01-01T03:56:00','MANUAL','test',NULL,16.98,0.0,20.31,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:56:00','MANUAL','ref',NULL,17.11,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars344'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars344',NULL,NULL,'1000-01-01T03:57:00','MANUAL','test',NULL,16.96,0.0,20.37,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:57:00','MANUAL','ref',NULL,17.03,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars345'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars345',NULL,NULL,'1000-01-01T03:58:00','MANUAL','test',NULL,16.96,0.0,20.36,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:58:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars346'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars346',NULL,NULL,'1000-01-01T03:59:00','MANUAL','test',NULL,16.96,0.0,20.35,'UV/IR-740','USB-A',NULL,'Si',NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T03:59:00','MANUAL','ref',NULL,17.05,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars348'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars348',NULL,NULL,'1000-01-01T04:00:00','MANUAL','test',NULL,16.98,0.0,20.39,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:00:00','MANUAL','ref',NULL,17.03,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars349'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars349',NULL,NULL,'1000-01-01T04:01:00','MANUAL','test',NULL,16.97,0.0,20.3,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:01:00','MANUAL','ref',NULL,17.11,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars350'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars350',NULL,NULL,'1000-01-01T04:02:00','MANUAL','test',NULL,16.98,0.0,20.38,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:02:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars351'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars351',NULL,NULL,'1000-01-01T04:03:00','MANUAL','test',NULL,16.98,0.0,20.35,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:03:00','MANUAL','ref',NULL,17.07,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars352'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars352',NULL,NULL,'1000-01-01T04:04:00','MANUAL','test',NULL,16.98,0.0,20.34,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:04:00','MANUAL','ref',NULL,17.08,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars353'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars353',NULL,NULL,'1000-01-01T04:05:00','MANUAL','test',NULL,16.96,0.0,20.4,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:05:00','MANUAL','ref',NULL,17.0,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars354'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars354',NULL,NULL,'1000-01-01T04:06:00','MANUAL','test',NULL,16.96,0.0,20.36,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:06:00','MANUAL','ref',NULL,17.04,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars355'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars355',NULL,NULL,'1000-01-01T04:07:00','MANUAL','test',NULL,16.96,0.0,20.33,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:07:00','MANUAL','ref',NULL,17.07,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars356'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars356',NULL,NULL,'1000-01-01T04:08:00','MANUAL','test',NULL,16.96,0.0,20.29,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:08:00','MANUAL','ref',NULL,17.11,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars357'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars357',NULL,NULL,'1000-01-01T04:09:00','MANUAL','test',NULL,16.96,0.0,20.33,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:09:00','MANUAL','ref',NULL,17.07,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars358'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars358',NULL,NULL,'1000-01-01T04:10:00','MANUAL','test',NULL,16.96,0.0,20.33,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:10:00','MANUAL','ref',NULL,17.07,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars359'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars359',NULL,NULL,'1000-01-01T04:11:00','MANUAL','test',NULL,16.96,0.0,20.29,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:11:00','MANUAL','ref',NULL,17.11,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars360'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars360',NULL,NULL,'1000-01-01T04:12:00','MANUAL','test',NULL,16.96,0.0,20.34,'UV/IR-740','USB-A',NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:12:00','MANUAL','ref',NULL,17.06,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars712'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars712','24:A1:60:2F:98:B3',NULL,'1000-01-01T04:13:00','MANUAL','test',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:13:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars737'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars737','E8:DB:84:82:69:F4',NULL,'1000-01-01T04:14:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740','USB-A','Caja plastico 
model FSH-714',NULL,'Calibrado por Cristobal',1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:14:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars784'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars784','E8:DB:84:83:93:85',NULL,'1000-01-01T04:15:00','MANUAL','test',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:15:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars794'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars794','E8:DB:84:83:06:4F',NULL,'1000-01-01T04:16:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740','USB-A','Caja plastico 
model FSH-714',NULL,'calibrado por Cristobal',1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:16:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars795'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars795','E8:DB:84:83:7C:98',NULL,'1000-01-01T04:17:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740','USB-A','Caja plastico 
model FSH-714',NULL,'calibrado por Cristobal',1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:17:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars796'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars796','E8:DB:84:82:32:C1',NULL,'1000-01-01T04:18:00','MANUAL','test',NULL,NULL,0.0,NULL,'UV/IR-740','USB-A','Caja plastico 
model FSH-714',NULL,'calibrado por Cristobal',1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:18:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-- 'stars798'
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment,upd_flag)
  VALUES('TESS-W','stars798','E8:DB:84:83:87:C',NULL,'1000-01-01T04:19:00','MANUAL','test',NULL,NULL,0.0,20.23,'UV/IR-740','USB-A','Caja plastico 
model FSH-714',NULL,'calibrado por Cristobal',1);
INSERT INTO summary_t(model, name, mac, firmware, session, calibration, role, freq, mag, offset, zero_point, filter, plug, box, collector, comment)
  VALUES('TESS-W','stars3','18:FE:34:CF:E9:A3',NULL,'1000-01-01T04:19:00','MANUAL','ref',NULL,NULL,0.0,20.50,'UV/IR-740','USB-A+serial','Caja plastico antigua','standard',NULL);

-----------------------------------------------
-- END NEW INSERT LINES MIGRACION POR migra1 --
-----------------------------------------------


COMMIT;
