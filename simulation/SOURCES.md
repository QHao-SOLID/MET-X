# Sources — industry benchmarks

Citation ledger for `benchmarks.json` (the targets used by `04_analysis.ipynb` §10).
Machine-readable copy: [`sources/benchmarks_sources.json`](sources/benchmarks_sources.json) —
including the exact search queries and the key values each source supports.

**Retrieval**: 2026-09-18, Parallel Search (parallel-cli 0.7.1, basic mode) via the
`research-lookup` skill. Results are **search-derived** titles/snippets — a full-text
Extract pass on the primary sources is recommended before quoting numbers externally.

<!-- --8<-- [start:content] -->

| Target metric | Value used | Sources |
|---|---|---|
| `own_damage_claim_rate` | 7–14% pass band | [paultan/PIAM 2025](https://paultan.org/2026/05/08/piam-motor-insurance-posts-rm289-3-mil-loss-in-2025-more-and-costlier-claims-notably-with-proton-models) · [The Sun](https://thesun.my/motoring/malaysias-motor-insurance-sector-lost-rm-289-million-in-2025-with-proton-x50-x70-saga-named-in-claims-data) · [PIAM FY2025 release](https://piam.org.my/news-media/stay-ahead/press-releases/article/Malaysia-s-General-Insurance-Industry-Posts-RM1-2-Billion-Underwriting-Profit-as-PIAM-Brings-Full-Year-Results-to-East-Malaysia) |
| `avg_claim_severity` | RM8,831 | [paultan/PIAM 2025](https://paultan.org/2026/05/08/piam-motor-insurance-posts-rm289-3-mil-loss-in-2025-more-and-costlier-claims-notably-with-proton-models) · [The Sun](https://thesun.my/motoring/malaysias-motor-insurance-sector-lost-rm-289-million-in-2025-with-proton-x50-x70-saga-named-in-claims-data) |
| `theft_claim_rate` | ~0.15% per policy-year | [Business Today/VTAREC](https://www.businesstoday.com.my/2026/09/04/33716-vehicles-stolen-in-three-years-losses-hit-rm682-million) · [paultan 2024](https://paultan.org/2024/11/12/car-thefts-on-the-rise-in-malaysia-10849-vehicles-stolen-in-2024-up-to-sept-pick-ups-suvs-targeted) · [The Star/VTAREC](https://www.thestar.com.my/news/nation/2025/05/29/drop-in-road-accident-vehicle-theft-cases-in-2024) · [DOSM crime stats](https://storage.dosm.gov.my/crime/crime_2023.pdf) |
| `avg_private_car_premium` | RM857 → ~RM950 | [Carz/PIAM](https://www.carz.com.my/2025/04/rising-motor-claims-fueling-shift-to-risk-based-insurance-pricing) |
| `retention_rate` | 75–92% | [PIAM motor page](https://piam.org.my/insurance-101/individual/motor) |
| `portfolio_claims_ratio` | ~75% | [AutoBuzz (combined ratio 103%)](https://autobuzz.my/2026/05/07/malaysias-auto-insurers-are-paying-out-more-than-theyre-earning) · [PIAM via insuranceinfo](https://insuranceinfo.com.my/piam-motor-insurance-posts-rm289-3-mil-loss-in-2025-more-and-costlier-claims-notably-with-proton-models) |

Supporting context (NCD table, excess rules, EV experience):

- NCD 0–55%: [Autore](https://autore.my/ncd-rate-malaysia) · [Zurich](https://www.zurich.com.my/knowledge-hub/articles/2023/getting-to-know-ncd-no-claim-discount) · [Kurnia](https://www.kurnia.com/blog/no-claim-discount-ncd-rate)
- Excess (RM400 compulsory / young-driver ~RM1,500): [BJAK](https://bjak.my/blog/car-insurance/what-is-excess-in-car-insurance-policies) · [Liberty PDS](https://www.libertyinsurance.com.my/auto365-tpft-premier)
- EV repair cost / total-loss risk (PIAM): [Carz](https://www.carz.com.my/2025/10/piam-motor-insurance-still-in-the-red-ev-boom-adds-new-risks) · [paultan](https://paultan.org/2025/10/09/ev-accident-repair-more-complex-and-costly-than-ice-vehicles-could-end-up-totalling-the-car-piam)
- EV registrations (+148% YoY, Jul 2026): [SoyaCincau/JPJ](https://soyacincau.com/2026/08/09/malaysia-jpj-ev-registration-july-2026)

## Maintenance

1. Add the source to `sources/benchmarks_sources.json` (id, url, `used_for`, key values).
2. Reference its id from `benchmarks.json` → target `source_ids`.
3. Add a row/link here.
4. Re-run `--scenarios realistic_claims` and check `04 §10` still reflects the intent.

<!-- --8<-- [end:content] -->
