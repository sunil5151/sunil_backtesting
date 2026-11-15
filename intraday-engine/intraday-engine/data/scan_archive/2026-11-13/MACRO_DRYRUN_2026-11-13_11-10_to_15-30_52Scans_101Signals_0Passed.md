# AWS S3 MACRO COMPILED DRY-TESTING REPORT — 2026-11-13 (11:10 to 15:30 IST)

> **Mode:** `DRYRUN` | **Testing Date:** `2026-11-13` | **Window:** `11:10 IST` to `15:30 IST` | **S3 Bucket:** `sunil-trading-signals` (`ap-south-2`)

## Architecture, File Naming & Strategy Configuration

- **Macro PDF File (Compiled):** `scans/2026-11-13/MACRO_DRYRUN_2026-11-13_11-10_to_15-30_52Scans_101Signals_0Passed.pdf`
- **Macro Markdown File (Compiled):** `scans/2026-11-13/MACRO_DRYRUN_2026-11-13_11-10_to_15-30_52Scans_101Signals_0Passed.md`
- **Micro S3 Files (Alag-Alag Har 5m Candle):** `scans/2026-11-13/<HH-MM>_Scan_72Stocks_<S>Signals_<P>Passed.json` (Total `52` Micro JSON files)
- **Live vs Dry Testing Rule:** Live trading candle-by-candle real time chalta hai, isliye live me sirf Micro files banti hain (Macro nahi). Dry Testing me poora date + time period replay hota hai, isliye Micro files ke saath ye Macro `.md` + `.pdf` files banti hain.
- **Context Note:** 2026-11-11 (22 scans, 56 signals, 1 WOULD TRADE: 12:05 BHARATFORG LONG) bhi separate Giant Macro PDF + MD me compiled hai.

### Strategy: `pdh_breakout` (`strategies/pdh_breakout.py`)

- **Timeframe / Lookback:** `5m` | Lookback `50` bars | Sides `LONG, SHORT` | Active Regimes `TREND_UP, TREND_DOWN` (`CHOPPY` blocked)
- **Strategy Params:** `vwap_filter=True`, `buffer_pct=0.001`, `vol_mult=1.5x`, `rvol_min=1.0x`, `max_chase_atr=0.5`, `min_stop_pct=0.006`, `max_stop_pct=0.015`, `target_r=1:2.0`, `breakeven_at_r=+1.0R`
- **Risk Rules:** Capital `Rs.50,000` | Product `MIS` (`5.0x`) | Risk/Trade `Rs.500` (Min `Rs.300`) | Notional Cap `Rs.83,333` | Max Open `3` | Max/Sector `2` | Max/Day `6` | Daily Loss Limit `Rs.1,500`

## 1. Macro Executive Summary & 8-Check Bottleneck Analysis

| Metric | Value | Metric | Value |
| :--- | :--- | :--- | :--- |
| Testing Date & Window | 2026-11-13 (11:10 - 15:30 IST) | Micro S3 Scans Compiled | 52 JSON files (72 kept stocks/scan) |
| Total Signals Evaluated | 101 signals | Passed (WOULD TRADE) | 0 signal(s) (0.0%) |
| Rejected Signals | 101 signals (100.0%) | Regimes Observed | TREND_DOWN:52 |

### Simulated Trade Execution & Outcome

- Session Summary Log: Dry run complete for 2026-11-13: 75 bars, 0 would trade, 101 rejected. Bars discarded.
- Session Summary Log: Dry run complete for 2026-11-13: 72 bars, 0 would trade, 91 rejected. Bars discarded.

### Time-of-Day Breakdown (IST)

| Time Period (IST) | S3 Scans | Signals Eval | Passed | Rejected | Pass % |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Morning (09:15 - 11:30) | 3 | 5 | 0 | 5 | 0.0% |
| Midday (11:30 - 13:30) | 24 | 44 | 0 | 44 | 0.0% |
| Afternoon (13:30 - 15:30) | 25 | 52 | 0 | 52 | 0.0% |

### 8-Check Bottleneck Analysis (All Signals Combined)

| Step | Check Name | Passed | Failed | Pass % | Kya Samjha (Bottleneck Insight) |
| :---: | :--- | ---: | ---: | ---: | :--- |
| #1 | Market Regime | 101 | 0 | 100.0% | 100% pass - koi rukawat nahi aayi |
| #2 | Sector Strength | 101 | 0 | 100.0% | 100% pass - koi rukawat nahi aayi |
| #3 | Breakout Candle | 101 | 0 | 100.0% | 100% pass - koi rukawat nahi aayi |
| #4 | VWAP Filter | 97 | 4 | 96.0% | Moderate filter (4 fails: 3 <=14:15, 1 >14:15) |
| #5 | 5m Slot Volume | 3 | 98 | 3.0% | MAIN BOTTLENECK (98 fails: 59 <=14:15, 39 >14:15) |
| #6 | Day RVOL | 4 | 97 | 4.0% | MAIN BOTTLENECK (97 fails: 61 <=14:15, 36 >14:15) |
| #7 | Gap & No-Chase | 101 | 0 | 100.0% | 100% pass - koi rukawat nahi aayi |
| #8 | Sizing & Risk Gate | 0 | 101 | 0.0% | MAIN BOTTLENECK (101 fails: 61 <=14:15, 40 >14:15) |

## 2. Market Regime Dissection — Engine Ne Market Ko 'Kya Samjha' Aur 'Kyun Samjha'

### Box A: Engine Ka Current Formula / Approach (`engine/regime.py` + `config.yaml`)

1. **ADX(14) on 5m NIFTY:** Agar `ADX < 20` ho → Weak Trend / Choppy Vote #1.
2. **Session Mean & Crosses(12):** Typical Price `(H+L+C)/3` ka expanding mean from `09:15`. Last 12 bars me close `>= 4` baar Session Mean cross kare → Choppy Vote #2.
3. **Universe Breadth (Adv/Dec vs PDC):** Agar `0.80 <= Breadth <= 1.25` ho → Choppy Vote #3 (`>1.0` Bullish, `<1.0` Bearish).
4. **Decision Rule:** Agar `>= 2` Choppy Votes lage → `Raw = CHOPPY`. Warna agar `NIFTY Close > Session Mean & Breadth > 1.0` → `Raw = TREND_UP`; agar `NIFTY Close < Session Mean & Breadth < 1.0` → `Raw = TREND_DOWN`; warna (dono disagree karein) → `Raw = CHOPPY`.
5. **2-Bar Confirmation:** Active Regime tabhi badalta hai jab naya Raw Regime lagatar `2` consecutive 5m bars (`confirm_bars=2`) par aaye.

### Box B: Real Data Se Nikle Key Approach Insights (Baad Me Tune Karne Ke Liye)

- 1. Low-ADX Trend Calls: Is period me 37/52 scans me ADX(14) < 20 tha, fir bhi engine ne market ko TREND mana (kyunki Crosses < 4 aur Breadth 0.80-1.25 ke bahar tha, so sirf 1/3 choppy vote laga).
- 2. Raw vs Active (2-Bar Delay): 1/52 scans me Raw Regime Active Regime se alag tha (15:30 (TREND_DOWN vs raw CHOPPY)).
- 3. 'Else' Branch CHOPPY Triggers: 1/52 scans me Choppy Votes < 2 hone ke bawajood Raw=CHOPPY aaya kyunki NIFTY Close Session Mean ke doosri taraf gaya jabki Breadth alag side thi (15:30).
- 4. Note on Missing Bar Gaps: Jahan 5m bar par 0 stocks ARMED the (ya regime CHOPPY tha), wahan S3 me alag signal-scan JSON save nahi hota (isliye activity feed me unka summary dikhta hai, aur last bar hamesha save hota hai).

| Time | NIFTY% | ADX14 | SessMean | Cross | Breadth (A/D) | Kya Samjha | Kyun Samjha (Exact Inputs & Rule) |
| :---: | ---: | ---: | ---: | :---: | :---: | :--- | :--- |
| 11:10 | -0.44% | 12.60 | 25191.1 | 1 | 0.543 (25/46) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25191.12) & Breadth 0.543 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=12.6<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:15 | -0.52% | 12.86 | 25190.5 | 1 | 0.511 (24/47) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25190.55) & Breadth 0.511 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=12.86<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:20 | -0.49% | 13.30 | 25189.9 | 1 | 0.440 (22/50) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25189.86) & Breadth 0.44 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=13.3<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:30 | -0.50% | 13.37 | 25189.0 | 1 | 0.385 (20/52) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25188.97) & Breadth 0.385 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=13.37<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:35 | -0.50% | 13.66 | 25188.3 | 1 | 0.365 (19/52) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25188.32) & Breadth 0.365 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=13.66<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:40 | -0.52% | 14.26 | 25187.5 | 1 | 0.333 (18/54) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25187.53) & Breadth 0.333 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=14.26<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:45 | -0.55% | 14.82 | 25186.8 | 1 | 0.333 (18/54) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25186.75) & Breadth 0.333 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=14.82<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:50 | -0.59% | 15.86 | 25185.6 | 1 | 0.333 (18/54) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25185.61) & Breadth 0.333 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=15.86<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 11:55 | -0.61% | 16.82 | 25184.5 | 1 | 0.286 (16/56) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25184.51) & Breadth 0.286 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=16.82<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 12:00 | -0.60% | 18.08 | 25183.2 | 0 | 0.315 (17/54) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25183.25) & Breadth 0.315 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=18.08<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 12:05 | -0.65% | 18.50 | 25182.0 | 0 | 0.309 (17/55) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25182.02) & Breadth 0.309 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=18.5<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 12:10 | -0.72% | 19.58 | 25180.3 | 0 | 0.220 (13/59) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25180.32) & Breadth 0.22 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=19.58<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 12:15 | -0.80% | 21.05 | 25178.2 | 0 | 0.200 (12/60) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25178.21) & Breadth 0.2 < 1.0 -> Raw=TREND_DOWN. |
| 12:20 | -0.85% | 22.82 | 25175.8 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25175.76) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. |
| 12:25 | -0.78% | 23.72 | 25173.7 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25173.7) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. |
| 12:30 | -0.74% | 23.85 | 25172.0 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25172.04) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. |
| 12:35 | -0.75% | 23.95 | 25170.5 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25170.53) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. |
| 12:40 | -0.71% | 23.33 | 25169.3 | 0 | 0.183 (11/60) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25169.3) & Breadth 0.183 < 1.0 -> Raw=TREND_DOWN. |
| 12:45 | -0.75% | 22.75 | 25168.0 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25168.01) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. |
| 12:50 | -0.80% | 22.74 | 25166.5 | 0 | 0.164 (10/61) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25166.47) & Breadth 0.164 < 1.0 -> Raw=TREND_DOWN. |
| 12:55 | -0.76% | 22.49 | 25165.1 | 0 | 0.164 (10/61) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25165.09) & Breadth 0.164 < 1.0 -> Raw=TREND_DOWN. |
| 13:00 | -0.74% | 22.00 | 25163.9 | 0 | 0.183 (11/60) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25163.92) & Breadth 0.183 < 1.0 -> Raw=TREND_DOWN. |
| 13:05 | -0.72% | 21.55 | 25162.8 | 0 | 0.183 (11/60) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25162.83) & Breadth 0.183 < 1.0 -> Raw=TREND_DOWN. |
| 13:10 | -0.74% | 20.86 | 25161.8 | 0 | 0.200 (12/60) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25161.79) & Breadth 0.2 < 1.0 -> Raw=TREND_DOWN. |
| 13:15 | -0.73% | 20.08 | 25160.8 | 0 | 0.246 (14/57) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25160.84) & Breadth 0.246 < 1.0 -> Raw=TREND_DOWN. |
| 13:20 | -0.66% | 18.66 | 25160.1 | 0 | 0.220 (13/59) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25160.13) & Breadth 0.22 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=18.66<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 13:25 | -0.69% | 17.59 | 25159.5 | 0 | 0.241 (14/58) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25159.5) & Breadth 0.241 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.59<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 13:30 | -0.71% | 16.38 | 25158.8 | 0 | 0.241 (14/58) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25158.8) & Breadth 0.241 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=16.38<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 13:35 | -0.74% | 16.03 | 25157.9 | 0 | 0.180 (11/61) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25157.93) & Breadth 0.18 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=16.03<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 13:40 | -0.69% | 15.08 | 25157.3 | 0 | 0.200 (12/60) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25157.26) & Breadth 0.2 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=15.08<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 13:45 | -0.75% | 14.89 | 25156.4 | 0 | 0.180 (11/61) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25156.41) & Breadth 0.18 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=14.89<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 13:50 | -0.84% | 15.39 | 25155.3 | 0 | 0.180 (11/61) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25155.3) & Breadth 0.18 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=15.39<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 13:55 | -0.85% | 16.05 | 25154.1 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25154.08) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=16.05<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:00 | -0.80% | 16.29 | 25153.0 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25153.01) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=16.29<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:05 | -0.88% | 16.84 | 25151.8 | 0 | 0.108 (7/65) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25151.81) & Breadth 0.108 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=16.84<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:10 | -0.86% | 17.36 | 25150.6 | 0 | 0.125 (8/64) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25150.6) & Breadth 0.125 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.36<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:15 | -0.89% | 17.48 | 25149.4 | 0 | 0.108 (7/65) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25149.39) & Breadth 0.108 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.48<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:20 | -0.90% | 17.83 | 25148.1 | 0 | 0.108 (7/65) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25148.14) & Breadth 0.108 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.83<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:25 | -0.90% | 18.91 | 25146.8 | 0 | 0.108 (7/65) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25146.83) & Breadth 0.108 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=18.91<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:30 | -0.84% | 18.63 | 25145.8 | 0 | 0.125 (8/64) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25145.82) & Breadth 0.125 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=18.63<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:35 | -0.78% | 17.63 | 25145.1 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25145.1) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.63<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:40 | -0.74% | 17.41 | 25144.6 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25144.57) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.41<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:45 | -0.76% | 17.21 | 25144.0 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25144.03) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.21<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:50 | -0.73% | 17.21 | 25143.6 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25143.58) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.21<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 14:55 | -0.72% | 17.20 | 25143.2 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25143.17) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.2<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 15:00 | -0.75% | 17.80 | 25142.8 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25142.78) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.8<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 15:05 | -0.76% | 17.46 | 25142.2 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25142.25) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.46<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 15:10 | -0.72% | 17.43 | 25141.8 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25141.83) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=17.43<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 15:15 | -0.63% | 18.55 | 25141.7 | 0 | 0.143 (9/63) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25141.7) & Breadth 0.143 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=18.55<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 15:20 | -0.63% | 19.59 | 25141.7 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 1/3 (<2); NIFTY < SessMean (25141.66) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. [Note: ADX=19.59<20 tha, fir bhi TREND mana kyunki 2/3 votes nahi lage] |
| 15:25 | -0.63% | 20.56 | 25141.6 | 0 | 0.161 (10/62) | Active: TREND_DOWN<br>(Raw: TREND_DOWN) | Choppy 0/3 (<2); NIFTY < SessMean (25141.63) & Breadth 0.161 < 1.0 -> Raw=TREND_DOWN. |
| 15:30 | -0.61% | 21.68 | 25141.6 | 1 | 0.145 (9/62) | Active: TREND_DOWN<br>(Raw: CHOPPY) | Choppy 0/3 (<2), par NIFTY Close bounced above SessMean 25141.64 while Breadth 0.145 < 1.0 -> 'else' branch se Raw=CHOPPY. [2-Bar Confirm: Raw CHOPPY abhi 1st bar pe hai, isliye Active TREND_DOWN raha] |

## 3. Sector Rotation Dissection — Engine Ne Sectors Ko 'Kya Samjha' Aur 'Kyun Samjha'

> `Sector Return % = median(member return vs PDC)` | `RS % = Sector Return % - NIFTY %` | `Top-3 > +0.25% = STRONG`, `Bottom-3 < -0.25% = WEAK`.

| Sector (Eligible) | STRONG Scans | WEAK Scans | NEUTRAL Scans | RS % Range (Period) | Avg RS % |
| :--- | ---: | ---: | ---: | :---: | ---: |
| FMCG | 48 | 0 | 4 | +0.14% to +0.82% | +0.55% |
| IT | 43 | 0 | 9 | -0.02% to +0.73% | +0.36% |
| Pharma | 16 | 0 | 36 | -0.56% to +0.77% | +0.24% |
| PSU Bank | 18 | 8 | 26 | -0.38% to +0.58% | +0.11% |
| Metal | 0 | 1 | 51 | -0.44% to +0.24% | -0.14% |
| Energy | 1 | 9 | 42 | -0.65% to +0.42% | -0.16% |
| Pvt Bank | 0 | 43 | 9 | -0.63% to -0.15% | -0.43% |
| Auto | 0 | 48 | 4 | -1.01% to -0.15% | -0.47% |
| Realty | 0 | 33 | 19 | -1.08% to +0.17% | -0.49% |

### Sector Snapshot @ 11:10 IST | Regime: `TREND_DOWN` | NIFTY: `-0.44%`

| Rank | Sector | Stocks | Med Ret% | RS % | Kya Samjha | Kyun Samjha (RS Formula & Cut) |
| :---: | :--- | ---: | ---: | ---: | :---: | :--- |
| #1 | IT | 9 | +0.29% | +0.73% | STRONG | Rank #1 (Top-3) & RS +0.73% > +0.25% (Ret +0.29% vs NIFTY -0.44%) -> STRONG (LONG allowed) |
| #2 | FMCG | 10 | +0.18% | +0.62% | STRONG | Rank #2 (Top-3) & RS +0.62% > +0.25% (Ret +0.18% vs NIFTY -0.44%) -> STRONG (LONG allowed) |
| #3 | Pharma | 7 | +0.02% | +0.46% | STRONG | Rank #3 (Top-3) & RS +0.46% > +0.25% (Ret +0.02% vs NIFTY -0.44%) -> STRONG (LONG allowed) |
| #4 | Metal | 9 | -0.20% | +0.24% | NEUTRAL | Rank #4, RS +0.24% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #5 | Energy | 9 | -0.22% | +0.22% | NEUTRAL | Rank #5, RS +0.22% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #6 | Realty | 6 | -0.27% | +0.17% | NEUTRAL | Rank #6, RS +0.17% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #7 | PSU Bank | 7 | -0.62% | -0.18% | NEUTRAL | Rank #7, RS -0.18% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #8 | Auto | 6 | -0.69% | -0.25% | NEUTRAL | Rank #8, RS -0.25% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #9 | Pvt Bank | 9 | -0.87% | -0.43% | WEAK | Rank #9 (Bottom-3) & RS -0.43% < -0.25% (Ret -0.87% vs NIFTY -0.44%) -> WEAK (SHORT allowed) |

### Sector Snapshot @ 13:25 IST | Regime: `TREND_DOWN` | NIFTY: `-0.69%`

| Rank | Sector | Stocks | Med Ret% | RS % | Kya Samjha | Kyun Samjha (RS Formula & Cut) |
| :---: | :--- | ---: | ---: | ---: | :---: | :--- |
| #1 | FMCG | 10 | +0.02% | +0.71% | STRONG | Rank #1 (Top-3) & RS +0.71% > +0.25% (Ret +0.02% vs NIFTY -0.69%) -> STRONG (LONG allowed) |
| #2 | IT | 9 | -0.13% | +0.56% | STRONG | Rank #2 (Top-3) & RS +0.56% > +0.25% (Ret -0.13% vs NIFTY -0.69%) -> STRONG (LONG allowed) |
| #3 | PSU Bank | 7 | -0.33% | +0.36% | STRONG | Rank #3 (Top-3) & RS +0.36% > +0.25% (Ret -0.33% vs NIFTY -0.69%) -> STRONG (LONG allowed) |
| #4 | Pharma | 7 | -0.55% | +0.14% | NEUTRAL | Rank #4, RS +0.14% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #5 | Metal | 9 | -0.59% | +0.10% | NEUTRAL | Rank #5, RS +0.10% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #6 | Energy | 9 | -0.91% | -0.22% | NEUTRAL | Rank #6, RS -0.22% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #7 | Auto | 6 | -1.02% | -0.33% | WEAK | Rank #7 (Bottom-3) & RS -0.33% < -0.25% (Ret -1.02% vs NIFTY -0.69%) -> WEAK (SHORT allowed) |
| #8 | Pvt Bank | 9 | -1.09% | -0.40% | WEAK | Rank #8 (Bottom-3) & RS -0.40% < -0.25% (Ret -1.09% vs NIFTY -0.69%) -> WEAK (SHORT allowed) |
| #9 | Realty | 6 | -1.11% | -0.42% | WEAK | Rank #9 (Bottom-3) & RS -0.42% < -0.25% (Ret -1.11% vs NIFTY -0.69%) -> WEAK (SHORT allowed) |

### Sector Snapshot @ 15:30 IST | Regime: `TREND_DOWN` | NIFTY: `-0.61%`

| Rank | Sector | Stocks | Med Ret% | RS % | Kya Samjha | Kyun Samjha (RS Formula & Cut) |
| :---: | :--- | ---: | ---: | ---: | :---: | :--- |
| #1 | FMCG | 10 | -0.47% | +0.14% | NEUTRAL | Rank #1, RS +0.14% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #2 | IT | 9 | -0.63% | -0.02% | NEUTRAL | Rank #2, RS -0.02% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #3 | PSU Bank | 7 | -0.68% | -0.07% | NEUTRAL | Rank #3, RS -0.07% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #4 | Metal | 9 | -0.70% | -0.09% | NEUTRAL | Rank #4, RS -0.09% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #5 | Pvt Bank | 9 | -0.89% | -0.28% | NEUTRAL | Rank #5, RS -0.28% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #6 | Pharma | 7 | -1.17% | -0.56% | NEUTRAL | Rank #6, RS -0.56% threshold (+/-0.25%) ya Top-3/Bottom-3 cut ke bahar -> NEUTRAL (Filtered) |
| #7 | Energy | 9 | -1.21% | -0.60% | WEAK | Rank #7 (Bottom-3) & RS -0.60% < -0.25% (Ret -1.21% vs NIFTY -0.61%) -> WEAK (SHORT allowed) |
| #8 | Realty | 6 | -1.34% | -0.73% | WEAK | Rank #8 (Bottom-3) & RS -0.73% < -0.25% (Ret -1.34% vs NIFTY -0.61%) -> WEAK (SHORT allowed) |
| #9 | Auto | 6 | -1.62% | -1.01% | WEAK | Rank #9 (Bottom-3) & RS -1.01% < -0.25% (Ret -1.62% vs NIFTY -0.61%) -> WEAK (SHORT allowed) |

## 4. Scanner Funnel & Complete 72-Stock Dissection ('Kya Samjha' & 'Kyun Samjha')

> Showing full 72-stock dissection for closing scan @ 15:30 IST.

- **Funnel @ 15:30:** Universe `104` -> Kept `72` (Dropped `32`) -> Sector Filtered `51` -> Far (>0.5 ATR) `10` -> Outside Top-5 `6` -> Shortlisted `5` -> Armed `4` -> Evaluated `4` (`0` Passed)
- **Most Frequently ARMED Stocks (52 Scans):** ICICIBANK (31x), RBLBANK (13x), M&M (12x), TMPV (12x), BALKRISIND (8x), MOTHERSON (8x), FEDERALBNK (7x), ADANIGREEN (4x), AXISBANK (2x), ASHOKLEY (1x), SAIL (1x), IOC (1x)
- **Most Frequently SHORTLISTED (Near Arm) Stocks:** HDFCBANK (36x), RBLBANK (29x), BANDHANBNK (18x), MOTHERSON (15x), FEDERALBNK (10x), BHARATFORG (10x), KOTAKBANK (7x), INDIANB (7x), GAIL (7x), ICICIBANK (6x), ADANIGREEN (5x), BALKRISIND (3x)

| Try# | Symbol (Sector) | Stage (Kya) | Levels (Rs.) | Kyun Samjha (Why Taken / Why Not Taken) + Min Condition |
| :---: | :--- | :---: | :--- | :--- |
| #1 | ADANIGREEN<br>(Energy: WEAK) | ARMED | LTP: 1403.00<br>PDH: 1426.4<br>PDL: 1406.0<br>ATR: 43.15 | ARMED par Signal REJECTED (6/8 checks pass, 2 fail): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 18,839 shares (1.5x of 5-day avg 12,559) chahiye tha, par actual sirf 8,804 shares (0.70x) aaya. \| #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1406.00 ke 0.5 ATR (₹21.57) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1407.41) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #2 | BALKRISIND<br>(Auto: WEAK) | ARMED | LTP: 2266.90<br>PDH: 2334.2<br>PDL: 2281.0<br>ATR: 67.06 | ARMED par Signal REJECTED (5/8 checks pass, 3 fail): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 10,732 shares (1.5x of 5-day avg 7,154) chahiye tha, par actual sirf 8,772 shares (1.23x) aaya. \| #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. \| #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹2281.00 ke 0.5 ATR (₹33.53) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹2283.28) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #3 | IOC<br>(Energy: WEAK) | ARMED | LTP: 144.04<br>PDH: 148.35<br>PDL: 145.05<br>ATR: 3.31 | ARMED par Signal REJECTED (4/8 checks pass, 4 fail): #4 VWAP Filter: Candle Close ₹144.04 VWAP (₹144.02) ke galat side tha (Close < VWAP (144.02) chahiye tha). \| #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,032,045 shares (1.5x of 5-day avg 688,030) chahiye tha, par actual sirf 624,001 shares (0.91x) aaya. \| #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. \| #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹145.05 ke 0.5 ATR (₹1.66) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹145.20) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #4 | POWERGRID<br>(Energy: WEAK) | ARMED | LTP: 257.45<br>PDH: 264.5<br>PDL: 258.5<br>ATR: 6.33 | ARMED par Signal REJECTED (5/8 checks pass, 3 fail): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,333,850 shares (1.5x of 5-day avg 889,233) chahiye tha, par actual sirf 759,448 shares (0.85x) aaya. \| #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.41x tha. \| #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹258.50 ke 0.5 ATR (₹3.17) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹258.76) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #5 | MOTHERSON<br>(Auto: WEAK) | SHORTLIST | LTP: 164.80<br>PDH: 169.37<br>PDL: 164.86<br>ATR: 5.57 | Top-5 Shortlist me tha (Score 1.61, Prox -0.011 ATR), par Armed nahi hua kyunki LTP ₹164.80 abhi arm level (<= ₹165.02) tak nahi pahuncha.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹164.86 ke 0.5 ATR (₹2.79) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹165.02) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #6 | BHARATFORG<br>(Auto: WEAK) | OUTSIDE_TOP5 | LTP: 1750.50<br>PDH: 1794.4<br>PDL: 1738.8<br>ATR: 53.76 | Level ke paas tha (0.22 ATR <= 0.50 ATR), par Top-5 Shortlist score me nahi aaya (aur stocks zyada paas the).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1738.80 ke 0.5 ATR (₹26.88) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1740.54) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #7 | GAIL<br>(Energy: WEAK) | OUTSIDE_TOP5 | LTP: 188.00<br>PDH: 189.36<br>PDL: 186.71<br>ATR: 4.07 | Level ke paas tha (0.32 ATR <= 0.50 ATR), par Top-5 Shortlist score me nahi aaya (aur stocks zyada paas the).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹186.71 ke 0.5 ATR (₹2.04) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹186.90) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #8 | M&M<br>(Auto: WEAK) | OUTSIDE_TOP5 | LTP: 3333.00<br>PDH: 3429.9<br>PDL: 3368.0<br>ATR: 81.58 | Level ke paas tha (0.43 ATR <= 0.50 ATR), par Top-5 Shortlist score me nahi aaya (aur stocks zyada paas the).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹3368.00 ke 0.5 ATR (₹40.79) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹3371.37) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #9 | NTPC<br>(Energy: WEAK) | OUTSIDE_TOP5 | LTP: 319.10<br>PDH: 327.45<br>PDL: 321.85<br>ATR: 7.46 | Level ke paas tha (0.37 ATR <= 0.50 ATR), par Top-5 Shortlist score me nahi aaya (aur stocks zyada paas the).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹321.85 ke 0.5 ATR (₹3.73) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹322.17) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #10 | ONGC<br>(Energy: WEAK) | OUTSIDE_TOP5 | LTP: 225.00<br>PDH: 227.75<br>PDL: 224.01<br>ATR: 4.92 | Level ke paas tha (0.20 ATR <= 0.50 ATR), par Top-5 Shortlist score me nahi aaya (aur stocks zyada paas the).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹224.01 ke 0.5 ATR (₹2.46) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹224.23) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #11 | RELIANCE<br>(Energy: WEAK) | OUTSIDE_TOP5 | LTP: 1339.70<br>PDH: 1342.5<br>PDL: 1330.9<br>ATR: 28.19 | Level ke paas tha (0.31 ATR <= 0.50 ATR), par Top-5 Shortlist score me nahi aaya (aur stocks zyada paas the).<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1330.90 ke 0.5 ATR (₹14.10) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1332.23) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #12 | ASHOKLEY<br>(Auto: WEAK) | FAR_FROM_LEVEL | LTP: 169.20<br>PDH: 175.99<br>PDL: 172.25<br>ATR: 5.16 | Breakout level (PDL ₹172.25) se bahut door tha: Actual distance 0.59 ATR (₹3.05), jabki Shortlist ke liye <= 0.50 ATR (<= ₹2.58) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹172.25 ke 0.5 ATR (₹2.58) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹172.42) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #13 | BPCL<br>(Energy: WEAK) | FAR_FROM_LEVEL | LTP: 302.00<br>PDH: 316.75<br>PDL: 309.85<br>ATR: 8.09 | Breakout level (PDL ₹309.85) se bahut door tha: Actual distance 0.97 ATR (₹7.85), jabki Shortlist ke liye <= 0.50 ATR (<= ₹4.04) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹309.85 ke 0.5 ATR (₹4.04) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹310.16) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #14 | DLF<br>(Realty: WEAK) | FAR_FROM_LEVEL | LTP: 758.75<br>PDH: 770.45<br>PDL: 740.0<br>ATR: 18.53 | Breakout level (PDL ₹740.00) se bahut door tha: Actual distance 1.01 ATR (₹18.75), jabki Shortlist ke liye <= 0.50 ATR (<= ₹9.27) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹740.00 ke 0.5 ATR (₹9.27) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹740.74) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #15 | GODREJPROP<br>(Realty: WEAK) | FAR_FROM_LEVEL | LTP: 1854.90<br>PDH: 1881.0<br>PDL: 1792.0<br>ATR: 58.76 | Breakout level (PDL ₹1792.00) se bahut door tha: Actual distance 1.07 ATR (₹62.90), jabki Shortlist ke liye <= 0.50 ATR (<= ₹29.38) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1792.00 ke 0.5 ATR (₹29.38) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1793.79) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #16 | LODHA<br>(Realty: WEAK) | FAR_FROM_LEVEL | LTP: 1220.00<br>PDH: 1227.8<br>PDL: 1170.3<br>ATR: 43.33 | Breakout level (PDL ₹1170.30) se bahut door tha: Actual distance 1.15 ATR (₹49.70), jabki Shortlist ke liye <= 0.50 ATR (<= ₹21.66) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1170.30 ke 0.5 ATR (₹21.66) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1171.47) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #17 | OBEROIRLTY<br>(Realty: WEAK) | FAR_FROM_LEVEL | LTP: 1797.60<br>PDH: 1834.0<br>PDL: 1740.6<br>ATR: 50.35 | Breakout level (PDL ₹1740.60) se bahut door tha: Actual distance 1.13 ATR (₹57.00), jabki Shortlist ke liye <= 0.50 ATR (<= ₹25.18) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1740.60 ke 0.5 ATR (₹25.18) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1742.34) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #18 | PHOENIXLTD<br>(Realty: WEAK) | FAR_FROM_LEVEL | LTP: 2255.00<br>PDH: 2292.0<br>PDL: 2158.5<br>ATR: 66.65 | Breakout level (PDL ₹2158.50) se bahut door tha: Actual distance 1.45 ATR (₹96.50), jabki Shortlist ke liye <= 0.50 ATR (<= ₹33.33) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹2158.50 ke 0.5 ATR (₹33.33) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹2160.66) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #19 | PRESTIGE<br>(Realty: WEAK) | FAR_FROM_LEVEL | LTP: 1650.00<br>PDH: 1695.2<br>PDL: 1601.5<br>ATR: 53.76 | Breakout level (PDL ₹1601.50) se bahut door tha: Actual distance 0.90 ATR (₹48.50), jabki Shortlist ke liye <= 0.50 ATR (<= ₹26.88) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1601.50 ke 0.5 ATR (₹26.88) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1603.10) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #20 | TATAPOWER<br>(Energy: WEAK) | FAR_FROM_LEVEL | LTP: 348.00<br>PDH: 367.4<br>PDL: 355.15<br>ATR: 8.91 | Breakout level (PDL ₹355.15) se bahut door tha: Actual distance 0.80 ATR (₹7.15), jabki Shortlist ke liye <= 0.50 ATR (<= ₹4.46) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹355.15 ke 0.5 ATR (₹4.46) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹355.51) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #21 | TMPV<br>(Auto: WEAK) | FAR_FROM_LEVEL | LTP: 287.40<br>PDH: 301.85<br>PDL: 293.6<br>ATR: 7.25 | Breakout level (PDL ₹293.60) se bahut door tha: Actual distance 0.86 ATR (₹6.20), jabki Shortlist ke liye <= 0.50 ATR (<= ₹3.62) chahiye.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹293.60 ke 0.5 ATR (₹3.62) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹293.89) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #22 | ADANIENT<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 2688.00<br>PDH: 2758.1<br>PDL: 2719.5<br>ATR: 73.41 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹2719.50 ke 0.5 ATR (₹36.70) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹2722.22) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #23 | AUBANK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 967.00<br>PDH: 981.8<br>PDL: 947.5<br>ATR: 30.69 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹947.50 ke 0.5 ATR (₹15.35) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹948.45) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #24 | AUROPHARMA<br>(Pharma: NEUTRAL) | SECTOR_FILTERED | LTP: 1823.20<br>PDH: 1821.1<br>PDL: 1785.4<br>ATR: 43.11 | Sector 'Pharma' abhi NEUTRAL hai (Rank #6, RS -0.56%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1785.40 ke 0.5 ATR (₹21.55) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1787.19) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #25 | AXISBANK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 1331.00<br>PDH: 1354.1<br>PDL: 1334.0<br>ATR: 28.99 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1334.00 ke 0.5 ATR (₹14.49) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1335.33) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #26 | BANDHANBNK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 172.88<br>PDH: 178.5<br>PDL: 171.77<br>ATR: 6.48 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹171.77 ke 0.5 ATR (₹3.24) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹171.94) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #27 | BANKBARODA<br>(PSU Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 273.84<br>PDH: 276.85<br>PDL: 272.87<br>ATR: 6.43 | Sector 'PSU Bank' abhi NEUTRAL hai (Rank #3, RS -0.07%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹272.87 ke 0.5 ATR (₹3.21) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹273.14) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #28 | BANKINDIA<br>(PSU Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 154.10<br>PDH: 151.95<br>PDL: 149.23<br>ATR: 4.12 | Sector 'PSU Bank' abhi NEUTRAL hai (Rank #3, RS -0.07%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹149.23 ke 0.5 ATR (₹2.06) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹149.38) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #29 | BIOCON<br>(Pharma: NEUTRAL) | SECTOR_FILTERED | LTP: 364.05<br>PDH: 372.2<br>PDL: 365.1<br>ATR: 9.27 | Sector 'Pharma' abhi NEUTRAL hai (Rank #6, RS -0.56%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹365.10 ke 0.5 ATR (₹4.63) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹365.47) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #30 | BRITANNIA<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 4750.50<br>PDH: 4845.0<br>PDL: 4783.3<br>ATR: 111.98 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹4783.30 ke 0.5 ATR (₹55.99) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹4788.08) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #31 | CANBK<br>(PSU Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 130.91<br>PDH: 133.25<br>PDL: 131.12<br>ATR: 3.19 | Sector 'PSU Bank' abhi NEUTRAL hai (Rank #3, RS -0.07%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹131.12 ke 0.5 ATR (₹1.59) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹131.25) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #32 | CIPLA<br>(Pharma: NEUTRAL) | SECTOR_FILTERED | LTP: 1391.80<br>PDH: 1420.0<br>PDL: 1399.5<br>ATR: 25.07 | Sector 'Pharma' abhi NEUTRAL hai (Rank #6, RS -0.56%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1399.50 ke 0.5 ATR (₹12.54) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1400.90) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #33 | COALINDIA<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 403.50<br>PDH: 406.5<br>PDL: 402.65<br>ATR: 8.6 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹402.65 ke 0.5 ATR (₹4.30) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹403.05) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #34 | COFORGE<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 2028.00<br>PDH: 2039.0<br>PDL: 1983.1<br>ATR: 64.56 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1983.10 ke 0.5 ATR (₹32.28) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1985.08) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #35 | COLPAL<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1714.00<br>PDH: 1758.6<br>PDL: 1721.4<br>ATR: 44.85 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1721.40 ke 0.5 ATR (₹22.43) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1723.12) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #36 | DABUR<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 380.50<br>PDH: 386.65<br>PDL: 380.4<br>ATR: 9.07 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹380.40 ke 0.5 ATR (₹4.54) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹380.78) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #37 | DRREDDY<br>(Pharma: NEUTRAL) | SECTOR_FILTERED | LTP: 1380.00<br>PDH: 1389.8<br>PDL: 1371.9<br>ATR: 25.91 | Sector 'Pharma' abhi NEUTRAL hai (Rank #6, RS -0.56%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1371.90 ke 0.5 ATR (₹12.96) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1373.27) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #38 | FEDERALBNK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 360.95<br>PDH: 365.75<br>PDL: 360.0<br>ATR: 9.11 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹360.00 ke 0.5 ATR (₹4.55) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹360.36) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #39 | GODREJCP<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 870.75<br>PDH: 884.2<br>PDL: 870.15<br>ATR: 22.37 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹870.15 ke 0.5 ATR (₹11.19) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹871.02) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #40 | HCLTECH<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 1378.00<br>PDH: 1399.0<br>PDL: 1372.4<br>ATR: 37.83 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1372.40 ke 0.5 ATR (₹18.91) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1373.77) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #41 | HDFCBANK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 804.00<br>PDH: 815.0<br>PDL: 798.65<br>ATR: 17.37 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹798.65 ke 0.5 ATR (₹8.69) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹799.45) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #42 | HINDALCO<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 943.60<br>PDH: 971.0<br>PDL: 953.7<br>ATR: 25.02 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹953.70 ke 0.5 ATR (₹12.51) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹954.65) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #43 | HINDUNILVR<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1992.90<br>PDH: 2011.1<br>PDL: 1969.0<br>ATR: 41.97 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1969.00 ke 0.5 ATR (₹20.98) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1970.97) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #44 | ICICIBANK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 1583.60<br>PDH: 1592.5<br>PDL: 1572.3<br>ATR: 31.91 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1572.30 ke 0.5 ATR (₹15.96) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1573.87) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #45 | INDIANB<br>(PSU Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 932.85<br>PDH: 948.4<br>PDL: 933.1<br>ATR: 23.28 | Sector 'PSU Bank' abhi NEUTRAL hai (Rank #3, RS -0.07%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹933.10 ke 0.5 ATR (₹11.64) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹934.03) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #46 | INDUSINDBK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 914.40<br>PDH: 931.9<br>PDL: 898.55<br>ATR: 26.4 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹898.55 ke 0.5 ATR (₹13.20) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹899.45) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #47 | INFY<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 1141.50<br>PDH: 1154.8<br>PDL: 1134.8<br>ATR: 35.53 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1134.80 ke 0.5 ATR (₹17.77) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1135.93) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #48 | ITC<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 285.00<br>PDH: 290.25<br>PDL: 283.65<br>ATR: 6.31 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹283.65 ke 0.5 ATR (₹3.15) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹283.93) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #49 | JINDALSTEL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 1157.80<br>PDH: 1172.2<br>PDL: 1155.0<br>ATR: 28.6 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1155.00 ke 0.5 ATR (₹14.30) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1156.15) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #50 | JSWSTEEL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 1348.00<br>PDH: 1366.7<br>PDL: 1343.8<br>ATR: 30.29 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1343.80 ke 0.5 ATR (₹15.14) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1345.14) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #51 | KOTAKBANK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 488.55<br>PDH: 494.05<br>PDL: 484.35<br>ATR: 10.37 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹484.35 ke 0.5 ATR (₹5.18) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹484.83) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #52 | LTM<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 4256.40<br>PDH: 4309.4<br>PDL: 4178.4<br>ATR: 138.28 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹4178.40 ke 0.5 ATR (₹69.14) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹4182.58) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #53 | LTTS<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 4240.00<br>PDH: 4316.9<br>PDL: 4206.4<br>ATR: 138.15 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹4206.40 ke 0.5 ATR (₹69.08) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹4210.61) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #54 | LUPIN<br>(Pharma: NEUTRAL) | SECTOR_FILTERED | LTP: 1980.30<br>PDH: 2030.9<br>PDL: 2006.0<br>ATR: 38.54 | Sector 'Pharma' abhi NEUTRAL hai (Rank #6, RS -0.56%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹2006.00 ke 0.5 ATR (₹19.27) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹2008.01) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #55 | MARICO<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 900.00<br>PDH: 915.0<br>PDL: 897.5<br>ATR: 20.68 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹897.50 ke 0.5 ATR (₹10.34) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹898.40) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #56 | MPHASIS<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 2455.00<br>PDH: 2418.9<br>PDL: 2364.0<br>ATR: 89.89 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹2364.00 ke 0.5 ATR (₹44.95) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹2366.36) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #57 | NATIONALUM<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 330.00<br>PDH: 334.75<br>PDL: 324.6<br>ATR: 10.35 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹324.60 ke 0.5 ATR (₹5.17) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹324.92) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #58 | NESTLEIND<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1263.20<br>PDH: 1280.6<br>PDL: 1260.3<br>ATR: 34.11 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1260.30 ke 0.5 ATR (₹17.05) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1261.56) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #59 | PNB<br>(PSU Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 142.81<br>PDH: 143.8<br>PDL: 137.76<br>ATR: 3.77 | Sector 'PSU Bank' abhi NEUTRAL hai (Rank #3, RS -0.07%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹137.76 ke 0.5 ATR (₹1.89) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹137.90) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #60 | RBLBANK<br>(Pvt Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 385.75<br>PDH: 394.5<br>PDL: 384.6<br>ATR: 11.63 | Sector 'Pvt Bank' abhi NEUTRAL hai (Rank #5, RS -0.28%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹384.60 ke 0.5 ATR (₹5.82) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹384.98) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #61 | SAIL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 176.20<br>PDH: 181.2<br>PDL: 175.86<br>ATR: 5.79 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹175.86 ke 0.5 ATR (₹2.90) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹176.04) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #62 | SBIN<br>(PSU Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 1080.00<br>PDH: 1089.0<br>PDL: 1058.5<br>ATR: 22.96 | Sector 'PSU Bank' abhi NEUTRAL hai (Rank #3, RS -0.07%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1058.50 ke 0.5 ATR (₹11.48) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1059.56) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #63 | SUNPHARMA<br>(Pharma: NEUTRAL) | SECTOR_FILTERED | LTP: 1880.00<br>PDH: 1896.8<br>PDL: 1874.4<br>ATR: 43.23 | Sector 'Pharma' abhi NEUTRAL hai (Rank #6, RS -0.56%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1874.40 ke 0.5 ATR (₹21.61) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1876.27) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #64 | TATACONSUM<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1079.00<br>PDH: 1096.4<br>PDL: 1077.4<br>ATR: 23.01 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1077.40 ke 0.5 ATR (₹11.51) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1078.48) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #65 | TATASTEEL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 186.68<br>PDH: 190.65<br>PDL: 187.56<br>ATR: 5.09 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹187.56 ke 0.5 ATR (₹2.54) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹187.75) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #66 | TCS<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 2407.50<br>PDH: 2472.0<br>PDL: 2422.5<br>ATR: 64.04 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹2422.50 ke 0.5 ATR (₹32.02) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹2424.92) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #67 | TECHM<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 1764.00<br>PDH: 1790.0<br>PDL: 1761.0<br>ATR: 45.72 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1761.00 ke 0.5 ATR (₹22.86) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1762.76) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #68 | TORNTPHARM<br>(Pharma: NEUTRAL) | SECTOR_FILTERED | LTP: 4670.00<br>PDH: 4765.1<br>PDL: 4660.0<br>ATR: 100.97 | Sector 'Pharma' abhi NEUTRAL hai (Rank #6, RS -0.56%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹4660.00 ke 0.5 ATR (₹50.48) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹4664.66) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #69 | UBL<br>(FMCG: NEUTRAL) | SECTOR_FILTERED | LTP: 1214.30<br>PDH: 1235.1<br>PDL: 1213.2<br>ATR: 38.67 | Sector 'FMCG' abhi NEUTRAL hai (Rank #1, RS 0.14%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹1213.20 ke 0.5 ATR (₹19.34) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹1214.41) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #70 | UNIONBANK<br>(PSU Bank: NEUTRAL) | SECTOR_FILTERED | LTP: 203.00<br>PDH: 204.4<br>PDL: 199.46<br>ATR: 4.95 | Sector 'PSU Bank' abhi NEUTRAL hai (Rank #3, RS -0.07%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹199.46 ke 0.5 ATR (₹2.48) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹199.66) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #71 | VEDL<br>(Metal: NEUTRAL) | SECTOR_FILTERED | LTP: 259.68<br>PDH: 264.47<br>PDL: 259.13<br>ATR: 7.12 | Sector 'Metal' abhi NEUTRAL hai (Rank #4, RS -0.09%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹259.13 ke 0.5 ATR (₹3.56) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹259.39) ke paas arm ho, (4) 8/8 signal checks pass kare.] |
| #72 | WIPRO<br>(IT: NEUTRAL) | SECTOR_FILTERED | LTP: 194.60<br>PDH: 197.4<br>PDL: 194.43<br>ATR: 4.71 | Sector 'IT' abhi NEUTRAL hai (Rank #2, RS -0.02%). SHORT trade ke liye sirf WEAK sector ke stocks allow hain.<br>[Min Cond: SHORT Arm & Entry ke liye: (1) Sector WEAK ho (RS <= -0.25%), (2) LTP PDL ₹194.43 ke 0.5 ATR (₹2.35) ke andar ho, (3) Top-5 score me aaye aur PDL+0.1% (₹194.62) ke paas arm ho, (4) 8/8 signal checks pass kare.] |

## 5. Complete Chronological Signal-by-Signal Dissection (All 101 Signals)

### [1/101] 11:10-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:10_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-10_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.20 | SL Rs.386.51 | Target Rs.379.59 | Slot Vol 0.6x | Day RVOL 0.39x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 45,591 shares (1.5x of 5-day avg 30,394) chahiye tha, par actual sirf 18,281 shares (0.60x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.39x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.60x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 12.6, Breadth 0.543) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.43%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.20 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.20 vs VWAP 384.80 | Close < VWAP (384.80) | - |
| #5 | 5m Slot Volume | FAIL | 18,281 vs avg 30,394 (0.60x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 45,591 shares (1.5x of 5-day avg 30,394) chahiye tha, par actual sirf 18,281 shares (0.60x) aaya. |
| #6 | Day RVOL | FAIL | 0.39x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.39x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.00 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: Bar vol 0.60x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.60x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [2/101] 11:15-ASHOKLEY-#1 (ASHOKLEY | Auto | SHORT) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-13_11:15_ASHOKLEY_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-15_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 485 | Entry Rs.171.05 | SL Rs.172.08 | Target Rs.169.00 | Slot Vol 0.23x | Day RVOL 0.26x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Candle Close ₹171.05 VWAP (₹171.00) ke galat side tha (Close < VWAP (171.00) chahiye tha). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,020,702 shares (1.5x of 5-day avg 680,468) chahiye tha, par actual sirf 157,782 shares (0.23x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.26x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close 171.05 >= VWAP 171.00 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 12.86, Breadth 0.511) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.27%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 171.05 | Close < 172.08 (PDL-0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 171.05 vs VWAP 171.00 | Close < VWAP (171.00) | Candle Close ₹171.05 VWAP (₹171.00) ke galat side tha (Close < VWAP (171.00) chahiye tha). |
| #5 | 5m Slot Volume | FAIL | 157,782 vs avg 680,468 (0.23x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,020,702 shares (1.5x of 5-day avg 680,468) chahiye tha, par actual sirf 157,782 shares (0.23x) aaya. |
| #6 | Day RVOL | FAIL | 0.26x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.26x tha. |
| #7 | Gap & No-Chase | PASS | Open 173.00, chase 0.20 ATR | Open > PDL (172.25), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 485 \| REJECTED: Close 171.05 >= VWAP 171.00 | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Close 171.05 >= VWAP 171.00 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [3/101] 11:15-M&M-#2 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:15_M&M_SHORT_#2  |  Micro S3 File: scans/2026-11-13/11-15_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3355.10 | SL Rs.3375.23 | Target Rs.3314.84 | Slot Vol 0.3x | Day RVOL 0.3x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 71,365 shares (1.5x of 5-day avg 47,576) chahiye tha, par actual sirf 14,115 shares (0.30x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.30x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 12.86, Breadth 0.511) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.27%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3355.10 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3355.10 vs VWAP 3355.94 | Close < VWAP (3355.94) | - |
| #5 | 5m Slot Volume | FAIL | 14,115 vs avg 47,576 (0.30x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 71,365 shares (1.5x of 5-day avg 47,576) chahiye tha, par actual sirf 14,115 shares (0.30x) aaya. |
| #6 | Day RVOL | FAIL | 0.30x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.12 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: Bar vol 0.30x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.30x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [4/101] 11:20-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:20_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-20_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.15 | SL Rs.386.45 | Target Rs.379.54 | Slot Vol 0.12x | Day RVOL 0.38x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 75,538 shares (1.5x of 5-day avg 50,359) chahiye tha, par actual sirf 5,843 shares (0.12x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.38x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.12x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 13.3, Breadth 0.44) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.55%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.15 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.15 vs VWAP 384.78 | Close < VWAP (384.78) | - |
| #5 | 5m Slot Volume | FAIL | 5,843 vs avg 50,359 (0.12x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 75,538 shares (1.5x of 5-day avg 50,359) chahiye tha, par actual sirf 5,843 shares (0.12x) aaya. |
| #6 | Day RVOL | FAIL | 0.38x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.38x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.01 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: Bar vol 0.12x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.12x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [5/101] 11:20-AXISBANK-#2 (AXISBANK | Pvt Bank | SHORT) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-13_11:20_AXISBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/11-20_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 62 | Entry Rs.1332.50 | SL Rs.1340.50 | Target Rs.1316.51 | Slot Vol 0.16x | Day RVOL 0.44x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Candle Close ₹1332.50 VWAP (₹1330.82) ke galat side tha (Close < VWAP (1330.82) chahiye tha). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 214,320 shares (1.5x of 5-day avg 142,880) chahiye tha, par actual sirf 23,062 shares (0.16x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.44x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close 1332.50 >= VWAP 1330.82 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 13.3, Breadth 0.44) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.55%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1332.50 | Close < 1332.67 (PDL-0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1332.50 vs VWAP 1330.82 | Close < VWAP (1330.82) | Candle Close ₹1332.50 VWAP (₹1330.82) ke galat side tha (Close < VWAP (1330.82) chahiye tha). |
| #5 | 5m Slot Volume | FAIL | 23,062 vs avg 142,880 (0.16x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 214,320 shares (1.5x of 5-day avg 142,880) chahiye tha, par actual sirf 23,062 shares (0.16x) aaya. |
| #6 | Day RVOL | FAIL | 0.44x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.44x tha. |
| #7 | Gap & No-Chase | PASS | Open 1338.00, chase 0.01 ATR | Open > PDL (1334.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 62 \| REJECTED: Close 1332.50 >= VWAP 1330.82 | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Close 1332.50 >= VWAP 1330.82 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [6/101] 11:30-FEDERALBNK-#1 (FEDERALBNK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:30_FEDERALBNK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-30_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 231 | Entry Rs.359.40 | SL Rs.361.56 | Target Rs.355.09 | Slot Vol 0.57x | Day RVOL 0.34x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 116,954 shares (1.5x of 5-day avg 77,969) chahiye tha, par actual sirf 44,302 shares (0.57x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.57x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 13.37, Breadth 0.385) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.45%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 359.40 | Close < 359.64 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 359.40 vs VWAP 360.99 | Close < VWAP (360.99) | - |
| #5 | 5m Slot Volume | FAIL | 44,302 vs avg 77,969 (0.57x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 116,954 shares (1.5x of 5-day avg 77,969) chahiye tha, par actual sirf 44,302 shares (0.57x) aaya. |
| #6 | Day RVOL | FAIL | 0.34x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. |
| #7 | Gap & No-Chase | PASS | Open 362.00, chase 0.03 ATR | Open > PDL (360.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 231 \| REJECTED: Bar vol 0.57x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.57x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [7/101] 11:35-TMPV-#1 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:35_TMPV_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-35_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 284 | Entry Rs.293.15 | SL Rs.294.91 | Target Rs.289.63 | Slot Vol 0.88x | Day RVOL 0.65x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 99,303 shares (1.5x of 5-day avg 66,202) chahiye tha, par actual sirf 57,964 shares (0.88x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.65x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.88x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 13.66, Breadth 0.365) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.29%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 293.15 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 293.15 vs VWAP 294.16 | Close < VWAP (294.16) | - |
| #5 | 5m Slot Volume | FAIL | 57,964 vs avg 66,202 (0.88x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 99,303 shares (1.5x of 5-day avg 66,202) chahiye tha, par actual sirf 57,964 shares (0.88x) aaya. |
| #6 | Day RVOL | FAIL | 0.65x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.65x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.02 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 284 \| REJECTED: Bar vol 0.88x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.88x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [8/101] 11:35-FEDERALBNK-#2 (FEDERALBNK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:35_FEDERALBNK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/11-35_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 231 | Entry Rs.359.50 | SL Rs.361.66 | Target Rs.355.19 | Slot Vol 0.22x | Day RVOL 0.33x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 186,114 shares (1.5x of 5-day avg 124,076) chahiye tha, par actual sirf 27,886 shares (0.22x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.33x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.22x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 13.66, Breadth 0.365) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.39%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 359.50 | Close < 359.64 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 359.50 vs VWAP 360.95 | Close < VWAP (360.95) | - |
| #5 | 5m Slot Volume | FAIL | 27,886 vs avg 124,076 (0.22x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 186,114 shares (1.5x of 5-day avg 124,076) chahiye tha, par actual sirf 27,886 shares (0.22x) aaya. |
| #6 | Day RVOL | FAIL | 0.33x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.33x tha. |
| #7 | Gap & No-Chase | PASS | Open 362.00, chase 0.02 ATR | Open > PDL (360.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 231 \| REJECTED: Bar vol 0.22x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.22x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [9/101] 11:35-M&M-#3 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:35_M&M_SHORT_#3  |  Micro S3 File: scans/2026-11-13/11-35_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3353.10 | SL Rs.3373.22 | Target Rs.3312.86 | Slot Vol 0.32x | Day RVOL 0.31x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 73,242 shares (1.5x of 5-day avg 48,828) chahiye tha, par actual sirf 15,500 shares (0.32x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 13.66, Breadth 0.365) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.29%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3353.10 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3353.10 vs VWAP 3356.11 | Close < VWAP (3356.11) | - |
| #5 | 5m Slot Volume | FAIL | 15,500 vs avg 48,828 (0.32x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 73,242 shares (1.5x of 5-day avg 48,828) chahiye tha, par actual sirf 15,500 shares (0.32x) aaya. |
| #6 | Day RVOL | FAIL | 0.31x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.14 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: Bar vol 0.32x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [10/101] 11:40-TMPV-#1 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:40_TMPV_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-40_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 284 | Entry Rs.293.20 | SL Rs.294.96 | Target Rs.289.68 | Slot Vol 1.26x | Day RVOL 0.66x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 164,722 shares (1.5x of 5-day avg 109,815) chahiye tha, par actual sirf 138,274 shares (1.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 1.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 14.26, Breadth 0.333) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.36%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 293.20 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 293.20 vs VWAP 294.11 | Close < VWAP (294.11) | - |
| #5 | 5m Slot Volume | FAIL | 138,274 vs avg 109,815 (1.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 164,722 shares (1.5x of 5-day avg 109,815) chahiye tha, par actual sirf 138,274 shares (1.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.66x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.02 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 284 \| REJECTED: Bar vol 1.26x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 1.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [11/101] 11:40-RBLBANK-#2 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:40_RBLBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/11-40_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 217 | Entry Rs.383.90 | SL Rs.386.20 | Target Rs.379.29 | Slot Vol 0.31x | Day RVOL 0.32x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 104,426 shares (1.5x of 5-day avg 69,617) chahiye tha, par actual sirf 21,756 shares (0.31x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.31x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 14.26, Breadth 0.333) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.36%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 383.90 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 383.90 vs VWAP 384.74 | Close < VWAP (384.74) | - |
| #5 | 5m Slot Volume | FAIL | 21,756 vs avg 69,617 (0.31x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 104,426 shares (1.5x of 5-day avg 69,617) chahiye tha, par actual sirf 21,756 shares (0.31x) aaya. |
| #6 | Day RVOL | FAIL | 0.32x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.03 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 217 \| REJECTED: Bar vol 0.31x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.31x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [12/101] 11:40-FEDERALBNK-#3 (FEDERALBNK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:40_FEDERALBNK_SHORT_#3  |  Micro S3 File: scans/2026-11-13/11-40_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 231 | Entry Rs.359.60 | SL Rs.361.76 | Target Rs.355.28 | Slot Vol 0.26x | Day RVOL 0.33x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 170,061 shares (1.5x of 5-day avg 113,374) chahiye tha, par actual sirf 29,539 shares (0.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.33x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 14.26, Breadth 0.333) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.36%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 359.60 | Close < 359.64 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 359.60 vs VWAP 360.92 | Close < VWAP (360.92) | - |
| #5 | 5m Slot Volume | FAIL | 29,539 vs avg 113,374 (0.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 170,061 shares (1.5x of 5-day avg 113,374) chahiye tha, par actual sirf 29,539 shares (0.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.33x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.33x tha. |
| #7 | Gap & No-Chase | PASS | Open 362.00, chase 0.00 ATR | Open > PDL (360.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 231 \| REJECTED: Bar vol 0.26x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [13/101] 11:40-M&M-#4 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:40_M&M_SHORT_#4  |  Micro S3 File: scans/2026-11-13/11-40_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3354.50 | SL Rs.3374.63 | Target Rs.3314.25 | Slot Vol 0.14x | Day RVOL 0.3x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 141,130 shares (1.5x of 5-day avg 94,087) chahiye tha, par actual sirf 13,413 shares (0.14x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.14x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 14.26, Breadth 0.333) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.36%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3354.50 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3354.50 vs VWAP 3356.06 | Close < VWAP (3356.06) | - |
| #5 | 5m Slot Volume | FAIL | 13,413 vs avg 94,087 (0.14x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 141,130 shares (1.5x of 5-day avg 94,087) chahiye tha, par actual sirf 13,413 shares (0.14x) aaya. |
| #6 | Day RVOL | FAIL | 0.30x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.12 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: Bar vol 0.14x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.14x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [14/101] 11:45-TMPV-#1 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:45_TMPV_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-45_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 284 | Entry Rs.293.00 | SL Rs.294.76 | Target Rs.289.48 | Slot Vol 0.44x | Day RVOL 0.66x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 155,197 shares (1.5x of 5-day avg 103,464) chahiye tha, par actual sirf 46,003 shares (0.44x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.44x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 14.82, Breadth 0.333) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.41%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 293.00 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 293.00 vs VWAP 294.10 | Close < VWAP (294.10) | - |
| #5 | 5m Slot Volume | FAIL | 46,003 vs avg 103,464 (0.44x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 155,197 shares (1.5x of 5-day avg 103,464) chahiye tha, par actual sirf 46,003 shares (0.44x) aaya. |
| #6 | Day RVOL | FAIL | 0.66x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.04 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 284 \| REJECTED: Bar vol 0.44x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.44x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [15/101] 11:50-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:50_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.15 | SL Rs.386.45 | Target Rs.379.54 | Slot Vol 0.05x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 280,883 shares (1.5x of 5-day avg 187,255) chahiye tha, par actual sirf 8,630 shares (0.05x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.05x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 15.86, Breadth 0.333) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.4%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.15 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.15 vs VWAP 384.72 | Close < VWAP (384.72) | - |
| #5 | 5m Slot Volume | FAIL | 8,630 vs avg 187,255 (0.05x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 280,883 shares (1.5x of 5-day avg 187,255) chahiye tha, par actual sirf 8,630 shares (0.05x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.01 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: Bar vol 0.05x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.05x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [16/101] 11:50-TMPV-#2 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:50_TMPV_SHORT_#2  |  Micro S3 File: scans/2026-11-13/11-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 284 | Entry Rs.292.90 | SL Rs.294.66 | Target Rs.289.39 | Slot Vol 0.72x | Day RVOL 0.66x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 97,695 shares (1.5x of 5-day avg 65,130) chahiye tha, par actual sirf 46,692 shares (0.72x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.72x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 15.86, Breadth 0.333) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.47%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 292.90 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 292.90 vs VWAP 294.08 | Close < VWAP (294.08) | - |
| #5 | 5m Slot Volume | FAIL | 46,692 vs avg 65,130 (0.72x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 97,695 shares (1.5x of 5-day avg 65,130) chahiye tha, par actual sirf 46,692 shares (0.72x) aaya. |
| #6 | Day RVOL | FAIL | 0.66x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.06 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 284 \| REJECTED: Bar vol 0.72x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.72x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [17/101] 11:55-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:55_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/11-55_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.20 | SL Rs.386.51 | Target Rs.379.59 | Slot Vol 0.32x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 106,711 shares (1.5x of 5-day avg 71,141) chahiye tha, par actual sirf 22,537 shares (0.32x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.82, Breadth 0.286) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.43%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.20 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.20 vs VWAP 384.70 | Close < VWAP (384.70) | - |
| #5 | 5m Slot Volume | FAIL | 22,537 vs avg 71,141 (0.32x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 106,711 shares (1.5x of 5-day avg 71,141) chahiye tha, par actual sirf 22,537 shares (0.32x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.00 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: Bar vol 0.32x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [18/101] 11:55-TMPV-#2 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_11:55_TMPV_SHORT_#2  |  Micro S3 File: scans/2026-11-13/11-55_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 284 | Entry Rs.292.40 | SL Rs.294.15 | Target Rs.288.89 | Slot Vol 0.94x | Day RVOL 0.66x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 221,094 shares (1.5x of 5-day avg 147,396) chahiye tha, par actual sirf 137,843 shares (0.94x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.94x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.82, Breadth 0.286) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.51%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 292.40 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 292.40 vs VWAP 294.02 | Close < VWAP (294.02) | - |
| #5 | 5m Slot Volume | FAIL | 137,843 vs avg 147,396 (0.94x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 221,094 shares (1.5x of 5-day avg 147,396) chahiye tha, par actual sirf 137,843 shares (0.94x) aaya. |
| #6 | Day RVOL | FAIL | 0.66x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.66x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.13 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 284 \| REJECTED: Bar vol 0.94x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.94x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [19/101] 12:00-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:00_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-00_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.15 | SL Rs.386.45 | Target Rs.379.54 | Slot Vol 0.28x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 61,157 shares (1.5x of 5-day avg 40,771) chahiye tha, par actual sirf 11,247 shares (0.28x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.28x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.08, Breadth 0.315) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.36%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.15 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.15 vs VWAP 384.70 | Close < VWAP (384.70) | - |
| #5 | 5m Slot Volume | FAIL | 11,247 vs avg 40,771 (0.28x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 61,157 shares (1.5x of 5-day avg 40,771) chahiye tha, par actual sirf 11,247 shares (0.28x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.01 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: Bar vol 0.28x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.28x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [20/101] 12:00-TMPV-#2 (TMPV | Auto | SHORT) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-13_12:00_TMPV_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-00_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 285 | Entry Rs.291.95 | SL Rs.293.70 | Target Rs.288.45 | Slot Vol 1.71x | Day RVOL 0.69x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.69x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: RVOL 0.69 < 1.0 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.08, Breadth 0.315) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.52%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 291.95 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 291.95 vs VWAP 293.91 | Close < VWAP (293.91) | - |
| #5 | 5m Slot Volume | PASS | 199,203 vs avg 116,426 (1.71x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.69x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.69x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.19 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 285 \| REJECTED: RVOL 0.69 < 1.0 | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: RVOL 0.69 < 1.0 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [21/101] 12:05-TMPV-#1 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:05_TMPV_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-05_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 285 | Entry Rs.292.10 | SL Rs.293.85 | Target Rs.288.59 | Slot Vol 0.59x | Day RVOL 0.69x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 137,996 shares (1.5x of 5-day avg 91,997) chahiye tha, par actual sirf 54,657 shares (0.59x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.69x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.59x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.5, Breadth 0.309) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.49%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 292.10 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 292.10 vs VWAP 293.88 | Close < VWAP (293.88) | - |
| #5 | 5m Slot Volume | FAIL | 54,657 vs avg 91,997 (0.59x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 137,996 shares (1.5x of 5-day avg 91,997) chahiye tha, par actual sirf 54,657 shares (0.59x) aaya. |
| #6 | Day RVOL | FAIL | 0.69x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.69x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.17 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 285 \| REJECTED: Bar vol 0.59x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.59x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [22/101] 12:10-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:10_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-10_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 217 | Entry Rs.383.90 | SL Rs.386.20 | Target Rs.379.29 | Slot Vol 0.87x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 36,783 shares (1.5x of 5-day avg 24,522) chahiye tha, par actual sirf 21,451 shares (0.87x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.87x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 19.58, Breadth 0.22) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.32%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 383.90 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 383.90 vs VWAP 384.68 | Close < VWAP (384.68) | - |
| #5 | 5m Slot Volume | FAIL | 21,451 vs avg 24,522 (0.87x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 36,783 shares (1.5x of 5-day avg 24,522) chahiye tha, par actual sirf 21,451 shares (0.87x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.03 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 217 \| REJECTED: Bar vol 0.87x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.87x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [23/101] 12:15-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:15_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 217 | Entry Rs.383.45 | SL Rs.385.75 | Target Rs.378.85 | Slot Vol 0.3x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 110,805 shares (1.5x of 5-day avg 73,870) chahiye tha, par actual sirf 22,344 shares (0.30x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.30x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.05, Breadth 0.2) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.53%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 383.45 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 383.45 vs VWAP 384.65 | Close < VWAP (384.65) | - |
| #5 | 5m Slot Volume | FAIL | 22,344 vs avg 73,870 (0.30x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 110,805 shares (1.5x of 5-day avg 73,870) chahiye tha, par actual sirf 22,344 shares (0.30x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.07 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 217 \| REJECTED: Bar vol 0.30x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.30x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [24/101] 12:15-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:15_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.80 | SL Rs.1578.21 | Target Rs.1549.97 | Slot Vol 0.55x | Day RVOL 0.27x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 570,101 shares (1.5x of 5-day avg 380,067) chahiye tha, par actual sirf 207,641 shares (0.55x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.27x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.55x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.05, Breadth 0.2) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.53%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.80 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.80 vs VWAP 1578.97 | Close < VWAP (1578.97) | - |
| #5 | 5m Slot Volume | FAIL | 207,641 vs avg 380,067 (0.55x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 570,101 shares (1.5x of 5-day avg 380,067) chahiye tha, par actual sirf 207,641 shares (0.55x) aaya. |
| #6 | Day RVOL | FAIL | 0.27x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.27x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.06 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.55x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.55x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [25/101] 12:15-AXISBANK-#3 (AXISBANK | Pvt Bank | SHORT) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-13_12:15_AXISBANK_SHORT_#3  |  Micro S3 File: scans/2026-11-13/12-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 62 | Entry Rs.1332.60 | SL Rs.1340.60 | Target Rs.1316.61 | Slot Vol 0.26x | Day RVOL 0.49x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Candle Close ₹1332.60 VWAP (₹1332.06) ke galat side tha (Close < VWAP (1332.06) chahiye tha). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 356,699 shares (1.5x of 5-day avg 237,799) chahiye tha, par actual sirf 62,547 shares (0.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.49x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Close 1332.60 >= VWAP 1332.06 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.05, Breadth 0.2) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.53%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1332.60 | Close < 1332.67 (PDL-0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 1332.60 vs VWAP 1332.06 | Close < VWAP (1332.06) | Candle Close ₹1332.60 VWAP (₹1332.06) ke galat side tha (Close < VWAP (1332.06) chahiye tha). |
| #5 | 5m Slot Volume | FAIL | 62,547 vs avg 237,799 (0.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 356,699 shares (1.5x of 5-day avg 237,799) chahiye tha, par actual sirf 62,547 shares (0.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.49x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.49x tha. |
| #7 | Gap & No-Chase | PASS | Open 1338.00, chase 0.00 ATR | Open > PDL (1334.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 62 \| REJECTED: Close 1332.60 >= VWAP 1332.06 | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Close 1332.60 >= VWAP 1332.06 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [26/101] 12:20-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:20_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-20_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 217 | Entry Rs.382.65 | SL Rs.384.95 | Target Rs.378.06 | Slot Vol 1.12x | Day RVOL 0.3x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 55,229 shares (1.5x of 5-day avg 36,819) chahiye tha, par actual sirf 41,061 shares (1.12x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 1.12x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.82, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.5%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 382.65 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 382.65 vs VWAP 384.56 | Close < VWAP (384.56) | - |
| #5 | 5m Slot Volume | FAIL | 41,061 vs avg 36,819 (1.12x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 55,229 shares (1.5x of 5-day avg 36,819) chahiye tha, par actual sirf 41,061 shares (1.12x) aaya. |
| #6 | Day RVOL | FAIL | 0.30x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.13 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 217 \| REJECTED: Bar vol 1.12x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 1.12x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [27/101] 12:20-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:20_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-20_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.70 | SL Rs.1578.11 | Target Rs.1549.88 | Slot Vol 0.64x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 504,249 shares (1.5x of 5-day avg 336,166) chahiye tha, par actual sirf 216,624 shares (0.64x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.64x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.82, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.5%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.70 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.70 vs VWAP 1578.45 | Close < VWAP (1578.45) | - |
| #5 | 5m Slot Volume | FAIL | 216,624 vs avg 336,166 (0.64x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 504,249 shares (1.5x of 5-day avg 336,166) chahiye tha, par actual sirf 216,624 shares (0.64x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.06 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.64x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.64x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [28/101] 12:25-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:25_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-25_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 217 | Entry Rs.383.50 | SL Rs.385.80 | Target Rs.378.90 | Slot Vol 0.82x | Day RVOL 0.31x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 46,066 shares (1.5x of 5-day avg 30,711) chahiye tha, par actual sirf 25,193 shares (0.82x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.82x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 23.72, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.63%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 383.50 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 383.50 vs VWAP 384.52 | Close < VWAP (384.52) | - |
| #5 | 5m Slot Volume | FAIL | 25,193 vs avg 30,711 (0.82x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 46,066 shares (1.5x of 5-day avg 30,711) chahiye tha, par actual sirf 25,193 shares (0.82x) aaya. |
| #6 | Day RVOL | FAIL | 0.31x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.06 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 217 \| REJECTED: Bar vol 0.82x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.82x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [29/101] 12:25-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:25_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-25_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.60 | SL Rs.1577.01 | Target Rs.1548.79 | Slot Vol 0.72x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 452,882 shares (1.5x of 5-day avg 301,921) chahiye tha, par actual sirf 217,797 shares (0.72x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.72x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 23.72, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.63%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.60 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.60 vs VWAP 1577.97 | Close < VWAP (1577.97) | - |
| #5 | 5m Slot Volume | FAIL | 217,797 vs avg 301,921 (0.72x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 452,882 shares (1.5x of 5-day avg 301,921) chahiye tha, par actual sirf 217,797 shares (0.72x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.10 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.72x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.72x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [30/101] 12:30-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:30_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-30_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.10 | SL Rs.386.40 | Target Rs.379.49 | Slot Vol 0.52x | Day RVOL 0.31x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 55,512 shares (1.5x of 5-day avg 37,008) chahiye tha, par actual sirf 19,347 shares (0.52x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.52x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 23.85, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.52%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.10 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.10 vs VWAP 384.51 | Close < VWAP (384.51) | - |
| #5 | 5m Slot Volume | FAIL | 19,347 vs avg 37,008 (0.52x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 55,512 shares (1.5x of 5-day avg 37,008) chahiye tha, par actual sirf 19,347 shares (0.52x) aaya. |
| #6 | Day RVOL | FAIL | 0.31x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.01 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: Bar vol 0.52x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.52x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [31/101] 12:30-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:30_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-30_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1569.20 | SL Rs.1578.62 | Target Rs.1550.37 | Slot Vol 0.26x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 604,921 shares (1.5x of 5-day avg 403,281) chahiye tha, par actual sirf 103,774 shares (0.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 23.85, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.52%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1569.20 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1569.20 vs VWAP 1577.77 | Close < VWAP (1577.77) | - |
| #5 | 5m Slot Volume | FAIL | 103,774 vs avg 403,281 (0.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 604,921 shares (1.5x of 5-day avg 403,281) chahiye tha, par actual sirf 103,774 shares (0.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.05 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.26x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [32/101] 12:35-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:35_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-35_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.30 | SL Rs.1576.70 | Target Rs.1548.49 | Slot Vol 0.47x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 374,677 shares (1.5x of 5-day avg 249,785) chahiye tha, par actual sirf 117,881 shares (0.47x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.47x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 23.95, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.41%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.30 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.30 vs VWAP 1577.53 | Close < VWAP (1577.53) | - |
| #5 | 5m Slot Volume | FAIL | 117,881 vs avg 249,785 (0.47x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 374,677 shares (1.5x of 5-day avg 249,785) chahiye tha, par actual sirf 117,881 shares (0.47x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.11 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.47x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.47x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [33/101] 12:40-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:40_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-40_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.10 | SL Rs.1576.50 | Target Rs.1548.29 | Slot Vol 0.3x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 748,894 shares (1.5x of 5-day avg 499,263) chahiye tha, par actual sirf 148,104 shares (0.30x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.30x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 23.33, Breadth 0.183) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.38%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.10 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.10 vs VWAP 1577.23 | Close < VWAP (1577.23) | - |
| #5 | 5m Slot Volume | FAIL | 148,104 vs avg 499,263 (0.30x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 748,894 shares (1.5x of 5-day avg 499,263) chahiye tha, par actual sirf 148,104 shares (0.30x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.11 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.30x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.30x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [34/101] 12:40-TMPV-#2 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:40_TMPV_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-40_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 285 | Entry Rs.291.15 | SL Rs.292.90 | Target Rs.287.66 | Slot Vol 1.19x | Day RVOL 0.79x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 87,636 shares (1.5x of 5-day avg 58,424) chahiye tha, par actual sirf 69,777 shares (1.19x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.79x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 1.19x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 23.33, Breadth 0.183) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.3%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 291.15 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 291.15 vs VWAP 293.26 | Close < VWAP (293.26) | - |
| #5 | 5m Slot Volume | FAIL | 69,777 vs avg 58,424 (1.19x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 87,636 shares (1.5x of 5-day avg 58,424) chahiye tha, par actual sirf 69,777 shares (1.19x) aaya. |
| #6 | Day RVOL | FAIL | 0.79x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.79x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.30 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 285 \| REJECTED: Bar vol 1.19x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 1.19x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [35/101] 12:45-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:45_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-45_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.80 | SL Rs.1577.21 | Target Rs.1548.99 | Slot Vol 0.28x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 648,771 shares (1.5x of 5-day avg 432,514) chahiye tha, par actual sirf 121,316 shares (0.28x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.28x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.75, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.42%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.80 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.80 vs VWAP 1577.01 | Close < VWAP (1577.01) | - |
| #5 | 5m Slot Volume | FAIL | 121,316 vs avg 432,514 (0.28x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 648,771 shares (1.5x of 5-day avg 432,514) chahiye tha, par actual sirf 121,316 shares (0.28x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.09 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.28x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.28x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [36/101] 12:45-TMPV-#2 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:45_TMPV_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-45_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 286 | Entry Rs.290.50 | SL Rs.292.24 | Target Rs.287.01 | Slot Vol 0.84x | Day RVOL 0.79x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 116,268 shares (1.5x of 5-day avg 77,512) chahiye tha, par actual sirf 64,766 shares (0.84x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.79x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.84x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.75, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.39%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 290.50 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 290.50 vs VWAP 293.22 | Close < VWAP (293.22) | - |
| #5 | 5m Slot Volume | FAIL | 64,766 vs avg 77,512 (0.84x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 116,268 shares (1.5x of 5-day avg 77,512) chahiye tha, par actual sirf 64,766 shares (0.84x) aaya. |
| #6 | Day RVOL | FAIL | 0.79x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.79x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.39 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 286 \| REJECTED: Bar vol 0.84x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.84x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [37/101] 12:50-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:50_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.15 | SL Rs.386.45 | Target Rs.379.54 | Slot Vol 0.19x | Day RVOL 0.3x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 77,581 shares (1.5x of 5-day avg 51,721) chahiye tha, par actual sirf 9,915 shares (0.19x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.19x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.74, Breadth 0.164) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.45%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.15 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.15 vs VWAP 384.51 | Close < VWAP (384.51) | - |
| #5 | 5m Slot Volume | FAIL | 9,915 vs avg 51,721 (0.19x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 77,581 shares (1.5x of 5-day avg 51,721) chahiye tha, par actual sirf 9,915 shares (0.19x) aaya. |
| #6 | Day RVOL | FAIL | 0.30x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.01 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: Bar vol 0.19x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.19x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [38/101] 12:50-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:50_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/12-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.00 | SL Rs.1576.40 | Target Rs.1548.20 | Slot Vol 0.33x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 432,685 shares (1.5x of 5-day avg 288,456) chahiye tha, par actual sirf 95,155 shares (0.33x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.33x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.74, Breadth 0.164) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.45%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.00 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.00 vs VWAP 1576.83 | Close < VWAP (1576.83) | - |
| #5 | 5m Slot Volume | FAIL | 95,155 vs avg 288,456 (0.33x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 432,685 shares (1.5x of 5-day avg 288,456) chahiye tha, par actual sirf 95,155 shares (0.33x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.12 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.33x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.33x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [39/101] 12:55-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_12:55_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/12-55_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.50 | SL Rs.1576.90 | Target Rs.1548.69 | Slot Vol 0.43x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 399,208 shares (1.5x of 5-day avg 266,139) chahiye tha, par actual sirf 113,313 shares (0.43x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.43x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.49, Breadth 0.164) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.46%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.50 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.50 vs VWAP 1576.63 | Close < VWAP (1576.63) | - |
| #5 | 5m Slot Volume | FAIL | 113,313 vs avg 266,139 (0.43x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 399,208 shares (1.5x of 5-day avg 266,139) chahiye tha, par actual sirf 113,313 shares (0.43x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.10 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.43x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.43x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [40/101] 13:00-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:00_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-00_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.50 | SL Rs.1576.90 | Target Rs.1548.69 | Slot Vol 0.25x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 561,960 shares (1.5x of 5-day avg 374,640) chahiye tha, par actual sirf 94,232 shares (0.25x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.25x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 22.0, Breadth 0.183) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.32%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.50 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.50 vs VWAP 1576.48 | Close < VWAP (1576.48) | - |
| #5 | 5m Slot Volume | FAIL | 94,232 vs avg 374,640 (0.25x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 561,960 shares (1.5x of 5-day avg 374,640) chahiye tha, par actual sirf 94,232 shares (0.25x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.10 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.25x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.25x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [41/101] 13:05-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:05_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-05_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.90 | SL Rs.1577.31 | Target Rs.1549.09 | Slot Vol 0.35x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 395,654 shares (1.5x of 5-day avg 263,769) chahiye tha, par actual sirf 91,048 shares (0.35x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.35x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.55, Breadth 0.183) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -0.38%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.90 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.90 vs VWAP 1576.33 | Close < VWAP (1576.33) | - |
| #5 | 5m Slot Volume | FAIL | 91,048 vs avg 263,769 (0.35x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 395,654 shares (1.5x of 5-day avg 263,769) chahiye tha, par actual sirf 91,048 shares (0.35x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.09 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.35x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.35x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [42/101] 13:10-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:10_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-10_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1566.80 | SL Rs.1576.20 | Target Rs.1548.00 | Slot Vol 0.18x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 498,907 shares (1.5x of 5-day avg 332,605) chahiye tha, par actual sirf 59,033 shares (0.18x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.18x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 20.86, Breadth 0.2) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.35%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1566.80 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1566.80 vs VWAP 1576.23 | Close < VWAP (1576.23) | - |
| #5 | 5m Slot Volume | FAIL | 59,033 vs avg 332,605 (0.18x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 498,907 shares (1.5x of 5-day avg 332,605) chahiye tha, par actual sirf 59,033 shares (0.18x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.12 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.18x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.18x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [43/101] 13:10-TMPV-#2 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:10_TMPV_SHORT_#2  |  Micro S3 File: scans/2026-11-13/13-10_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 285 | Entry Rs.291.15 | SL Rs.292.90 | Target Rs.287.66 | Slot Vol 0.54x | Day RVOL 0.77x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 163,234 shares (1.5x of 5-day avg 108,822) chahiye tha, par actual sirf 59,198 shares (0.54x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.77x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.54x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 20.86, Breadth 0.2) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.38%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 291.15 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 291.15 vs VWAP 293.07 | Close < VWAP (293.07) | - |
| #5 | 5m Slot Volume | FAIL | 59,198 vs avg 108,822 (0.54x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 163,234 shares (1.5x of 5-day avg 108,822) chahiye tha, par actual sirf 59,198 shares (0.54x) aaya. |
| #6 | Day RVOL | FAIL | 0.77x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.77x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.30 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 285 \| REJECTED: Bar vol 0.54x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.54x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [44/101] 13:15-TMPV-#1 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:15_TMPV_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-15_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 285 | Entry Rs.292.30 | SL Rs.294.05 | Target Rs.288.79 | Slot Vol 0.69x | Day RVOL 0.77x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 307,599 shares (1.5x of 5-day avg 205,066) chahiye tha, par actual sirf 142,047 shares (0.69x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.77x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.69x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 20.08, Breadth 0.246) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.37%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 292.30 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 292.30 vs VWAP 293.04 | Close < VWAP (293.04) | - |
| #5 | 5m Slot Volume | FAIL | 142,047 vs avg 205,066 (0.69x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 307,599 shares (1.5x of 5-day avg 205,066) chahiye tha, par actual sirf 142,047 shares (0.69x) aaya. |
| #6 | Day RVOL | FAIL | 0.77x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.77x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.14 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 285 \| REJECTED: Bar vol 0.69x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.69x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [45/101] 13:15-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:15_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/13-15_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1566.90 | SL Rs.1576.30 | Target Rs.1548.10 | Slot Vol 0.36x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 577,104 shares (1.5x of 5-day avg 384,736) chahiye tha, par actual sirf 139,881 shares (0.36x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.36x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 20.08, Breadth 0.246) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.31%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1566.90 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1566.90 vs VWAP 1576.01 | Close < VWAP (1576.01) | - |
| #5 | 5m Slot Volume | FAIL | 139,881 vs avg 384,736 (0.36x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 577,104 shares (1.5x of 5-day avg 384,736) chahiye tha, par actual sirf 139,881 shares (0.36x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.12 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.36x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.36x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [46/101] 13:20-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:20_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-20_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1569.20 | SL Rs.1578.62 | Target Rs.1550.37 | Slot Vol 0.32x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 605,233 shares (1.5x of 5-day avg 403,488) chahiye tha, par actual sirf 129,864 shares (0.32x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.66, Breadth 0.22) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.34%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1569.20 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1569.20 vs VWAP 1575.84 | Close < VWAP (1575.84) | - |
| #5 | 5m Slot Volume | FAIL | 129,864 vs avg 403,488 (0.32x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 605,233 shares (1.5x of 5-day avg 403,488) chahiye tha, par actual sirf 129,864 shares (0.32x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.05 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.32x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [47/101] 13:20-TMPV-#2 (TMPV | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:20_TMPV_SHORT_#2  |  Micro S3 File: scans/2026-11-13/13-20_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 284 | Entry Rs.292.45 | SL Rs.294.20 | Target Rs.288.94 | Slot Vol 0.43x | Day RVOL 0.76x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 285,309 shares (1.5x of 5-day avg 190,206) chahiye tha, par actual sirf 82,525 shares (0.43x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.76x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.43x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.66, Breadth 0.22) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.39%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 292.45 | Close < 293.31 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 292.45 vs VWAP 293.02 | Close < VWAP (293.02) | - |
| #5 | 5m Slot Volume | FAIL | 82,525 vs avg 190,206 (0.43x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 285,309 shares (1.5x of 5-day avg 190,206) chahiye tha, par actual sirf 82,525 shares (0.43x) aaya. |
| #6 | Day RVOL | FAIL | 0.76x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.76x tha. |
| #7 | Gap & No-Chase | PASS | Open 297.25, chase 0.12 ATR | Open > PDL (293.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 284 \| REJECTED: Bar vol 0.43x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.43x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [48/101] 13:25-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:25_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-25_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.90 | SL Rs.1577.31 | Target Rs.1549.09 | Slot Vol 0.25x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 570,298 shares (1.5x of 5-day avg 380,199) chahiye tha, par actual sirf 93,639 shares (0.25x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.25x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.59, Breadth 0.241) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.4%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.90 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.90 vs VWAP 1575.73 | Close < VWAP (1575.73) | - |
| #5 | 5m Slot Volume | FAIL | 93,639 vs avg 380,199 (0.25x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 570,298 shares (1.5x of 5-day avg 380,199) chahiye tha, par actual sirf 93,639 shares (0.25x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.09 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.25x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.25x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [49/101] 13:25-M&M-#2 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:25_M&M_SHORT_#2  |  Micro S3 File: scans/2026-11-13/13-25_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3350.50 | SL Rs.3370.60 | Target Rs.3310.29 | Slot Vol 0.2x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 94,312 shares (1.5x of 5-day avg 62,875) chahiye tha, par actual sirf 12,664 shares (0.20x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.20x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.59, Breadth 0.241) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.33%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3350.50 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3350.50 vs VWAP 3353.54 | Close < VWAP (3353.54) | - |
| #5 | 5m Slot Volume | FAIL | 12,664 vs avg 62,875 (0.20x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 94,312 shares (1.5x of 5-day avg 62,875) chahiye tha, par actual sirf 12,664 shares (0.20x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.17 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: Bar vol 0.20x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.20x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [50/101] 13:30-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:30_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-30_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1566.90 | SL Rs.1576.30 | Target Rs.1548.10 | Slot Vol 0.2x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 522,577 shares (1.5x of 5-day avg 348,385) chahiye tha, par actual sirf 68,969 shares (0.20x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.20x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.38, Breadth 0.241) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.45%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1566.90 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1566.90 vs VWAP 1575.63 | Close < VWAP (1575.63) | - |
| #5 | 5m Slot Volume | FAIL | 68,969 vs avg 348,385 (0.20x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 522,577 shares (1.5x of 5-day avg 348,385) chahiye tha, par actual sirf 68,969 shares (0.20x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.12 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.20x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.20x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [51/101] 13:30-M&M-#2 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:30_M&M_SHORT_#2  |  Micro S3 File: scans/2026-11-13/13-30_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3350.50 | SL Rs.3370.60 | Target Rs.3310.29 | Slot Vol 0.18x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 64,910 shares (1.5x of 5-day avg 43,273) chahiye tha, par actual sirf 7,911 shares (0.18x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.18x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.38, Breadth 0.241) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.39%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3350.50 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3350.50 vs VWAP 3353.52 | Close < VWAP (3353.52) | - |
| #5 | 5m Slot Volume | FAIL | 7,911 vs avg 43,273 (0.18x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 64,910 shares (1.5x of 5-day avg 43,273) chahiye tha, par actual sirf 7,911 shares (0.18x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.17 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: Bar vol 0.18x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.18x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [52/101] 13:35-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:35_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-35_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.00 | SL Rs.1576.40 | Target Rs.1548.20 | Slot Vol 0.15x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 753,728 shares (1.5x of 5-day avg 502,485) chahiye tha, par actual sirf 73,916 shares (0.15x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.15x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.03, Breadth 0.18) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.39%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.00 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.00 vs VWAP 1575.53 | Close < VWAP (1575.53) | - |
| #5 | 5m Slot Volume | FAIL | 73,916 vs avg 502,485 (0.15x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 753,728 shares (1.5x of 5-day avg 502,485) chahiye tha, par actual sirf 73,916 shares (0.15x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.12 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.15x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.15x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [53/101] 13:40-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:40_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-40_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.50 | SL Rs.1577.91 | Target Rs.1549.68 | Slot Vol 0.2x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 609,791 shares (1.5x of 5-day avg 406,527) chahiye tha, par actual sirf 82,870 shares (0.20x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.20x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 15.08, Breadth 0.2) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.52%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.50 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.50 vs VWAP 1575.43 | Close < VWAP (1575.43) | - |
| #5 | 5m Slot Volume | FAIL | 82,870 vs avg 406,527 (0.20x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 609,791 shares (1.5x of 5-day avg 406,527) chahiye tha, par actual sirf 82,870 shares (0.20x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.07 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.20x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.20x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [54/101] 13:45-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:45_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-45_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1569.50 | SL Rs.1578.92 | Target Rs.1550.67 | Slot Vol 0.32x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 619,783 shares (1.5x of 5-day avg 413,188) chahiye tha, par actual sirf 131,307 shares (0.32x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 14.89, Breadth 0.18) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.5%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1569.50 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1569.50 vs VWAP 1575.29 | Close < VWAP (1575.29) | - |
| #5 | 5m Slot Volume | FAIL | 131,307 vs avg 413,188 (0.32x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 619,783 shares (1.5x of 5-day avg 413,188) chahiye tha, par actual sirf 131,307 shares (0.32x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.04 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.32x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.32x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [55/101] 13:50-RBLBANK-#1 (RBLBANK | Pvt Bank | SHORT) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-13_13:50_RBLBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 216 | Entry Rs.384.05 | SL Rs.386.35 | Target Rs.379.44 | Slot Vol 2.0x | Day RVOL 0.38x
- **Kya & Kyun Samjha (FAILED 2/8): #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.38x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: RVOL 0.38 < 1.0 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 15.39, Breadth 0.18) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.49%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 384.05 | Close < 384.22 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 384.05 vs VWAP 384.53 | Close < VWAP (384.53) | - |
| #5 | 5m Slot Volume | PASS | 103,628 vs avg 51,867 (2.00x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | FAIL | 0.38x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.38x tha. |
| #7 | Gap & No-Chase | PASS | Open 388.40, chase 0.01 ATR | Open > PDL (384.60), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 216 \| REJECTED: RVOL 0.38 < 1.0 | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: RVOL 0.38 < 1.0 (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [56/101] 13:50-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:50_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/13-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.60 | SL Rs.1578.01 | Target Rs.1549.78 | Slot Vol 0.15x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,036,769 shares (1.5x of 5-day avg 691,179) chahiye tha, par actual sirf 101,825 shares (0.15x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.15x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 15.39, Breadth 0.18) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.49%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.60 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.60 vs VWAP 1575.19 | Close < VWAP (1575.19) | - |
| #5 | 5m Slot Volume | FAIL | 101,825 vs avg 691,179 (0.15x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,036,769 shares (1.5x of 5-day avg 691,179) chahiye tha, par actual sirf 101,825 shares (0.15x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.07 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.15x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.15x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [57/101] 13:55-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_13:55_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/13-55_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.70 | SL Rs.1577.11 | Target Rs.1548.89 | Slot Vol 0.21x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 562,864 shares (1.5x of 5-day avg 375,243) chahiye tha, par actual sirf 78,547 shares (0.21x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.21x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.05, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.48%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.70 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.70 vs VWAP 1575.11 | Close < VWAP (1575.11) | - |
| #5 | 5m Slot Volume | FAIL | 78,547 vs avg 375,243 (0.21x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 562,864 shares (1.5x of 5-day avg 375,243) chahiye tha, par actual sirf 78,547 shares (0.21x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.09 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.21x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.21x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [58/101] 14:00-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:00_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-00_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.40 | SL Rs.1577.81 | Target Rs.1549.58 | Slot Vol 0.26x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 693,993 shares (1.5x of 5-day avg 462,662) chahiye tha, par actual sirf 118,465 shares (0.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.29, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.48%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.40 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.40 vs VWAP 1574.98 | Close < VWAP (1574.98) | - |
| #5 | 5m Slot Volume | FAIL | 118,465 vs avg 462,662 (0.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 693,993 shares (1.5x of 5-day avg 462,662) chahiye tha, par actual sirf 118,465 shares (0.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.07 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.26x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.26x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [59/101] 14:05-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:05_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-05_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.60 | SL Rs.1577.01 | Target Rs.1548.79 | Slot Vol 0.19x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 849,063 shares (1.5x of 5-day avg 566,042) chahiye tha, par actual sirf 107,868 shares (0.19x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.19x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 16.84, Breadth 0.108) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.48%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.60 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.60 vs VWAP 1574.87 | Close < VWAP (1574.87) | - |
| #5 | 5m Slot Volume | FAIL | 107,868 vs avg 566,042 (0.19x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 849,063 shares (1.5x of 5-day avg 566,042) chahiye tha, par actual sirf 107,868 shares (0.19x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.10 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.19x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.19x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [60/101] 14:10-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:10_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-10_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.00 | SL Rs.1577.41 | Target Rs.1549.18 | Slot Vol 0.7x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 575,405 shares (1.5x of 5-day avg 383,603) chahiye tha, par actual sirf 269,632 shares (0.70x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.70x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.36, Breadth 0.125) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.4%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.00 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.00 vs VWAP 1574.58 | Close < VWAP (1574.58) | - |
| #5 | 5m Slot Volume | FAIL | 269,632 vs avg 383,603 (0.70x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 575,405 shares (1.5x of 5-day avg 383,603) chahiye tha, par actual sirf 269,632 shares (0.70x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.09 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.70x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.70x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [61/101] 14:15-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:15_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-15_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.00 | SL Rs.1577.41 | Target Rs.1549.18 | Slot Vol 0.17x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 767,305 shares (1.5x of 5-day avg 511,536) chahiye tha, par actual sirf 86,530 shares (0.17x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: Bar vol 0.17x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.48, Breadth 0.108) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.46%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.00 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.00 vs VWAP 1574.50 | Close < VWAP (1574.50) | - |
| #5 | 5m Slot Volume | FAIL | 86,530 vs avg 511,536 (0.17x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 767,305 shares (1.5x of 5-day avg 511,536) chahiye tha, par actual sirf 86,530 shares (0.17x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.09 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: Bar vol 0.17x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: Bar vol 0.17x <= 1.5x slot avg (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [62/101] 14:20-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:20_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-20_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1567.40 | SL Rs.1576.80 | Target Rs.1548.59 | Slot Vol 0.13x | Day RVOL 0.28x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,144,272 shares (1.5x of 5-day avg 762,848) chahiye tha, par actual sirf 95,943 shares (0.13x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.83, Breadth 0.108) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.48%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1567.40 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1567.40 vs VWAP 1574.41 | Close < VWAP (1574.41) | - |
| #5 | 5m Slot Volume | FAIL | 95,943 vs avg 762,848 (0.13x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,144,272 shares (1.5x of 5-day avg 762,848) chahiye tha, par actual sirf 95,943 shares (0.13x) aaya. |
| #6 | Day RVOL | FAIL | 0.28x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.28x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.10 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: After entry cutoff (14:15); Bar vol 0.13x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [63/101] 14:25-ADANIGREEN-#1 (ADANIGREEN | Energy | SHORT) — **REJECTED** (7/8 Pass, 1 Fail)

- Full ID: 2026-11-13_14:25_ADANIGREEN_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty - | Entry Rs.1400.00 | SL - | Target - | Slot Vol 2.46x | Day RVOL 1.77x
- **Kya & Kyun Samjha (FAILED 1/8): #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.91, Breadth 0.108) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.65%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1400.00 | Close < 1404.59 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1400.00 vs VWAP 1421.18 | Close < VWAP (1421.18) | - |
| #5 | 5m Slot Volume | PASS | 59,719 vs avg 24,314 (2.46x) | > 1.5x 5-day same-slot avg | - |
| #6 | Day RVOL | PASS | 1.77x cumulative | >= 1.0x | - |
| #7 | Gap & No-Chase | PASS | Open 1425.90, chase 0.11 ATR | Open > PDL (1406.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty - \| REJECTED: After entry cutoff (14:15) | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [64/101] 14:25-BALKRISIND-#2 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:25_BALKRISIND_SHORT_#2  |  Micro S3 File: scans/2026-11-13/14-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 36 | Entry Rs.2270.60 | SL Rs.2284.22 | Target Rs.2243.35 | Slot Vol 0.7x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 4,020 shares (1.5x of 5-day avg 2,680) chahiye tha, par actual sirf 1,884 shares (0.70x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.91, Breadth 0.108) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.62%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2270.60 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2270.60 vs VWAP 2287.15 | Close < VWAP (2287.15) | - |
| #5 | 5m Slot Volume | FAIL | 1,884 vs avg 2,680 (0.70x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 4,020 shares (1.5x of 5-day avg 2,680) chahiye tha, par actual sirf 1,884 shares (0.70x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.12 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 36 \| REJECTED: After entry cutoff (14:15); Bar vol 0.70x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [65/101] 14:25-MOTHERSON-#3 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:25_MOTHERSON_SHORT_#3  |  Micro S3 File: scans/2026-11-13/14-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 507 | Entry Rs.164.13 | SL Rs.165.11 | Target Rs.162.16 | Slot Vol 0.1x | Day RVOL 0.26x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,003,894 shares (1.5x of 5-day avg 669,263) chahiye tha, par actual sirf 69,778 shares (0.10x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.26x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.91, Breadth 0.108) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.62%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.13 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.13 vs VWAP 165.34 | Close < VWAP (165.34) | - |
| #5 | 5m Slot Volume | FAIL | 69,778 vs avg 669,263 (0.10x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,003,894 shares (1.5x of 5-day avg 669,263) chahiye tha, par actual sirf 69,778 shares (0.10x) aaya. |
| #6 | Day RVOL | FAIL | 0.26x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.26x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.10 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 507 \| REJECTED: After entry cutoff (14:15); Bar vol 0.10x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [66/101] 14:30-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:30_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-30_Scan_72Stocks_1Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.00 | SL Rs.1577.41 | Target Rs.1549.18 | Slot Vol 0.3x | Day RVOL 0.35x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 489,939 shares (1.5x of 5-day avg 326,626) chahiye tha, par actual sirf 98,686 shares (0.30x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.35x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.63, Breadth 0.125) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.51%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.00 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.00 vs VWAP 1574.20 | Close < VWAP (1574.20) | - |
| #5 | 5m Slot Volume | FAIL | 98,686 vs avg 326,626 (0.30x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 489,939 shares (1.5x of 5-day avg 326,626) chahiye tha, par actual sirf 98,686 shares (0.30x) aaya. |
| #6 | Day RVOL | FAIL | 0.35x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.35x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.09 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: After entry cutoff (14:15); Bar vol 0.30x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [67/101] 14:35-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:35_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-35_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.10 | SL Rs.1577.51 | Target Rs.1549.28 | Slot Vol 0.26x | Day RVOL 0.34x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 768,765 shares (1.5x of 5-day avg 512,510) chahiye tha, par actual sirf 134,278 shares (0.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.63, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.55%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.10 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.10 vs VWAP 1574.09 | Close < VWAP (1574.09) | - |
| #5 | 5m Slot Volume | FAIL | 134,278 vs avg 512,510 (0.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 768,765 shares (1.5x of 5-day avg 512,510) chahiye tha, par actual sirf 134,278 shares (0.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.34x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.08 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: After entry cutoff (14:15); Bar vol 0.26x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [68/101] 14:35-FEDERALBNK-#2 (FEDERALBNK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:35_FEDERALBNK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/14-35_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 231 | Entry Rs.359.60 | SL Rs.361.76 | Target Rs.355.28 | Slot Vol 0.43x | Day RVOL 0.46x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 138,476 shares (1.5x of 5-day avg 92,317) chahiye tha, par actual sirf 39,696 shares (0.43x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.46x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.63, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.55%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 359.60 | Close < 359.64 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 359.60 vs VWAP 360.19 | Close < VWAP (360.19) | - |
| #5 | 5m Slot Volume | FAIL | 39,696 vs avg 92,317 (0.43x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 138,476 shares (1.5x of 5-day avg 92,317) chahiye tha, par actual sirf 39,696 shares (0.43x) aaya. |
| #6 | Day RVOL | FAIL | 0.46x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.46x tha. |
| #7 | Gap & No-Chase | PASS | Open 362.00, chase 0.00 ATR | Open > PDL (360.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 231 \| REJECTED: After entry cutoff (14:15); Bar vol 0.43x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [69/101] 14:40-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:40_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-40_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.50 | SL Rs.1577.91 | Target Rs.1549.68 | Slot Vol 0.38x | Day RVOL 0.34x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 560,199 shares (1.5x of 5-day avg 373,466) chahiye tha, par actual sirf 143,212 shares (0.38x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.41, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.53%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.50 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.50 vs VWAP 1573.98 | Close < VWAP (1573.98) | - |
| #5 | 5m Slot Volume | FAIL | 143,212 vs avg 373,466 (0.38x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 560,199 shares (1.5x of 5-day avg 373,466) chahiye tha, par actual sirf 143,212 shares (0.38x) aaya. |
| #6 | Day RVOL | FAIL | 0.34x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.07 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: After entry cutoff (14:15); Bar vol 0.38x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [70/101] 14:40-BALKRISIND-#2 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:40_BALKRISIND_SHORT_#2  |  Micro S3 File: scans/2026-11-13/14-40_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 36 | Entry Rs.2275.90 | SL Rs.2289.56 | Target Rs.2248.59 | Slot Vol 0.28x | Day RVOL 0.24x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 4,463 shares (1.5x of 5-day avg 2,975) chahiye tha, par actual sirf 819 shares (0.28x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.24x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.41, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.55%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2275.90 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2275.90 vs VWAP 2286.75 | Close < VWAP (2286.75) | - |
| #5 | 5m Slot Volume | FAIL | 819 vs avg 2,975 (0.28x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 4,463 shares (1.5x of 5-day avg 2,975) chahiye tha, par actual sirf 819 shares (0.28x) aaya. |
| #6 | Day RVOL | FAIL | 0.24x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.24x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.04 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 36 \| REJECTED: After entry cutoff (14:15); Bar vol 0.28x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [71/101] 14:40-FEDERALBNK-#3 (FEDERALBNK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:40_FEDERALBNK_SHORT_#3  |  Micro S3 File: scans/2026-11-13/14-40_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 231 | Entry Rs.359.35 | SL Rs.361.51 | Target Rs.355.04 | Slot Vol 0.59x | Day RVOL 0.46x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 163,480 shares (1.5x of 5-day avg 108,987) chahiye tha, par actual sirf 64,601 shares (0.59x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.46x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.41, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.53%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 359.35 | Close < 359.64 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 359.35 vs VWAP 360.17 | Close < VWAP (360.17) | - |
| #5 | 5m Slot Volume | FAIL | 64,601 vs avg 108,987 (0.59x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 163,480 shares (1.5x of 5-day avg 108,987) chahiye tha, par actual sirf 64,601 shares (0.59x) aaya. |
| #6 | Day RVOL | FAIL | 0.46x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.46x tha. |
| #7 | Gap & No-Chase | PASS | Open 362.00, chase 0.03 ATR | Open > PDL (360.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 231 \| REJECTED: After entry cutoff (14:15); Bar vol 0.59x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [72/101] 14:45-ADANIGREEN-#1 (ADANIGREEN | Energy | SHORT) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-13_14:45_ADANIGREEN_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-45_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 59 | Entry Rs.1404.40 | SL Rs.1412.83 | Target Rs.1387.55 | Slot Vol 1.27x | Day RVOL 1.65x
- **Kya & Kyun Samjha (FAILED 2/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 45,715 shares (1.5x of 5-day avg 30,477) chahiye tha, par actual sirf 38,689 shares (1.27x) aaya. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.21, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.48%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1404.40 | Close < 1404.59 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1404.40 vs VWAP 1420.24 | Close < VWAP (1420.24) | - |
| #5 | 5m Slot Volume | FAIL | 38,689 vs avg 30,477 (1.27x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 45,715 shares (1.5x of 5-day avg 30,477) chahiye tha, par actual sirf 38,689 shares (1.27x) aaya. |
| #6 | Day RVOL | PASS | 1.65x cumulative | >= 1.0x | - |
| #7 | Gap & No-Chase | PASS | Open 1425.90, chase 0.00 ATR | Open > PDL (1406.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 59 \| REJECTED: After entry cutoff (14:15); Bar vol 1.27x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [73/101] 14:45-ICICIBANK-#2 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:45_ICICIBANK_SHORT_#2  |  Micro S3 File: scans/2026-11-13/14-45_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1568.20 | SL Rs.1577.61 | Target Rs.1549.38 | Slot Vol 0.31x | Day RVOL 0.34x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 534,865 shares (1.5x of 5-day avg 356,577) chahiye tha, par actual sirf 110,439 shares (0.31x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.21, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.46%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1568.20 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1568.20 vs VWAP 1573.89 | Close < VWAP (1573.89) | - |
| #5 | 5m Slot Volume | FAIL | 110,439 vs avg 356,577 (0.31x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 534,865 shares (1.5x of 5-day avg 356,577) chahiye tha, par actual sirf 110,439 shares (0.31x) aaya. |
| #6 | Day RVOL | FAIL | 0.34x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.08 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: After entry cutoff (14:15); Bar vol 0.31x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [74/101] 14:45-FEDERALBNK-#3 (FEDERALBNK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:45_FEDERALBNK_SHORT_#3  |  Micro S3 File: scans/2026-11-13/14-45_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 231 | Entry Rs.359.50 | SL Rs.361.66 | Target Rs.355.19 | Slot Vol 0.16x | Day RVOL 0.46x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 214,773 shares (1.5x of 5-day avg 143,182) chahiye tha, par actual sirf 22,931 shares (0.16x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.46x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.21, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.46%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 359.50 | Close < 359.64 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 359.50 vs VWAP 360.17 | Close < VWAP (360.17) | - |
| #5 | 5m Slot Volume | FAIL | 22,931 vs avg 143,182 (0.16x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 214,773 shares (1.5x of 5-day avg 143,182) chahiye tha, par actual sirf 22,931 shares (0.16x) aaya. |
| #6 | Day RVOL | FAIL | 0.46x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.46x tha. |
| #7 | Gap & No-Chase | PASS | Open 362.00, chase 0.02 ATR | Open > PDL (360.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 231 \| REJECTED: After entry cutoff (14:15); Bar vol 0.16x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [75/101] 14:50-SAIL-#1 (SAIL | Metal | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:50_SAIL_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 474 | Entry Rs.175.62 | SL Rs.176.67 | Target Rs.173.51 | Slot Vol 0.58x | Day RVOL 0.87x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 243,144 shares (1.5x of 5-day avg 162,096) chahiye tha, par actual sirf 93,292 shares (0.58x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.87x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.21, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.44%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 175.62 | Close < 175.68 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 175.62 vs VWAP 176.27 | Close < VWAP (176.27) | - |
| #5 | 5m Slot Volume | FAIL | 93,292 vs avg 162,096 (0.58x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 243,144 shares (1.5x of 5-day avg 162,096) chahiye tha, par actual sirf 93,292 shares (0.58x) aaya. |
| #6 | Day RVOL | FAIL | 0.87x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.87x tha. |
| #7 | Gap & No-Chase | PASS | Open 176.70, chase 0.01 ATR | Open > PDL (175.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 474 \| REJECTED: After entry cutoff (14:15); Bar vol 0.58x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [76/101] 14:50-MOTHERSON-#2 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:50_MOTHERSON_SHORT_#2  |  Micro S3 File: scans/2026-11-13/14-50_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 505 | Entry Rs.164.47 | SL Rs.165.46 | Target Rs.162.50 | Slot Vol 0.26x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 627,961 shares (1.5x of 5-day avg 418,641) chahiye tha, par actual sirf 107,274 shares (0.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.21, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.49%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.47 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.47 vs VWAP 165.30 | Close < VWAP (165.30) | - |
| #5 | 5m Slot Volume | FAIL | 107,274 vs avg 418,641 (0.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 627,961 shares (1.5x of 5-day avg 418,641) chahiye tha, par actual sirf 107,274 shares (0.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.04 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 505 \| REJECTED: After entry cutoff (14:15); Bar vol 0.26x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [77/101] 14:55-MOTHERSON-#1 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:55_MOTHERSON_SHORT_#1  |  Micro S3 File: scans/2026-11-13/14-55_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 505 | Entry Rs.164.47 | SL Rs.165.46 | Target Rs.162.50 | Slot Vol 0.1x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,073,455 shares (1.5x of 5-day avg 715,637) chahiye tha, par actual sirf 69,774 shares (0.10x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.2, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.46%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.47 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.47 vs VWAP 165.29 | Close < VWAP (165.29) | - |
| #5 | 5m Slot Volume | FAIL | 69,774 vs avg 715,637 (0.10x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,073,455 shares (1.5x of 5-day avg 715,637) chahiye tha, par actual sirf 69,774 shares (0.10x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.04 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 505 \| REJECTED: After entry cutoff (14:15); Bar vol 0.10x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [78/101] 14:55-M&M-#2 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_14:55_M&M_SHORT_#2  |  Micro S3 File: scans/2026-11-13/14-55_Scan_72Stocks_2Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3346.60 | SL Rs.3366.68 | Target Rs.3306.44 | Slot Vol 0.33x | Day RVOL 0.35x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 159,221 shares (1.5x of 5-day avg 106,147) chahiye tha, par actual sirf 34,904 shares (0.33x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.35x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.2, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.46%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3346.60 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3346.60 vs VWAP 3350.22 | Close < VWAP (3350.22) | - |
| #5 | 5m Slot Volume | FAIL | 34,904 vs avg 106,147 (0.33x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 159,221 shares (1.5x of 5-day avg 106,147) chahiye tha, par actual sirf 34,904 shares (0.33x) aaya. |
| #6 | Day RVOL | FAIL | 0.35x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.35x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.22 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: After entry cutoff (14:15); Bar vol 0.33x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [79/101] 15:00-ADANIGREEN-#1 (ADANIGREEN | Energy | SHORT) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-13_15:00_ADANIGREEN_SHORT_#1  |  Micro S3 File: scans/2026-11-13/15-00_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 59 | Entry Rs.1404.40 | SL Rs.1412.83 | Target Rs.1387.55 | Slot Vol 1.03x | Day RVOL 1.62x
- **Kya & Kyun Samjha (FAILED 2/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 47,340 shares (1.5x of 5-day avg 31,560) chahiye tha, par actual sirf 32,587 shares (1.03x) aaya. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.8, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.49%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1404.40 | Close < 1404.59 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1404.40 vs VWAP 1419.51 | Close < VWAP (1419.51) | - |
| #5 | 5m Slot Volume | FAIL | 32,587 vs avg 31,560 (1.03x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 47,340 shares (1.5x of 5-day avg 31,560) chahiye tha, par actual sirf 32,587 shares (1.03x) aaya. |
| #6 | Day RVOL | PASS | 1.62x cumulative | >= 1.0x | - |
| #7 | Gap & No-Chase | PASS | Open 1425.90, chase 0.00 ATR | Open > PDL (1406.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 59 \| REJECTED: After entry cutoff (14:15); Bar vol 1.03x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [80/101] 15:00-MOTHERSON-#2 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:00_MOTHERSON_SHORT_#2  |  Micro S3 File: scans/2026-11-13/15-00_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 505 | Entry Rs.164.30 | SL Rs.165.29 | Target Rs.162.33 | Slot Vol 0.13x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,738,705 shares (1.5x of 5-day avg 1,159,137) chahiye tha, par actual sirf 156,162 shares (0.13x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.8, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.51%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.30 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.30 vs VWAP 165.27 | Close < VWAP (165.27) | - |
| #5 | 5m Slot Volume | FAIL | 156,162 vs avg 1,159,137 (0.13x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,738,705 shares (1.5x of 5-day avg 1,159,137) chahiye tha, par actual sirf 156,162 shares (0.13x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.07 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 505 \| REJECTED: After entry cutoff (14:15); Bar vol 0.13x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [81/101] 15:00-M&M-#3 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:00_M&M_SHORT_#3  |  Micro S3 File: scans/2026-11-13/15-00_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3344.40 | SL Rs.3364.47 | Target Rs.3304.27 | Slot Vol 0.39x | Day RVOL 0.35x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 139,831 shares (1.5x of 5-day avg 93,220) chahiye tha, par actual sirf 36,454 shares (0.39x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.35x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.8, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.51%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3344.40 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3344.40 vs VWAP 3350.14 | Close < VWAP (3350.14) | - |
| #5 | 5m Slot Volume | FAIL | 36,454 vs avg 93,220 (0.39x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 139,831 shares (1.5x of 5-day avg 93,220) chahiye tha, par actual sirf 36,454 shares (0.39x) aaya. |
| #6 | Day RVOL | FAIL | 0.35x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.35x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.25 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: After entry cutoff (14:15); Bar vol 0.39x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [82/101] 15:05-ICICIBANK-#1 (ICICIBANK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:05_ICICIBANK_SHORT_#1  |  Micro S3 File: scans/2026-11-13/15-05_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 53 | Entry Rs.1570.10 | SL Rs.1579.52 | Target Rs.1551.26 | Slot Vol 0.8x | Day RVOL 0.37x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 737,860 shares (1.5x of 5-day avg 491,907) chahiye tha, par actual sirf 391,547 shares (0.80x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.46, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.49%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1570.10 | Close < 1570.73 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1570.10 vs VWAP 1573.29 | Close < VWAP (1573.29) | - |
| #5 | 5m Slot Volume | FAIL | 391,547 vs avg 491,907 (0.80x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 737,860 shares (1.5x of 5-day avg 491,907) chahiye tha, par actual sirf 391,547 shares (0.80x) aaya. |
| #6 | Day RVOL | FAIL | 0.37x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. |
| #7 | Gap & No-Chase | PASS | Open 1576.10, chase 0.02 ATR | Open > PDL (1572.30), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 53 \| REJECTED: After entry cutoff (14:15); Bar vol 0.80x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [83/101] 15:05-M&M-#2 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:05_M&M_SHORT_#2  |  Micro S3 File: scans/2026-11-13/15-05_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3346.00 | SL Rs.3366.08 | Target Rs.3305.85 | Slot Vol 0.58x | Day RVOL 0.36x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 150,175 shares (1.5x of 5-day avg 100,116) chahiye tha, par actual sirf 57,935 shares (0.58x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.36x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.46, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.63%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3346.00 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3346.00 vs VWAP 3349.98 | Close < VWAP (3349.98) | - |
| #5 | 5m Slot Volume | FAIL | 57,935 vs avg 100,116 (0.58x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 150,175 shares (1.5x of 5-day avg 100,116) chahiye tha, par actual sirf 57,935 shares (0.58x) aaya. |
| #6 | Day RVOL | FAIL | 0.36x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.36x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.23 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: After entry cutoff (14:15); Bar vol 0.58x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [84/101] 15:05-FEDERALBNK-#3 (FEDERALBNK | Pvt Bank | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:05_FEDERALBNK_SHORT_#3  |  Micro S3 File: scans/2026-11-13/15-05_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 232 | Entry Rs.359.05 | SL Rs.361.20 | Target Rs.354.74 | Slot Vol 0.47x | Day RVOL 0.47x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 255,940 shares (1.5x of 5-day avg 170,627) chahiye tha, par actual sirf 80,556 shares (0.47x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.47x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.46, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.49%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 359.05 | Close < 359.64 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 359.05 vs VWAP 360.09 | Close < VWAP (360.09) | - |
| #5 | 5m Slot Volume | FAIL | 80,556 vs avg 170,627 (0.47x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 255,940 shares (1.5x of 5-day avg 170,627) chahiye tha, par actual sirf 80,556 shares (0.47x) aaya. |
| #6 | Day RVOL | FAIL | 0.47x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.47x tha. |
| #7 | Gap & No-Chase | PASS | Open 362.00, chase 0.06 ATR | Open > PDL (360.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 232 \| REJECTED: After entry cutoff (14:15); Bar vol 0.47x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [85/101] 15:05-BALKRISIND-#4 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:05_BALKRISIND_SHORT_#4  |  Micro S3 File: scans/2026-11-13/15-05_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 36 | Entry Rs.2268.50 | SL Rs.2282.11 | Target Rs.2241.28 | Slot Vol 1.15x | Day RVOL 0.29x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 14,504 shares (1.5x of 5-day avg 9,669) chahiye tha, par actual sirf 11,109 shares (1.15x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.46, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.63%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2268.50 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2268.50 vs VWAP 2284.13 | Close < VWAP (2284.13) | - |
| #5 | 5m Slot Volume | FAIL | 11,109 vs avg 9,669 (1.15x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 14,504 shares (1.5x of 5-day avg 9,669) chahiye tha, par actual sirf 11,109 shares (1.15x) aaya. |
| #6 | Day RVOL | FAIL | 0.29x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.29x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.15 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 36 \| REJECTED: After entry cutoff (14:15); Bar vol 1.15x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [86/101] 15:10-MOTHERSON-#1 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:10_MOTHERSON_SHORT_#1  |  Micro S3 File: scans/2026-11-13/15-10_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 505 | Entry Rs.164.40 | SL Rs.165.39 | Target Rs.162.43 | Slot Vol 0.26x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,335,261 shares (1.5x of 5-day avg 890,174) chahiye tha, par actual sirf 232,169 shares (0.26x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.43, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.6%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.40 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.40 vs VWAP 165.21 | Close < VWAP (165.21) | - |
| #5 | 5m Slot Volume | FAIL | 232,169 vs avg 890,174 (0.26x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,335,261 shares (1.5x of 5-day avg 890,174) chahiye tha, par actual sirf 232,169 shares (0.26x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.05 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 505 \| REJECTED: After entry cutoff (14:15); Bar vol 0.26x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [87/101] 15:10-BALKRISIND-#2 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:10_BALKRISIND_SHORT_#2  |  Micro S3 File: scans/2026-11-13/15-10_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 36 | Entry Rs.2270.80 | SL Rs.2284.42 | Target Rs.2243.55 | Slot Vol 0.64x | Day RVOL 0.3x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 20,072 shares (1.5x of 5-day avg 13,381) chahiye tha, par actual sirf 8,551 shares (0.64x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.43, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.6%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2270.80 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2270.80 vs VWAP 2282.93 | Close < VWAP (2282.93) | - |
| #5 | 5m Slot Volume | FAIL | 8,551 vs avg 13,381 (0.64x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 20,072 shares (1.5x of 5-day avg 13,381) chahiye tha, par actual sirf 8,551 shares (0.64x) aaya. |
| #6 | Day RVOL | FAIL | 0.30x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.30x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.12 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 36 \| REJECTED: After entry cutoff (14:15); Bar vol 0.64x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [88/101] 15:10-M&M-#3 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:10_M&M_SHORT_#3  |  Micro S3 File: scans/2026-11-13/15-10_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3347.50 | SL Rs.3367.59 | Target Rs.3307.33 | Slot Vol 0.77x | Day RVOL 0.37x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 160,936 shares (1.5x of 5-day avg 107,291) chahiye tha, par actual sirf 82,444 shares (0.77x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 17.43, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.6%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3347.50 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3347.50 vs VWAP 3349.81 | Close < VWAP (3349.81) | - |
| #5 | 5m Slot Volume | FAIL | 82,444 vs avg 107,291 (0.77x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 160,936 shares (1.5x of 5-day avg 107,291) chahiye tha, par actual sirf 82,444 shares (0.77x) aaya. |
| #6 | Day RVOL | FAIL | 0.37x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.21 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: After entry cutoff (14:15); Bar vol 0.77x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [89/101] 15:15-MOTHERSON-#1 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:15_MOTHERSON_SHORT_#1  |  Micro S3 File: scans/2026-11-13/15-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 505 | Entry Rs.164.56 | SL Rs.165.55 | Target Rs.162.59 | Slot Vol 0.29x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,458,913 shares (1.5x of 5-day avg 972,609) chahiye tha, par actual sirf 282,702 shares (0.29x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.55, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.65%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.56 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.56 vs VWAP 165.19 | Close < VWAP (165.19) | - |
| #5 | 5m Slot Volume | FAIL | 282,702 vs avg 972,609 (0.29x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,458,913 shares (1.5x of 5-day avg 972,609) chahiye tha, par actual sirf 282,702 shares (0.29x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.03 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 505 \| REJECTED: After entry cutoff (14:15); Bar vol 0.29x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [90/101] 15:15-BALKRISIND-#2 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:15_BALKRISIND_SHORT_#2  |  Micro S3 File: scans/2026-11-13/15-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 36 | Entry Rs.2273.00 | SL Rs.2286.64 | Target Rs.2245.72 | Slot Vol 0.54x | Day RVOL 0.31x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 14,132 shares (1.5x of 5-day avg 9,421) chahiye tha, par actual sirf 5,085 shares (0.54x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.55, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.65%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2273.00 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2273.00 vs VWAP 2282.40 | Close < VWAP (2282.40) | - |
| #5 | 5m Slot Volume | FAIL | 5,085 vs avg 9,421 (0.54x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 14,132 shares (1.5x of 5-day avg 9,421) chahiye tha, par actual sirf 5,085 shares (0.54x) aaya. |
| #6 | Day RVOL | FAIL | 0.31x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.31x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.09 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 36 \| REJECTED: After entry cutoff (14:15); Bar vol 0.54x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [91/101] 15:15-M&M-#3 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:15_M&M_SHORT_#3  |  Micro S3 File: scans/2026-11-13/15-15_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3347.00 | SL Rs.3367.08 | Target Rs.3306.84 | Slot Vol 0.65x | Day RVOL 0.37x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 163,802 shares (1.5x of 5-day avg 109,201) chahiye tha, par actual sirf 71,376 shares (0.65x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 18.55, Breadth 0.143) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.65%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3347.00 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3347.00 vs VWAP 3349.74 | Close < VWAP (3349.74) | - |
| #5 | 5m Slot Volume | FAIL | 71,376 vs avg 109,201 (0.65x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 163,802 shares (1.5x of 5-day avg 109,201) chahiye tha, par actual sirf 71,376 shares (0.65x) aaya. |
| #6 | Day RVOL | FAIL | 0.37x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.22 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: After entry cutoff (14:15); Bar vol 0.65x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [92/101] 15:20-MOTHERSON-#1 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:20_MOTHERSON_SHORT_#1  |  Micro S3 File: scans/2026-11-13/15-20_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 505 | Entry Rs.164.51 | SL Rs.165.50 | Target Rs.162.54 | Slot Vol 1.37x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 2,451 shares (1.5x of 5-day avg 1,634) chahiye tha, par actual sirf 2,242 shares (1.37x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 19.59, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.67%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.51 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.51 vs VWAP 165.19 | Close < VWAP (165.19) | - |
| #5 | 5m Slot Volume | FAIL | 2,242 vs avg 1,634 (1.37x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 2,451 shares (1.5x of 5-day avg 1,634) chahiye tha, par actual sirf 2,242 shares (1.37x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.03 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 505 \| REJECTED: After entry cutoff (14:15); Bar vol 1.37x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [93/101] 15:20-BALKRISIND-#2 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:20_BALKRISIND_SHORT_#2  |  Micro S3 File: scans/2026-11-13/15-20_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 36 | Entry Rs.2272.20 | SL Rs.2285.83 | Target Rs.2244.93 | Slot Vol 0.57x | Day RVOL 0.32x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 12,349 shares (1.5x of 5-day avg 8,233) chahiye tha, par actual sirf 4,655 shares (0.57x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 19.59, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.67%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2272.20 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2272.20 vs VWAP 2281.96 | Close < VWAP (2281.96) | - |
| #5 | 5m Slot Volume | FAIL | 4,655 vs avg 8,233 (0.57x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 12,349 shares (1.5x of 5-day avg 8,233) chahiye tha, par actual sirf 4,655 shares (0.57x) aaya. |
| #6 | Day RVOL | FAIL | 0.32x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.10 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 36 \| REJECTED: After entry cutoff (14:15); Bar vol 0.57x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [94/101] 15:20-M&M-#3 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:20_M&M_SHORT_#3  |  Micro S3 File: scans/2026-11-13/15-20_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3347.10 | SL Rs.3367.18 | Target Rs.3306.93 | Slot Vol 0.45x | Day RVOL 0.37x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 528 shares (1.5x of 5-day avg 352) chahiye tha, par actual sirf 160 shares (0.45x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 19.59, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.67%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3347.10 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3347.10 vs VWAP 3349.74 | Close < VWAP (3349.74) | - |
| #5 | 5m Slot Volume | FAIL | 160 vs avg 352 (0.45x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 528 shares (1.5x of 5-day avg 352) chahiye tha, par actual sirf 160 shares (0.45x) aaya. |
| #6 | Day RVOL | FAIL | 0.37x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.21 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: After entry cutoff (14:15); Bar vol 0.45x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [95/101] 15:25-MOTHERSON-#1 (MOTHERSON | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:25_MOTHERSON_SHORT_#1  |  Micro S3 File: scans/2026-11-13/15-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 505 | Entry Rs.164.51 | SL Rs.165.50 | Target Rs.162.54 | Slot Vol 1.37x | Day RVOL 0.25x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 2,451 shares (1.5x of 5-day avg 1,634) chahiye tha, par actual sirf 2,242 shares (1.37x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 20.56, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.69%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 164.51 | Close < 164.70 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 164.51 vs VWAP 165.19 | Close < VWAP (165.19) | - |
| #5 | 5m Slot Volume | FAIL | 2,242 vs avg 1,634 (1.37x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 2,451 shares (1.5x of 5-day avg 1,634) chahiye tha, par actual sirf 2,242 shares (1.37x) aaya. |
| #6 | Day RVOL | FAIL | 0.25x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.25x tha. |
| #7 | Gap & No-Chase | PASS | Open 165.83, chase 0.03 ATR | Open > PDL (164.86), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 505 \| REJECTED: After entry cutoff (14:15); Bar vol 1.37x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [96/101] 15:25-BALKRISIND-#2 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:25_BALKRISIND_SHORT_#2  |  Micro S3 File: scans/2026-11-13/15-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 36 | Entry Rs.2271.20 | SL Rs.2284.83 | Target Rs.2243.95 | Slot Vol 0.64x | Day RVOL 0.32x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 10,976 shares (1.5x of 5-day avg 7,317) chahiye tha, par actual sirf 4,647 shares (0.64x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 20.56, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.69%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2271.20 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2271.20 vs VWAP 2281.52 | Close < VWAP (2281.52) | - |
| #5 | 5m Slot Volume | FAIL | 4,647 vs avg 7,317 (0.64x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 10,976 shares (1.5x of 5-day avg 7,317) chahiye tha, par actual sirf 4,647 shares (0.64x) aaya. |
| #6 | Day RVOL | FAIL | 0.32x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.11 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 36 \| REJECTED: After entry cutoff (14:15); Bar vol 0.64x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [97/101] 15:25-M&M-#3 (M&M | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:25_M&M_SHORT_#3  |  Micro S3 File: scans/2026-11-13/15-25_Scan_72Stocks_3Signals_0Passed.json
- Order Specs: Qty 24 | Entry Rs.3347.10 | SL Rs.3367.18 | Target Rs.3306.93 | Slot Vol 0.45x | Day RVOL 0.37x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 528 shares (1.5x of 5-day avg 352) chahiye tha, par actual sirf 160 shares (0.45x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 20.56, Breadth 0.161) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #8 WEAK (RS -0.69%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 3347.10 | Close < 3364.63 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 3347.10 vs VWAP 3349.74 | Close < VWAP (3349.74) | - |
| #5 | 5m Slot Volume | FAIL | 160 vs avg 352 (0.45x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 528 shares (1.5x of 5-day avg 352) chahiye tha, par actual sirf 160 shares (0.45x) aaya. |
| #6 | Day RVOL | FAIL | 0.37x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.37x tha. |
| #7 | Gap & No-Chase | PASS | Open 3380.00, chase 0.21 ATR | Open > PDL (3368.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 24 \| REJECTED: After entry cutoff (14:15); Bar vol 0.45x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [98/101] 15:30-ADANIGREEN-#1 (ADANIGREEN | Energy | SHORT) — **REJECTED** (6/8 Pass, 2 Fail)

- Full ID: 2026-11-13_15:30_ADANIGREEN_SHORT_#1  |  Micro S3 File: scans/2026-11-13/15-30_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 59 | Entry Rs.1403.00 | SL Rs.1411.42 | Target Rs.1386.16 | Slot Vol 0.7x | Day RVOL 1.64x
- **Kya & Kyun Samjha (FAILED 2/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 18,839 shares (1.5x of 5-day avg 12,559) chahiye tha, par actual sirf 8,804 shares (0.70x) aaya. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.68, Breadth 0.145) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.6%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 1403.00 | Close < 1404.59 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 1403.00 vs VWAP 1418.01 | Close < VWAP (1418.01) | - |
| #5 | 5m Slot Volume | FAIL | 8,804 vs avg 12,559 (0.70x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 18,839 shares (1.5x of 5-day avg 12,559) chahiye tha, par actual sirf 8,804 shares (0.70x) aaya. |
| #6 | Day RVOL | PASS | 1.64x cumulative | >= 1.0x | - |
| #7 | Gap & No-Chase | PASS | Open 1425.90, chase 0.04 ATR | Open > PDL (1406.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 59 \| REJECTED: After entry cutoff (14:15); Bar vol 0.70x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [99/101] 15:30-BALKRISIND-#2 (BALKRISIND | Auto | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:30_BALKRISIND_SHORT_#2  |  Micro S3 File: scans/2026-11-13/15-30_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 30 | Entry Rs.2266.90 | SL Rs.2283.14 | Target Rs.2234.42 | Slot Vol 1.23x | Day RVOL 0.34x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 10,732 shares (1.5x of 5-day avg 7,154) chahiye tha, par actual sirf 8,772 shares (1.23x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.68, Breadth 0.145) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #9 WEAK (RS -1.01%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 2266.90 | Close < 2278.72 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 2266.90 vs VWAP 2280.40 | Close < VWAP (2280.40) | - |
| #5 | 5m Slot Volume | FAIL | 8,772 vs avg 7,154 (1.23x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 10,732 shares (1.5x of 5-day avg 7,154) chahiye tha, par actual sirf 8,772 shares (1.23x) aaya. |
| #6 | Day RVOL | FAIL | 0.34x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.34x tha. |
| #7 | Gap & No-Chase | PASS | Open 2296.70, chase 0.18 ATR | Open > PDL (2281.00), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 30 \| REJECTED: After entry cutoff (14:15); Bar vol 1.23x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [100/101] 15:30-POWERGRID-#3 (POWERGRID | Energy | SHORT) — **REJECTED** (5/8 Pass, 3 Fail)

- Full ID: 2026-11-13_15:30_POWERGRID_SHORT_#3  |  Micro S3 File: scans/2026-11-13/15-30_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 323 | Entry Rs.257.45 | SL Rs.258.99 | Target Rs.254.36 | Slot Vol 0.85x | Day RVOL 0.41x
- **Kya & Kyun Samjha (FAILED 3/8): #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,333,850 shares (1.5x of 5-day avg 889,233) chahiye tha, par actual sirf 759,448 shares (0.85x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.41x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.68, Breadth 0.145) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.6%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 257.45 | Close < 258.24 (PDL-0.1%) | - |
| #4 | VWAP Filter | PASS | Close 257.45 vs VWAP 258.20 | Close < VWAP (258.20) | - |
| #5 | 5m Slot Volume | FAIL | 759,448 vs avg 889,233 (0.85x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,333,850 shares (1.5x of 5-day avg 889,233) chahiye tha, par actual sirf 759,448 shares (0.85x) aaya. |
| #6 | Day RVOL | FAIL | 0.41x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.41x tha. |
| #7 | Gap & No-Chase | PASS | Open 259.50, chase 0.12 ATR | Open > PDL (258.50), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 323 \| REJECTED: After entry cutoff (14:15); Bar vol 0.85x <= 1.5x slot avg | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

### [101/101] 15:30-IOC-#4 (IOC | Energy | SHORT) — **REJECTED** (4/8 Pass, 4 Fail)

- Full ID: 2026-11-13_15:30_IOC_SHORT_#4  |  Micro S3 File: scans/2026-11-13/15-30_Scan_72Stocks_4Signals_0Passed.json
- Order Specs: Qty 578 | Entry Rs.144.04 | SL Rs.144.90 | Target Rs.142.31 | Slot Vol 0.91x | Day RVOL 0.32x
- **Kya & Kyun Samjha (FAILED 4/8): #4 VWAP Filter: Candle Close ₹144.04 VWAP (₹144.02) ke galat side tha (Close < VWAP (144.02) chahiye tha). | #5 5m Slot Volume: 5m Candle Volume kam tha: Minimum > 1,032,045 shares (1.5x of 5-day avg 688,030) chahiye tha, par actual sirf 624,001 shares (0.91x) aaya. | #6 Day RVOL: Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. | #8 Sizing & Risk Gate: Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai).**

| # | Check | Result | Actual | Minimum Required | Why Failed |
| :---: | :--- | :---: | :--- | :--- | :--- |
| #1 | Market Regime | PASS | TREND_DOWN (ADX 21.68, Breadth 0.145) | TREND_UP (LONG) / TREND_DOWN (SHORT) | - |
| #2 | Sector Strength | PASS | Rank #7 WEAK (RS -0.6%) | STRONG (LONG) / WEAK (SHORT) | - |
| #3 | Breakout Candle | PASS | Close 144.04 | Close < 144.90 (PDL-0.1%) | - |
| #4 | VWAP Filter | FAIL | Close 144.04 vs VWAP 144.02 | Close < VWAP (144.02) | Candle Close ₹144.04 VWAP (₹144.02) ke galat side tha (Close < VWAP (144.02) chahiye tha). |
| #5 | 5m Slot Volume | FAIL | 624,001 vs avg 688,030 (0.91x) | > 1.5x 5-day same-slot avg | 5m Candle Volume kam tha: Minimum > 1,032,045 shares (1.5x of 5-day avg 688,030) chahiye tha, par actual sirf 624,001 shares (0.91x) aaya. |
| #6 | Day RVOL | FAIL | 0.32x cumulative | >= 1.0x | Din ka cumulative RVOL kam tha: Minimum >= 1.0x chahiye tha, par actual sirf 0.32x tha. |
| #7 | Gap & No-Chase | PASS | Open 145.38, chase 0.26 ATR | Open > PDL (145.05), chase <= 0.5 ATR | - |
| #8 | Sizing & Risk Gate | FAIL | Qty 578 \| REJECTED: After entry cutoff (14:15); Close 144.04 >= VWAP 144.02 | Qty > 0 (risk ₹500, cap ₹83,333), limits OK | Entry Gate / Timing / Sizing rukawat: After entry cutoff (14:15) (Entry window 09:30–14:15 aur risk limits pass hona zaroori hai). |

## 6. Complete AWS S3 Micro Scan File Inventory (52 Compiled Micro Files)

| Bar | Micro S3 File Name | Checked | Speed | Regime | Arm | Eval (P/R) | Evaluated Signals |
| :---: | :--- | :---: | ---: | :--- | ---: | :---: | :--- |
| 11:10 | 11-10_Scan_72Stocks_1Signals_0Passed.json | 16:01:02 | 55 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 11:10-RBLBANK-#1 (rejected) |
| 11:15 | 11-15_Scan_72Stocks_2Signals_0Passed.json | 16:01:03 | 86 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 11:15-ASHOKLEY-#1 (rejected), 11:15-M&M-#2 (rejected) |
| 11:20 | 11-20_Scan_72Stocks_2Signals_0Passed.json | 16:01:03 | 124 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 11:20-RBLBANK-#1 (rejected), 11:20-AXISBANK-#2 (rejected) |
| 11:30 | 11-30_Scan_72Stocks_1Signals_0Passed.json | 16:01:04 | 76 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 11:30-FEDERALBNK-#1 (rejected) |
| 11:35 | 11-35_Scan_72Stocks_3Signals_0Passed.json | 16:01:04 | 191 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 11:35-TMPV-#1 (rejected), 11:35-FEDERALBNK-#2 (rejected), 11:35-M&M-#3 (rejected) |
| 11:40 | 11-40_Scan_72Stocks_4Signals_0Passed.json | 16:01:05 | 214 ms | TREND_DOWN | 4 | 4 (0P / 4R) | 11:40-TMPV-#1 (rejected), 11:40-RBLBANK-#2 (rejected), 11:40-FEDERALBNK-#3 (rejected), 11:40-M&M-#4 (rejected) |
| 11:45 | 11-45_Scan_72Stocks_1Signals_0Passed.json | 16:01:05 | 137 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 11:45-TMPV-#1 (rejected) |
| 11:50 | 11-50_Scan_72Stocks_2Signals_0Passed.json | 16:01:05 | 125 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 11:50-RBLBANK-#1 (rejected), 11:50-TMPV-#2 (rejected) |
| 11:55 | 11-55_Scan_72Stocks_2Signals_0Passed.json | 16:01:06 | 94 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 11:55-RBLBANK-#1 (rejected), 11:55-TMPV-#2 (rejected) |
| 12:00 | 12-00_Scan_72Stocks_2Signals_0Passed.json | 16:01:06 | 102 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 12:00-RBLBANK-#1 (rejected), 12:00-TMPV-#2 (rejected) |
| 12:05 | 12-05_Scan_72Stocks_1Signals_0Passed.json | 16:01:06 | 109 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 12:05-TMPV-#1 (rejected) |
| 12:10 | 12-10_Scan_72Stocks_1Signals_0Passed.json | 16:01:07 | 91 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 12:10-RBLBANK-#1 (rejected) |
| 12:15 | 12-15_Scan_72Stocks_3Signals_0Passed.json | 16:01:07 | 106 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 12:15-RBLBANK-#1 (rejected), 12:15-ICICIBANK-#2 (rejected), 12:15-AXISBANK-#3 (rejected) |
| 12:20 | 12-20_Scan_72Stocks_2Signals_0Passed.json | 16:01:07 | 112 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 12:20-RBLBANK-#1 (rejected), 12:20-ICICIBANK-#2 (rejected) |
| 12:25 | 12-25_Scan_72Stocks_2Signals_0Passed.json | 16:01:08 | 101 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 12:25-RBLBANK-#1 (rejected), 12:25-ICICIBANK-#2 (rejected) |
| 12:30 | 12-30_Scan_72Stocks_2Signals_0Passed.json | 16:01:08 | 106 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 12:30-RBLBANK-#1 (rejected), 12:30-ICICIBANK-#2 (rejected) |
| 12:35 | 12-35_Scan_72Stocks_1Signals_0Passed.json | 16:01:09 | 89 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 12:35-ICICIBANK-#1 (rejected) |
| 12:40 | 12-40_Scan_72Stocks_2Signals_0Passed.json | 16:01:09 | 81 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 12:40-ICICIBANK-#1 (rejected), 12:40-TMPV-#2 (rejected) |
| 12:45 | 12-45_Scan_72Stocks_2Signals_0Passed.json | 16:01:09 | 108 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 12:45-ICICIBANK-#1 (rejected), 12:45-TMPV-#2 (rejected) |
| 12:50 | 12-50_Scan_72Stocks_2Signals_0Passed.json | 16:01:10 | 105 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 12:50-RBLBANK-#1 (rejected), 12:50-ICICIBANK-#2 (rejected) |
| 12:55 | 12-55_Scan_72Stocks_1Signals_0Passed.json | 16:01:10 | 108 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 12:55-ICICIBANK-#1 (rejected) |
| 13:00 | 13-00_Scan_72Stocks_1Signals_0Passed.json | 16:01:10 | 61 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 13:00-ICICIBANK-#1 (rejected) |
| 13:05 | 13-05_Scan_72Stocks_1Signals_0Passed.json | 16:01:11 | 64 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 13:05-ICICIBANK-#1 (rejected) |
| 13:10 | 13-10_Scan_72Stocks_2Signals_0Passed.json | 16:01:11 | 91 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 13:10-ICICIBANK-#1 (rejected), 13:10-TMPV-#2 (rejected) |
| 13:15 | 13-15_Scan_72Stocks_2Signals_0Passed.json | 16:01:11 | 95 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 13:15-TMPV-#1 (rejected), 13:15-ICICIBANK-#2 (rejected) |
| 13:20 | 13-20_Scan_72Stocks_2Signals_0Passed.json | 16:01:11 | 86 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 13:20-ICICIBANK-#1 (rejected), 13:20-TMPV-#2 (rejected) |
| 13:25 | 13-25_Scan_72Stocks_2Signals_0Passed.json | 16:01:12 | 131 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 13:25-ICICIBANK-#1 (rejected), 13:25-M&M-#2 (rejected) |
| 13:30 | 13-30_Scan_72Stocks_2Signals_0Passed.json | 16:01:12 | 85 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 13:30-ICICIBANK-#1 (rejected), 13:30-M&M-#2 (rejected) |
| 13:35 | 13-35_Scan_72Stocks_1Signals_0Passed.json | 16:01:13 | 70 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 13:35-ICICIBANK-#1 (rejected) |
| 13:40 | 13-40_Scan_72Stocks_1Signals_0Passed.json | 16:01:13 | 162 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 13:40-ICICIBANK-#1 (rejected) |
| 13:45 | 13-45_Scan_72Stocks_1Signals_0Passed.json | 16:01:13 | 79 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 13:45-ICICIBANK-#1 (rejected) |
| 13:50 | 13-50_Scan_72Stocks_2Signals_0Passed.json | 16:01:14 | 84 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 13:50-RBLBANK-#1 (rejected), 13:50-ICICIBANK-#2 (rejected) |
| 13:55 | 13-55_Scan_72Stocks_1Signals_0Passed.json | 16:01:14 | 90 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 13:55-ICICIBANK-#1 (rejected) |
| 14:00 | 14-00_Scan_72Stocks_1Signals_0Passed.json | 16:01:14 | 61 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 14:00-ICICIBANK-#1 (rejected) |
| 14:05 | 14-05_Scan_72Stocks_1Signals_0Passed.json | 16:01:15 | 128 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 14:05-ICICIBANK-#1 (rejected) |
| 14:10 | 14-10_Scan_72Stocks_1Signals_0Passed.json | 16:01:15 | 117 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 14:10-ICICIBANK-#1 (rejected) |
| 14:15 | 14-15_Scan_72Stocks_1Signals_0Passed.json | 16:01:15 | 61 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 14:15-ICICIBANK-#1 (rejected) |
| 14:20 | 14-20_Scan_72Stocks_1Signals_0Passed.json | 16:01:16 | 84 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 14:20-ICICIBANK-#1 (rejected) |
| 14:25 | 14-25_Scan_72Stocks_3Signals_0Passed.json | 16:01:16 | 159 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 14:25-ADANIGREEN-#1 (rejected), 14:25-BALKRISIND-#2 (rejected), 14:25-MOTHERSON-#3 (rejected) |
| 14:30 | 14-30_Scan_72Stocks_1Signals_0Passed.json | 16:01:16 | 61 ms | TREND_DOWN | 1 | 1 (0P / 1R) | 14:30-ICICIBANK-#1 (rejected) |
| 14:35 | 14-35_Scan_72Stocks_2Signals_0Passed.json | 16:01:17 | 85 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 14:35-ICICIBANK-#1 (rejected), 14:35-FEDERALBNK-#2 (rejected) |
| 14:40 | 14-40_Scan_72Stocks_3Signals_0Passed.json | 16:01:17 | 118 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 14:40-ICICIBANK-#1 (rejected), 14:40-BALKRISIND-#2 (rejected), 14:40-FEDERALBNK-#3 (rejected) |
| 14:45 | 14-45_Scan_72Stocks_3Signals_0Passed.json | 16:01:18 | 110 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 14:45-ADANIGREEN-#1 (rejected), 14:45-ICICIBANK-#2 (rejected), 14:45-FEDERALBNK-#3 (rejected) |
| 14:50 | 14-50_Scan_72Stocks_2Signals_0Passed.json | 16:01:18 | 129 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 14:50-SAIL-#1 (rejected), 14:50-MOTHERSON-#2 (rejected) |
| 14:55 | 14-55_Scan_72Stocks_2Signals_0Passed.json | 16:01:18 | 112 ms | TREND_DOWN | 2 | 2 (0P / 2R) | 14:55-MOTHERSON-#1 (rejected), 14:55-M&M-#2 (rejected) |
| 15:00 | 15-00_Scan_72Stocks_3Signals_0Passed.json | 16:01:19 | 141 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 15:00-ADANIGREEN-#1 (rejected), 15:00-MOTHERSON-#2 (rejected), 15:00-M&M-#3 (rejected) |
| 15:05 | 15-05_Scan_72Stocks_4Signals_0Passed.json | 16:01:19 | 151 ms | TREND_DOWN | 4 | 4 (0P / 4R) | 15:05-ICICIBANK-#1 (rejected), 15:05-M&M-#2 (rejected), 15:05-FEDERALBNK-#3 (rejected), 15:05-BALKRISIND-#4 (rejected) |
| 15:10 | 15-10_Scan_72Stocks_3Signals_0Passed.json | 16:01:19 | 136 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 15:10-MOTHERSON-#1 (rejected), 15:10-BALKRISIND-#2 (rejected), 15:10-M&M-#3 (rejected) |
| 15:15 | 15-15_Scan_72Stocks_3Signals_0Passed.json | 16:01:20 | 149 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 15:15-MOTHERSON-#1 (rejected), 15:15-BALKRISIND-#2 (rejected), 15:15-M&M-#3 (rejected) |
| 15:20 | 15-20_Scan_72Stocks_3Signals_0Passed.json | 16:01:20 | 111 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 15:20-MOTHERSON-#1 (rejected), 15:20-BALKRISIND-#2 (rejected), 15:20-M&M-#3 (rejected) |
| 15:25 | 15-25_Scan_72Stocks_3Signals_0Passed.json | 16:01:21 | 109 ms | TREND_DOWN | 3 | 3 (0P / 3R) | 15:25-MOTHERSON-#1 (rejected), 15:25-BALKRISIND-#2 (rejected), 15:25-M&M-#3 (rejected) |
| 15:30 | 15-30_Scan_72Stocks_4Signals_0Passed.json | 16:01:21 | 200 ms | TREND_DOWN | 4 | 4 (0P / 4R) | 15:30-ADANIGREEN-#1 (rejected), 15:30-BALKRISIND-#2 (rejected), 15:30-POWERGRID-#3 (rejected), 15:30-IOC-#4 (rejected) |
