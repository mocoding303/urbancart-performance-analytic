-- Query 5: New vs Returning Customer Cohort Analysis
-- Objective: Has the business stopped acquiring new customers — or stopped measuring correctly?
-- Trap: Blended CPA looks OK but new-customer CPA is catastrophic

WITH monthly_orders AS (
    SELECT
        o.attributed_channel         AS channel,
        EXTRACT(MONTH FROM o.order_date) AS month,
        o.is_new_customer,
        COUNT(o.order_id)            AS orders,
        SUM(o.revenue)               AS revenue
    FROM fact_orders o
    WHERE EXTRACT(MONTH FROM o.order_date) IN (9, 10)
    GROUP BY 1, 2, 3
),

spend_monthly AS (
    SELECT
        channel,
        EXTRACT(MONTH FROM date) AS month,
        SUM(spend) AS total_spend
    FROM fact_ad_performance
    WHERE EXTRACT(MONTH FROM date) IN (9, 10)
    GROUP BY 1, 2
),

cohort_summary AS (
    SELECT
        m.channel,
        m.month,
        SUM(m.orders)                AS total_orders,
        SUM(CASE WHEN m.is_new_customer THEN m.orders ELSE 0 END) AS new_orders,
        SUM(CASE WHEN NOT m.is_new_customer THEN m.orders ELSE 0 END) AS returning_orders,
        SUM(m.revenue)               AS total_revenue,
        SUM(CASE WHEN m.is_new_customer THEN m.revenue ELSE 0 END) AS new_revenue,
        ROUND(
            SUM(CASE WHEN m.is_new_customer THEN m.orders ELSE 0 END)::numeric
            / NULLIF(SUM(m.orders), 0) * 100
        , 1) AS new_customer_pct,
        s.total_spend,
        -- Blended CPA
        ROUND(s.total_spend / NULLIF(SUM(m.orders), 0), 2) AS blended_cpa,
        -- New customer CPA only
        ROUND(
            s.total_spend /
            NULLIF(SUM(CASE WHEN m.is_new_customer THEN m.orders ELSE 0 END), 0)
        , 2) AS new_customer_cpa
    FROM monthly_orders m
    JOIN spend_monthly s
        ON m.channel = s.channel AND m.month = s.month
    GROUP BY m.channel, m.month, s.total_spend
)

SELECT
    channel,
    MAX(CASE WHEN month = 9  THEN new_customer_pct  END) AS sep_new_pct,
    MAX(CASE WHEN month = 10 THEN new_customer_pct  END) AS oct_new_pct,
    MAX(CASE WHEN month = 9  THEN blended_cpa       END) AS sep_blended_cpa,
    MAX(CASE WHEN month = 10 THEN blended_cpa       END) AS oct_blended_cpa,
    MAX(CASE WHEN month = 9  THEN new_customer_cpa  END) AS sep_new_cpa,
    MAX(CASE WHEN month = 10 THEN new_customer_cpa  END) AS oct_new_cpa,
    ROUND(
        MAX(CASE WHEN month = 10 THEN new_customer_pct END) -
        MAX(CASE WHEN month = 9  THEN new_customer_pct END)
    , 1) AS new_customer_pct_change,
    CASE
        WHEN MAX(CASE WHEN month = 10 THEN new_customer_pct END) <
             MAX(CASE WHEN month = 9  THEN new_customer_pct END) - 10
        THEN 'FLAG: New customer acquisition declining significantly'
        ELSE 'OK'
    END AS verdict
FROM cohort_summary
GROUP BY channel
ORDER BY new_customer_pct_change ASC;
