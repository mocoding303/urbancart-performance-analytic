-- Query 4: Day-11 Anomaly Detection using Rolling Window
-- Objective: Find the exact day and campaign where revenue deviated > 30% from 7-day rolling avg
-- Trap: The anomaly date differs by channel — never aggregate before isolating

WITH daily_channel_revenue AS (
    SELECT
        o.order_date,
        o.attributed_channel          AS channel,
        SUM(o.revenue)                AS daily_revenue,
        SUM(p.spend)                  AS daily_spend
    FROM fact_orders o
    LEFT JOIN (
        SELECT date, channel, SUM(spend) AS spend
        FROM fact_ad_performance
        GROUP BY 1, 2
    ) p ON o.order_date = p.date AND o.attributed_channel = p.channel
    GROUP BY 1, 2
),

with_rolling AS (
    SELECT
        order_date,
        channel,
        daily_revenue,
        daily_spend,
        -- 7-day rolling average (preceding 7 days)
        ROUND(AVG(daily_revenue) OVER (
            PARTITION BY channel
            ORDER BY order_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ), 2) AS rolling_avg_7d,
        -- 7-day rolling standard deviation
        ROUND(STDDEV(daily_revenue) OVER (
            PARTITION BY channel
            ORDER BY order_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ), 2) AS rolling_std_7d
    FROM daily_channel_revenue
),

with_zscore AS (
    SELECT
        *,
        -- Z-score: how many standard deviations from rolling average
        ROUND(
            (daily_revenue - rolling_avg_7d) / NULLIF(rolling_std_7d, 0)
        , 2) AS z_score,
        -- Percentage deviation from rolling average
        ROUND(
            (daily_revenue - rolling_avg_7d) / NULLIF(rolling_avg_7d, 0) * 100
        , 1) AS pct_deviation
    FROM with_rolling
    WHERE rolling_avg_7d IS NOT NULL
)

SELECT
    order_date,
    channel,
    daily_revenue,
    rolling_avg_7d,
    z_score,
    pct_deviation,
    CASE
        WHEN z_score < -2.0 THEN 'ANOMALY: Beyond -2 std dev — investigate immediately'
        WHEN z_score < -1.5 THEN 'WARNING: Approaching anomaly threshold'
        WHEN pct_deviation < -30 THEN 'FLAG: Revenue > 30% below rolling average'
        ELSE 'Normal'
    END AS alert_level
FROM with_zscore
WHERE z_score < -1.5 OR pct_deviation < -25
ORDER BY z_score ASC, order_date;
