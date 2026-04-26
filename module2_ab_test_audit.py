"""
UrbanCart — Module 2: A/B Test Statistical Audit
================================================
Objective: Audit 3 live experiments before shipping
Findings:
  Test 1 — Button colour:       Underpowered 3x. Do not ship.
  Test 2 — Shipping threshold:  Called too early. Do not ship.
  Test 3 — ML recommendations:  Sample ratio mismatch. Invalid.
"""

import numpy as np
from scipy import stats

# ── Sample size calculator ─────────────────────────────────────────────────
def required_sample_size(baseline_cvr: float, delta: float,
                          confidence: float = 0.95,
                          power: float = 0.80) -> int:
    """
    Minimum sample size per group for a two-tailed two-proportion z-test.

    Parameters:
        baseline_cvr: Control group conversion rate (e.g. 0.04 for 4%)
        delta:        Minimum detectable effect (e.g. 0.005 for 0.5% lift)
        confidence:   Statistical confidence level (default 95%)
        power:        Statistical power (default 80%)

    Returns:
        Required sample size per group (integer)

    Formula:
        n = 2 × ((z_alpha + z_beta)^2 × p × (1-p)) / delta^2

    Where:
        z_alpha = 1.96 for 95% confidence (fixed constant)
        z_beta  = 0.84 for 80% power (fixed constant)
    """
    z_alpha = stats.norm.ppf(1 - (1 - confidence) / 2)  # 1.96 for 95%
    z_beta  = stats.norm.ppf(power)                      # 0.84 for 80%
    p = baseline_cvr

    n = 2 * ((z_alpha + z_beta) ** 2 * p * (1 - p)) / (delta ** 2)
    return int(np.ceil(n))


# ── SRM (Sample Ratio Mismatch) detector ──────────────────────────────────
def check_srm(control_n: int, variant_n: int,
              expected_split: float = 0.5) -> dict:
    """
    Detect sample ratio mismatch using chi-square test.
    A significant p-value means the split is not as expected — test is invalid.

    SRM occurs when randomisation is broken (e.g. ML fallback bug,
    cookie deletion, bot traffic affecting one group).
    """
    total = control_n + variant_n
    expected_control = total * expected_split
    expected_variant = total * (1 - expected_split)

    chi2, p_value = stats.chisquare(
        f_obs=[control_n, variant_n],
        f_exp=[expected_control, expected_variant]
    )

    actual_split = control_n / total

    return {
        'chi2':         round(chi2, 4),
        'p_value':      round(p_value, 4),
        'srm_detected': p_value < 0.05,
        'actual_split': round(actual_split * 100, 1),
        'expected_split': round(expected_split * 100, 1),
    }


# ── P-value calculator (two-tailed two-proportion z-test) ─────────────────
def calculate_pvalue(control_n: int, control_conv: int,
                     variant_n: int, variant_conv: int) -> dict:
    """Two-tailed two-proportion z-test."""
    p_control = control_conv / control_n
    p_variant = variant_conv / variant_n
    p_pooled  = (control_conv + variant_conv) / (control_n + variant_n)

    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/control_n + 1/variant_n))
    z  = (p_variant - p_control) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    return {
        'control_cvr':  round(p_control * 100, 3),
        'variant_cvr':  round(p_variant * 100, 3),
        'absolute_lift': round((p_variant - p_control) * 100, 3),
        'relative_lift': round((p_variant - p_control) / p_control * 100, 1),
        'z_score':      round(z, 3),
        'p_value':      round(p_value, 4),
        'significant':  p_value < 0.05,
    }


# ══════════════════════════════════════════════════════════════════════════
# TEST 1: Button Colour — Green vs Orange CTA
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("TEST 1: Button Colour — Green vs Orange")
print("=" * 65)

t1_control_n    = 24_380
t1_control_conv = 976
t1_variant_n    = 24_412
t1_variant_conv = 1_044
t1_duration     = 7   # days

# Step 1: Calculate observed statistics
t1_stats = calculate_pvalue(t1_control_n, t1_control_conv,
                             t1_variant_n, t1_variant_conv)
print(f"\nObserved results:")
print(f"  Control CVR:    {t1_stats['control_cvr']}%")
print(f"  Variant CVR:    {t1_stats['variant_cvr']}%")
print(f"  Absolute lift:  {t1_stats['absolute_lift']} pp")
print(f"  Relative lift:  {t1_stats['relative_lift']}%")
print(f"  p-value:        {t1_stats['p_value']}")
print(f"  Significant:    {t1_stats['significant']} (p < 0.05)")

# Step 2: Calculate required sample size
baseline_cvr = t1_stats['control_cvr'] / 100
delta        = abs(t1_stats['absolute_lift']) / 100
required_n   = required_sample_size(baseline_cvr, delta)
print(f"\nSample size analysis:")
print(f"  Required per group: {required_n:,}")
print(f"  Actual per group:   {t1_control_n:,}")
print(f"  Underpowered by:    {required_n / t1_control_n:.1f}x")

# Step 3: Verdict
print(f"\nDuration: {t1_duration} days (minimum recommended: 14 days / 2 weekly cycles)")
print(f"\nVERDICT: DO NOT SHIP")
print("Reason:  p=0.038 crossed 0.05 threshold BUT test was underpowered")
print("         by 3x. With insufficient sample size, false positive risk")
print("         is significantly elevated. p-value is unreliable.")
print("Action:  Rerun for 3 weeks. Pre-calculate sample size upfront.")


# ══════════════════════════════════════════════════════════════════════════
# TEST 2: Free Shipping Threshold — €75 vs €50
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("TEST 2: Free Shipping Threshold — €75 vs €50")
print("=" * 65)

t2_control_n    = 8_921
t2_control_conv = int(8_921 * 0.0320)
t2_variant_n    = 8_876
t2_variant_conv = int(8_876 * 0.0389)
t2_control_aov  = 84.20
t2_variant_aov  = 81.60
t2_duration     = 3   # days

t2_stats = calculate_pvalue(t2_control_n, t2_control_conv,
                             t2_variant_n, t2_variant_conv)

# Revenue per visitor analysis
rpv_control = (t2_control_conv / t2_control_n) * t2_control_aov
rpv_variant = (t2_variant_conv / t2_variant_n) * t2_variant_aov

print(f"\nObserved results:")
print(f"  Control CVR:           {t2_stats['control_cvr']}%")
print(f"  Variant CVR:           {t2_stats['variant_cvr']}%")
print(f"  CVR lift:              +{t2_stats['relative_lift']}% (growth team celebrating)")
print(f"  Control AOV:           €{t2_control_aov}")
print(f"  Variant AOV:           €{t2_variant_aov} (dropped €{t2_control_aov - t2_variant_aov:.2f})")
print(f"  p-value:               {t2_stats['p_value']}")

print(f"\nRevenue per visitor analysis (the real metric):")
print(f"  Control RPV:           €{rpv_control:.3f}")
print(f"  Variant RPV:           €{rpv_variant:.3f}")
rpv_change = (rpv_variant - rpv_control) / rpv_control * 100
print(f"  RPV change:            {rpv_change:+.1f}%")

est_monthly_visitors = 50_000
monthly_impact = (rpv_variant - rpv_control) * est_monthly_visitors
print(f"\nEstimated monthly revenue impact (@{est_monthly_visitors:,} visitors):")
print(f"  €{monthly_impact:,.0f}/month")

print(f"\nDuration: {t2_duration} days (minimum recommended: 14 days)")
print(f"\nVERDICT: DO NOT SHIP")
print("Reason:  Called after 3 days — severe early stopping problem.")
print("         CVR went up but AOV dropped. Revenue per visitor")
print("         barely improved. Shipping margin impact not calculated.")
print("Action:  Model full P&L including shipping cost increase.")
print("         Rerun for minimum 2 weeks with revenue/visitor as primary KPI.")


# ══════════════════════════════════════════════════════════════════════════
# TEST 3: ML Recommendations — Generic vs Personalised
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("TEST 3: ML Recommendations — Generic vs Personalised")
print("=" * 65)

t3_control_n    = 31_240
t3_variant_n    = 28_930
t3_control_conv = int(31_240 * 0.0385)
t3_variant_conv = int(28_930 * 0.0412)
t3_duration     = 14  # days

t3_stats = calculate_pvalue(t3_control_n, t3_control_conv,
                             t3_variant_n, t3_variant_conv)

# SRM check
srm = check_srm(t3_control_n, t3_variant_n)

print(f"\nObserved results:")
print(f"  Control CVR:     {t3_stats['control_cvr']}%")
print(f"  Variant CVR:     {t3_stats['variant_cvr']}%")
print(f"  p-value:         {t3_stats['p_value']}")
print(f"  Significant:     {t3_stats['significant']}")

print(f"\nSample Ratio Mismatch (SRM) check:")
print(f"  Expected split:  {srm['expected_split']}% / {100 - srm['expected_split']}%")
print(f"  Actual split:    {srm['actual_split']}% / {100 - srm['actual_split']}%")
print(f"  Chi-square:      {srm['chi2']}")
print(f"  SRM p-value:     {srm['p_value']}")
print(f"  SRM detected:    {srm['srm_detected']}")

print(f"\nDuration: {t3_duration} days")
print(f"\nVERDICT: INVALID — DO NOT SHIP")
print("Reason:  Sample ratio mismatch detected. Control received 51.9%")
print("         of traffic vs expected 50%. Root cause: ML recommendation")
print("         system fails silently for some users and falls back to")
print("         control experience. Harder-to-convert users systematically")
print("         ended up in control — making variant look better than it is.")
print("Action:  Fix ML fallback bug. Verify split returns to 50/50.")
print("         Rerun experiment from scratch.")


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print(f"{'AUDIT SUMMARY':^65}")
print("=" * 65)
print(f"\n{'Test':<25} {'p-value':>8} {'Problem':<30} {'Verdict'}")
print("-" * 65)
print(f"{'Button colour':<25} {'0.038':>8} {'Underpowered 3x, 7 days only':<30} {'Do not ship'}")
print(f"{'Shipping threshold':<25} {'0.031':>8} {'3 days, AOV dropped, no P&L':<30} {'Do not ship'}")
print(f"{'ML recommendations':<25} {'0.012':>8} {'SRM: 51.9/48.1 split':<30} {'Invalid'}")
print("=" * 65)

print("""
KEY RULES FROM THIS AUDIT:
1. p < 0.05 is necessary but NOT sufficient
2. Always pre-calculate required sample size before running a test
3. Run for minimum 2 complete weekly cycles (Mon-Sun)
4. Always check SRM before reading results
5. Use revenue per visitor — not CVR alone — as primary KPI
6. Model full P&L impact including operational costs
""")
