-- UrbanCart Analytics Warehouse
-- Module 1: SQL Forensics
-- Schema: 5 tables

CREATE TABLE dim_campaigns (
    campaign_id     VARCHAR(20)  PRIMARY KEY,
    campaign_name   VARCHAR(100) NOT NULL,
    channel         VARCHAR(20)  NOT NULL,
    objective       VARCHAR(30)  NOT NULL,
    campaign_type   VARCHAR(30)  NOT NULL,
    start_date      DATE         NOT NULL,
    status          VARCHAR(10)  NOT NULL
);

CREATE TABLE fact_ad_performance (
    perf_id              SERIAL PRIMARY KEY,
    date                 DATE          NOT NULL,
    campaign_id          VARCHAR(20)   NOT NULL,
    channel              VARCHAR(20)   NOT NULL,
    impressions          INTEGER       NOT NULL,
    clicks               INTEGER       NOT NULL,
    spend                NUMERIC(10,2) NOT NULL,
    reach                INTEGER,
    frequency            NUMERIC(4,2),
    platform_conversions INTEGER,       -- WARNING: includes modeled data
    platform_revenue     NUMERIC(12,2)  -- WARNING: platform-reported, not warehouse truth
);

CREATE TABLE fact_orders (
    order_id             VARCHAR(20)   PRIMARY KEY,
    order_date           DATE          NOT NULL,
    customer_id          VARCHAR(20)   NOT NULL,
    revenue              NUMERIC(10,2) NOT NULL,
    attributed_channel   VARCHAR(20),
    attributed_campaign  VARCHAR(20),
    is_new_customer      BOOLEAN       NOT NULL,
    product_category     VARCHAR(30),
    attribution_window   INTEGER        -- 1, 7, or 28 days click window
);

CREATE TABLE dim_customers (
    customer_id          VARCHAR(20) PRIMARY KEY,
    first_order_date     DATE,
    acquisition_channel  VARCHAR(20),
    city                 VARCHAR(30),
    customer_segment     VARCHAR(20)  -- 'high_value', 'mid_value', 'low_value'
);

CREATE TABLE fact_sessions (
    session_date      DATE          NOT NULL,
    channel           VARCHAR(20)   NOT NULL,
    campaign_id       VARCHAR(20)   NOT NULL,
    sessions          INTEGER       NOT NULL,
    product_views     INTEGER,
    add_to_cart       INTEGER,
    checkout_started  INTEGER,
    conversions       INTEGER,
    session_revenue   NUMERIC(12,2),
    PRIMARY KEY (session_date, channel, campaign_id)
);
