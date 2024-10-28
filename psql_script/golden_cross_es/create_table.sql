\c demo_db
DROP TABLE IF EXISTS golden_cross_es.kline_1;

CREATE TABLE golden_cross_es.kline_1 (
    time_key    VARCHAR(30) NOT NULL,
    code        VARCHAR(20) NOT NULL,
    open        INT NOT NULL,
    high        INT NOT NULL,
    low         INT NOT NULL,
    close       INT NOT NULL,
    volume      BIGINT NOT NULL,
    k_type      VARCHAR(20) NOT NULL,
    sma_short   DOUBLE PRECISION,
    sma_long    DOUBLE PRECISION,
    signal      INT,
    PRIMARY KEY (time_key)
);

-- Add column sma_long, sma_short, signal
-- ALTER TABLE golden_cross_es.kline
-- ADD COLUMN sma_long NUMERIC(10, 2),
-- ADD COLUMN sma_short NUMERIC(10, 2),
-- ADD COLUMN signal INT;