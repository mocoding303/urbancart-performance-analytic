-- Query 3: Platform vs Warehouse Reconciliation
-- Objective: Find campaigns where platform overclaims conversions vs real warehouse orders
-- Smoking gun: Any campaign with ratio > 2.0 is using modeled/estimated conversions
-- Trap: META_003 has a ratio of ~4.8x — platform inflation from iOS signal loss

WITH platform_data AS (
    SELECT
        campaign_id,
        EXTRACT(MONTH FROM date)    AS month,
        SUM(spend)                  AS total_spend,
        SUM(platform_conversions)   AS platform_conv,
        SUM(platform_revenue)       AS platform_revenue
    FROM fact_ad_performance
    WHERE EXTRACT(MONTH FROM date) = 10  -- October only
    GROUP BY 1, 2
),

warehouse_data AS (
    SELECT
        attributed_campaign         AS campaign_id,
        EXTRACT(MONTH FROM order_date) AS month,
        COUNT(order_id)             AS real_orders,
        SUM(revenue)                AS real_revenue
    FROM fact_orders
    WHERE EXTRACT(MONTH FROM order_date) = 10
    GROUP BY 1, 2
)

SELECT
    p.campaign_id,
    c.campaign_name,
    c.channel,
    p.total_spend,
    p.platform_conv,
    COALESCE(w.real_orders, 0)   AS real_orders,
    -- The key discrepancy ratio
    ROUND(
        p.platform_conv::numeric / NULLIF(COALESCE(w.real_orders, 0), 0)
    , 2) AS platform_to_warehouse_ratio,
    p.platform_revenue,
    COALESCE(w.real_revenue, 0)  AS real_revenue,
    ROUND(
        p.platform_revenue / NULLIF(COALESCE(w.real_revenue, 0), 0)
    , 2) AS revenue_discrepancy_ratio,
    CASE
        WHEN p.platform_conv::numeric / NULLIF(COALESCE(w.real_orders, 0), 0) > 2.0
        THEN 'FLAG: Conversion overclaim > 2x — likely modeled data'
        WHEN p.platform_conv::numeric / NULLIF(COALESCE(w.real_orders, 0), 0) BETWEEN 1.2 AND 2.0
        THEN 'WATCH: Mild overclaim — monitor'
        ELSE 'OK: Within acceptable range'
    END AS verdict
FROM platform_data p
JOIN dim_campaigns c ON p.campaign_id = c.campaign_id
LEFT JOIN warehouse_data w
    ON p.campaign_id = w.campaign_id
    AND p.month = w.month
ORDER BY platform_to_warehouse_ratio DESC NULLS LAST;
