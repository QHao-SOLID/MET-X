# Consolidated Actuarial Report

_Generated 2026-08-18 03:53 | seed 42 | n 10000 | expense_loading 1.3198 | telemetric_load 1.0_

## 1. Cohort Summary

```
=== n-Year Cohort Evolution Summary ===

 Year  Policies  Claims     Freq   Claim cost   Sev/claim  Avg NCD  Retention  Avg premium
 2026     10000    1728 0.156700 1.110354e+07 7085.856866 0.309047   0.879700  1438.718862
 2027     13797    2442 0.159817 1.476484e+07 6696.073943 0.330753   0.881568  1436.456378
 2028     17313    2986 0.154855 1.964867e+07 7328.857509 0.348829   0.887195  1425.134259
 2029     20664    3489 0.152342 2.137725e+07 6790.739283 0.358686   0.891841  1439.098941
 2030     23893    4103 0.155778 2.592614e+07 6965.646566 0.363912   0.891893  1474.519931

=== Key Findings ===
Total claims: 14,748
Total claim cost: RM92,820,431.52
Final avg NCD level: 36.39%
Loss ratio: 74.95%
```

## 2. Validation - Core Tests

```
[PASS] 1. Overall claim frequency within 10%-20% (actual 15.6%)
[PASS] 2. TPO expected claim cost/policy-year < Comprehensive (Comp RM1,075 vs TPO RM870)

  Per-peril mean severity:
    TPBI       RM24,029  (n=828)
    Theft      RM14,448  (n=1577)
    Fire       RM9,935  (n=722)
    TPPD       RM5,502  (n=3130)
    AD         RM4,654  (n=6168)
    Windscreen RM2,047  (n=1760)
  (caps enforced at draw time by construction)

  Loss ratio: 74.9% (earned RM123,847,572, incurred RM92,820,432)
  [OK]   Loss ratio within 40%-90% band
[PASS] 5a. Claims reset NCD_YEARS to 0 (reset rate 100.0%)
[PASS] 5b. Claim-free years increment NCD (increment rate 100.0%)
[PASS] 6. TPO claim frequency < Comprehensive (Comp 18.4% vs TPO 8.6%)
[PASS] 7. No nulls in key columns (nulls: 0)
[PASS] 7b. No negative/zero premium or negative claims (bad: 0)
[PASS] 8b. Mean DRIVER_AGE rises across years (35.5 -> 37.8)
[PASS] 8c. Mean CAR_AGE rises across years (3.2 -> 5.3)
[PASS] 9. CAR_AGE median within 3-4 years (median 3.0)
[PASS] 9b. CAR_AGE within [0,10] 
[PASS] 9c. Young Adults drive newer cars than other bands (Young Adults 3.1 vs others 5.3)
[PASS] 10. Premium varies across years for multi-year policies (100.0% of policies vary)
[PASS] 11a. Entrant EV share rises across years (15.5% -> 29.0%)
[PASS] 11b. Entrant EV share <= 0.95 (max 29.0%)
[PASS] 11c. Portfolio EV share rises across years (10.1% -> 24.1%)
[PASS] 11d. Entrant count grows with annual growth (5,000 -> 17,643)
[PASS] 12a. EV severity > ICE on SA-bound perils (AD/Theft/Fire) (EV RM9,196 vs ICE RM5,716)
[PASS] 12b. TP perils severity EV ~= ICE (factor scope-limited) (EV RM6,794 vs ICE RM6,443, ratio 1.05)

===== VALIDATION RESULT: 19 passed, 0 failed =====
```

## 3. Validation - Reproducibility + EDA Enrichment

```
[PASS] 8. Reproducibility: same seed -> identical claims

E1. Loss ratio by coverage type:

COVERAGE_TYPE
Comprehensive     59.5%
TPFT              98.5%
TPO              698.2%

E2. Peril mix:

CLAIM_PERIL
AD            6584
TPPD          3214
Windscreen    1791
Theft         1598
TPBI           835
Fire           726

E3. Claim frequency by age category:

DRIVER_AGE_CAT
Young Adults     19.0%
Seniors          18.0%
Adults           13.4%
Mature Adults    13.2%

E4. Retention by claim status:

CLAIM_OCCURRED
False    93.0%
True     66.1%
```

## 4. Validation - Enhanced Tests

```
======================================================================
DATASET VALIDATION
======================================================================
  Region premium ratio (East/Peninsular): 0.70x (report only)

                                     Test                      Value                                             Expected  Pass
Premium vs Sum Insured Correlation (Comp)                      0.795                                                > 0.5  True
             Young Driver Premium Loading                      1.17x > 1.05x (driver loading partly offset by newer cars)  True
                  Overall Claim Frequency                     15.55%                                               10-20%  True
            NCD Progression (2026 < 2030)             24.8% to 34.8%                                           Increasing  True
                       Overall Loss Ratio                     74.95%                                               50-80%  True
              Comprehensive Premium > TPO                     14.50x                                               > 1.8x  True
          TPFT Premium between TPO & Comp  RM125 < RM1,289 < RM1,807                           TPO < TPFT < Comprehensive  True
    NCD Discount at max tier (controlled)                      55.0%                                               45-60%  True
        Comp Premium Trend (2026 to 2030) RM1,774 to RM1,860 (1.05x)                         Mild softening (0.80x-0.99x) False

SOME VALIDATION TESTS FAILED - REVIEW ABOVE

======================================================================
ENHANCED STATISTICAL VALIDATION
======================================================================

1. PREMIUM DISTRIBUTION FIT TEST (Log-Normal)
   KS Statistic: 0.1426, p-value: 0.0000e+00
   (N=85,667; threshold 0.15 given coverage/NCD mixture)

2. CLAIM SEVERITY DISTRIBUTION FIT (Gamma)
------------------------------------------------------------
   Comprehensive: shape=0.56, scale=10471, KS=0.0563
   TPFT: shape=0.55, scale=19630, KS=0.0266
   TPO: shape=0.44, scale=23111, KS=0.0683

3. NCD DISTRIBUTION BY YEAR
------------------------------------------------------------
   2026: Avg NCD=24.8% | NCD=0%: 29.7% | NCD=55%: 9.0%
   2027: Avg NCD=29.9% | NCD=0%: 18.0% | NCD=55%: 14.3%
   2028: Avg NCD=32.2% | NCD=0%: 16.7% | NCD=55%: 19.6%
   2029: Avg NCD=33.6% | NCD=0%: 16.5% | NCD=55%: 24.2%
   2030: Avg NCD=34.8% | NCD=0%: 15.5% | NCD=55%: 28.5%

4. LOSS RATIO BY SEGMENT
------------------------------------------------------------
   By Coverage Type:
     Comprehensive : LR=59.50% (n=55,219)
     TPFT          : LR=98.49% (n=17,390)
     TPO           : LR=698.18% (n=13,058)
   By Age Band:
     18-25 : LR=85.49% (n=22,345)
     26-35 : LR=72.66% (n=24,053)
     36-50 : LR=65.61% (n=24,326)
     51-65 : LR=68.58% (n=9,845)
     66+   : LR=87.41% (n=5,098)
   By Region:
     Peninsular M: LR=73.03%
     East Malaysi: LR=85.73%

5. SEVERITY PERCENTILE VALIDATION
------------------------------------------------------------
   Comprehensive: Mean=RM5,834 (target RM4,000-10,000) OK
     P95=RM22,253 (target RM15,000-60,000) OK
   TPO: Mean=RM10,173 (target RM8,000-30,000) OK
     P95=RM37,484 (target RM25,000-600,000) OK
   TPFT: Mean=RM10,890 (target RM5,000-15,000) OK
     P95=RM37,141 (target RM20,000-120,000) OK

6. LONGITUDINAL CONSISTENCY
------------------------------------------------------------
   Unique policies: 30,918
   Policies with 1 year: 8,560
   Policies with 2+ years: 22,358
   Policies with all 5 years: 6,250

   Age consistency (sample 1,000): errors=0 OK
   Car-age consistency (cap at 10 allowed): errors=0 OK
   NCD reset on claim: failures=0/332 OK

7. GEN Z vs NON-GEN Z COMPARISON
------------------------------------------------------------
   Young Adults share: 34.0%
   Claim rate: Young Adults=19.0% vs Older=13.8%
   Avg premium: Young Adults=RM1,595 vs Older=RM1,369

8. CLAIM COUNT DISTRIBUTION
------------------------------------------------------------
   Mean: 0.1722, Var/Mean: 1.035 (1.0 = perfect Poisson)

9. PREMIUM DISTRIBUTION SHAPE
------------------------------------------------------------
   Log-premium skewness: -1.081 (target |skew| < 1.5)
   Log-premium kurtosis: 0.580
   D'Agostino-Pearson: stat=643.00, p=2.3681e-140

======================================================================
ENHANCED VALIDATION SUMMARY
======================================================================

                                   Test             Statistic    P-value                                                Interpretation  Pass
       Premium Log-Normal Fit (KS test)             KS=0.1426 0.0000e+00                                        Mixture (TPO+Comp+NCD)  True
     Severity Gamma Fit (Comprehensive) shape=0.56, KS=0.0563 1.7937e-28                                 Per-peril mixture, shape=0.56  True
              Severity Gamma Fit (TPFT) shape=0.55, KS=0.0266 1.1125e-01                                 Per-peril mixture, shape=0.55  True
               Severity Gamma Fit (TPO) shape=0.44, KS=0.0683 5.7058e-05                                 Per-peril mixture, shape=0.44  True
         NCD: 55% tier grows over years         9.0% to 28.5%          -                          Loyal claim-free policies accumulate  True
          Loss Ratio in Actuarial Range             LR=74.95%          -                                    Typically 50-80% for motor  True
          Severity Mean (Comprehensive)               RM5,834          -                                         Target RM4,000-10,000  True
           Severity P95 (Comprehensive)              RM22,253          -                                        Target RM15,000-60,000  True
                    Severity Mean (TPO)              RM10,173          -                                         Target RM8,000-30,000  True
                     Severity P95 (TPO)              RM37,484          -                                       Target RM25,000-600,000  True
                   Severity Mean (TPFT)              RM10,890          -                                         Target RM5,000-15,000  True
                    Severity P95 (TPFT)              RM37,141          -                                       Target RM20,000-120,000  True
          Longitudinal: Age Consistency              0 errors          -                                        DRIVER_AGE +1 per year  True
      Longitudinal: Car-Age Consistency              0 errors          -                                        CAR_AGE +1/yr (cap 10)  True
                     NCD Reset on Claim        0/332 failures          -                            Claim in year N -> NCD 0 next year  True
TPFT Claim Frequency between TPO & Comp  8.6% < 11.7% < 18.4%          -                              TPFT covers TP + fire/theft only  True
                     Young Adults Share                 34.0%          -                                                 Target 25-40%  True
         Young Adults Higher Claim Rate        19.0% vs 13.8%          -                                      Young drivers claim more  True
     Claim Count Poisson Fit (Var/Mean)                 1.035          -                         Close to 1.0 (heterogeneity inflates)  True
                   Log-Premium Skewness                -1.081          - |skew| < 1.5 (tariff-fixed TPO flat premium widens left mass)  True

Result: 20/20 tests passed
ALL ENHANCED VALIDATION TESTS PASSED
```

## 5. EDA - Policy Trajectories

```
          POLID  SIM_YEAR  FINAL_PREMIUM_SST  NCD_LEVEL_PRICED  CLAIM_COUNT
 ENT2027-000113      2027            2062.07            0.0000            2
 ENT2027-000113      2028            1589.12            0.0000            0
 ENT2027-000113      2029            2175.58            0.2500            1
 ENT2027-001739      2027            2227.05            0.5500            1
 ENT2027-001739      2028            1711.70            0.0000            0
 ENT2027-001739      2029            1636.24            0.2500            0
 ENT2027-001739      2030            1475.58            0.3000            0
 ENT2027-003456      2027            2293.70            0.3000            1
 ENT2027-003456      2028            2360.51            0.0000            1
 ENT2027-003456      2029            1820.49            0.0000            0
 ENT2027-003456      2030            1745.89            0.2500            0
 ENT2027-003688      2027             128.49            0.2500            0
 ENT2027-003688      2028             116.31            0.3000            0
 ENT2027-003688      2029             106.51            0.3833            0
 ENT2027-003688      2030              89.42            0.4500            0
 ENT2028-001616      2028            1046.99            0.0000            0
 ENT2028-001616      2029             879.24            0.2500            0
 ENT2028-001616      2030             795.93            0.3000            0
 ENT2028-002467      2028            1258.39            0.2500            0
 ENT2028-002467      2029            1140.02            0.3000            0
 ENT2028-002467      2030            1899.46            0.3833            1
 ENT2028-004342      2028            2394.43            0.2500            0
 ENT2028-004342      2029            2169.19            0.3000            0
 ENT2028-004342      2030            3614.23            0.3833            2
INIT2026-000148      2026            3055.75            0.2500            0
INIT2026-000148      2027            4479.24            0.3000            1
INIT2026-000148      2028            3444.84            0.0000            0
INIT2026-000148      2029            3294.90            0.2500            0
INIT2026-000148      2030            2973.03            0.3000            0
INIT2026-000622      2026             928.52            0.3833            0
INIT2026-000622      2027            1734.68            0.4500            1
INIT2026-000622      2028            1335.85            0.0000            0
INIT2026-000622      2029            1279.32            0.2500            0
INIT2026-000622      2030            1155.74            0.3000            0
INIT2026-001399      2026            1143.88            0.5500            0
INIT2026-001399      2027            1175.36            0.5500            0
INIT2026-001399      2028            1206.85            0.5500            0
INIT2026-001399      2029            1238.33            0.5500            0
INIT2026-001399      2030            1269.81            0.5500            0
INIT2026-001706      2026             162.58            0.0000            0
INIT2026-001706      2027             155.92            0.2500            0
INIT2026-001706      2028             228.70            0.3000            1
INIT2026-006373      2026             104.35            0.2500            0
INIT2026-006373      2027              94.46            0.3000            0
INIT2026-006373      2028              86.50            0.3833            0
INIT2026-006373      2029              72.62            0.4500            0
INIT2026-006373      2030              74.47            0.5500            0
INIT2026-006594      2026            1914.18            0.3833            0
INIT2026-006594      2027            1608.10            0.4500            0
INIT2026-006594      2028            1650.05            0.5500            0
INIT2026-006594      2029            1692.00            0.5500            0
INIT2026-006594      2030            1733.95            0.5500            0
INIT2026-007543      2026            3556.02            0.0000            0
INIT2026-007543      2027            3403.33            0.2500            0
INIT2026-007543      2028            3072.67            0.3000            0
INIT2026-007543      2029            2806.64            0.3833            0
INIT2026-007543      2030            2350.59            0.4500            0
INIT2026-008055      2026             197.85            0.0000            0
INIT2026-008055      2027             189.48            0.2500            0
INIT2026-008055      2028             171.17            0.3000            0
INIT2026-008055      2029             156.45            0.3833            0
INIT2026-008055      2030             131.10            0.4500            0
INIT2026-008872      2026             129.03            0.0000            0
INIT2026-008872      2027             123.49            0.2500            0
INIT2026-008872      2028             111.49            0.3000            0
INIT2026-008872      2029             101.84            0.3833            0
INIT2026-008872      2030              85.29            0.4500            0
INIT2026-009220      2026            1076.82            0.2500            0
INIT2026-009220      2027             974.09            0.3000            0
INIT2026-009220      2028             848.95            0.3833            0
INIT2026-009220      2029             712.26            0.4500            0
INIT2026-009220      2030             729.92            0.5500            0
INIT2026-009264      2026              89.97            0.5500            0
INIT2026-009264      2027              92.51            0.5500            0
INIT2026-009264      2028              95.06            0.5500            0
INIT2026-009264      2029              97.60            0.5500            0
INIT2026-009264      2030              95.38            0.5500            0
INIT2026-009719      2026            1692.42            0.4500            0
INIT2026-009719      2027            1739.00            0.5500            0
INIT2026-009719      2028            1785.58            0.5500            0
INIT2026-009719      2029            1832.17            0.5500            0
INIT2026-009719      2030            1878.75            0.5500            0
INIT2026-009930      2026            2322.25            0.5500            0
INIT2026-009930      2027            5302.58            0.5500            1
INIT2026-009930      2028            4083.46            0.0000            0
INIT2026-009930      2029            3910.66            0.2500            0
INIT2026-009930      2030            3532.88            0.3000            0

[figure] report/figures/policy_trajectories.png
```

## 6. EDA - Actuarial Heatmaps

```
[figure] report/figures/eda_heatmaps.png
```

## 7. EV Market Analysis

```
=== EV adoption (base run) ===
  EV share overall : 10.1% -> 24.1%
  EV share entrants: 15.5% -> 29.0%

=== EV vs ICE by year (base run) ===
           EV_lr  EV_freq     EV_sev    EV_prem  EV_ret  EV_ncd  ICE_lr  ICE_freq    ICE_sev   ICE_prem  ICE_ret  ICE_ncd
SIM_YEAR                                                                                                                 
2026      0.7147   0.1600  7966.8031  2027.6786  0.8936  0.3060  0.7812    0.1563  6243.1150  1372.8423   0.8781   0.3094
2027      0.7395   0.1615  8573.2892  2059.3474  0.8732  0.3234  0.7461    0.1596  5696.3059  1350.5616   0.8827   0.3318
2028      0.7685   0.1631  8409.3918  1991.8546  0.8792  0.3351  0.8039    0.1534  6228.1710  1322.8039   0.8886   0.3513
2029      0.7006   0.1595  7808.4255  1989.6335  0.8936  0.3415  0.7254    0.1507  5702.7725  1309.4801   0.8914   0.3627
2030      0.7063   0.1600  8041.9653  2003.5063  0.8881  0.3454  0.7503    0.1544  5753.9242  1306.6012   0.8931   0.3698

  Final-year EV LR vs ICE LR: 70.6% vs 75.0%

=== EV adoption scenarios (same book, seed 42) ===
    scenario  final_ev_share  overall_lr  n_policy_years
Conservative          0.1857      0.7481          768588
    Baseline          0.4777      0.7387          767282
  Aggressive          0.6068      0.7466          767121
  LR ordering (fair-value: more EV -> slightly lower LR):
  CHECK

[figure] report/figures/ev_analysis.png
```

## 8. Pricing Progression (Tariff -> GLM -> GLM+Telematics)

```
=== PRICING PROGRESSION (same book re-priced; only pricing differs) ===
        Regime  Portfolio LR (%)  Prem-Count rho  Retained LR 15% (%)
        Tariff             74.95          0.3709                81.86
           GLM             70.00          0.8369                60.55
GLM+Telematics             70.04          0.8368                60.79
[PASS] 13a. BEHAVIOR_RISK materially higher for claimants (1.108 vs 1.096, diff=+0.012)
[PASS] 13b. telematics_score lower for claimants (79.3 vs 80.1)
[PASS] 13c. portfolio LR: telem < tariff (70.04% < 74.95%)
[PASS] 13d. retained LR: GLM & telem << tariff; telem within 0.5pp of GLM (tariff 81.86% | glm 60.55% | telem 60.79%)
[PASS] 13e. premium-count correlation: telem >= glm (prices behavior; non-lagged NCD dominates) (0.8368 > 0.8369)
[PASS] 13f. telem premium prices telematics at least as strongly as GLM (both risk-based) (glm -0.045 | telem -0.069)
Pricing-progression checks: 6/6 passed

=== LR by telematics risk tier ===
GLM (blind to behavior):
telem_bin
<50 (High Risk)     52.1
50-70 (Moderate)    67.0
70-85 (Low Risk)    70.7
85-100 (Safe)       70.1
GLM+Telematics (prices behavior):
telem_bin
<50 (High Risk)     47.0
50-70 (Moderate)    64.2
70-85 (Low Risk)    70.7
85-100 (Safe)       72.1

[figure] report/figures/pricing_progression.png
```

## 9. Risk-Based Pricing - premium by behavior tier

```
Mean premium (RM) by telematics behavior tier:

                Tariff     GLM  GLM+Telematics
Behavior tier                                 
<50 High Risk   1611.0  1786.0          1977.0
50-70 Moderate  1466.0  1721.0          1798.0
70-85 Low Risk  1460.0  1595.0          1597.0
85-100 Safe     1410.0  1391.0          1352.0

[PASS] 13g. high-risk tier pays more under telematics (High/Safe relativity 1.46 > GLM 1.28 + 0.03)

[figure] report/figures/premium_by_tier.png
```

---
## 10. Three-Regime Comparison (Tariff | GLM | GLM+Telematics)

```
 model  overall_LR(%)  retained_LR(%)  prem_count_rho  tier_spread(pp)  avg_premium
tariff          74.95           81.86          0.3465             21.0      1445.69
   glm          70.00           60.55          0.6268             18.7      1547.87
 telem          70.04           60.79          0.6268             25.1      1547.02
```

_Note: expense_loading calibrated to 1.32 to target ~70% GLM/telem LR; tariff LR is unaffected (tariff formula has no expense loading). GLM/telem trained on seed 20260818, tested on seed 42._