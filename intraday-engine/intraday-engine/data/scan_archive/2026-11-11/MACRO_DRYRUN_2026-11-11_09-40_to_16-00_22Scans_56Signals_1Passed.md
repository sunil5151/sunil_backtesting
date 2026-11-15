# AWS S3 MACRO COMPILED DRY-TESTING REPORT — 2026-11-11 (09:40 to 16:00 IST)

> **Mode:** `DRYRUN` | **Testing Date:** `2026-11-11` | **Window:** `09:40 IST` to `16:00 IST` | **S3 Bucket:** `sunil-trading-signals` (`ap-south-2`)

## Architecture, File Naming & Strategy Configuration

- **Macro PDF File (Compiled):** `scans/2026-11-11/MACRO_DRYRUN_2026-11-11_09-40_to_16-00_22Scans_56Signals_1Passed.pdf`
- **Macro Markdown File (Compiled):** `scans/2026-11-11/MACRO_DRYRUN_2026-11-11_09-40_to_16-00_22Scans_56Signals_1Passed.md`
- **Micro S3 Files (Alag-Alag Har 5m Candle):** `scans/2026-11-11/<HH-MM>_Scan_72Stocks_<S>Signals_<P>Passed.json` (Total `22` Micro JSON files)
- **Live vs Dry Testing Rule:** Live trading candle-by-candle real time chalta hai, isliye live me sirf Micro files banti hain (Macro nahi). Dry Testing me poora date + time period replay hota hai, isliye Micro files ke saath ye Macro `.md` + `.pdf` files banti hain.
- **Context Note:** 2026-11-13 (52 scans, 101 signals, 0 WOULD TRADE) bhi separate Giant Macro PDF + MD me compiled hai.

### Strategy: `pdh_breakout` (`strategies/pdh_breakout.py`)

- **Timeframe / Lookback:** `5m` | Lookback `50` bars | Sides `LONG, SHORT` | Active Regimes `TREND_UP, TREND_DOWN` (`CHOPPY` blocked)
- **Strategy Params:** `vwap_filter=True`, `buffer_pct=0.001`, `vol_mult=1.5x`, `rvol_min=1.0x`, `max_chase_atr=0.5`, `min_stop_pct=0.006`, `max_stop_pct=0.015`, `target_r=1:2.0`, `breakeven_at_r=+1.0R`
- **Risk Rules:** Capital `Rs.50,000` | Product `MIS` (`5.0x`) | Risk/Trade `Rs.500` (Min `Rs.300`) | Notional Cap `Rs.83,333` | Max Open `3` | Max/Sector `2` | Max/Day `6` | Daily Loss Limit `Rs.1,500`

## 1. Macro Executive Summary & 8-Check Bottleneck Analysis

| Metric | Value | Metric | Value |
| :--- | :--- | :--- | :--- |
| Testing Date & Window | 2026-11-11 (09:40 - 16:00 IST) | Micro S3 Scans Compiled | 22 JSON files (72 kept stocks/scan) |
| Total Signals Evaluated | 56 signals | Passed (WOULD TRADE) | 1 signal(s) (1.8%) |
| Rejected Signals | 55 signals (98.2%) | Regimes Observed | TREND_UP:20, CHOPPY:2 |

### Simulated Trade Execution & Outcome

- Trade Event: [Dry run 2026-11-11] 12:05 OPENED LONG BHARATFORG x47 @ ₹1750.20 (SL ₹1739.70, Tgt ₹1771.20, R:R 1:2.00)
- Trade Event: [Dry run 2026-11-11] 13:10 CLOSED LONG BHARATFORG (STOP) In ₹1750.20 → Out ₹1739.70 | Net ₹-577.61 (-1.00R)
- Session Summary Log: Dry run complete for 2026-11-11 (09:15–15:30): 75 bars, 1 would trade, 55 rejected | Trades: 1, Net P&L: ₹-577.61 (-1.16R). Bars discarded.
- Session Summary Log: Dry run complete for 2026-11-11: 81 bars, 1 would trade, 55 rejected. Bars discarded.

### Time-of-Day Breakdown (IST)

| Time Period (IST) | S3 Scans | Signals Eval | Passed | Rejected | Pass % |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Morning (09:15 - 11:30) | 10 | 26 | 0 | 26 | 0.0% |
| Midday (11:30 - 13:30) | 10 | 30 | 1 | 29 | 3.3% |
| Afternoon (13:30 - 15:30) | 1 | 0 | 0 | 0 | 0.0% |
| Post-Close (> 15:30) | 1 | 0 | 0 | 0 | 0.0% |

### 8-Check Bottleneck Analysis (All Signals Combined)

| Step | Check Name | Passed | Failed | Pass % | Kya Samjha (Bottleneck Insight) |
| :---: | :--- | ---: | ---: | ---: | :--- |
| #1 | Market Regime | 56 | 0 | 100.0% | 100% pass - koi rukawat nahi aayi |
| #2 | Sector Strength | 56 | 0 | 100.0% | 100% pass - koi rukawat nahi aayi |
| #3 | Breakout Candle | 56 | 0 | 100.0% | 100% pass - koi rukawat nahi aayi |
| #4 | VWAP Filter | 44 | 12 | 78.6% | Moderate filter (12 fails: 12 <=14:15, 0 >14:15) |
| #5 | 5m Slot Volume | 28 | 28 | 50.0% | Moderate filter (28 fails: 28 <=14:15, 0 >14:15) |
| #6 | Day RVOL | 40 | 16 | 71.4% | Moderate filter (16 fails: 16 <=14:15, 0 >14:15) |
| #7 | Gap, No-Chase & Stop Risk | 16 | 40 | 28.6% | Moderate filter (40 fails: 40 <=14:15, 0 >14:15) |
| #8 | Sizing & Risk Gate | 1 | 55 | 1.8% | MAIN BOTTLENECK (55 fails: 55 <=14:15, 0 >14:15) |

## 2. Market Regime Dissection — Engine Ne Market Ko 'Kya Samjha' Aur 'Kyun Samjha'

### Box A: Engine Ka Current Formula / Approach (`engine/regime.py` + `config.yaml`)

1. **ADX(14) on 5m NIFTY:** Agar `ADX < 20` ho → Weak Trend / Choppy Vote #1.
2. **Session Mean & Crosses(12):** Typical Price `(H+L+C)/3` ka expanding mean from `09:15`. Last 12 bars me close `>= 4` baar Session Mean cross kare → Choppy Vote #2.
3. **Universe Breadth (Adv/Dec vs PDC):** Agar `0.80 <= Breadth <= 1.25` ho → Choppy Vote #3 (`>1.0` Bullish, `<1.0` Bearish).
4. **Decision Rule:** Agar `>= 2` Choppy Votes lage → `Raw = CHOPPY`. Warna agar `NIFTY Close > Session Mean & Breadth > 1.0` → `Raw = TREND_UP`; agar `NIFTY Close < Session Mean & Breadth < 1.0` → `Raw = TREND_DOWN`; warna (dono disagree karein) → `Raw = CHOPPY`.
5. **2-Bar Confirmation:** Active Regime tabhi badalta hai jab naya Raw Regime lagatar `2` consecutive 5m bars (`confirm_bars=2`) par aaye.

### Box B: Real Data Se Nikle Key Approach Insights (Baad Me Tune Karne Ke Liye)

- 1. Low-ADX Trend Calls: Is period me 0/22 scans me ADX(14) < 20 tha, fir bhi engine ne market ko TREND mana (kyunki Crosses < 4 aur Breadth 0.80-1.25 ke bahar tha, so sirf 1/3 choppy vote laga).
- 2. Raw vs Active (2-Bar Delay): 1/22 scans me Raw Regime Active Regime se alag tha (12:15 (TREND_UP vs raw CHOPPY)).
- 3. 'Else' Branch CHOPPY Triggers: 3/22 scans me Choppy Votes < 2 hone ke bawajood Raw=CHOPPY aaya kyunki NIFTY Close Session Mean ke doosri taraf gaya jabki Breadth alag side thi (12:15, 15:30, 16:00).
- 4. Note on Missing Bar Gaps: Jahan 5m bar par 0 stocks ARMED the (ya regime CHOPPY tha), wahan S3 me alag signal-scan JSON save nahi hota (isliye activity feed me unka summary dikhta hai, aur last bar hamesha save hota hai).

| Time | NIFTY% | ADX14 | SessMean | Cross | Breadth (A/D) | Kya Samjha | Kyun Samjha (Exact Inputs & Rule) |
| :---: | ---: | ---: | ---: | :---: | :---: | :--- | :--- |
| 09:40 | +1.40% | 48.10 | 25353.9 | 2 | 4.538 (59/13) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25353.9) & Breadth 4.538 > 1.0 -> Raw=TREND_UP. |
| 09:45 | +1.47% | 50.50 | 25362.8 | 2 | 4.538 (59/13) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25362.81) & Breadth 4.538 > 1.0 -> Raw=TREND_UP. |
| 09:50 | +1.43% | 52.76 | 25369.4 | 2 | 4.917 (59/12) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25369.4) & Breadth 4.917 > 1.0 -> Raw=TREND_UP. |
| 10:55 | +1.29% | 51.81 | 25361.8 | 1 | 3.176 (54/17) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25361.85) & Breadth 3.176 > 1.0 -> Raw=TREND_UP. |
| 11:00 | +1.34% | 51.99 | 25362.6 | 1 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25362.59) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 11:05 | +1.35% | 52.17 | 25363.4 | 1 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25363.38) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 11:10 | +1.34% | 52.35 | 25364.2 | 1 | 3.235 (55/17) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25364.19) & Breadth 3.235 > 1.0 -> Raw=TREND_UP. |
| 11:15 | +1.32% | 51.93 | 25364.7 | 1 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25364.67) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 11:20 | +1.35% | 51.86 | 25365.4 | 1 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25365.37) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 11:25 | +1.33% | 51.79 | 25365.9 | 1 | 2.737 (52/19) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25365.94) & Breadth 2.737 > 1.0 -> Raw=TREND_UP. |
| 11:30 | +1.28% | 51.09 | 25366.1 | 1 | 2.381 (50/21) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25366.13) & Breadth 2.381 > 1.0 -> Raw=TREND_UP. |
| 11:35 | +1.37% | 50.66 | 25366.6 | 1 | 2.737 (52/19) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25366.62) & Breadth 2.737 > 1.0 -> Raw=TREND_UP. |
| 11:40 | +1.37% | 50.28 | 25367.3 | 1 | 2.944 (53/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25367.35) & Breadth 2.944 > 1.0 -> Raw=TREND_UP. |
| 11:45 | +1.35% | 49.99 | 25368.0 | 0 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25367.99) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 11:50 | +1.38% | 49.65 | 25368.6 | 0 | 3.235 (55/17) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25368.59) & Breadth 3.235 > 1.0 -> Raw=TREND_UP. |
| 11:55 | +1.34% | 49.26 | 25369.0 | 0 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25369.05) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 12:00 | +1.39% | 48.30 | 25369.5 | 0 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25369.55) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 12:05 | +1.37% | 47.41 | 25370.1 | 0 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25370.09) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 12:10 | +1.32% | 45.54 | 25370.3 | 0 | 3.000 (54/18) | Active: TREND_UP<br>(Raw: TREND_UP) | Choppy 0/3 (<2); NIFTY > SessMean (25370.31) & Breadth 3.0 > 1.0 -> Raw=TREND_UP. |
| 12:15 | +1.11% | 43.36 | 25369.5 | 1 | 2.789 (53/19) | Active: TREND_UP<br>(Raw: CHOPPY) | Choppy 0/3 (<2), par NIFTY Close slipped below SessMean 25369.46 while Breadth 2.789 > 1.0 -> 'else' branch se Raw=CHOPPY. [2-Bar Confirm: Raw CHOPPY abhi 1st bar pe hai, isliye Active TREND_UP raha] |
| 15:30 | +0.84% | 34.19 | 25298.9 | 0 | 1.731 (45/26) | Active: CHOPPY<br>(Raw: CHOPPY) | Choppy 0/3 (<2), par NIFTY Close slipped below SessMean 25298.93 while Breadth 1.731 > 1.0 -> 'else' branch se Raw=CHOPPY. |
| 16:00 | +0.84% | 26.60 | 25295.7 | 0 | 1.731 (45/26) | Active: CHOPPY<br>(Raw: CHOPPY) | Choppy 0/3 (<2), par NIFTY Close slipped below SessMean 25295.68 while Breadth 1.731 > 1.0 -> 'else' branch se Raw=CHOPPY. |

## 3. Sector Rotation Dissection — Engine Ne Sectors Ko 'Kya Samjha' Aur 'Kyun Samjha'

> `Sector Return % = median(member return vs PDC)` | `RS % = Sector Return % - NIFTY %` | `Top-3 > +0.25% = STRONG`, `Bottom-3 < -0.25% = WEAK`.

| Sector (Eligible) | STRONG Scans | WEAK Scans | NEUTRAL Scans | RS % Range (Period) | Avg RS % |
| :--- | ---: | ---: | ---: | :---: | ---: |
| PSU Bank | 22 | 0 | 0 | +0.47% to +2.44% | +1.83% |
| Pvt Bank | 19 | 0 | 3 | +0.03% to +1.27% | +0.87% |
| FMCG | 7 | 0 | 15 | -0.42% to +0.95% | +0.20% |
| Auto | 1 | 0 | 21 | -0.54% to +0.56% | +0.07% |
| Metal | 0 | 0 | 22 | -0.51% to +0.14% | -0.21% |
| Energy | 0 | 0 | 22 | -0.69% to -0.06% | -0.34% |
| IT | 0 | 22 | 0 | -1.79% to -0.65% | -1.48% |
| Pharma | 0 | 22 | 0 | -2.09% to -0.96% | -1.73% |
| Realty | 0 | 22 | 0 | -2.10% to -1.06% | -1.75% |

### Sector Snapshot @ 09:40 IST | Regime: `TREND_UP` | NIFTY: `+1.40%`

| Rank | Sector | Stocks | Med Ret% | RS % | Kya Samjha | Kyun Samjha (RS Formula & Cut) |
| :---: | :--- | ---: | ---: | ---: | :---: | :--- |
| #1 | PSU Bank | 7 | +1.99% | +0.59% | STRONG | Rank #1 (Top-3) & RS +0.59% > +0.25% (Ret +1.99% vs NIFTY +1.40%) -> STRONG (LONG allowed) |
| #2 | Pvt Bank | 9 | +1.45% | +0.05% | NEUTRAL | Rank #2, RS +0.05% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #3 | Metal | 9 | +1.17% | -0.23% | NEUTRAL | Rank #3, RS -0.23% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #4 | FMCG | 10 | +0.98% | -0.42% | NEUTRAL | Rank #4, RS -0.42% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #5 | Auto | 6 | +0.88% | -0.52% | NEUTRAL | Rank #5, RS -0.52% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #6 | Energy | 9 | +0.85% | -0.55% | NEUTRAL | Rank #6, RS -0.55% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #7 | IT | 9 | +0.69% | -0.71% | WEAK | Rank #7 (Bottom-3) & RS -0.71% < -0.25% (Ret +0.69% vs NIFTY +1.40%) -> WEAK (SHORT allowed) |
| #8 | Realty | 6 | +0.14% | -1.26% | WEAK | Rank #8 (Bottom-3) & RS -1.26% < -0.25% (Ret +0.14% vs NIFTY +1.40%) -> WEAK (SHORT allowed) |
| #9 | Pharma | 7 | -0.33% | -1.73% | WEAK | Rank #9 (Bottom-3) & RS -1.73% < -0.25% (Ret -0.33% vs NIFTY +1.40%) -> WEAK (SHORT allowed) |

### Sector Snapshot @ 12:05 IST | Regime: `TREND_UP` | NIFTY: `+1.37%`

| Rank | Sector | Stocks | Med Ret% | RS % | Kya Samjha | Kyun Samjha (RS Formula & Cut) |
| :---: | :--- | ---: | ---: | ---: | :---: | :--- |
| #1 | PSU Bank | 7 | +3.66% | +2.29% | STRONG | Rank #1 (Top-3) & RS +2.29% > +0.25% (Ret +3.66% vs NIFTY +1.37%) -> STRONG (LONG allowed) |
| #2 | Pvt Bank | 9 | +2.21% | +0.84% | STRONG | Rank #2 (Top-3) & RS +0.84% > +0.25% (Ret +2.21% vs NIFTY +1.37%) -> STRONG (LONG allowed) |
| #3 | Auto | 6 | +1.71% | +0.34% | STRONG | Rank #3 (Top-3) & RS +0.34% > +0.25% (Ret +1.71% vs NIFTY +1.37%) -> STRONG (LONG allowed) |
| #4 | FMCG | 10 | +1.62% | +0.25% | NEUTRAL | Rank #4, RS +0.25% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #5 | Metal | 9 | +1.51% | +0.14% | NEUTRAL | Rank #5, RS +0.14% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #6 | Energy | 9 | +1.31% | -0.06% | NEUTRAL | Rank #6, RS -0.06% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #7 | IT | 9 | -0.38% | -1.75% | WEAK | Rank #7 (Bottom-3) & RS -1.75% < -0.25% (Ret -0.38% vs NIFTY +1.37%) -> WEAK (SHORT allowed) |
| #8 | Pharma | 7 | -0.57% | -1.94% | WEAK | Rank #8 (Bottom-3) & RS -1.94% < -0.25% (Ret -0.57% vs NIFTY +1.37%) -> WEAK (SHORT allowed) |
| #9 | Realty | 6 | -0.58% | -1.95% | WEAK | Rank #9 (Bottom-3) & RS -1.95% < -0.25% (Ret -0.58% vs NIFTY +1.37%) -> WEAK (SHORT allowed) |

### Sector Snapshot @ 16:00 IST | Regime: `CHOPPY` | NIFTY: `+0.84%`

| Rank | Sector | Stocks | Med Ret% | RS % | Kya Samjha | Kyun Samjha (RS Formula & Cut) |
| :---: | :--- | ---: | ---: | ---: | :---: | :--- |
| #1 | PSU Bank | 7 | +3.28% | +2.44% | STRONG | Rank #1 (Top-3) & RS +2.44% > +0.25% (Ret +3.28% vs NIFTY +0.84%) -> STRONG (LONG allowed) |
| #2 | FMCG | 10 | +1.79% | +0.95% | STRONG | Rank #2 (Top-3) & RS +0.95% > +0.25% (Ret +1.79% vs NIFTY +0.84%) -> STRONG (LONG allowed) |
| #3 | Pvt Bank | 9 | +1.75% | +0.91% | STRONG | Rank #3 (Top-3) & RS +0.91% > +0.25% (Ret +1.75% vs NIFTY +0.84%) -> STRONG (LONG allowed) |
| #4 | Auto | 6 | +1.40% | +0.56% | NEUTRAL | Rank #4, RS +0.56% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #5 | Metal | 9 | +0.72% | -0.12% | NEUTRAL | Rank #5, RS -0.12% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #6 | Energy | 9 | +0.56% | -0.28% | NEUTRAL | Rank #6, RS -0.28% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #7 | Pharma | 7 | -0.12% | -0.96% | WEAK | Rank #7 (Bottom-3) & RS -0.96% < -0.25% (Ret -0.12% vs NIFTY +0.84%) -> WEAK (SHORT allowed) |
| #8 | IT | 9 | -0.85% | -1.69% | WEAK | Rank #8 (Bottom-3) & RS -1.69% < -0.25% (Ret -0.85% vs NIFTY +0.84%) -> WEAK (SHORT allowed) |
| #9 | Realty | 6 | -1.26% | -2.10% | WEAK | Rank #9 (Bottom-3) & RS -2.10% < -0.25% (Ret -1.26% vs NIFTY +0.84%) -> WEAK (SHORT allowed) |

## 4. Scanner Funnel & Complete 72-Stock Dissection ('Kya Samjha' & 'Kyun Samjha')

> Showing active TREND scan @ 12:05 (kyunki closing scan @ 16:00 par Regime CHOPPY hone se saare 72 stocks REGIME_CHOPPY stage me the).

- **Funnel @ 12:05:** Universe `104` -> Kept `72` (Dropped `32`) -> Sector Filtered `50` -> Far (>0.5 ATR) `18` -> Outside Top-5 `0` -> Shortlisted `4` -> Armed `2` -> Evaluated `2` (`1` Passed)
- **Most Frequently ARMED Stocks (22 Scans):** INDUSINDBK (16x), ICICIBANK (8x), KOTAKBANK (8x), DABUR (5x), ITC (5x), UBL (5x), UNIONBANK (3x), CANBK (2x), BANDHANBNK (2x), MARICO (1x), BHARATFORG (1x)
- **Most Frequently SHORTLISTED (Near Arm) Stocks:** TATACONSUM (5x), ICICIBANK (4x), BALKRISIND (1x)

| Try# | Symbol (Sector) | Stage (Kya) | Levels (Rs.) | Kyun Samjha (Why Taken / Why Not Taken) + Min Condition |
| :---: | :--- | :---: | :--- | :--- |
| #1 | BHARATFORG<br>(Auto: STRONG) | ARMED | LTP: 1750.20<br>PDH: 1736.0<br>PDL: 1711.6<br>ATR: 52.16 | PASSED (8/8 checks): Entry signal pass hua (LONG breakout: vol 2.5x slot, RVOL 1.00, stop 0.60%, R:R 1:2.0).<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1736.00 ke 0.5 ATR (₹26.08) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1734.26) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #2 | INDUSINDBK<br>(Pvt Bank: STRONG) | ARMED | LTP: 914.75<br>PDH: 904.85<br>PDL: 886.85<br>ATR: 25.94 | ARMED par Signal REJECTED (5/8 checks pass, 3 fail): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 63,828 shares (1.5x of 5-day avg 42,552) chahiye tha, par actual sirf 48,722 (1.14x) aaya. \| #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha \| #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 63,828 shares (1.5x of 5-day avg 42,552) chahiye tha, par actual sirf 48,722 (1.14x) aaya. \| Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹904.85 ke 0.5 ATR (₹12.97) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹903.95) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #3 | BALKRISIND<br>(Auto: STRONG) | SHORTLIST | LTP: 2360.00<br>PDH: 2368.7<br>PDL: 2321.1<br>ATR: 65.92 | Top-5 Shortlist me tha (Score 0.93, Prox 0.132 ATR), par Armed nahi hua kyunki LTP ₹2360.00 abhi arm level (>= ₹2366.33) tak nahi pahuncha.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2368.70 ke 0.5 ATR (₹32.96) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2366.33) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #4 | ICICIBANK<br>(Pvt Bank: STRONG) | SHORTLIST | LTP: 1585.30<br>PDH: 1592.0<br>PDL: 1572.3<br>ATR: 31.34 | Top-5 Shortlist me tha (Score -1.0, Prox 0.214 ATR), par Armed nahi hua kyunki LTP ₹1585.30 abhi arm level (>= ₹1590.41) tak nahi pahuncha.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1592.00 ke 0.5 ATR (₹15.67) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1590.41) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #5 | ASHOKLEY<br>(Auto: STRONG) | FAR_FROM_LEVEL | LTP: 175.64<br>PDH: 178.83<br>PDL: 173.3<br>ATR: 5.14 | Breakout level (PDH ₹178.83) se bahut door tha: Actual distance 0.62 ATR (₹3.19), jabki Shortlist ke liye <= 0.50 ATR (<= ₹2.57) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹178.83 ke 0.5 ATR (₹2.57) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹178.65) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #6 | AUBANK<br>(Pvt Bank: STRONG) | FAR_FROM_LEVEL | LTP: 962.35<br>PDH: 930.5<br>PDL: 911.2<br>ATR: 29.82 | Breakout level (PDH ₹930.50) se bahut door tha: Actual distance 1.07 ATR (₹31.85), jabki Shortlist ke liye <= 0.50 ATR (<= ₹14.91) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹930.50 ke 0.5 ATR (₹14.91) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹929.57) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #7 | AXISBANK<br>(Pvt Bank: STRONG) | FAR_FROM_LEVEL | LTP: 1353.00<br>PDH: 1324.0<br>PDL: 1295.2<br>ATR: 28.14 | Breakout level (PDH ₹1324.00) se bahut door tha: Actual distance 1.03 ATR (₹29.00), jabki Shortlist ke liye <= 0.50 ATR (<= ₹14.07) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1324.00 ke 0.5 ATR (₹14.07) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1322.68) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #8 | BANDHANBNK<br>(Pvt Bank: STRONG) | FAR_FROM_LEVEL | LTP: 172.07<br>PDH: 168.6<br>PDL: 163.73<br>ATR: 6.28 | Breakout level (PDH ₹168.60) se bahut door tha: Actual distance 0.55 ATR (₹3.47), jabki Shortlist ke liye <= 0.50 ATR (<= ₹3.14) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹168.60 ke 0.5 ATR (₹3.14) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹168.43) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #9 | BANKBARODA<br>(PSU Bank: STRONG) | FAR_FROM_LEVEL | LTP: 275.20<br>PDH: 260.01<br>PDL: 248.25<br>ATR: 6.21 | Breakout level (PDH ₹260.01) se bahut door tha: Actual distance 2.45 ATR (₹15.19), jabki Shortlist ke liye <= 0.50 ATR (<= ₹3.10) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹260.01 ke 0.5 ATR (₹3.10) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹259.75) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #10 | BANKINDIA<br>(PSU Bank: STRONG) | FAR_FROM_LEVEL | LTP: 152.21<br>PDH: 145.0<br>PDL: 139.06<br>ATR: 4.25 | Breakout level (PDH ₹145.00) se bahut door tha: Actual distance 1.70 ATR (₹7.21), jabki Shortlist ke liye <= 0.50 ATR (<= ₹2.12) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹145.00 ke 0.5 ATR (₹2.12) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹144.85) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #11 | CANBK<br>(PSU Bank: STRONG) | FAR_FROM_LEVEL | LTP: 132.79<br>PDH: 128.2<br>PDL: 123.12<br>ATR: 3.18 | Breakout level (PDH ₹128.20) se bahut door tha: Actual distance 1.44 ATR (₹4.59), jabki Shortlist ke liye <= 0.50 ATR (<= ₹1.59) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹128.20 ke 0.5 ATR (₹1.59) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹128.07) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #12 | FEDERALBNK<br>(Pvt Bank: STRONG) | FAR_FROM_LEVEL | LTP: 361.15<br>PDH: 344.1<br>PDL: 333.25<br>ATR: 8.76 | Breakout level (PDH ₹344.10) se bahut door tha: Actual distance 1.95 ATR (₹17.05), jabki Shortlist ke liye <= 0.50 ATR (<= ₹4.38) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹344.10 ke 0.5 ATR (₹4.38) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹343.76) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #13 | HDFCBANK<br>(Pvt Bank: STRONG) | FAR_FROM_LEVEL | LTP: 815.00<br>PDH: 801.9<br>PDL: 786.0<br>ATR: 17.15 | Breakout level (PDH ₹801.90) se bahut door tha: Actual distance 0.76 ATR (₹13.10), jabki Shortlist ke liye <= 0.50 ATR (<= ₹8.57) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹801.90 ke 0.5 ATR (₹8.57) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹801.10) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #14 | INDIANB<br>(PSU Bank: STRONG) | FAR_FROM_LEVEL | LTP: 949.90<br>PDH: 934.15<br>PDL: 897.05<br>ATR: 22.82 | Breakout level (PDH ₹934.15) se bahut door tha: Actual distance 0.69 ATR (₹15.75), jabki Shortlist ke liye <= 0.50 ATR (<= ₹11.41) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹934.15 ke 0.5 ATR (₹11.41) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹933.22) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #15 | KOTAKBANK<br>(Pvt Bank: STRONG) | FAR_FROM_LEVEL | LTP: 488.45<br>PDH: 483.1<br>PDL: 474.65<br>ATR: 10.09 | Breakout level (PDH ₹483.10) se bahut door tha: Actual distance 0.53 ATR (₹5.35), jabki Shortlist ke liye <= 0.50 ATR (<= ₹5.04) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹483.10 ke 0.5 ATR (₹5.04) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹482.62) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #16 | M&M<br>(Auto: STRONG) | FAR_FROM_LEVEL | LTP: 3448.50<br>PDH: 3302.2<br>PDL: 3240.3<br>ATR: 80.68 | Breakout level (PDH ₹3302.20) se bahut door tha: Actual distance 1.81 ATR (₹146.30), jabki Shortlist ke liye <= 0.50 ATR (<= ₹40.34) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹3302.20 ke 0.5 ATR (₹40.34) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹3298.90) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #17 | MOTHERSON<br>(Auto: STRONG) | FAR_FROM_LEVEL | LTP: 167.01<br>PDH: 164.28<br>PDL: 159.02<br>ATR: 5.39 | Breakout level (PDH ₹164.28) se bahut door tha: Actual distance 0.51 ATR (₹2.73), jabki Shortlist ke liye <= 0.50 ATR (<= ₹2.69) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹164.28 ke 0.5 ATR (₹2.69) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹164.12) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #18 | PNB<br>(PSU Bank: STRONG) | FAR_FROM_LEVEL | LTP: 138.90<br>PDH: 132.46<br>PDL: 126.04<br>ATR: 3.77 | Breakout level (PDH ₹132.46) se bahut door tha: Actual distance 1.71 ATR (₹6.44), jabki Shortlist ke liye <= 0.50 ATR (<= ₹1.89) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹132.46 ke 0.5 ATR (₹1.89) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹132.33) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #19 | RBLBANK<br>(Pvt Bank: STRONG) | FAR_FROM_LEVEL | LTP: 393.75<br>PDH: 381.25<br>PDL: 374.5<br>ATR: 11.39 | Breakout level (PDH ₹381.25) se bahut door tha: Actual distance 1.10 ATR (₹12.50), jabki Shortlist ke liye <= 0.50 ATR (<= ₹5.70) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹381.25 ke 0.5 ATR (₹5.70) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹380.87) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #20 | SBIN<br>(PSU Bank: STRONG) | FAR_FROM_LEVEL | LTP: 1075.75<br>PDH: 1048.6<br>PDL: 1023.45<br>ATR: 22.5 | Breakout level (PDH ₹1048.60) se bahut door tha: Actual distance 1.21 ATR (₹27.15), jabki Shortlist ke liye <= 0.50 ATR (<= ₹11.25) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1048.60 ke 0.5 ATR (₹11.25) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1047.55) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #21 | TMPV<br>(Auto: STRONG) | FAR_FROM_LEVEL | LTP: 300.80<br>PDH: 295.95<br>PDL: 291.0<br>ATR: 7.45 | Breakout level (PDH ₹295.95) se bahut door tha: Actual distance 0.65 ATR (₹4.85), jabki Shortlist ke liye <= 0.50 ATR (<= ₹3.73) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹295.95 ke 0.5 ATR (₹3.73) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹295.65) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #22 | UNIONBANK<br>(PSU Bank: STRONG) | FAR_FROM_LEVEL | LTP: 201.47<br>PDH: 197.0<br>PDL: 187.39<br>ATR: 4.88 | Breakout level (PDH ₹197.00) se bahut door tha: Actual distance 0.92 ATR (₹4.47), jabki Shortlist ke liye <= 0.50 ATR (<= ₹2.44) chahiye.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹197.00 ke 0.5 ATR (₹2.44) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹196.80) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #23 | ADANIENT<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 2751.10<br>PDH: 2749.5<br>PDL: 2695.0<br>ATR: 73.38 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2749.50 ke 0.5 ATR (₹36.69) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2746.75) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #24 | ADANIGREEN<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 1462.90<br>PDH: 1449.5<br>PDL: 1417.0<br>ATR: 43.24 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1449.50 ke 0.5 ATR (₹21.62) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1448.05) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #25 | AUROPHARMA<br>(Pharma: WEAK) | SECTOR_FILTERED | LTP: 1824.70<br>PDH: 1856.0<br>PDL: 1802.4<br>ATR: 42.34 | Sector 'Pharma' abhi WEAK hai (Rank #8, RS -1.94%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1856.00 ke 0.5 ATR (₹21.17) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1854.14) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #26 | BIOCON<br>(Pharma: WEAK) | SECTOR_FILTERED | LTP: 370.90<br>PDH: 375.2<br>PDL: 366.35<br>ATR: 9.13 | Sector 'Pharma' abhi WEAK hai (Rank #8, RS -1.94%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹375.20 ke 0.5 ATR (₹4.57) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹374.82) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #27 | BPCL<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 321.70<br>PDH: 318.85<br>PDL: 314.0<br>ATR: 8.19 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹318.85 ke 0.5 ATR (₹4.09) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹318.53) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #28 | BRITANNIA<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 4865.90<br>PDH: 4830.0<br>PDL: 4742.1<br>ATR: 108.89 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹4830.00 ke 0.5 ATR (₹54.45) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹4825.17) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #29 | CIPLA<br>(Pharma: WEAK) | SECTOR_FILTERED | LTP: 1409.80<br>PDH: 1420.9<br>PDL: 1397.7<br>ATR: 25.2 | Sector 'Pharma' abhi WEAK hai (Rank #8, RS -1.94%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1420.90 ke 0.5 ATR (₹12.60) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1419.48) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #30 | COALINDIA<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 407.55<br>PDH: 403.5<br>PDL: 398.8<br>ATR: 8.27 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹403.50 ke 0.5 ATR (₹4.13) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹403.10) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #31 | COFORGE<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 2030.10<br>PDH: 2060.5<br>PDL: 2016.8<br>ATR: 63.44 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2060.50 ke 0.5 ATR (₹31.72) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2058.44) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #32 | COLPAL<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1725.70<br>PDH: 1695.0<br>PDL: 1666.2<br>ATR: 43.84 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1695.00 ke 0.5 ATR (₹21.92) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1693.31) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #33 | DABUR<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 381.90<br>PDH: 380.0<br>PDL: 374.0<br>ATR: 8.86 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹380.00 ke 0.5 ATR (₹4.43) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹379.62) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #34 | DLF<br>(Realty: WEAK) | SECTOR_FILTERED | LTP: 750.60<br>PDH: 755.95<br>PDL: 742.7<br>ATR: 18.46 | Sector 'Realty' abhi WEAK hai (Rank #9, RS -1.95%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹755.95 ke 0.5 ATR (₹9.23) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹755.19) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #35 | DRREDDY<br>(Pharma: WEAK) | SECTOR_FILTERED | LTP: 1377.10<br>PDH: 1390.2<br>PDL: 1369.3<br>ATR: 26.08 | Sector 'Pharma' abhi WEAK hai (Rank #8, RS -1.94%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1390.20 ke 0.5 ATR (₹13.04) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1388.81) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #36 | GAIL<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 187.95<br>PDH: 188.0<br>PDL: 184.7<br>ATR: 4.0 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹188.00 ke 0.5 ATR (₹2.00) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹187.81) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #37 | GODREJCP<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 876.40<br>PDH: 850.65<br>PDL: 833.55<br>ATR: 21.81 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹850.65 ke 0.5 ATR (₹10.90) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹849.80) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #38 | GODREJPROP<br>(Realty: WEAK) | SECTOR_FILTERED | LTP: 1804.00<br>PDH: 1815.0<br>PDL: 1769.0<br>ATR: 57.63 | Sector 'Realty' abhi WEAK hai (Rank #9, RS -1.95%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1815.00 ke 0.5 ATR (₹28.82) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1813.18) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #39 | HCLTECH<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 1414.10<br>PDH: 1431.5<br>PDL: 1394.5<br>ATR: 37.14 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1431.50 ke 0.5 ATR (₹18.57) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1430.07) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #40 | HINDALCO<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 962.45<br>PDH: 967.7<br>PDL: 919.45<br>ATR: 24.84 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹967.70 ke 0.5 ATR (₹12.42) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹966.73) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #41 | HINDUNILVR<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 2023.10<br>PDH: 2003.2<br>PDL: 1980.0<br>ATR: 41.36 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2003.20 ke 0.5 ATR (₹20.68) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2001.20) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #42 | INFY<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 1154.90<br>PDH: 1167.1<br>PDL: 1139.4<br>ATR: 34.39 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1167.10 ke 0.5 ATR (₹17.20) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1165.93) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #43 | IOC<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 148.29<br>PDH: 149.08<br>PDL: 145.81<br>ATR: 3.29 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹149.08 ke 0.5 ATR (₹1.65) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹148.93) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #44 | ITC<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 285.05<br>PDH: 283.4<br>PDL: 277.95<br>ATR: 6.09 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹283.40 ke 0.5 ATR (₹3.04) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹283.12) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #45 | JINDALSTEL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 1173.50<br>PDH: 1160.7<br>PDL: 1132.9<br>ATR: 27.8 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1160.70 ke 0.5 ATR (₹13.90) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1159.54) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #46 | JSWSTEEL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 1358.80<br>PDH: 1359.2<br>PDL: 1336.5<br>ATR: 29.48 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1359.20 ke 0.5 ATR (₹14.74) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1357.84) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #47 | LODHA<br>(Realty: WEAK) | SECTOR_FILTERED | LTP: 1178.90<br>PDH: 1195.0<br>PDL: 1148.2<br>ATR: 43.13 | Sector 'Realty' abhi WEAK hai (Rank #9, RS -1.95%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1195.00 ke 0.5 ATR (₹21.57) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1193.81) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #48 | LTM<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 4273.20<br>PDH: 4328.2<br>PDL: 4243.1<br>ATR: 134.55 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹4328.20 ke 0.5 ATR (₹67.28) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹4323.87) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #49 | LTTS<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 4244.50<br>PDH: 4233.7<br>PDL: 4142.5<br>ATR: 134.31 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹4233.70 ke 0.5 ATR (₹67.16) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹4229.47) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #50 | LUPIN<br>(Pharma: WEAK) | SECTOR_FILTERED | LTP: 2010.00<br>PDH: 2036.5<br>PDL: 1992.5<br>ATR: 39.12 | Sector 'Pharma' abhi WEAK hai (Rank #8, RS -1.94%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2036.50 ke 0.5 ATR (₹19.56) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2034.46) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #51 | MARICO<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 908.00<br>PDH: 903.55<br>PDL: 891.1<br>ATR: 20.11 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹903.55 ke 0.5 ATR (₹10.05) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹902.65) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #52 | MPHASIS<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 2439.60<br>PDH: 2515.1<br>PDL: 2418.1<br>ATR: 89.11 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2515.10 ke 0.5 ATR (₹44.55) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2512.58) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #53 | NATIONALUM<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 330.70<br>PDH: 329.0<br>PDL: 321.8<br>ATR: 10.36 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹329.00 ke 0.5 ATR (₹5.18) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹328.67) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #54 | NESTLEIND<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1289.40<br>PDH: 1297.8<br>PDL: 1255.7<br>ATR: 33.07 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1297.80 ke 0.5 ATR (₹16.54) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1296.50) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #55 | NTPC<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 333.05<br>PDH: 328.75<br>PDL: 322.1<br>ATR: 7.35 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹328.75 ke 0.5 ATR (₹3.67) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹328.42) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #56 | OBEROIRLTY<br>(Realty: WEAK) | SECTOR_FILTERED | LTP: 1762.40<br>PDH: 1794.4<br>PDL: 1722.2<br>ATR: 49.68 | Sector 'Realty' abhi WEAK hai (Rank #9, RS -1.95%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1794.40 ke 0.5 ATR (₹24.84) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1792.61) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #57 | ONGC<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 235.48<br>PDH: 236.78<br>PDL: 233.2<br>ATR: 4.73 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹236.78 ke 0.5 ATR (₹2.37) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹236.54) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #58 | PHOENIXLTD<br>(Realty: WEAK) | SECTOR_FILTERED | LTP: 2173.30<br>PDH: 2150.0<br>PDL: 2125.0<br>ATR: 67.6 | Sector 'Realty' abhi WEAK hai (Rank #9, RS -1.95%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2150.00 ke 0.5 ATR (₹33.80) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2147.85) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #59 | POWERGRID<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 265.85<br>PDH: 262.0<br>PDL: 257.05<br>ATR: 6.17 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹262.00 ke 0.5 ATR (₹3.08) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹261.74) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #60 | PRESTIGE<br>(Realty: WEAK) | SECTOR_FILTERED | LTP: 1600.50<br>PDH: 1619.7<br>PDL: 1572.6<br>ATR: 54.09 | Sector 'Realty' abhi WEAK hai (Rank #9, RS -1.95%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1619.70 ke 0.5 ATR (₹27.05) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1618.08) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #61 | RELIANCE<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 1342.40<br>PDH: 1330.2<br>PDL: 1305.5<br>ATR: 28.09 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1330.20 ke 0.5 ATR (₹14.04) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1328.87) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #62 | SAIL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 176.12<br>PDH: 172.64<br>PDL: 167.85<br>ATR: 5.66 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹172.64 ke 0.5 ATR (₹2.83) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹172.47) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #63 | SUNPHARMA<br>(Pharma: WEAK) | SECTOR_FILTERED | LTP: 1895.80<br>PDH: 1943.9<br>PDL: 1900.8<br>ATR: 43.37 | Sector 'Pharma' abhi WEAK hai (Rank #8, RS -1.94%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1943.90 ke 0.5 ATR (₹21.68) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1941.96) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #64 | TATACONSUM<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1091.30<br>PDH: 1093.0<br>PDL: 1074.2<br>ATR: 22.39 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1093.00 ke 0.5 ATR (₹11.20) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1091.91) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #65 | TATAPOWER<br>(Energy: NEUTRAL) | SECTOR_FILTERED | LTP: 367.75<br>PDH: 360.2<br>PDL: 351.15<br>ATR: 9.0 | Sector 'Energy' abhi NEUTRAL hai (Rank #6, RS -0.06%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹360.20 ke 0.5 ATR (₹4.50) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹359.84) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #66 | TATASTEEL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 189.38<br>PDH: 193.7<br>PDL: 184.4<br>ATR: 4.91 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹193.70 ke 0.5 ATR (₹2.46) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹193.51) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #67 | TCS<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 2470.80<br>PDH: 2495.6<br>PDL: 2449.6<br>ATR: 63.04 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹2495.60 ke 0.5 ATR (₹31.52) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹2493.10) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #68 | TECHM<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 1789.50<br>PDH: 1829.0<br>PDL: 1794.1<br>ATR: 44.48 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1829.00 ke 0.5 ATR (₹22.24) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1827.17) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #69 | TORNTPHARM<br>(Pharma: WEAK) | SECTOR_FILTERED | LTP: 4748.10<br>PDH: 4835.0<br>PDL: 4734.5<br>ATR: 99.95 | Sector 'Pharma' abhi WEAK hai (Rank #8, RS -1.94%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹4835.00 ke 0.5 ATR (₹49.98) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹4830.16) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #70 | UBL<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1236.70<br>PDH: 1229.9<br>PDL: 1187.5<br>ATR: 36.87 | Sector 'FMCG' abhi NEUTRAL hai (Rank #4, RS 0.25%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹1229.90 ke 0.5 ATR (₹18.43) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹1228.67) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #71 | VEDL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 262.69<br>PDH: 263.97<br>PDL: 258.34<br>ATR: 6.97 | Sector 'Metal' abhi NEUTRAL hai (Rank #5, RS 0.14%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹263.97 ke 0.5 ATR (₹3.48) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹263.71) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #72 | WIPRO<br>(IT: WEAK) | SECTOR_FILTERED | LTP: 198.25<br>PDH: 199.0<br>PDL: 194.76<br>ATR: 4.61 | Sector 'IT' abhi WEAK hai (Rank #7, RS -1.75%). LONG trade ke liye sirf STRONG sector ke stocks allow hain.<br>[Min Cond: LONG Arm & Entry ke liye: (1) Sector STRONG ho (RS >= +0.25%), (2) LTP PDH ₹199.00 ke 0.5 ATR (₹2.31) ke andar ho, (3) Top-5 score me aaye aur PDH-0.1% (₹198.80) ke paas arm ho, (4) 8/8 signal checks pass kare.] |

## 5. Complete Chronological Signal-by-Signal Dissection (All 56 Signals)

### [1/56] 09:40-CANBK-#1 (CANBK | PSU Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_09:40_CANBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/09-40_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 641 | Entry Rs.129.46 | SL Rs.128.68 | Target Rs.131.01 | R:R 1:1.99 | Risk Rs.500 -> Reward Rs.994 | Slot Vol 1.99x | Day RVOL 2.16x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | PSU Bank (Rank #1, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 129.46 | Close > 128.33 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 129.46 vs VWAP 129.27 | Close > VWAP (129.27) | - |
| #5 | 5m Slot Volume | PASS | 1,244,237 vs avg 626,177 (1.99x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.16x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 129.58, ext 0.40 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 641 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha |

### [2/56] 09:40-UNIONBANK-#2 (UNIONBANK | PSU Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_09:40_UNIONBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/09-40_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 420 | Entry Rs.198.23 | SL Rs.197.04 | Target Rs.200.61 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.1000 | Slot Vol 1.53x | Day RVOL 2.91x
- **Kya & Kyun Samjha (FAILED 3/8): #4 VWAP Filter: Close ₹198.23 VWAP (₹198.57) ke galat side tha (Close > VWAP (198.57) chahiye). | #7 Gap, No-Chase & Stop Risk: Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹198.23 VWAP (₹198.57) ke galat side tha (Close > VWAP (198.57) chahiye). | Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | PSU Bank (Rank #1, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 198.23 | Close > 197.20 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 198.23 vs VWAP 198.57 | Close > VWAP (198.57) | Close ₹198.23 VWAP (₹198.57) ke galat side tha (Close > VWAP (198.57) chahiye). |
| #5 | 5m Slot Volume | PASS | 355,493 vs avg 232,359 (1.53x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.91x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 197.37, ext 0.25 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 420 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹198.23 VWAP (₹198.57) ke galat side tha (Close > VWAP (198.57) chahiye). \| Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha |

### [3/56] 09:45-CANBK-#1 (CANBK | PSU Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_09:45_CANBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/09-45_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 641 | Entry Rs.129.45 | SL Rs.128.67 | Target Rs.131.00 | R:R 1:1.99 | Risk Rs.500 -> Reward Rs.994 | Slot Vol 2.31x | Day RVOL 2.17x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | PSU Bank (Rank #1, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 129.45 | Close > 128.33 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 129.45 vs VWAP 129.31 | Close > VWAP (129.31) | - |
| #5 | 5m Slot Volume | PASS | 1,254,876 vs avg 543,551 (2.31x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.17x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 129.58, ext 0.39 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 641 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹129.58 pehle hi PDH (₹128.20) cross kar chuka tha |

### [4/56] 09:45-UNIONBANK-#2 (UNIONBANK | PSU Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_09:45_UNIONBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/09-45_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 420 | Entry Rs.198.38 | SL Rs.197.19 | Target Rs.200.76 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.1000 | Slot Vol 1.94x | Day RVOL 2.79x
- **Kya & Kyun Samjha (FAILED 3/8): #4 VWAP Filter: Close ₹198.38 VWAP (₹198.56) ke galat side tha (Close > VWAP (198.56) chahiye). | #7 Gap, No-Chase & Stop Risk: Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹198.38 VWAP (₹198.56) ke galat side tha (Close > VWAP (198.56) chahiye). | Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | PSU Bank (Rank #1, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 198.38 | Close > 197.20 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 198.38 vs VWAP 198.56 | Close > VWAP (198.56) | Close ₹198.38 VWAP (₹198.56) ke galat side tha (Close > VWAP (198.56) chahiye). |
| #5 | 5m Slot Volume | PASS | 453,842 vs avg 233,736 (1.94x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.79x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 197.37, ext 0.28 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 420 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹198.38 VWAP (₹198.56) ke galat side tha (Close > VWAP (198.56) chahiye). \| Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha |

### [5/56] 09:50-UNIONBANK-#1 (UNIONBANK | PSU Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_09:50_UNIONBANK_LONG_#1  |  Micro S3 File: scans/2026-11-11/09-50_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 416 | Entry Rs.199.25 | SL Rs.198.05 | Target Rs.201.64 | R:R 1:1.99 | Risk Rs.499 -> Reward Rs.994 | Slot Vol 5.27x | Day RVOL 2.99x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | PSU Bank (Rank #1, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 199.25 | Close > 197.20 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 199.25 vs VWAP 198.63 | Close > VWAP (198.63) | - |
| #5 | 5m Slot Volume | PASS | 859,410 vs avg 163,124 (5.27x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.99x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 197.37, ext 0.46 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 416 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹197.37 pehle hi PDH (₹197.00) cross kar chuka tha |

### [6/56] 10:55-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_10:55_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/10-55_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.910.50 | SL Rs.905.04 | Target Rs.921.43 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.995 | Slot Vol 3.13x | Day RVOL 2.07x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 910.50 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 910.50 vs VWAP 905.27 | Close > VWAP (905.27) | - |
| #5 | 5m Slot Volume | PASS | 113,385 vs avg 36,256 (3.13x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.07x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.22 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [7/56] 10:55-KOTAKBANK-#2 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_10:55_KOTAKBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/10-55_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 171 | Entry Rs.486.60 | SL Rs.483.68 | Target Rs.492.44 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.999 | Slot Vol 1.43x | Day RVOL 1.3x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 277,889 shares (1.5x of 5-day avg 185,259) chahiye tha, par actual sirf 265,441 (1.43x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 277,889 shares (1.5x of 5-day avg 185,259) chahiye tha, par actual sirf 265,441 (1.43x) aaya. | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 486.60 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 486.60 vs VWAP 484.27 | Close > VWAP (484.27) | - |
| #5 | 5m Slot Volume | FAIL | 265,441 vs avg 185,259 (1.43x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 277,889 shares (1.5x of 5-day avg 185,259) chahiye tha, par actual sirf 265,441 (1.43x) aaya. |
| #6 | Day RVOL | PASS | 1.30x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.35 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 171 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 277,889 shares (1.5x of 5-day avg 185,259) chahiye tha, par actual sirf 265,441 (1.43x) aaya. \| Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [8/56] 10:55-ICICIBANK-#3 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_10:55_ICICIBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/10-55_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1600.10 | SL Rs.1590.50 | Target Rs.1619.30 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 1.23x | Day RVOL 1.19x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Close ₹1600.10 VWAP (₹1605.84) ke galat side tha (Close > VWAP (1605.84) chahiye). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 263,397 shares (1.5x of 5-day avg 175,598) chahiye tha, par actual sirf 215,195 (1.23x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1600.10 VWAP (₹1605.84) ke galat side tha (Close > VWAP (1605.84) chahiye). | 5m Candle Volume kam tha: Minimum > 263,397 shares (1.5x of 5-day avg 175,598) chahiye tha, par actual sirf 215,195 (1.23x) aaya. | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1600.10 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1600.10 vs VWAP 1605.84 | Close > VWAP (1605.84) | Close ₹1600.10 VWAP (₹1605.84) ke galat side tha (Close > VWAP (1605.84) chahiye). |
| #5 | 5m Slot Volume | FAIL | 215,195 vs avg 175,598 (1.23x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 263,397 shares (1.5x of 5-day avg 175,598) chahiye tha, par actual sirf 215,195 (1.23x) aaya. |
| #6 | Day RVOL | PASS | 1.19x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.26 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1600.10 VWAP (₹1605.84) ke galat side tha (Close > VWAP (1605.84) chahiye). \| 5m Candle Volume kam tha: Minimum > 263,397 shares (1.5x of 5-day avg 175,598) chahiye tha, par actual sirf 215,195 (1.23x) aaya. \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [9/56] 11:00-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:00_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-00_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.909.65 | SL Rs.904.19 | Target Rs.920.57 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 8.95x | Day RVOL 2.15x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 909.65 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 909.65 vs VWAP 905.54 | Close > VWAP (905.54) | - |
| #5 | 5m Slot Volume | PASS | 133,007 vs avg 14,864 (8.95x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.15x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.19 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [10/56] 11:00-KOTAKBANK-#2 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:00_KOTAKBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-00_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 171 | Entry Rs.486.75 | SL Rs.483.83 | Target Rs.492.59 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.999 | Slot Vol 2.17x | Day RVOL 1.33x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 486.75 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 486.75 vs VWAP 484.37 | Close > VWAP (484.37) | - |
| #5 | 5m Slot Volume | PASS | 380,856 vs avg 175,732 (2.17x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 1.33x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.36 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 171 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [11/56] 11:00-ICICIBANK-#3 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:00_ICICIBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-00_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1599.50 | SL Rs.1589.90 | Target Rs.1618.69 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 1.76x | Day RVOL 1.2x
- **Kya & Kyun Samjha (FAILED 3/8): #4 VWAP Filter: Close ₹1599.50 VWAP (₹1605.68) ke galat side tha (Close > VWAP (1605.68) chahiye). | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1599.50 VWAP (₹1605.68) ke galat side tha (Close > VWAP (1605.68) chahiye). | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1599.50 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1599.50 vs VWAP 1605.68 | Close > VWAP (1605.68) | Close ₹1599.50 VWAP (₹1605.68) ke galat side tha (Close > VWAP (1605.68) chahiye). |
| #5 | 5m Slot Volume | PASS | 286,368 vs avg 163,001 (1.76x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 1.20x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.24 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1599.50 VWAP (₹1605.68) ke galat side tha (Close > VWAP (1605.68) chahiye). \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [12/56] 11:05-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:05_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-05_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.909.95 | SL Rs.904.49 | Target Rs.920.87 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 2.04x | Day RVOL 2.15x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 909.95 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 909.95 vs VWAP 905.62 | Close > VWAP (905.62) | - |
| #5 | 5m Slot Volume | PASS | 55,606 vs avg 27,261 (2.04x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.15x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.20 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [13/56] 11:05-KOTAKBANK-#2 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:05_KOTAKBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-05_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 171 | Entry Rs.487.20 | SL Rs.484.28 | Target Rs.493.05 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.1000 | Slot Vol 1.41x | Day RVOL 1.33x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 283,044 shares (1.5x of 5-day avg 188,696) chahiye tha, par actual sirf 266,841 (1.41x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 283,044 shares (1.5x of 5-day avg 188,696) chahiye tha, par actual sirf 266,841 (1.41x) aaya. | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 487.20 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 487.20 vs VWAP 484.45 | Close > VWAP (484.45) | - |
| #5 | 5m Slot Volume | FAIL | 266,841 vs avg 188,696 (1.41x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 283,044 shares (1.5x of 5-day avg 188,696) chahiye tha, par actual sirf 266,841 (1.41x) aaya. |
| #6 | Day RVOL | PASS | 1.33x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.41 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 171 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 283,044 shares (1.5x of 5-day avg 188,696) chahiye tha, par actual sirf 266,841 (1.41x) aaya. \| Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [14/56] 11:05-ICICIBANK-#3 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_11:05_ICICIBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-05_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1599.20 | SL Rs.1589.60 | Target Rs.1618.39 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 0.5x | Day RVOL 1.17x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Close ₹1599.20 VWAP (₹1605.59) ke galat side tha (Close > VWAP (1605.59) chahiye). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 444,487 shares (1.5x of 5-day avg 296,324) chahiye tha, par actual sirf 147,474 (0.50x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1599.20 VWAP (₹1605.59) ke galat side tha (Close > VWAP (1605.59) chahiye). | 5m Candle Volume kam tha: Minimum > 444,487 shares (1.5x of 5-day avg 296,324) chahiye tha, par actual sirf 147,474 (0.50x) aaya. | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1599.20 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1599.20 vs VWAP 1605.59 | Close > VWAP (1605.59) | Close ₹1599.20 VWAP (₹1605.59) ke galat side tha (Close > VWAP (1605.59) chahiye). |
| #5 | 5m Slot Volume | FAIL | 147,474 vs avg 296,324 (0.50x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 444,487 shares (1.5x of 5-day avg 296,324) chahiye tha, par actual sirf 147,474 (0.50x) aaya. |
| #6 | Day RVOL | PASS | 1.17x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.23 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1599.20 VWAP (₹1605.59) ke galat side tha (Close > VWAP (1605.59) chahiye). \| 5m Candle Volume kam tha: Minimum > 444,487 shares (1.5x of 5-day avg 296,324) chahiye tha, par actual sirf 147,474 (0.50x) aaya. \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [15/56] 11:10-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:10_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-10_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.909.85 | SL Rs.904.39 | Target Rs.920.77 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 6.91x | Day RVOL 2.19x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 909.85 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 909.85 vs VWAP 905.76 | Close > VWAP (905.76) | - |
| #5 | 5m Slot Volume | PASS | 92,330 vs avg 13,370 (6.91x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.19x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.19 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [16/56] 11:10-KOTAKBANK-#2 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:10_KOTAKBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-10_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 171 | Entry Rs.487.20 | SL Rs.484.28 | Target Rs.493.05 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.1000 | Slot Vol 0.5x | Day RVOL 1.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 624,933 shares (1.5x of 5-day avg 416,622) chahiye tha, par actual sirf 208,526 (0.50x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 624,933 shares (1.5x of 5-day avg 416,622) chahiye tha, par actual sirf 208,526 (0.50x) aaya. | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 487.20 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 487.20 vs VWAP 484.51 | Close > VWAP (484.51) | - |
| #5 | 5m Slot Volume | FAIL | 208,526 vs avg 416,622 (0.50x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 624,933 shares (1.5x of 5-day avg 416,622) chahiye tha, par actual sirf 208,526 (0.50x) aaya. |
| #6 | Day RVOL | PASS | 1.28x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.41 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 171 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 624,933 shares (1.5x of 5-day avg 416,622) chahiye tha, par actual sirf 208,526 (0.50x) aaya. \| Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [17/56] 11:10-ICICIBANK-#3 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_11:10_ICICIBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-10_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1599.30 | SL Rs.1589.70 | Target Rs.1618.49 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 0.81x | Day RVOL 1.17x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Close ₹1599.30 VWAP (₹1605.50) ke galat side tha (Close > VWAP (1605.50) chahiye). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 274,197 shares (1.5x of 5-day avg 182,798) chahiye tha, par actual sirf 148,115 (0.81x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1599.30 VWAP (₹1605.50) ke galat side tha (Close > VWAP (1605.50) chahiye). | 5m Candle Volume kam tha: Minimum > 274,197 shares (1.5x of 5-day avg 182,798) chahiye tha, par actual sirf 148,115 (0.81x) aaya. | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1599.30 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1599.30 vs VWAP 1605.50 | Close > VWAP (1605.50) | Close ₹1599.30 VWAP (₹1605.50) ke galat side tha (Close > VWAP (1605.50) chahiye). |
| #5 | 5m Slot Volume | FAIL | 148,115 vs avg 182,798 (0.81x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 274,197 shares (1.5x of 5-day avg 182,798) chahiye tha, par actual sirf 148,115 (0.81x) aaya. |
| #6 | Day RVOL | PASS | 1.17x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.23 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1599.30 VWAP (₹1605.50) ke galat side tha (Close > VWAP (1605.50) chahiye). \| 5m Candle Volume kam tha: Minimum > 274,197 shares (1.5x of 5-day avg 182,798) chahiye tha, par actual sirf 148,115 (0.81x) aaya. \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [18/56] 11:15-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:15_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.910.25 | SL Rs.904.79 | Target Rs.921.17 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 3.16x | Day RVOL 2.21x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 910.25 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 910.25 vs VWAP 905.84 | Close > VWAP (905.84) | - |
| #5 | 5m Slot Volume | PASS | 52,555 vs avg 16,625 (3.16x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.21x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.21 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [19/56] 11:15-ICICIBANK-#2 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_11:15_ICICIBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1598.90 | SL Rs.1589.31 | Target Rs.1618.09 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 0.8x | Day RVOL 1.16x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Close ₹1598.90 VWAP (₹1605.42) ke galat side tha (Close > VWAP (1605.42) chahiye). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 259,734 shares (1.5x of 5-day avg 173,156) chahiye tha, par actual sirf 139,042 (0.80x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1598.90 VWAP (₹1605.42) ke galat side tha (Close > VWAP (1605.42) chahiye). | 5m Candle Volume kam tha: Minimum > 259,734 shares (1.5x of 5-day avg 173,156) chahiye tha, par actual sirf 139,042 (0.80x) aaya. | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1598.90 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1598.90 vs VWAP 1605.42 | Close > VWAP (1605.42) | Close ₹1598.90 VWAP (₹1605.42) ke galat side tha (Close > VWAP (1605.42) chahiye). |
| #5 | 5m Slot Volume | FAIL | 139,042 vs avg 173,156 (0.80x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 259,734 shares (1.5x of 5-day avg 173,156) chahiye tha, par actual sirf 139,042 (0.80x) aaya. |
| #6 | Day RVOL | PASS | 1.16x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.22 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1598.90 VWAP (₹1605.42) ke galat side tha (Close > VWAP (1605.42) chahiye). \| 5m Candle Volume kam tha: Minimum > 259,734 shares (1.5x of 5-day avg 173,156) chahiye tha, par actual sirf 139,042 (0.80x) aaya. \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [20/56] 11:15-KOTAKBANK-#3 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:15_KOTAKBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 171 | Entry Rs.487.20 | SL Rs.484.28 | Target Rs.493.05 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.1000 | Slot Vol 0.68x | Day RVOL 1.26x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 350,692 shares (1.5x of 5-day avg 233,794) chahiye tha, par actual sirf 158,110 (0.68x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 350,692 shares (1.5x of 5-day avg 233,794) chahiye tha, par actual sirf 158,110 (0.68x) aaya. | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 487.20 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 487.20 vs VWAP 484.55 | Close > VWAP (484.55) | - |
| #5 | 5m Slot Volume | FAIL | 158,110 vs avg 233,794 (0.68x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 350,692 shares (1.5x of 5-day avg 233,794) chahiye tha, par actual sirf 158,110 (0.68x) aaya. |
| #6 | Day RVOL | PASS | 1.26x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.41 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 171 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 350,692 shares (1.5x of 5-day avg 233,794) chahiye tha, par actual sirf 158,110 (0.68x) aaya. \| Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [21/56] 11:20-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:20_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-20_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.908.65 | SL Rs.903.20 | Target Rs.919.55 | R:R 1:2.00 | Risk Rs.496 -> Reward Rs.992 | Slot Vol 9.16x | Day RVOL 2.32x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 908.65 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 908.65 vs VWAP 906.06 | Close > VWAP (906.06) | - |
| #5 | 5m Slot Volume | PASS | 201,769 vs avg 22,034 (9.16x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.32x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.15 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [22/56] 11:20-KOTAKBANK-#2 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:20_KOTAKBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-20_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 170 | Entry Rs.487.90 | SL Rs.484.97 | Target Rs.493.75 | R:R 1:2.00 | Risk Rs.498 -> Reward Rs.994 | Slot Vol 0.43x | Day RVOL 1.2x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 861,991 shares (1.5x of 5-day avg 574,661) chahiye tha, par actual sirf 248,429 (0.43x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 861,991 shares (1.5x of 5-day avg 574,661) chahiye tha, par actual sirf 248,429 (0.43x) aaya. | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 487.90 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 487.90 vs VWAP 484.64 | Close > VWAP (484.64) | - |
| #5 | 5m Slot Volume | FAIL | 248,429 vs avg 574,661 (0.43x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 861,991 shares (1.5x of 5-day avg 574,661) chahiye tha, par actual sirf 248,429 (0.43x) aaya. |
| #6 | Day RVOL | PASS | 1.20x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.48 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 170 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 861,991 shares (1.5x of 5-day avg 574,661) chahiye tha, par actual sirf 248,429 (0.43x) aaya. \| Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [23/56] 11:20-ICICIBANK-#3 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_11:20_ICICIBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-20_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1599.40 | SL Rs.1589.80 | Target Rs.1618.59 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 1.02x | Day RVOL 1.16x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Close ₹1599.40 VWAP (₹1605.28) ke galat side tha (Close > VWAP (1605.28) chahiye). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 395,296 shares (1.5x of 5-day avg 263,530) chahiye tha, par actual sirf 268,608 (1.02x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1599.40 VWAP (₹1605.28) ke galat side tha (Close > VWAP (1605.28) chahiye). | 5m Candle Volume kam tha: Minimum > 395,296 shares (1.5x of 5-day avg 263,530) chahiye tha, par actual sirf 268,608 (1.02x) aaya. | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1599.40 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1599.40 vs VWAP 1605.28 | Close > VWAP (1605.28) | Close ₹1599.40 VWAP (₹1605.28) ke galat side tha (Close > VWAP (1605.28) chahiye). |
| #5 | 5m Slot Volume | FAIL | 268,608 vs avg 263,530 (1.02x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 395,296 shares (1.5x of 5-day avg 263,530) chahiye tha, par actual sirf 268,608 (1.02x) aaya. |
| #6 | Day RVOL | PASS | 1.16x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.24 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1599.40 VWAP (₹1605.28) ke galat side tha (Close > VWAP (1605.28) chahiye). \| 5m Candle Volume kam tha: Minimum > 395,296 shares (1.5x of 5-day avg 263,530) chahiye tha, par actual sirf 268,608 (1.02x) aaya. \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [24/56] 11:25-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:25_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.909.90 | SL Rs.904.44 | Target Rs.920.82 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 3.49x | Day RVOL 2.33x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 909.90 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 909.90 vs VWAP 906.12 | Close > VWAP (906.12) | - |
| #5 | 5m Slot Volume | PASS | 55,097 vs avg 15,792 (3.49x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.33x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.19 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [25/56] 11:25-KOTAKBANK-#2 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:25_KOTAKBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 170 | Entry Rs.488.00 | SL Rs.485.07 | Target Rs.493.86 | R:R 1:2.00 | Risk Rs.498 -> Reward Rs.996 | Slot Vol 0.56x | Day RVOL 1.18x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 537,989 shares (1.5x of 5-day avg 358,659) chahiye tha, par actual sirf 200,189 (0.56x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 537,989 shares (1.5x of 5-day avg 358,659) chahiye tha, par actual sirf 200,189 (0.56x) aaya. | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 488.00 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 488.00 vs VWAP 484.71 | Close > VWAP (484.71) | - |
| #5 | 5m Slot Volume | FAIL | 200,189 vs avg 358,659 (0.56x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 537,989 shares (1.5x of 5-day avg 358,659) chahiye tha, par actual sirf 200,189 (0.56x) aaya. |
| #6 | Day RVOL | PASS | 1.18x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.49 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 170 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 537,989 shares (1.5x of 5-day avg 358,659) chahiye tha, par actual sirf 200,189 (0.56x) aaya. \| Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [26/56] 11:25-ICICIBANK-#3 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_11:25_ICICIBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1597.80 | SL Rs.1588.21 | Target Rs.1616.97 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.997 | Slot Vol 1.18x | Day RVOL 1.16x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Close ₹1597.80 VWAP (₹1605.14) ke galat side tha (Close > VWAP (1605.14) chahiye). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 308,025 shares (1.5x of 5-day avg 205,350) chahiye tha, par actual sirf 241,953 (1.18x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1597.80 VWAP (₹1605.14) ke galat side tha (Close > VWAP (1605.14) chahiye). | 5m Candle Volume kam tha: Minimum > 308,025 shares (1.5x of 5-day avg 205,350) chahiye tha, par actual sirf 241,953 (1.18x) aaya. | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1597.80 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1597.80 vs VWAP 1605.14 | Close > VWAP (1605.14) | Close ₹1597.80 VWAP (₹1605.14) ke galat side tha (Close > VWAP (1605.14) chahiye). |
| #5 | 5m Slot Volume | FAIL | 241,953 vs avg 205,350 (1.18x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 308,025 shares (1.5x of 5-day avg 205,350) chahiye tha, par actual sirf 241,953 (1.18x) aaya. |
| #6 | Day RVOL | PASS | 1.16x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.19 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1597.80 VWAP (₹1605.14) ke galat side tha (Close > VWAP (1605.14) chahiye). \| 5m Candle Volume kam tha: Minimum > 308,025 shares (1.5x of 5-day avg 205,350) chahiye tha, par actual sirf 241,953 (1.18x) aaya. \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [27/56] 11:30-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:30_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-30_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.909.90 | SL Rs.904.44 | Target Rs.920.82 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 7.88x | Day RVOL 2.38x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 909.90 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 909.90 vs VWAP 906.24 | Close > VWAP (906.24) | - |
| #5 | 5m Slot Volume | PASS | 97,854 vs avg 12,412 (7.88x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.38x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.19 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [28/56] 11:30-ICICIBANK-#2 (ICICIBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:30_ICICIBANK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-30_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 52 | Entry Rs.1593.90 | SL Rs.1584.34 | Target Rs.1613.03 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.995 | Slot Vol 2.08x | Day RVOL 1.18x
- **Kya & Kyun Samjha (FAILED 3/8): #4 VWAP Filter: Close ₹1593.90 VWAP (₹1604.82) ke galat side tha (Close > VWAP (1604.82) chahiye). | #7 Gap, No-Chase & Stop Risk: Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹1593.90 VWAP (₹1604.82) ke galat side tha (Close > VWAP (1604.82) chahiye). | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1593.90 | Close > 1593.59 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1593.90 vs VWAP 1604.82 | Close > VWAP (1604.82) | Close ₹1593.90 VWAP (₹1604.82) ke galat side tha (Close > VWAP (1604.82) chahiye). |
| #5 | 5m Slot Volume | PASS | 409,677 vs avg 196,490 (2.08x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 1.18x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 1605.70, ext 0.06 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 52 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹1593.90 VWAP (₹1604.82) ke galat side tha (Close > VWAP (1604.82) chahiye). \| Day Open ₹1605.70 pehle hi PDH (₹1592.00) cross kar chuka tha |

### [29/56] 11:30-KOTAKBANK-#3 (KOTAKBANK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:30_KOTAKBANK_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-30_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 170 | Entry Rs.487.75 | SL Rs.484.82 | Target Rs.493.60 | R:R 1:2.00 | Risk Rs.498 -> Reward Rs.994 | Slot Vol 0.55x | Day RVOL 1.14x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 757,923 shares (1.5x of 5-day avg 505,282) chahiye tha, par actual sirf 275,965 (0.55x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 757,923 shares (1.5x of 5-day avg 505,282) chahiye tha, par actual sirf 275,965 (0.55x) aaya. | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 487.75 | Close > 483.58 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 487.75 vs VWAP 484.79 | Close > VWAP (484.79) | - |
| #5 | 5m Slot Volume | FAIL | 275,965 vs avg 505,282 (0.55x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 757,923 shares (1.5x of 5-day avg 505,282) chahiye tha, par actual sirf 275,965 (0.55x) aaya. |
| #6 | Day RVOL | PASS | 1.14x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 484.50, ext 0.46 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 170 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 757,923 shares (1.5x of 5-day avg 505,282) chahiye tha, par actual sirf 275,965 (0.55x) aaya. \| Day Open ₹484.50 pehle hi PDH (₹483.10) cross kar chuka tha |

### [30/56] 11:35-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:35_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-35_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.909.95 | SL Rs.904.49 | Target Rs.920.87 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 7.77x | Day RVOL 2.52x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 909.95 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 909.95 vs VWAP 906.58 | Close > VWAP (906.58) | - |
| #5 | 5m Slot Volume | PASS | 299,099 vs avg 38,505 (7.77x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.52x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.20 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [31/56] 11:40-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:40_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-40_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.913.55 | SL Rs.908.07 | Target Rs.924.51 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.997 | Slot Vol 7.99x | Day RVOL 2.73x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 913.55 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 913.55 vs VWAP 907.20 | Close > VWAP (907.20) | - |
| #5 | 5m Slot Volume | PASS | 437,260 vs avg 54,726 (7.99x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.73x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.34 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [32/56] 11:40-BANDHANBNK-#2 (BANDHANBNK | Pvt Bank | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_11:40_BANDHANBNK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-40_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 485 | Entry Rs.171.62 | SL Rs.170.59 | Target Rs.173.68 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.999 | Slot Vol 1.33x | Day RVOL 2.07x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Close ₹171.62 VWAP (₹171.85) ke galat side tha (Close > VWAP (171.85) chahiye). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 202,991 shares (1.5x of 5-day avg 135,327) chahiye tha, par actual sirf 180,068 (1.33x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹171.62 VWAP (₹171.85) ke galat side tha (Close > VWAP (171.85) chahiye). | 5m Candle Volume kam tha: Minimum > 202,991 shares (1.5x of 5-day avg 135,327) chahiye tha, par actual sirf 180,068 (1.33x) aaya. | Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 171.62 | Close > 168.77 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 171.62 vs VWAP 171.85 | Close > VWAP (171.85) | Close ₹171.62 VWAP (₹171.85) ke galat side tha (Close > VWAP (171.85) chahiye). |
| #5 | 5m Slot Volume | FAIL | 180,068 vs avg 135,327 (1.33x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 202,991 shares (1.5x of 5-day avg 135,327) chahiye tha, par actual sirf 180,068 (1.33x) aaya. |
| #6 | Day RVOL | PASS | 2.07x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 170.32, ext 0.48 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 485 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹171.62 VWAP (₹171.85) ke galat side tha (Close > VWAP (171.85) chahiye). \| 5m Candle Volume kam tha: Minimum > 202,991 shares (1.5x of 5-day avg 135,327) chahiye tha, par actual sirf 180,068 (1.33x) aaya. \| Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha |

### [33/56] 11:45-DABUR-#1 (DABUR | FMCG | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:45_DABUR_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-45_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 218 | Entry Rs.381.75 | SL Rs.379.46 | Target Rs.386.33 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 1.62x | Day RVOL 0.54x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.54x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.54x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 381.75 | Close > 380.38 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 381.75 vs VWAP 380.71 | Close > VWAP (380.71) | - |
| #5 | 5m Slot Volume | PASS | 34,332 vs avg 21,193 (1.62x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.54x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.54x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 379.15, ext 0.20 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 218 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.54x tha. |

### [34/56] 11:45-ITC-#2 (ITC | FMCG | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:45_ITC_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-45_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 292 | Entry Rs.285.15 | SL Rs.283.44 | Target Rs.288.57 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.999 | Slot Vol 2.98x | Day RVOL 0.89x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.89x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.89x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 285.15 | Close > 283.68 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 285.15 vs VWAP 282.89 | Close > VWAP (282.89) | - |
| #5 | 5m Slot Volume | PASS | 623,978 vs avg 209,353 (2.98x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.89x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.89x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 281.50, ext 0.29 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 292 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.89x tha. |

### [35/56] 11:45-UBL-#3 (UBL | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:45_UBL_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-45_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 67 | Entry Rs.1235.80 | SL Rs.1228.39 | Target Rs.1250.63 | R:R 1:2.00 | Risk Rs.496 -> Reward Rs.994 | Slot Vol 0.72x | Day RVOL 0.55x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,722 shares (1.5x of 5-day avg 1,148) chahiye tha, par actual sirf 822 (0.72x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 1,722 shares (1.5x of 5-day avg 1,148) chahiye tha, par actual sirf 822 (0.72x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1235.80 | Close > 1231.13 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1235.80 vs VWAP 1231.43 | Close > VWAP (1231.43) | - |
| #5 | 5m Slot Volume | FAIL | 822 vs avg 1,148 (0.72x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,722 shares (1.5x of 5-day avg 1,148) chahiye tha, par actual sirf 822 (0.72x) aaya. |
| #6 | Day RVOL | FAIL | 0.55x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 1229.00, ext 0.16 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 67 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 1,722 shares (1.5x of 5-day avg 1,148) chahiye tha, par actual sirf 822 (0.72x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |

### [36/56] 11:45-INDUSINDBK-#4 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:45_INDUSINDBK_LONG_#4  |  Micro S3 File: scans/2026-11-11/11-45_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.914.60 | SL Rs.909.11 | Target Rs.925.58 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.999 | Slot Vol 0.79x | Day RVOL 2.59x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 164,367 shares (1.5x of 5-day avg 109,578) chahiye tha, par actual sirf 86,565 (0.79x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 164,367 shares (1.5x of 5-day avg 109,578) chahiye tha, par actual sirf 86,565 (0.79x) aaya. | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 914.60 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 914.60 vs VWAP 907.33 | Close > VWAP (907.33) | - |
| #5 | 5m Slot Volume | FAIL | 86,565 vs avg 109,578 (0.79x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 164,367 shares (1.5x of 5-day avg 109,578) chahiye tha, par actual sirf 86,565 (0.79x) aaya. |
| #6 | Day RVOL | PASS | 2.59x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.38 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 164,367 shares (1.5x of 5-day avg 109,578) chahiye tha, par actual sirf 86,565 (0.79x) aaya. \| Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [37/56] 11:50-INDUSINDBK-#1 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:50_INDUSINDBK_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.915.00 | SL Rs.909.51 | Target Rs.925.98 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.999 | Slot Vol 0.65x | Day RVOL 2.46x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 176,233 shares (1.5x of 5-day avg 117,488) chahiye tha, par actual sirf 75,781 (0.65x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 176,233 shares (1.5x of 5-day avg 117,488) chahiye tha, par actual sirf 75,781 (0.65x) aaya. | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 915.00 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 915.00 vs VWAP 907.47 | Close > VWAP (907.47) | - |
| #5 | 5m Slot Volume | FAIL | 75,781 vs avg 117,488 (0.65x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 176,233 shares (1.5x of 5-day avg 117,488) chahiye tha, par actual sirf 75,781 (0.65x) aaya. |
| #6 | Day RVOL | PASS | 2.46x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.39 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 176,233 shares (1.5x of 5-day avg 117,488) chahiye tha, par actual sirf 75,781 (0.65x) aaya. \| Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [38/56] 11:50-BANDHANBNK-#2 (BANDHANBNK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:50_BANDHANBNK_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 485 | Entry Rs.171.37 | SL Rs.170.34 | Target Rs.173.43 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.999 | Slot Vol 16.43x | Day RVOL 2.18x
- **Kya & Kyun Samjha (FAILED 3/8): #4 VWAP Filter: Close ₹171.37 VWAP (₹171.83) ke galat side tha (Close > VWAP (171.83) chahiye). | #7 Gap, No-Chase & Stop Risk: Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close ₹171.37 VWAP (₹171.83) ke galat side tha (Close > VWAP (171.83) chahiye). | Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 171.37 | Close > 168.77 (PDH+0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 171.37 vs VWAP 171.83 | Close > VWAP (171.83) | Close ₹171.37 VWAP (₹171.83) ke galat side tha (Close > VWAP (171.83) chahiye). |
| #5 | 5m Slot Volume | PASS | 535,237 vs avg 32,583 (16.43x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.18x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 170.32, ext 0.44 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 485 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Close ₹171.37 VWAP (₹171.83) ke galat side tha (Close > VWAP (171.83) chahiye). \| Day Open ₹170.32 pehle hi PDH (₹168.60) cross kar chuka tha |

### [39/56] 11:55-DABUR-#1 (DABUR | FMCG | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_11:55_DABUR_LONG_#1  |  Micro S3 File: scans/2026-11-11/11-55_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 218 | Entry Rs.381.95 | SL Rs.379.66 | Target Rs.386.53 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 2.37x | Day RVOL 0.56x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 381.95 | Close > 380.38 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 381.95 vs VWAP 380.78 | Close > VWAP (380.78) | - |
| #5 | 5m Slot Volume | PASS | 36,334 vs avg 15,299 (2.37x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.56x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 379.15, ext 0.22 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 218 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |

### [40/56] 11:55-ITC-#2 (ITC | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:55_ITC_LONG_#2  |  Micro S3 File: scans/2026-11-11/11-55_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 291 | Entry Rs.285.45 | SL Rs.283.74 | Target Rs.288.88 | R:R 1:2.01 | Risk Rs.498 -> Reward Rs.998 | Slot Vol 1.27x | Day RVOL 0.92x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 226,807 shares (1.5x of 5-day avg 151,204) chahiye tha, par actual sirf 191,804 (1.27x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.92x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 226,807 shares (1.5x of 5-day avg 151,204) chahiye tha, par actual sirf 191,804 (1.27x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.92x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 285.45 | Close > 283.68 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 285.45 vs VWAP 283.04 | Close > VWAP (283.04) | - |
| #5 | 5m Slot Volume | FAIL | 191,804 vs avg 151,204 (1.27x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 226,807 shares (1.5x of 5-day avg 151,204) chahiye tha, par actual sirf 191,804 (1.27x) aaya. |
| #6 | Day RVOL | FAIL | 0.92x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.92x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 281.50, ext 0.34 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 291 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 226,807 shares (1.5x of 5-day avg 151,204) chahiye tha, par actual sirf 191,804 (1.27x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.92x tha. |

### [41/56] 11:55-UBL-#3 (UBL | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_11:55_UBL_LONG_#3  |  Micro S3 File: scans/2026-11-11/11-55_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 67 | Entry Rs.1236.60 | SL Rs.1229.18 | Target Rs.1251.44 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 0.54x | Day RVOL 0.55x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 984 shares (1.5x of 5-day avg 656) chahiye tha, par actual sirf 356 (0.54x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 984 shares (1.5x of 5-day avg 656) chahiye tha, par actual sirf 356 (0.54x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1236.60 | Close > 1231.13 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1236.60 vs VWAP 1231.51 | Close > VWAP (1231.51) | - |
| #5 | 5m Slot Volume | FAIL | 356 vs avg 656 (0.54x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 984 shares (1.5x of 5-day avg 656) chahiye tha, par actual sirf 356 (0.54x) aaya. |
| #6 | Day RVOL | FAIL | 0.55x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 1229.00, ext 0.18 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 67 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 984 shares (1.5x of 5-day avg 656) chahiye tha, par actual sirf 356 (0.54x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |

### [42/56] 11:55-MARICO-#4 (MARICO | FMCG | LONG) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-11_11:55_MARICO_LONG_#4  |  Micro S3 File: scans/2026-11-11/11-55_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.907.70 | SL Rs.902.25 | Target Rs.918.59 | R:R 1:2.00 | Risk Rs.496 -> Reward Rs.991 | Slot Vol 0.75x | Day RVOL 0.65x
- **Kya & Kyun Samjha (FAILED 4/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 48,061 shares (1.5x of 5-day avg 32,041) chahiye tha, par actual sirf 24,051 (0.75x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.65x tha. | #7 Gap, No-Chase & Stop Risk: Day Open ₹907.40 pehle hi PDH (₹903.55) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 48,061 shares (1.5x of 5-day avg 32,041) chahiye tha, par actual sirf 24,051 (0.75x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.65x tha. | Day Open ₹907.40 pehle hi PDH (₹903.55) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 907.70 | Close > 904.45 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 907.70 vs VWAP 906.59 | Close > VWAP (906.59) | - |
| #5 | 5m Slot Volume | FAIL | 24,051 vs avg 32,041 (0.75x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 48,061 shares (1.5x of 5-day avg 32,041) chahiye tha, par actual sirf 24,051 (0.75x) aaya. |
| #6 | Day RVOL | FAIL | 0.65x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.65x tha. |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 907.40, ext 0.21 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹907.40 pehle hi PDH (₹903.55) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 48,061 shares (1.5x of 5-day avg 32,041) chahiye tha, par actual sirf 24,051 (0.75x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.65x tha. \| Day Open ₹907.40 pehle hi PDH (₹903.55) cross kar chuka tha |

### [43/56] 12:00-DABUR-#1 (DABUR | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:00_DABUR_LONG_#1  |  Micro S3 File: scans/2026-11-11/12-00_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 218 | Entry Rs.382.00 | SL Rs.379.71 | Target Rs.386.58 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 1.2x | Day RVOL 0.56x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 24,535 shares (1.5x of 5-day avg 16,357) chahiye tha, par actual sirf 19,617 (1.20x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 24,535 shares (1.5x of 5-day avg 16,357) chahiye tha, par actual sirf 19,617 (1.20x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 382.00 | Close > 380.38 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 382.00 vs VWAP 380.80 | Close > VWAP (380.80) | - |
| #5 | 5m Slot Volume | FAIL | 19,617 vs avg 16,357 (1.20x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 24,535 shares (1.5x of 5-day avg 16,357) chahiye tha, par actual sirf 19,617 (1.20x) aaya. |
| #6 | Day RVOL | FAIL | 0.56x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 379.15, ext 0.23 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 218 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 24,535 shares (1.5x of 5-day avg 16,357) chahiye tha, par actual sirf 19,617 (1.20x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |

### [44/56] 12:00-ITC-#2 (ITC | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:00_ITC_LONG_#2  |  Micro S3 File: scans/2026-11-11/12-00_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 292 | Entry Rs.285.35 | SL Rs.283.64 | Target Rs.288.77 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.999 | Slot Vol 0.67x | Day RVOL 0.91x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 394,740 shares (1.5x of 5-day avg 263,160) chahiye tha, par actual sirf 175,622 (0.67x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.91x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 394,740 shares (1.5x of 5-day avg 263,160) chahiye tha, par actual sirf 175,622 (0.67x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.91x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 285.35 | Close > 283.68 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 285.35 vs VWAP 283.07 | Close > VWAP (283.07) | - |
| #5 | 5m Slot Volume | FAIL | 175,622 vs avg 263,160 (0.67x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 394,740 shares (1.5x of 5-day avg 263,160) chahiye tha, par actual sirf 175,622 (0.67x) aaya. |
| #6 | Day RVOL | FAIL | 0.91x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.91x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 281.50, ext 0.32 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 292 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 394,740 shares (1.5x of 5-day avg 263,160) chahiye tha, par actual sirf 175,622 (0.67x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.91x tha. |

### [45/56] 12:00-UBL-#3 (UBL | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:00_UBL_LONG_#3  |  Micro S3 File: scans/2026-11-11/12-00_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 67 | Entry Rs.1234.80 | SL Rs.1227.39 | Target Rs.1249.62 | R:R 1:2.00 | Risk Rs.496 -> Reward Rs.993 | Slot Vol 0.76x | Day RVOL 0.56x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,314 shares (1.5x of 5-day avg 876) chahiye tha, par actual sirf 664 (0.76x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 1,314 shares (1.5x of 5-day avg 876) chahiye tha, par actual sirf 664 (0.76x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1234.80 | Close > 1231.13 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1234.80 vs VWAP 1231.55 | Close > VWAP (1231.55) | - |
| #5 | 5m Slot Volume | FAIL | 664 vs avg 876 (0.76x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,314 shares (1.5x of 5-day avg 876) chahiye tha, par actual sirf 664 (0.76x) aaya. |
| #6 | Day RVOL | FAIL | 0.56x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 1229.00, ext 0.13 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 67 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 1,314 shares (1.5x of 5-day avg 876) chahiye tha, par actual sirf 664 (0.76x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |

### [46/56] 12:00-INDUSINDBK-#4 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_12:00_INDUSINDBK_LONG_#4  |  Micro S3 File: scans/2026-11-11/12-00_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 90 | Entry Rs.915.95 | SL Rs.910.45 | Target Rs.926.94 | R:R 1:2.00 | Risk Rs.495 -> Reward Rs.989 | Slot Vol 2.28x | Day RVOL 2.45x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 915.95 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 915.95 vs VWAP 907.68 | Close > VWAP (907.68) | - |
| #5 | 5m Slot Volume | PASS | 55,152 vs avg 24,162 (2.28x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.45x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.43 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 90 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [47/56] 12:05-BHARATFORG-#1 (BHARATFORG | Auto | LONG) — **WOULD TRADE** (8/8 Pass, 0 Fail)

- Full ID: 2026-11-11_12:05_BHARATFORG_LONG_#1  |  Micro S3 File: scans/2026-11-11/12-05_Scan_72Stocks_2Signals_1Passed.json
- Order Specs: Qty 47 | Entry Rs.1750.20 | SL Rs.1739.70 | Target Rs.1771.20 | R:R 1:2.00 | Risk Rs.494 -> Reward Rs.987 | Slot Vol 2.53x | Day RVOL 1.0x
- **Kya & Kyun Samjha (PASSED): LONG breakout: vol 2.5x slot, RVOL 1.00, stop 0.60%, R:R 1:2.0**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Auto (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1750.20 | Close > 1737.74 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1750.20 vs VWAP 1746.75 | Close > VWAP (1746.75) | - |
| #5 | 5m Slot Volume | PASS | 64,789 vs avg 25,564 (2.53x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 1.00x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 1732.20, ext 0.27 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | PASS | Qty 47 \| WOULD TRADE | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | - |

### [48/56] 12:05-INDUSINDBK-#2 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:05_INDUSINDBK_LONG_#2  |  Micro S3 File: scans/2026-11-11/12-05_Scan_72Stocks_2Signals_1Passed.json
- Order Specs: Qty 91 | Entry Rs.914.75 | SL Rs.909.26 | Target Rs.925.73 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.999 | Slot Vol 1.14x | Day RVOL 2.42x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 63,828 shares (1.5x of 5-day avg 42,552) chahiye tha, par actual sirf 48,722 (1.14x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 63,828 shares (1.5x of 5-day avg 42,552) chahiye tha, par actual sirf 48,722 (1.14x) aaya. | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 914.75 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 914.75 vs VWAP 907.76 | Close > VWAP (907.76) | - |
| #5 | 5m Slot Volume | FAIL | 48,722 vs avg 42,552 (1.14x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 63,828 shares (1.5x of 5-day avg 42,552) chahiye tha, par actual sirf 48,722 (1.14x) aaya. |
| #6 | Day RVOL | PASS | 2.42x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.38 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 63,828 shares (1.5x of 5-day avg 42,552) chahiye tha, par actual sirf 48,722 (1.14x) aaya. \| Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [49/56] 12:10-DABUR-#1 (DABUR | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:10_DABUR_LONG_#1  |  Micro S3 File: scans/2026-11-11/12-10_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 218 | Entry Rs.382.00 | SL Rs.379.71 | Target Rs.386.58 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 0.58x | Day RVOL 0.56x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 34,011 shares (1.5x of 5-day avg 22,674) chahiye tha, par actual sirf 13,140 (0.58x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 34,011 shares (1.5x of 5-day avg 22,674) chahiye tha, par actual sirf 13,140 (0.58x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 382.00 | Close > 380.38 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 382.00 vs VWAP 380.83 | Close > VWAP (380.83) | - |
| #5 | 5m Slot Volume | FAIL | 13,140 vs avg 22,674 (0.58x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 34,011 shares (1.5x of 5-day avg 22,674) chahiye tha, par actual sirf 13,140 (0.58x) aaya. |
| #6 | Day RVOL | FAIL | 0.56x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 379.15, ext 0.23 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 218 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 34,011 shares (1.5x of 5-day avg 22,674) chahiye tha, par actual sirf 13,140 (0.58x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |

### [50/56] 12:10-ITC-#2 (ITC | FMCG | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_12:10_ITC_LONG_#2  |  Micro S3 File: scans/2026-11-11/12-10_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 292 | Entry Rs.285.15 | SL Rs.283.44 | Target Rs.288.57 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.999 | Slot Vol 6.15x | Day RVOL 0.96x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.96x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.96x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 285.15 | Close > 283.68 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 285.15 vs VWAP 283.21 | Close > VWAP (283.21) | - |
| #5 | 5m Slot Volume | PASS | 736,063 vs avg 119,662 (6.15x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.96x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.96x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 281.50, ext 0.29 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 292 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.96x tha. |

### [51/56] 12:10-UBL-#3 (UBL | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:10_UBL_LONG_#3  |  Micro S3 File: scans/2026-11-11/12-10_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 67 | Entry Rs.1237.90 | SL Rs.1230.47 | Target Rs.1252.75 | R:R 1:2.00 | Risk Rs.498 -> Reward Rs.995 | Slot Vol 0.21x | Day RVOL 0.55x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 2,780 shares (1.5x of 5-day avg 1,853) chahiye tha, par actual sirf 383 (0.21x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 2,780 shares (1.5x of 5-day avg 1,853) chahiye tha, par actual sirf 383 (0.21x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1237.90 | Close > 1231.13 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1237.90 vs VWAP 1231.71 | Close > VWAP (1231.71) | - |
| #5 | 5m Slot Volume | FAIL | 383 vs avg 1,853 (0.21x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 2,780 shares (1.5x of 5-day avg 1,853) chahiye tha, par actual sirf 383 (0.21x) aaya. |
| #6 | Day RVOL | FAIL | 0.55x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 1229.00, ext 0.22 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 67 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 2,780 shares (1.5x of 5-day avg 1,853) chahiye tha, par actual sirf 383 (0.21x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |

### [52/56] 12:10-INDUSINDBK-#4 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:10_INDUSINDBK_LONG_#4  |  Micro S3 File: scans/2026-11-11/12-10_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.914.80 | SL Rs.909.31 | Target Rs.925.78 | R:R 1:2.00 | Risk Rs.500 -> Reward Rs.999 | Slot Vol 1.0x | Day RVOL 2.37x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 80,839 shares (1.5x of 5-day avg 53,893) chahiye tha, par actual sirf 53,996 (1.00x) aaya. | #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 80,839 shares (1.5x of 5-day avg 53,893) chahiye tha, par actual sirf 53,996 (1.00x) aaya. | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 914.80 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 914.80 vs VWAP 907.84 | Close > VWAP (907.84) | - |
| #5 | 5m Slot Volume | FAIL | 53,996 vs avg 53,893 (1.00x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 80,839 shares (1.5x of 5-day avg 53,893) chahiye tha, par actual sirf 53,996 (1.00x) aaya. |
| #6 | Day RVOL | PASS | 2.37x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.38 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 80,839 shares (1.5x of 5-day avg 53,893) chahiye tha, par actual sirf 53,996 (1.00x) aaya. \| Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [53/56] 12:15-ITC-#1 (ITC | FMCG | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_12:15_ITC_LONG_#1  |  Micro S3 File: scans/2026-11-11/12-15_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 292 | Entry Rs.285.05 | SL Rs.283.34 | Target Rs.288.47 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.999 | Slot Vol 4.38x | Day RVOL 0.99x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.99x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.99x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 285.05 | Close > 283.68 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 285.05 vs VWAP 283.29 | Close > VWAP (283.29) | - |
| #5 | 5m Slot Volume | PASS | 644,557 vs avg 147,016 (4.38x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.99x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.99x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 281.50, ext 0.27 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 292 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.99x tha. |

### [54/56] 12:15-DABUR-#2 (DABUR | FMCG | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_12:15_DABUR_LONG_#2  |  Micro S3 File: scans/2026-11-11/12-15_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 218 | Entry Rs.382.05 | SL Rs.379.76 | Target Rs.386.63 | R:R 1:2.00 | Risk Rs.499 -> Reward Rs.998 | Slot Vol 1.68x | Day RVOL 0.56x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 382.05 | Close > 380.38 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 382.05 vs VWAP 380.85 | Close > VWAP (380.85) | - |
| #5 | 5m Slot Volume | PASS | 21,012 vs avg 12,482 (1.68x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.56x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 379.15, ext 0.23 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 218 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.56x tha. |

### [55/56] 12:15-INDUSINDBK-#3 (INDUSINDBK | Pvt Bank | LONG) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-11_12:15_INDUSINDBK_LONG_#3  |  Micro S3 File: scans/2026-11-11/12-15_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 91 | Entry Rs.911.65 | SL Rs.906.18 | Target Rs.922.59 | R:R 1:2.00 | Risk Rs.498 -> Reward Rs.996 | Slot Vol 4.3x | Day RVOL 2.4x
- **Kya & Kyun Samjha (FAILED 2/8): #7 Gap, No-Chase & Stop Risk: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Pvt Bank (Rank #2, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 911.65 | Close > 905.75 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 911.65 vs VWAP 907.97 | Close > VWAP (907.97) | - |
| #5 | 5m Slot Volume | PASS | 123,301 vs avg 28,644 (4.30x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 2.40x cumulative | >= 1.0x | - |
| #7 | Gap, No-Chase & Stop Risk | FAIL | Open 909.15, ext 0.26 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |
| #8 | Sizing & Risk Gate | FAIL | Qty 91 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: Day Open ₹909.15 pehle hi PDH (₹904.85) cross kar chuka tha |

### [56/56] 12:15-UBL-#4 (UBL | FMCG | LONG) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-11_12:15_UBL_LONG_#4  |  Micro S3 File: scans/2026-11-11/12-15_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 67 | Entry Rs.1236.90 | SL Rs.1229.48 | Target Rs.1251.74 | R:R 1:2.00 | Risk Rs.497 -> Reward Rs.994 | Slot Vol 0.36x | Day RVOL 0.55x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 2,454 shares (1.5x of 5-day avg 1,636) chahiye tha, par actual sirf 590 (0.36x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 2,454 shares (1.5x of 5-day avg 1,636) chahiye tha, par actual sirf 590 (0.36x) aaya. | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha.**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_UP | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | FMCG (Rank #3, bias +1) | STRONG (+1) | - |
| #3 | Breakout Candle | PASS | Close 1236.90 | Close > 1231.13 (PDH+0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1236.90 vs VWAP 1231.76 | Close > VWAP (1231.76) | - |
| #5 | 5m Slot Volume | FAIL | 590 vs avg 1,636 (0.36x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 2,454 shares (1.5x of 5-day avg 1,636) chahiye tha, par actual sirf 590 (0.36x) aaya. |
| #6 | Day RVOL | FAIL | 0.55x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |
| #7 | Gap, No-Chase & Stop Risk | PASS | Open 1229.00, ext 0.19 ATR, stop 0.60% | No gap-trap, ext < 0.5 ATR, stop <= 1.5%, fresh | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 67 \| REJECTED | Qty > 0 (risk ₹500, cap ₹83,333), time 09:30–14:15, limits OK | Entry Gate / Timing / Sizing rukawat: 5m Candle Volume kam tha: Minimum > 2,454 shares (1.5x of 5-day avg 1,636) chahiye tha, par actual sirf 590 (0.36x) aaya. \| Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye, actual 0.55x tha. |

## 6. Complete AWS S3 Micro Scan File Inventory (22 Compiled Micro Files)

| Bar | Micro S3 File Name | Checked | Speed | Regime | Arm | Eval (P/R) | Evaluated Signals |
| :---: | :--- | :---: | ---: | :--- | ---: | :---: | :--- |
| 09:40 | 09-40_Scan_72Stocks_2Signals_0Passed.json | 07:31:40 | 64 ms | TREND_UP | 2 | 2 (0P / 2R) | 09:40-CANBK-#1 (rejected), 09:40-UNIONBANK-#2 (rejected) |
| 09:45 | 09-45_Scan_72Stocks_2Signals_0Passed.json | 07:31:45 | 84 ms | TREND_UP | 2 | 2 (0P / 2R) | 09:45-CANBK-#1 (rejected), 09:45-UNIONBANK-#2 (rejected) |
| 09:50 | 09-50_Scan_72Stocks_1Signals_0Passed.json | 07:31:45 | 72 ms | TREND_UP | 1 | 1 (0P / 1R) | 09:50-UNIONBANK-#1 (rejected) |
| 10:55 | 10-55_Scan_72Stocks_3Signals_0Passed.json | 07:31:46 | 109 ms | TREND_UP | 3 | 3 (0P / 3R) | 10:55-INDUSINDBK-#1 (rejected), 10:55-KOTAKBANK-#2 (rejected), 10:55-ICICIBANK-#3 (rejected) |
| 11:00 | 11-00_Scan_72Stocks_3Signals_0Passed.json | 07:31:47 | 118 ms | TREND_UP | 3 | 3 (0P / 3R) | 11:00-INDUSINDBK-#1 (rejected), 11:00-KOTAKBANK-#2 (rejected), 11:00-ICICIBANK-#3 (rejected) |
| 11:05 | 11-05_Scan_72Stocks_3Signals_0Passed.json | 07:31:47 | 85 ms | TREND_UP | 3 | 3 (0P / 3R) | 11:05-INDUSINDBK-#1 (rejected), 11:05-KOTAKBANK-#2 (rejected), 11:05-ICICIBANK-#3 (rejected) |
| 11:10 | 11-10_Scan_72Stocks_3Signals_0Passed.json | 07:31:47 | 73 ms | TREND_UP | 3 | 3 (0P / 3R) | 11:10-INDUSINDBK-#1 (rejected), 11:10-KOTAKBANK-#2 (rejected), 11:10-ICICIBANK-#3 (rejected) |
| 11:15 | 11-15_Scan_72Stocks_3Signals_0Passed.json | 07:31:48 | 96 ms | TREND_UP | 3 | 3 (0P / 3R) | 11:15-INDUSINDBK-#1 (rejected), 11:15-ICICIBANK-#2 (rejected), 11:15-KOTAKBANK-#3 (rejected) |
| 11:20 | 11-20_Scan_72Stocks_3Signals_0Passed.json | 07:31:48 | 99 ms | TREND_UP | 3 | 3 (0P / 3R) | 11:20-INDUSINDBK-#1 (rejected), 11:20-KOTAKBANK-#2 (rejected), 11:20-ICICIBANK-#3 (rejected) |
| 11:25 | 11-25_Scan_72Stocks_3Signals_0Passed.json | 07:31:48 | 117 ms | TREND_UP | 3 | 3 (0P / 3R) | 11:25-INDUSINDBK-#1 (rejected), 11:25-KOTAKBANK-#2 (rejected), 11:25-ICICIBANK-#3 (rejected) |
| 11:30 | 11-30_Scan_72Stocks_3Signals_0Passed.json | 07:31:49 | 101 ms | TREND_UP | 3 | 3 (0P / 3R) | 11:30-INDUSINDBK-#1 (rejected), 11:30-ICICIBANK-#2 (rejected), 11:30-KOTAKBANK-#3 (rejected) |
| 11:35 | 11-35_Scan_72Stocks_1Signals_0Passed.json | 07:31:49 | 60 ms | TREND_UP | 1 | 1 (0P / 1R) | 11:35-INDUSINDBK-#1 (rejected) |
| 11:40 | 11-40_Scan_72Stocks_2Signals_0Passed.json | 07:31:49 | 114 ms | TREND_UP | 2 | 2 (0P / 2R) | 11:40-INDUSINDBK-#1 (rejected), 11:40-BANDHANBNK-#2 (rejected) |
| 11:45 | 11-45_Scan_72Stocks_4Signals_0Passed.json | 07:31:50 | 114 ms | TREND_UP | 4 | 4 (0P / 4R) | 11:45-DABUR-#1 (rejected), 11:45-ITC-#2 (rejected), 11:45-UBL-#3 (rejected), 11:45-INDUSINDBK-#4 (rejected) |
| 11:50 | 11-50_Scan_72Stocks_2Signals_0Passed.json | 07:31:50 | 52 ms | TREND_UP | 2 | 2 (0P / 2R) | 11:50-INDUSINDBK-#1 (rejected), 11:50-BANDHANBNK-#2 (rejected) |
| 11:55 | 11-55_Scan_72Stocks_4Signals_0Passed.json | 07:31:50 | 105 ms | TREND_UP | 4 | 4 (0P / 4R) | 11:55-DABUR-#1 (rejected), 11:55-ITC-#2 (rejected), 11:55-UBL-#3 (rejected), 11:55-MARICO-#4 (rejected) |
| 12:00 | 12-00_Scan_72Stocks_4Signals_0Passed.json | 07:31:51 | 106 ms | TREND_UP | 4 | 4 (0P / 4R) | 12:00-DABUR-#1 (rejected), 12:00-ITC-#2 (rejected), 12:00-UBL-#3 (rejected), 12:00-INDUSINDBK-#4 (rejected) |
| 12:05 | 12-05_Scan_72Stocks_2Signals_1Passed.json | 07:31:51 | 92 ms | TREND_UP | 2 | 2 (1P / 1R) | 12:05-BHARATFORG-#1 (would trade), 12:05-INDUSINDBK-#2 (rejected) |
| 12:10 | 12-10_Scan_72Stocks_4Signals_0Passed.json | 07:31:52 | 120 ms | TREND_UP | 4 | 4 (0P / 4R) | 12:10-DABUR-#1 (rejected), 12:10-ITC-#2 (rejected), 12:10-UBL-#3 (rejected), 12:10-INDUSINDBK-#4 (rejected) |
| 12:15 | 12-15_Scan_72Stocks_4Signals_0Passed.json | 07:31:52 | 112 ms | TREND_UP | 4 | 4 (0P / 4R) | 12:15-ITC-#1 (rejected), 12:15-DABUR-#2 (rejected), 12:15-INDUSINDBK-#3 (rejected), 12:15-UBL-#4 (rejected) |
| 15:30 | 15-30_Scan_72Stocks_0Signals_0Passed.json | 07:31:53 | 20 ms | CHOPPY | 0 | 0 (0P / 0R) | - |
| 16:00 | 16-00_Scan_72Stocks_0Signals_0Passed.json | 17:23:56 | 12 ms | CHOPPY | 0 | 0 (0P / 0R) | - |
