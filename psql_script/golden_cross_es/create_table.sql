\c demo_db

-- DROP TABLE IF EXISTS golden_cross_es.dummy;
-- CREATE TABLE golden_cross_es.dummy(
--     updated_time    VARCHAR(30) NOT NULL,
--     code            VARCHAR(20) NOT NULL,
--     open            INT NOT NULL,
--     high            INT NOT NULL,
--     low             INT NOT NULL,
--     close           INT NOT NULL,
--     volume          BIGINT NOT NULL,
--     k_type          VARCHAR(20) NOT NULL,
--     sma_short       DOUBLE PRECISION,
--     sma_long        DOUBLE PRECISION,
--     signal          INT,
--     PRIMARY KEY (updated_time, code)
-- );
-- select * from golden_cross_es.dummy;


-- DROP TABLE IF EXISTS golden_cross_es.k_line;
-- CREATE TABLE golden_cross_es.k_line(
--     updated_time    VARCHAR(30) NOT NULL,
--     code            VARCHAR(20) NOT NULL,
--     open            INT NOT NULL,
--     high            INT NOT NULL,
--     low             INT NOT NULL,
--     close           INT NOT NULL,
--     volume          BIGINT NOT NULL,
--     k_type          VARCHAR(20) NOT NULL,
--     sma_short       DOUBLE PRECISION,
--     sma_long        DOUBLE PRECISION,
--     signal          INT,
--     PRIMARY KEY (updated_time, code)
-- );
-- select * from golden_cross_es.k_line;


-- DROP TABLE IF EXISTS golden_cross_es.order_record;
-- CREATE TABLE golden_cross_es.order_record (
--     updated_time        VARCHAR(30) NOT NULL,
--     order_id            VARCHAR(10) NOT NULL,
--     order_status        VARCHAR(20) NOT NULL,
--     code                VARCHAR(20) NOT NULL,
--     order_type          VARCHAR(20) NOT NULL,
--     trd_side            VARCHAR(10) NOT NULL,
--     qty                 INT NOT NULL,
--     price               DOUBLE PRECISION NOT NULL,
--     dealt_qty           DOUBLE PRECISION,
--     dealt_avg_price     DOUBLE PRECISION,
--     action              VARCHAR(10),
--     logic               VARCHAR(20),
--     commission          DOUBLE PRECISION,
--     pnl_realized        DOUBLE PRECISION,
--     PRIMARY KEY (updated_time, order_id, order_status)
-- );
-- select * from golden_cross_es.order_record;


-- DROP TABLE IF EXISTS golden_cross_es.acc_status;
-- CREATE TABLE golden_cross_es.acc_status (
--     updated_time    VARCHAR(30) NOT NULL,
--     reason          VARCHAR(20) NOT NULL,
--     nav             DOUBLE PRECISION NOT NULL,
--     bal_cash        DOUBLE PRECISION NOT NULL,
--     bal_available   DOUBLE PRECISION NOT NULL,
--     margin_i        DOUBLE PRECISION NOT NULL,
--     margin_m        DOUBLE PRECISION NOT NULL,
--     cap_usage       DOUBLE PRECISION NOT NULL,
--     code            VARCHAR(20),
--     pos_size        INT,
--     pos_price       DOUBLE PRECISION,
--     mkt_price       DOUBLE PRECISION,
--     stop_level      DOUBLE PRECISION,
--     target_level    DOUBLE PRECISION,
--     pnl_unrealized  DOUBLE PRECISION,
--     k_type          VARCHAR(10),
--     order_id        VARCHAR(10),
--     PRIMARY KEY (updated_time)
-- );

-- select * from golden_cross_es.acc_status;