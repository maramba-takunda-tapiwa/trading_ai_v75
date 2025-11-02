"""
Risk Limits Recommendation based on Monte Carlo Results
Saves to results/risk_limits_recommendation.txt
"""

import pandas as pd
from pathlib import Path

root = Path(r"c:\Users\maram\trading_ai_v75")
results_dir = root / 'results'

# Read baseline Monte Carlo (1000 sims)
baseline_mc = pd.read_csv(results_dir / 'monte_carlo_results_block.csv')

# Read improved config validation (150 sims on REOPT_2)
validation = pd.read_csv(results_dir / 'monte_carlo_validation.csv')
reopt2 = validation[validation['config'] == 'REOPT_2'].iloc[0]

# Compute percentiles
maxdd_p75 = baseline_mc['max_dd'].quantile(0.75)
maxdd_p90 = baseline_mc['max_dd'].quantile(0.90)
maxdd_p95 = baseline_mc['max_dd'].quantile(0.95)

loss_p25 = baseline_mc['profit'].quantile(0.25)
loss_p10 = baseline_mc['profit'].quantile(0.10)
loss_p05 = baseline_mc['profit'].quantile(0.05)

# Recommendation doc
doc = []
doc.append("="*70)
doc.append("RISK LIMITS RECOMMENDATION")
doc.append("Based on Monte Carlo robustness testing (1000 sims baseline)")
doc.append("and improved config validation (REOPT_2: 150 sims)")
doc.append("="*70)
doc.append("")

doc.append("1. RECOMMENDED LIVE TRADING PARAMETERS")
doc.append("-" * 70)
doc.append("Use REOPT_2 configuration instead of baseline:")
doc.append(f"  Breakout Length: 35 (was 30)")
doc.append(f"  ATR Stop Multiplier: 0.3 (was 0.5) <- more sensitive stops")
doc.append(f"  ATR TP Multiplier: 4.0 (unchanged)")
doc.append(f"  Risk per Trade: 0.5% (unchanged)")
doc.append("")
doc.append(f"Improvement over baseline:")
doc.append(f"  - PF: {reopt2['pf_mean']:.3f} vs 0.981 baseline (+{(reopt2['pf_mean']/0.981-1)*100:.1f}%)")
doc.append(f"  - Win Rate: {reopt2['pf_gt1_pct']:.1f}% vs 41.3% baseline (+{reopt2['pf_gt1_pct']-41.3:.1f}pp)")
doc.append(f"  - Profit Mean: ${reopt2['profit_mean']:.0f} vs $93 baseline (+{(reopt2['profit_mean']/93-1)*100:.0f}%)")
doc.append("")

doc.append("2. RECOMMENDED LIVE RISK LIMITS (for demo/live account)")
doc.append("-" * 70)
doc.append("Set these absolute limits in live_trader_saxo.py:")
doc.append("")
doc.append(f"MAX_DRAWDOWN (hard stop):")
doc.append(f"  Conservative:     {int(maxdd_p75):,}  (75th percentile from baseline MC)")
doc.append(f"  Moderate:         {int(maxdd_p90):,}  (90th percentile)")
doc.append(f"  Aggressive:       {int(maxdd_p95):,}  (95th percentile)")
doc.append(f"  -> RECOMMENDED:   {int(maxdd_p75):,}")
doc.append("")
doc.append(f"DAILY_LOSS_FREEZE (daily loss limit):")
doc.append(f"  Set to:  {int(abs(loss_p25)*0.5):,}  (half of 25th percentile daily loss)")
doc.append(f"  Rationale: 25th percentile loss is {int(abs(loss_p25)):,}; set freeze at {int(abs(loss_p25)*0.5):,}")
doc.append("")

doc.append("3. INTERPRETATION (per-sim statistics, baseline MC 1000 sims)")
doc.append("-" * 70)
doc.append(f"Max Drawdown (per simulation):")
doc.append(f"  Mean: {baseline_mc['max_dd'].mean():.0f}")
doc.append(f"  Median: {baseline_mc['max_dd'].median():.0f}")
doc.append(f"  75th percentile: {maxdd_p75:.0f}")
doc.append(f"  95th percentile: {maxdd_p95:.0f}")
doc.append("")
doc.append(f"Profit per simulation:")
doc.append(f"  Mean: {baseline_mc['profit'].mean():.0f}")
doc.append(f"  Median: {baseline_mc['profit'].median():.0f}")
doc.append(f"  25th percentile (bad scenarios): {loss_p25:.0f}")
doc.append(f"  5th percentile (worst 5%): {loss_p05:.0f}")
doc.append("")

doc.append("4. INTERPRETATION (session duration)")
doc.append("-" * 70)
doc.append("Note: each 'sim' is a resampled full historical dataset (~3 months EUR/USD).")
doc.append("In live trading, you may experience drawdowns approaching or exceeding")
doc.append(f"the recommended MAX_DRAWDOWN limit ({int(maxdd_p75):,}) depending on market regime.")
doc.append("The DAILY_LOSS_FREEZE provides additional circuit-breaker protection.")
doc.append("")

doc.append("5. NEXT STEPS FOR LIVE DEPLOYMENT")
doc.append("-" * 70)
doc.append("1. Update live_trader_saxo.py with:")
doc.append(f"   - New strategy params: breakout_length=35, atr_stop_multiplier=0.3")
doc.append(f"   - MAX_DRAWDOWN = {int(maxdd_p75):,}")
doc.append(f"   - DAILY_LOSS_FREEZE = {int(abs(loss_p25)*0.5):,}")
doc.append("")
doc.append("2. Confirm demo account starting equity; scale limits proportionally if different.")
doc.append("3. Run a 24-48 hour live-demo validation with these settings.")
doc.append("4. Monitor logs in results/live_* files; look for patterns in drawdowns and daily losses.")
doc.append("5. If consistent with Monte Carlo expectations, proceed to live (or keep demo longer).")
doc.append("")

# Write file
doc_text = "\n".join(doc)
out_path = results_dir / 'risk_limits_recommendation.txt'
out_path.write_text(doc_text)

print(doc_text)
print(f"\nRecommendation saved to {out_path}")

# Return values for live trader update
print("\n" + "="*70)
print("VALUES TO SET IN live_trader_saxo.py:")
print(f"  breakout_length = 35")
print(f"  atr_stop_multiplier = 0.3")
print(f"  MAX_DRAWDOWN = {int(maxdd_p75)}")
print(f"  DAILY_LOSS_FREEZE = {int(abs(loss_p25)*0.5)}")
