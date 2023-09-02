-------------------------------
-- TKAzotea database Data Model
-------------------------------

-- This is the database counterpart of a configuration file
-- All configurations are stored here
CREATE TABLE IF NOT EXISTS config_t
(
    section        TEXT NOT NULL,  -- Configuration section
    property       TEXT NOT NULL,  -- Property name
    value          TEXT NOT NULL,  -- Property value

    PRIMARY KEY(section, property)
);

-- batch calibration table
CREATE TABLE IF NOT EXISTS batch_t
(
    begin_tstamp    TIMESTAMP,  -- begin timestamp session
    end_tstamp      TIMESTAMP,  -- end   timestamp session
    email_sent      INTEGER,    -- 1=Yes, 0=No, NULL=didn't even try.
    calibrations    INTEGER,    -- number of calibrations performed in this period
    comment         TEXT,       -- optional comment for the opened calibration batch

    PRIMARY KEY(begin_tstamp)
);

-- raw samples table
CREATE TABLE IF NOT EXISTS samples_t
(
    tstamp          TIMESTAMP,  -- sample timestamp
    role            TEXT,       -- either 'test' or 'ref'
    session         TIMESTAMP,  -- calibration session identifier
    freq            REAL,       -- measured frequency
    seq             INTEGER,    -- sequence number for JSON based raw readings, NULL otherwise
    temp_box        REAL,       -- Box temperature for JSON based raw readings, NULL otherwise
  
    PRIMARY KEY(role, tstamp)
);

-- rounds window table
CREATE TABLE IF NOT EXISTS rounds_t
(
    session         TIMESTAMP,  -- calibration session identifier
    round           INTEGER,    -- to link ref and test windows
    role            TEXT,       -- either 'test' or 'ref'
    begin_tstamp    TIMESTAMP,  -- calibration window start timestamp
    end_tstamp      TIMESTAMP,  -- calibration window end timestamp
    central         TEXT,       -- estimate of central tendency: either 'mean','median' or 'mode'
    freq            REAL,       -- central frequency estimate
    stddev          REAL,       -- Standard deviation for frequency central estimate
    mag             REAL,       -- magnitiude corresponding to central frequency and summing ficticious zero point 
    zp_fict         REAL,       -- Ficticious ZP to estimate instrumental magnitudes (=20.50)
    zero_point      REAL,       -- Estimated Zero Point for this round ('test' photometer round only, else NULL)
    nsamples        INTEGER,    -- Number of samples for this round
    duration        REAL,       -- Approximate duration, in seconds

    PRIMARY KEY(session, role, round)
);

CREATE VIEW IF NOT EXISTS rounds_v 
AS SELECT
    r.session,
    r.round,
    r.role,
    r.begin_tstamp,
    r.end_tstamp,
    r.central,
    r.freq,
    r.stddev,
    r.mag,
    r.zp_fict,
    r.zero_point,
    r.nsamples,
    r.duration,
    s.model,
    s.name,
    s.mac,
    s.nrounds,
    s.upd_flag
FROM rounds_t AS r
JOIN summary_t AS s USING (session, role);

-- Summary calibration table
CREATE TABLE IF NOT EXISTS summary_t
(
    session           TIMESTAMP,  -- calibration session identifier
    role              TEXT,       -- either 'test' or 'ref'
    calibration       TEXT,       -- either 'MANUAL' or 'AUTO'
    calversion        TEXT,       -- calibration software version
    model             TEXT,  -- TESS model
    name              TEXT,  -- TESS name
    mac               TEXT,  -- TESS MAC address
    firmware          TEXT,  -- firmware revision
    sensor            TEXT,  -- Sensor model (TSL237, S9705-01DT)
    prev_zp           REAL,  -- previous ZP before calibration
    author            TEXT,  -- who run the calibration
    nrounds           INTEGER, -- Number of rounds passed
    offset            REAL,  -- Additional offset that was summed to the computed zero_point
    upd_flag          INTEGER, -- 1 => TESS-W ZP was updated, 0 => TESS-W ZP was not updated,
    zero_point        REAL,  -- calibrated zero point
    zero_point_method TEXT,  -- either the 'mode' or 'median' of the different rounds
    freq              REAL,  -- final chosen frequency
    freq_method       TEXT,  -- either the 'mode' or 'median' of the different rounds
    mag               REAL,  -- final chosen magnitude uzing ficticious ZP
    filter            TEXT,  -- Filter type (i.e. UV-IR/740)
    plug              TEXT,  -- Plug type (i.e. USB-A)
    box               TEXT,  -- Box model (i.e. FSH714)
    collector         TEXT,  -- Collector model
    comment           TEXT,  -- Additional comment for the callibration process
    PRIMARY KEY(session, role)
);


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