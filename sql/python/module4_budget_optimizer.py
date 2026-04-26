"""
UrbanCart — Module 4: Python Budget Optimiser
============================================
Objective: Allocate €1.84M across 4 channels to maximise incremental revenue
Method:    scipy.optimize with square root diminishing returns model
Principle: Marginal ROAS equalisation across all channels
"""

import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Channel configuration ──────────────────────────────────────────────────
# iROAS from incrementality holdout test (Module 3)
channels = {
    'tiktok': {'iroas': 2.12, 'min': 150_000, 'max': 700_000, 'current': 261_000},
    'google': {'iroas': 0.93, 'min': 200_000, 'max': 500_000, 'current': 395_000},
    'meta':   {'iroas': 0.61, 'min': 200_000, 'max': 600_000, 'current': 799_000},
    'snap':   {'iroas': 0.45, 'min': 50_000,  'max': 150_000, 'current': 274_000},
}

# Scaling factors calibrated to match real incremental revenue from Module 3
# Derivation: scale = target_revenue / (iroas * sqrt(current_spend))
scaling = {
    'tiktok': 180,
    'google': 120,
    'meta':   110,
    'snap':   80,
}

TOTAL_BUDGET = 1_840_000

channel_names = list(channels.keys())


# ── Revenue function ───────────────────────────────────────────────────────
def channel_revenue(spend: float, name: str) -> float:
    """
    Model incremental revenue using square root to capture diminishing returns.

    revenue = iROAS × scaling_factor × √spend

    Why square root?
    - Spend 4x → output only 2x (√4 = 2)
    - Spend 9x → output only 3x (√9 = 3)
    - Each additional euro returns less than the previous one
    """
    iroas = channels[name]['iroas']
    scale = scaling[name]
    return iroas * scale * np.sqrt(spend)


def total_revenue(spend_array: np.ndarray) -> float:
    """Sum of incremental revenue across all channels."""
    return sum(channel_revenue(spend_array[i], channel_names[i])
               for i in range(len(channel_names)))


# ── Objective function ─────────────────────────────────────────────────────
def objective(spend_array: np.ndarray) -> float:
    """
    Negate total revenue because scipy.minimize minimises.
    Minimising -revenue = Maximising revenue.
    """
    return -total_revenue(spend_array)


# ── Constraints and bounds ─────────────────────────────────────────────────
constraints = [
    {
        'type': 'eq',
        'fun': lambda x: sum(x) - TOTAL_BUDGET  # Total spend must equal budget
    }
]

bounds = [
    (channels[name]['min'], channels[name]['max'])
    for name in channel_names
]

# Starting point: current spend allocation
x0 = np.array([channels[name]['current'] for name in channel_names])


# ── Run optimiser ──────────────────────────────────────────────────────────
result = minimize(
    objective,
    x0,
    method='SLSQP',        # Sequential Least Squares Programming
    bounds=bounds,
    constraints=constraints,
    options={'ftol': 1e-9, 'maxiter': 1000}
)

if not result.success:
    print(f"WARNING: Optimiser did not converge — {result.message}")


# ── Print results ──────────────────────────────────────────────────────────
print("=" * 65)
print(f"{'UrbanCart Budget Optimiser — Results':^65}")
print("=" * 65)
print(f"\n{'Channel':<10} {'Current':>10} {'Optimal':>10} {'Change':>10} {'iROAS':>7}")
print("-" * 55)

for i, name in enumerate(channel_names):
    current = channels[name]['current']
    optimal = result.x[i]
    change  = ((optimal - current) / current) * 100
    iroas   = channels[name]['iroas']
    print(f"{name:<10} €{current:>8,.0f} €{optimal:>8,.0f} {change:>+9.1f}%  {iroas:.2f}x")

print("-" * 55)
print(f"{'TOTAL':<10} €{sum(x0):>8,.0f} €{sum(result.x):>8,.0f}")
print()
print(f"{'Current revenue:':30} €{total_revenue(x0):>10,.0f}")
print(f"{'Optimal revenue:':30} €{total_revenue(result.x):>10,.0f}")
improvement = total_revenue(result.x) - total_revenue(x0)
print(f"{'Revenue improvement:':30} €{improvement:>10,.0f} / month")
print("=" * 65)

# ── Marginal ROAS analysis ─────────────────────────────────────────────────
print("\nMarginal ROAS at optimal spend points:")
print("(The return on the NEXT €10,000 added to each channel)")
print("-" * 50)
delta = 10_000
for i, name in enumerate(channel_names):
    opt_spend = result.x[i]
    marginal  = (channel_revenue(opt_spend + delta, name) -
                 channel_revenue(opt_spend, name)) / delta
    print(f"  {name:<10} marginal ROAS = {marginal:.3f}x")
print()
print("At the optimum, marginal ROAS should be approximately equal")
print("across all channels (subject to binding constraints).")
print("TikTok hitting its ceiling means its marginal ROAS is still")
print("higher — a signal to test raising the ceiling.")


# ── Visualisation ──────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('UrbanCart Budget Optimisation Results', fontsize=14, fontweight='bold')

colors_map = {
    'tiktok': '#D85A30',
    'google': '#1D9E75',
    'meta':   '#378ADD',
    'snap':   '#7F77DD'
}
bar_colors = [colors_map[n] for n in channel_names]

x = np.arange(len(channel_names))
width = 0.35

# Chart 1: Spend comparison
ax1 = axes[0]
b1 = ax1.bar(x - width/2, [channels[n]['current']/1000 for n in channel_names],
             width, label='Current', color='#B5D4F4', edgecolor='white')
b2 = ax1.bar(x + width/2, [result.x[i]/1000 for i in range(4)],
             width, label='Optimal', color=bar_colors, edgecolor='white')
ax1.set_title('Budget Allocation')
ax1.set_ylabel('Spend (€000s)')
ax1.set_xticks(x)
ax1.set_xticklabels(channel_names)
ax1.legend()
ax1.grid(axis='y', alpha=0.3)

# Chart 2: Revenue contribution
ax2 = axes[1]
current_revs = [channel_revenue(channels[n]['current'], n)/1000 for n in channel_names]
optimal_revs = [channel_revenue(result.x[i], channel_names[i])/1000 for i in range(4)]
ax2.bar(x - width/2, current_revs, width, label='Current', color='#B5D4F4', edgecolor='white')
ax2.bar(x + width/2, optimal_revs, width, label='Optimal', color=bar_colors, edgecolor='white')
ax2.set_title('Revenue Contribution')
ax2.set_ylabel('Revenue (€000s)')
ax2.set_xticks(x)
ax2.set_xticklabels(channel_names)
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# Chart 3: Diminishing returns curves
ax3 = axes[2]
spend_range = np.linspace(50_000, 800_000, 300)
for name in channel_names:
    rev_curve = [channel_revenue(s, name) / 1000 for s in spend_range]
    ax3.plot(spend_range / 1000, rev_curve,
             label=name, color=colors_map[name], linewidth=2)
    # Mark optimal point
    opt_rev = channel_revenue(result.x[channel_names.index(name)], name) / 1000
    ax3.scatter(result.x[channel_names.index(name)] / 1000, opt_rev,
                color=colors_map[name], s=80, zorder=5)
ax3.set_title('Diminishing Returns Curves')
ax3.set_xlabel('Spend (€000s)')
ax3.set_ylabel('Revenue (€000s)')
ax3.legend(fontsize=8)
ax3.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('module4_budget_optimization.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nChart saved as module4_budget_optimization.png")
