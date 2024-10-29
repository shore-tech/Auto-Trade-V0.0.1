\c demo_db
-- DROP TABLE IF EXISTS golden_cross_es.kline_1;

-- CREATE TABLE golden_cross_es.kline_1 (
--     time_key    VARCHAR(30) NOT NULL,
--     code        VARCHAR(20) NOT NULL,
--     open        INT NOT NULL,
--     high        INT NOT NULL,
--     low         INT NOT NULL,
--     close       INT NOT NULL,
--     volume      BIGINT NOT NULL,
--     k_type      VARCHAR(20) NOT NULL,
--     sma_short   DOUBLE PRECISION,
--     sma_long    DOUBLE PRECISION,
--     signal      INT,
--     PRIMARY KEY (time_key)
-- );
-- select * from golden_cross_es.kline_1;

DROP TABLE IF EXISTS golden_cross_es.order_record;

CREATE TABLE golden_cross_es.order_record (
    updated_time        VARCHAR(30) NOT NULL,
    order_id            VARCHAR(10) NOT NULL,
    order_status        VARCHAR(20) NOT NULL,
    code                VARCHAR(20) NOT NULL,
    order_type          VARCHAR(20) NOT NULL,
    trd_side            VARCHAR(10) NOT NULL,
    qty                 INT NOT NULL,
    price               DOUBLE PRECISION NOT NULL,
    dealt_qty           DOUBLE PRECISION,
    dealt_avg_price     DOUBLE PRECISION,
    action              VARCHAR(10),
    logic               VARCHAR(20),
    commission          DOUBLE PRECISION,
    pnl_realized        DOUBLE PRECISION,
    PRIMARY KEY (updated_time, order_id, order_status)
);


-- select * from golden_cross_es.order_record;