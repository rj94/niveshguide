# Stock Momentum Score Logic

## Overview

This framework calculates a **Momentum Score out of 100** by combining:

| Factor | Weight | Purpose |
|---|---:|---|
| Returns Momentum | 30% | Measures price performance across multiple periods |
| DMA / Trend | 25% | Measures trend strength and moving-average alignment |
| Volume Momentum | 20% | Checks whether price action has volume confirmation |
| Result / Fundamental Momentum | 25% | Measures earnings and business growth |

---

# 1. Returns Momentum — 30 Points

Use multiple return periods instead of relying on a single timeframe.

```text
Return Score =
20% × 1 Month Return Score
+ 30% × 3 Month Return Score
+ 30% × 6 Month Return Score
+ 20% × 12 Month Return Score
```

Each return period should ideally be converted into a **percentile rank** against the entire stock universe.

## Example Scoring

| Percentile Rank | Score |
|---|---:|
| Top 10% | 100 |
| 80–90% | 90 |
| 60–80% | 70 |
| 40–60% | 50 |
| 20–40% | 30 |
| Bottom 20% | 10 |

Final contribution:

```text
Returns Momentum Points = Return Score × 0.30
```

---

# 2. DMA / Trend Score — 25 Points

Use:

- 20 DMA
- 50 DMA
- 200 DMA

## Trend Conditions

```text
Price > 20 DMA
Price > 50 DMA
Price > 200 DMA

20 DMA > 50 DMA
50 DMA > 200 DMA

Price close to 52-week high
```

A strong bullish structure is:

```text
Price > 20 DMA > 50 DMA > 200 DMA
```

## Suggested Raw Scoring

| Condition | Points |
|---|---:|
| Price > 20 DMA | 15 |
| Price > 50 DMA | 20 |
| Price > 200 DMA | 25 |
| 20 DMA > 50 DMA | 15 |
| 50 DMA > 200 DMA | 15 |
| Within 10% of 52-week high | 10 |

Maximum score: **100**

## DMA Distance

Calculate the distance from each moving average:

```text
Distance from DMA =
(Current Price / DMA - 1) × 100
```

Calculate this for:

```text
Distance_20DMA
Distance_50DMA
Distance_200DMA
```

Final contribution:

```text
DMA Momentum Points = DMA Score × 0.25
```

---

# 3. Volume Momentum — 20 Points

Calculate:

```text
Volume Ratio =
Today's Volume / 20-Day Average Volume
```

## Volume Ratio Scoring

| Volume Ratio | Score |
|---|---:|
| > 3x | 100 |
| 2–3x | 85 |
| 1.5–2x | 70 |
| 1–1.5x | 50 |
| < 1x | 20 |

Volume should also be checked against price movement.

```text
If 5-Day Return > 0 AND Volume Ratio > 1.5
→ Positive volume confirmation

If 5-Day Return < 0 AND Volume Ratio > 1.5
→ Possible distribution / negative confirmation
```

Suggested formula:

```text
Volume Score =
60% × Current Volume Ratio Score
+ 40% × 20-Day Positive Volume Trend
```

Final contribution:

```text
Volume Momentum Points = Volume Score × 0.20
```

---

# 4. Result / Fundamental Momentum — 25 Points

Use the latest quarterly results to measure whether the business is improving.

Track:

- Revenue Growth YoY
- PAT Growth YoY
- Revenue Growth QoQ
- PAT Growth QoQ
- Operating Margin Change
- Earnings Acceleration

## Revenue Growth Example

| Revenue Growth | Score |
|---|---:|
| > 30% | 100 |
| 20–30% | 80 |
| 10–20% | 60 |
| 0–10% | 40 |
| < 0% | 10 |

## Suggested Result Score Formula

```text
Result Score =
25% × Revenue Growth
+ 30% × PAT Growth
+ 20% × Margin Trend
+ 15% × QoQ Growth
+ 10% × Earnings Acceleration
```

Earnings acceleration can identify companies where growth is improving:

```text
If Current Quarter PAT Growth > Previous Quarter PAT Growth
→ Positive Earnings Acceleration
```

Final contribution:

```text
Result Momentum Points = Result Score × 0.25
```

---

# 5. Final Momentum Score

```text
MOMENTUM SCORE =

(Return Score × 0.30)
+ (DMA Score × 0.25)
+ (Volume Score × 0.20)
+ (Result Score × 0.25)
```

## Example

| Component | Raw Score | Weight | Weighted Points |
|---|---:|---:|---:|
| Returns | 90 | 30% | 27.00 |
| DMA Trend | 85 | 25% | 21.25 |
| Volume | 70 | 20% | 14.00 |
| Results | 80 | 25% | 20.00 |
| **Final Momentum Score** | | | **82.25 / 100** |

---

# 6. Momentum Classification

| Score | Category | Interpretation |
|---|---|---|
| 85–100 | 🚀 Strong Momentum | Price, volume and fundamentals strongly aligned |
| 70–85 | 🟢 Positive Momentum | Strong momentum candidate |
| 55–70 | 🟡 Emerging Momentum | Momentum developing; worth monitoring |
| 40–55 | ⚪ Neutral | No clear momentum edge |
| 20–40 | 🟠 Weak | Momentum deteriorating |
| 0–20 | 🔴 Negative | Weak trend / bearish characteristics |

---

# 7. Momentum Acceleration

A stock can have a high momentum score but slowing momentum. Therefore, also calculate the change in momentum over time.

```text
Momentum Acceleration =
Current Momentum Score
- Momentum Score 20 Trading Days Ago
```

Example:

```text
Current Score = 78
Score 20 Trading Days Ago = 58

Momentum Acceleration = +20
```

## Suggested Interpretation

| Acceleration | Meaning |
|---|---|
| > +15 | Rapidly improving momentum |
| +5 to +15 | Improving |
| -5 to +5 | Stable |
| -5 to -15 | Weakening |
| < -15 | Rapid deterioration |

---

# 8. Suggested Database / Spreadsheet Structure

```text
Symbol
Company Name
Market Cap
LTP

Return_1M
Return_3M
Return_6M
Return_12M
Return_Score

DMA_20
DMA_50
DMA_200

Distance_20DMA
Distance_50DMA
Distance_200DMA

Price_vs_52W_High
Trend_Score

Volume_Today
Volume_Avg_20D
Volume_Ratio
Positive_Volume_Days_20D
Volume_Score

Revenue_Growth_YoY
PAT_Growth_YoY

Revenue_Growth_QoQ
PAT_Growth_QoQ

Operating_Margin_Current
Operating_Margin_Previous
Margin_Change

Earnings_Acceleration
Result_Score

Momentum_Score
Momentum_Score_20D_Ago
Momentum_Acceleration

Momentum_Category
```

---

# 9. Recommended Improvements

## Relative Strength vs Benchmark

Add stock performance against Nifty or the relevant sector index.

```text
Relative Strength =
Stock Return - Benchmark Return
```

A stock rising 10% when the market rises 15% is weaker than a stock rising 8% when the market is flat.

## 52-Week High Proximity

```text
52W High Distance =
(Current Price / 52W High - 1) × 100
```

Stocks near their 52-week highs often demonstrate stronger momentum than stocks recovering from deep drawdowns.

## Sector Momentum

Calculate:

```text
Sector Return
Sector Relative Strength
Sector Momentum Score
```

Strong stocks in strong sectors can receive an additional score or ranking advantage.

## Delivery and Institutional Activity

Future versions can include:

- Delivery percentage
- Delivery volume trend
- Mutual fund holding changes
- FII holding changes
- Promoter holding changes

---

# 10. Recommended Version 2 Formula

For a more robust screener:

```text
TOTAL MOMENTUM SCORE =

25% Returns
+ 20% DMA Trend
+ 15% Volume
+ 20% Results
+ 10% Relative Strength
+ 5% 52W High Proximity
+ 5% Momentum Acceleration
```

This version combines:

**Price + Trend + Volume + Fundamentals + Relative Strength + Acceleration**

The key principle is to calculate as many factors as possible using **percentile rankings against the complete stock universe** rather than fixed thresholds. This makes the scoring system adaptive to different market conditions.

---

# Implementation Notes

1. Calculate raw metrics for every stock.
2. Convert comparable metrics into percentile ranks from 0–100.
3. Apply component weights.
4. Calculate the final Momentum Score.
5. Store historical daily scores.
6. Calculate Momentum Acceleration using historical scores.
7. Rank stocks by both `Momentum_Score` and `Momentum_Acceleration`.

A useful screener can then filter for:

```text
Momentum Score > 70
AND Momentum Acceleration > 5
AND Price > 50 DMA
AND Price > 200 DMA
AND Volume Ratio > 1
```

This can identify stocks with both **strong existing momentum** and **improving momentum**.
