# plot_optimization_heatmap.py
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

# Load results
file = Path(__file__).resolve().parents[1] / "data" / "optimization_results.csv"
df = pd.read_csv(file)

# Optional: round multipliers for cleaner axis grouping
df["SL"] = df["atr_sl_mult"].round(2)
df["TP"] = df["atr_tp_mult"].round(2)
df["BO"] = df["breakout_len"].astype(int)

# Pivot for heatmap
pivot_pf = df.pivot_table(index="TP", columns="BO", values="profit_factor")
pivot_exp = df.pivot_table(index="TP", columns="BO", values="expectancy")

plt.figure(figsize=(12, 5))
sns.heatmap(pivot_pf, annot=True, fmt=".2f", cmap="YlGnBu", cbar_kws={"label": "Profit Factor"})
plt.title("📈 Profit Factor Heatmap (Breakout vs TP)")
plt.ylabel("TP Multiplier")
plt.xlabel("Breakout Length")
plt.tight_layout()
plt.show()

# Optional: show expectancy map
plt.figure(figsize=(12, 5))
sns.heatmap(pivot_exp, annot=True, fmt=".3f", cmap="OrRd", cbar_kws={"label": "Expectancy (R/trade)"})
plt.title("💡 Expectancy Heatmap (Breakout vs TP)")
plt.ylabel("TP Multiplier")
plt.xlabel("Breakout Length")
plt.tight_layout()
plt.show()
