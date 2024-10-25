\c demo_db
DROP TABLE IF EXISTS golden_cross_es.kline;

CREATE TABLE golden_cross_es.kline (
    time_key    VARCHAR(30) NOT NULL,
    code        VARCHAR(20) NOT NULL,
    open        NUMERIC(10, 2) NOT NULL,
    high        NUMERIC(10, 2) NOT NULL,
    low         NUMERIC(10, 2) NOT NULL,
    close       NUMERIC(10, 2) NOT NULL,
    volume      BIGINT NOT NULL,
    k_type      VARCHAR(20) NOT NULL,
    PRIMARY KEY (time_key)
);