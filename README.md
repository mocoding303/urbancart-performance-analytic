# UrbanCart — Performance Marketing Analytics Case Study

> A senior-level analytics investigation identifying **€504K of monthly wasted ad spend** using SQL forensics, statistical A/B test auditing, incrementality-based attribution, Python budget optimisation, and automated anomaly detection.

---

## The Business Problem

UrbanCart, a Berlin-based fashion e-commerce company, experienced a critical performance collapse in October 2024:

| Metric | September | October | Change |
|--------|-----------|---------|--------|
| Ad Spend | €1.64M | €1.84M | +12% |
| Revenue | €5.0M | €4.1M | **-18%** |
| ROAS | 3.1x | 2.23x | **-28%** |
| CPA | €26.80 | €38.40 | **+43%** |

---

## Key Findings

| Finding | Impact | Tool |
|---------|--------|------|
| META_003 modeled conversions — 4.8x platform vs warehouse discrepancy | €285K/month wasted | PostgreSQL |
| Snapchat awareness campaign receiving conversion budget — CPA €1,546 | €219K/month wasted | SQL |
| TikTok undercredited by last-click — true iROAS = 2.12x | €300K+ saved from bad cut | Incrementality |
| iOS 17.4 broke Meta pixel day 11 — CVR -62%, z-score -2.09 | Revenue -34% single day | Python |
| All 3 live A/B tests had critical statistical flaws | 3 false positives blocked | Statistics |

---

## Module 1 — SQL Forensics

Core pattern — aggregate first, then join:

```sql
WITH spend AS (
    SELECT channel, EXTRACT(MONTH FROM date) AS month, SUM(spend) AS total_spend
    FROM fact_ad_performance GROUP BY 1, 2
),
revenue AS (
    SELECT attributed_channel, EXTRACT(MONTH FROM order_date) AS month,
           SUM(revenue) AS total_revenue, COUNT(*) AS total_orders
    FROM fact_orders GROUP BY 1, 2
)
SELECT s.channel, s.month,
       ROUND(r.total_revenue / s.total_spend, 2) AS roas,
       ROUND(s.total_spend / r.total_orders, 2) AS cpa
FROM spend s
JOIN revenue r ON s.channel = r.attributed_channel AND s.month = r.month
WHERE s.month IN (9, 10)
ORDER BY s.channel, s.month;
```

Three traps found: META_003 4.8x conversion overclaim, GGL_002 silent pause day 11, SNP_001 awareness objective receiving conversion budget.

---

## Module 2 — A/B Test Audit

Sample size formula:

```python
n = 2 * ((1.96 + 0.84)**2 * p * (1 - p)) / (delta**2)
# Button test: needed 76,786 per group. Actual: 24,380. Underpowered 3x.
```

| Test | Problem | Verdict |
|------|---------|---------|
| Button colour p=0.038 | Underpowered 3x. 7 days = 1 weekend. | Rerun 3 weeks |
| Shipping threshold p=0.031 | Called after 3 days. AOV dropped. | Model P&L first |
| ML recommendations p=0.012 | SRM 51.9/48.1 split. ML bug. | Fix bug, rerun |

---

## Module 3 — Attribution War

| Channel | Last-click | Incrementality | iROAS | Decision |
|---------|-----------|----------------|-------|----------|
| TikTok | 15% | **34%** | **2.12x** | Scale +60% |
| Google | 45% | 23% | 0.93x | Hold -15% |
| Meta | 30% | 30% | 0.61x | Cut -40% |
| Snap | 10% | 7% | 0.45x | Cut -80% |

TikTok geo-holdout test: turning off for 20% of users caused €1,106,000 monthly revenue loss. iROAS = 2.12x. CFO cut blocked. €300K+ preserved.

---

## Module 4 — Python Budget Optimiser

```python
from scipy.optimize import minimize
import numpy as np

channels = {
    'tiktok': {'iroas': 2.12, 'min': 150000, 'max': 700000},
    'google': {'iroas': 0.93, 'min': 200000, 'max': 500000},
    'meta':   {'iroas': 0.61, 'min': 200000, 'max': 600000},
    'snap':   {'iroas': 0.45, 'min': 50000,  'max': 150000},
}
scaling = {'tiktok': 180, 'google': 120, 'meta': 110, 'snap': 80}

def objective(x):
    names = list(channels.keys())
    return -sum(channels[names[i]]['iroas'] * scaling[names[i]] * np.sqrt(x[i]) for i in range(4))

result = minimize(objective, x0=[261000, 395000, 799000, 274000], method='SLSQP',
    bounds=[(v['min'], v['max']) for v in channels.values()],
    constraints=[{'type': 'eq', 'fun': lambda x: sum(x) - 1840000}])
```

Result: €115,186 additional monthly incremental revenue from same €1.84M budget.

---

## Module 5 — Anomaly Detection

```python
daily['rolling_avg'] = daily['total_revenue'].rolling(window=7).mean()
daily['rolling_std'] = daily['total_revenue'].rolling(window=7).std()
daily['z_score'] = (daily['total_revenue'] - daily['rolling_avg']) / daily['rolling_std']
daily['anomaly'] = daily['z_score'] < -2.0
```

Day 11: z-score = -2.09. Channel isolation: only Meta CVR collapsed (-62%). Root cause: iOS 17.4 pixel tracking break. Fix: Meta Conversions API — 48 hour recovery.

---

## Recovery Plan

| Timeline | Action | Impact |
|----------|--------|--------|
| Today | Pause META_003 | €285K/month saved |
| Today | Implement Meta CAPI | CVR recovery 48hrs |
| This week | Cut Snap to €55K | €219K/month saved |
| Next month | Scale TikTok to €418K | +€157K revenue/month |

Expected: ROAS to 2.8x in 30 days. Revenue recovery in 45 days.

---

## Skills

**SQL** — CTEs, window functions, rolling averages, cohort analysis, platform vs warehouse reconciliation  
**Statistics** — Sample size formula, z-score, p-value, statistical power, SRM detection  
**Attribution** — Last-click, data-driven, incrementality, geo-holdout, iROAS, marginal ROAS  
**Python** — pandas, numpy, scipy.optimize, matplotlib, anomaly detection, budget optimisation  
**Tools** — PostgreSQL, pgAdmin, Jupyter, GA4, Meta Ads Manager, Looker Studio

---

*Mouhssine — Performance Marketing Analyst & M.Sc. Data Science candidate, Berlin*
# urbancart-performance-analytic
