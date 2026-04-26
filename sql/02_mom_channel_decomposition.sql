-- Query 1: Month-over-Month Channel Decomposition
-- Objective: Find where revenue dropped by channel
-- Key rule: Use fact_orders (warehouse truth) NOT fact_ad_performance.platform_revenue

WITH spend_by_channel AS (
    SELECT
        channel,
        EXTRACT(MONTH FROM date) AS month,
        SUM(spend)               AS total_spend
    FROM fact_ad_performance
    GROUP BY 1, 2
),

revenue_by_channel AS (
    SELECT
        attributed_channel       AS channel,
        EXTRACT(MONTH FROM order_date) AS month,
        SUM(revenue)             AS total_revenue,
        COUNT(order_id)          AS total_orders
    FROM fact_orders
    GROUP BY 1, 2
),

combined AS (
    SELECT
        s.channel,
        s.month,
        s.total_spend,
        r.total_revenue,
        r.total_orders,
        ROUND(r.total_revenue / NULLIF(s.total_spend, 0), 2)  AS roas,
        ROUND(s.total_spend   / NULLIF(r.total_orders, 0), 2) AS cpa,
        RANK() OVER (
            PARTITION BY s.month
            ORDER BY r.total_revenue DESC
        ) AS revenue_rank
    FROM spend_by_channel s
    JOIN revenue_by_channel r
        ON s.channel = r.attributed_channel
        AND s.month  = r.month
    WHERE s.month IN (9, 10)
)

SELECT
    channel,
    MAX(CASE WHEN month = 9 THEN total_spend    END) AS sep_spend,
    MAX(CASE WHEN month = 10 THEN total_spend   END) AS oct_spend,
    MAX(CASE WHEN month = 9 THEN total_revenue  END) AS sep_revenue,
    MAX(CASE WHEN month = 10 THEN total_revenue END) AS oct_revenue,
    MAX(CASE WHEN month = 9 THEN roas           END) AS sep_roas,
    MAX(CASE WHEN month = 10 THEN roas          END) AS oct_roas,
    MAX(CASE WHEN month = 9 THEN cpa            END) AS sep_cpa,
    MAX(CASE WHEN month = 10 THEN cpa           END) AS oct_cpa,
    ROUND(
        MAX(CASE WHEN month = 10 THEN total_revenue END) -
        MAX(CASE WHEN month = 9  THEN total_revenue END)
    , 2) AS revenue_delta_eur
FROM combined
GROUP BY channel
ORDER BY revenue_delta_eur ASC; -- worst channels first
