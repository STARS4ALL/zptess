-- Global section
BEGIN TRANSACTION;

------------------------------
-- Database version upgrade --
------------------------------

INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '06');

------------------------------------
-- Schema change for summary data --
------------------------------------

ALTER TABLE summary_t ADD COLUMN calversion TEXT;

DROP VIEW summary_v;

CREATE VIEW IF NOT EXISTS summary_v 
AS SELECT
    test_t.session,
    test_t.role,
    test_t.calibration,
    test_t.calversion,
    test_t.model,
    test_t.name,
    test_t.mac,
    test_t.firmware,
    test_t.sensor,
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


COMMIT;