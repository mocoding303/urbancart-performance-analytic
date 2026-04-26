-- Query 2: Campaign-Level Breakdown using NTILE
-- Objective: Rank campaigns by CPA quartile, find which dropped from Q1 to Q4
-- Trap: A new campaign (META_003) skews the channel average in October

WITH campaign_monthly AS (
    SELECT
        p.campaign_id,
        c.campaign_name,
        c.channel,
        c.campaign_type,
        c.start_date,
        EXTRACT(MONTH FROM p.date)  AS month,
        SUM(p.spend)                AS total_spend,
        SUM(p.platform_conversions) AS platform_conv,
        SUM(p.impressions)          AS total_impressions,
        SUM(p.clicks)               AS total_clicks,
        ROUND(AVG(p.frequency), 2)  AS avg_frequency
    FROM fact_ad_performance p
    JOIN dim_campaigns c ON p.campaign_id = c.campaign_id
    GROUP BY 1, 2, 3, 4, 5, 6
),

with_warehouse AS (
    SELECT
        cm.*,
        COALESCE(o.real_orders, 0)   AS real_orders,
        COALESCE(o.real_revenue, 0)  AS real_revenue,
        ROUND(cm.total_spend / NULLIF(COALESCE(o.real_orders, 0), 0), 2) AS real_cpa,
        ROUND(COALESCE(o.real_revenue, 0) / NULLIF(cm.total_spend, 0), 2) AS real_roas
    FROM campaign_monthly cm
    LEFT JOIN (
        SELECT
            attributed_campaign,
            EXTRACT(MONTH FROM order_date) AS month,
            COUNT(order_id)  AS real_orders,
            SUM(revenue)     AS real_revenue
        FROM fact_orders
        GROUP BY 1, 2
    ) o ON cm.campaign_id = o.attributed_campaign AND cm.month = o.month
),

october_ranked AS (
    SELECT
        *,
        NTILE(4) OVER (
            PARTITION BY channel
            ORDER BY real_cpa ASC NULLS LAST
        ) AS cpa_quartile  -- Q1 = best CPA, Q4 = worst CPA
    FROM with_warehouse
    WHERE month = 10
)

SELECT
    r.campaign_id,
    r.campaign_name,
    r.channel,
    r.campaign_type,
    r.start_date,
    r.total_spend    AS oct_spend,
    r.real_orders    AS oct_real_orders,
    r.real_cpa       AS oct_real_cpa,
    r.real_roas      AS oct_real_roas,
    r.avg_frequency  AS oct_frequency,
    r.cpa_quartile,
    CASE
        WHEN r.cpa_quartile = 4 THEN 'INVESTIGATE — worst CPA quartile'
        WHEN r.cpa_quartile = 1 THEN 'Strong performer'
        ELSE 'Monitor'
    END AS flag
FROM october_ranked r
ORDER BY r.channel, r.cpa_quartile DESC;
