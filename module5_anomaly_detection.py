"""
UrbanCart — Module 5: Anomaly Detection System
==============================================
Objective: Detect performance anomalies within 24 hours using z-score
Method:    7-day rolling average + standard deviation threshold
Root cause: iOS 17.4 broke Meta pixel tracking on day 11

Three suspects tested:
  A — iOS update (Meta CVR collapse)  ← GUILTY
  B — Creative fatigue (TikTok freq)  ← Innocent
  C — Bid strategy change (Google CPA) ← Innocent
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, timedelta

np.random.seed(42)

# ── Generate 30 days of campaign data ─────────────────────────────────────
days = list(range(1, 31))

baseline = {
    'meta':   {'spend': 26_000, 'ctr': 0.022, 'cvr': 0.041, 'aov': 88},
    'google': {'spend': 13_000, 'ctr': 0.045, 'cvr': 0.058, 'aov': 91},
    'tiktok': {'spend': 17_000, 'ctr': 0.018, 'cvr': 0.038, 'aov': 83},
    'snap':   {'spend': 9_000,  'ctr': 0.008, 'cvr': 0.022, 'aov': 85},
}

records = []

for day in days:
    for channel, b in baseline.items():
        spend = b['spend'] * np.random.uniform(0.92, 1.08)
        ctr   = b['ctr']   * np.random.uniform(0.90, 1.10)
        cvr   = b['cvr']   * np.random.uniform(0.90, 1.10)
        aov   = b['aov']   * np.random.uniform(0.95, 1.05)
        freq  = np.random.uniform(1.2, 2.8)

        # ── EMBEDDED ANOMALIES ──────────────────────────────────────────
        # Suspect A — iOS 17.4 breaks Meta pixel tracking (THE CULPRIT)
        if day == 11 and channel == 'meta':
            cvr = cvr * 0.38   # CVR collapses 62%

        # Suspect B — TikTok creative fatigue (distractor — builds but not catastrophic)
        if day >= 9 and channel == 'tiktok':
            freq = freq + (day - 8) * 0.4
            ctr  = ctr * max(0.6, 1 - (day - 8) * 0.02)

        # Suspect C — Google bid strategy change (distractor — minor noise only)
        if day >= 10 and channel == 'google':
            ctr = ctr * np.random.uniform(0.88, 1.12)
        # ───────────────────────────────────────────────────────────────

        impressions = int(spend / 0.012)
        clicks      = int(impressions * ctr)
        conversions = int(clicks * cvr)
        revenue     = round(conversions * aov, 2)
        cpa         = round(spend / conversions, 2) if conversions else 0

        records.append({
            'day':         day,
            'channel':     channel,
            'spend':       round(spend, 2),
            'impressions': impressions,
            'clicks':      clicks,
            'ctr':         round(ctr, 4),
            'cvr':         round(cvr, 4),
            'conversions': conversions,
            'revenue':     revenue,
            'cpa':         cpa,
            'frequency':   round(freq, 2),
        })

df = pd.DataFrame(records)
print(f"Dataset: {len(df)} rows ({df['channel'].nunique()} channels × {df['day'].nunique()} days)")


# ── STEP 1: Aggregate daily total revenue ─────────────────────────────────
daily = df.groupby('day').agg(
    total_revenue=('revenue', 'sum'),
    total_spend=('spend', 'sum')
).reset_index()


# ── STEP 2: Calculate 7-day rolling average and std deviation ─────────────
daily['rolling_avg'] = daily['total_revenue'].rolling(window=7).mean()
daily['rolling_std'] = daily['total_revenue'].rolling(window=7).std()


# ── STEP 3: Calculate z-score ─────────────────────────────────────────────
daily['z_score'] = (
    (daily['total_revenue'] - daily['rolling_avg']) / daily['rolling_std']
)

# Flag anomalies beyond -2 standard deviations
daily['anomaly'] = daily['z_score'] < -2.0


# ── STEP 4: Print anomaly report ──────────────────────────────────────────
print("\n" + "=" * 70)
print(f"{'ANOMALY DETECTION REPORT — DAILY REVENUE':^70}")
print("=" * 70)
print(f"\n{'Day':>4} {'Revenue':>12} {'Rolling Avg':>12} {'Z-Score':>9} {'Alert':>8}")
print("-" * 55)

for _, row in daily.iterrows():
    if pd.isna(row['rolling_avg']):
        continue
    flag = "*** ANOMALY" if row['anomaly'] else ""
    print(f"{row['day']:>4.0f} €{row['total_revenue']:>10,.0f} "
          f"€{row['rolling_avg']:>10,.0f} {row['z_score']:>9.2f}  {flag}")

print("=" * 70)


# ── STEP 5: Channel isolation on the anomaly day ──────────────────────────
anomaly_day = daily[daily['anomaly'] == True]['day'].values
if len(anomaly_day) > 0:
    aday = int(anomaly_day[0])
    print(f"\nAnomaly detected on Day {aday}. Isolating by channel...\n")

    day_before = df[df['day'] == aday - 1][['channel','spend','clicks','cvr','conversions','revenue','cpa','frequency']]
    day_of     = df[df['day'] == aday][['channel','spend','clicks','cvr','conversions','revenue','cpa','frequency']]

    print(f"Day {aday - 1} (normal):")
    print(day_before.to_string(index=False))
    print(f"\nDay {aday} (anomaly):")
    print(day_of.to_string(index=False))

    print(f"\n{'Channel Revenue Change (Day {aday-1} → Day {aday})':}")
    print("-" * 60)
    for channel in ['meta', 'google', 'tiktok', 'snap']:
        r_before = day_before[day_before['channel'] == channel]['revenue'].values[0]
        r_after  = day_of[day_of['channel'] == channel]['revenue'].values[0]
        cvr_before = day_before[day_before['channel'] == channel]['cvr'].values[0]
        cvr_after  = day_of[day_of['channel'] == channel]['cvr'].values[0]
        rev_change = ((r_after - r_before) / r_before) * 100
        cvr_change = ((cvr_after - cvr_before) / cvr_before) * 100
        flag = " ← SUSPECT" if abs(cvr_change) > 40 else ""
        print(f"  {channel:<10} Revenue: {rev_change:>+6.1f}%  CVR: {cvr_change:>+6.1f}%{flag}")


# ── STEP 6: Visualisation ──────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
fig.suptitle('UrbanCart — Anomaly Detection: CVR by Channel (30 days)',
             fontsize=13, fontweight='bold')

ch_colors = {'meta': '#378ADD', 'google': '#1D9E75', 'tiktok': '#D85A30', 'snap': '#7F77DD'}

for idx, channel in enumerate(['meta', 'google', 'tiktok', 'snap']):
    ax = axes[idx // 2][idx % 2]
    ch_data = df[df['channel'] == channel].copy()

    ax.plot(ch_data['day'], ch_data['cvr'],
            color=ch_colors[channel], linewidth=2, marker='o', markersize=3)
    ax.axvline(x=11, color='red', linestyle='--', linewidth=1.5, label='Day 11 anomaly')
    ax.axhline(y=ch_data['cvr'].mean(), color='gray', linestyle=':',
               linewidth=1, label='Average CVR')

    # Shade ±1 std dev band
    mean_cvr = ch_data['cvr'].mean()
    std_cvr  = ch_data['cvr'].std()
    ax.axhspan(mean_cvr - std_cvr, mean_cvr + std_cvr,
               alpha=0.1, color=ch_colors[channel], label='±1 std dev')

    ax.set_title(f'{channel.upper()} — CVR over 30 days')
    ax.set_xlabel('Day')
    ax.set_ylabel('CVR')
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('module5_anomaly_detection.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nChart saved as module5_anomaly_detection.png")


# ── STEP 7: Three suspects summary ────────────────────────────────────────
print("\n" + "=" * 70)
print(f"{'SUSPECT ANALYSIS':^70}")
print("=" * 70)

suspects = {
    'A — iOS 17.4 update': {
        'metric': 'Meta CVR',
        'finding': f"CVR: {day_before[day_before['channel']=='meta']['cvr'].values[0]:.4f} → "
                   f"{day_of[day_of['channel']=='meta']['cvr'].values[0]:.4f} "
                   f"({((day_of[day_of['channel']=='meta']['cvr'].values[0] - day_before[day_before['channel']=='meta']['cvr'].values[0]) / day_before[day_before['channel']=='meta']['cvr'].values[0] * 100):.1f}%)",
        'verdict': 'GUILTY — root cause'
    },
    'B — TikTok creative fatigue': {
        'metric': 'TikTok frequency + CTR',
        'finding': f"Frequency: {day_of[day_of['channel']=='tiktok']['frequency'].values[0]:.2f} (elevated but not catastrophic)",
        'verdict': 'Innocent — distractor'
    },
    'C — Google bid strategy change': {
        'metric': 'Google CPA',
        'finding': f"CPA: €{day_before[day_before['channel']=='google']['cpa'].values[0]:.2f} → "
                   f"€{day_of[day_of['channel']=='google']['cpa'].values[0]:.2f} (no material change)",
        'verdict': 'Innocent — distractor'
    },
}

for suspect, details in suspects.items():
    print(f"\n  {suspect}")
    print(f"  Metric checked: {details['metric']}")
    print(f"  Finding:        {details['finding']}")
    print(f"  Verdict:        {details['verdict']}")

print("\n" + "=" * 70)
print("CONCLUSION: iOS 17.4 broke Meta pixel tracking on day 11.")
print("Meta CVR collapsed 62%. Spend and clicks were normal.")
print("Fix: Implement Meta Conversions API (server-side tracking).")
print("Expected CVR recovery: within 48 hours of CAPI deployment.")
print("=" * 70)
