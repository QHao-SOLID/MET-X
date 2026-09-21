#set par(
  justify: true,
  leading: 0.52em,
)

= Problem Statement

== Our Stakeholder: PIAM (Persatuan Insurans Am Malaysia)

PIAM is Malaysia's general insurance industry body. It represents 29 member companies that underwrite motor, fire, and commercial lines. PIAM's role is unique: it convenes insurers, coordinates industry standards, and advises regulators (BNM, MITI, JPJ) on policy.

*Why PIAM?* PIAM has publicly admitted the motor insurance industry is unprepared for EVs. CEO Chua Kim Soon stated in May 2026: "People switching from ICE to EV have *higher risk* of being involved in an accident." PIAM is already collaborating with JPJ on repair workshop standards and supported MITI's Malaysian Standard for smash repair requirements. This gives PIAM both the *mandate to lead* and the *convening power* to act across silos.

== ONE Specific Problem

*Malaysia's EV repair ecosystem lacks coordinated standards, data transparency, and repairer access — causing repair cost inflation that threatens insurance sustainability and slows EV adoption.*

This is not a single-actor problem. Insurers cannot price accurately without repair data. OEMs control parts and diagnostics. Workshops lack certification. Regulators are still drafting standards. Each actor optimises their own silo while the system-level cost escalates.

== Problem Identification

=== Who is affected?
- *Insurers:* Motor combined ratio at 102.2% (underwriting loss). EV claims 25.5% costlier than ICE (UK Thatcham benchmark). No Malaysian claims data pool exists to price accurately.
- *EV owners:* Premiums 10–30% above ICE. Limited workshop options. Total loss declarations more frequent due to battery cost concentration.
- *Workshops:* 7 of 10 independent workshops in Klang Valley decline EV repairs (FMT, May 2026). Lack certification, tools, and OEM diagnostic access.
- *OEMs:* CKD transition (Proton e.MAS, Perodua) requires local repair capability. Current model: 4S dealership monopoly inflates costs.

=== Where is the problem?
Nationwide, but concentrated in:
- *Klang Valley:* Highest EV density, but independent workshops lack EV capability
- *East Malaysia:* Thin repair coverage, long turnaround times
- *Highway corridors:* Limited DC fast-charger repair support

=== Why does it matter for EV adoption?
- *Repair cost → premium spiral:* Battery = 30–50% of vehicle value. Moderate damage triggers total loss. Premiums rise → consumers deterred → fewer EVs on road → less claims data → worse pricing → repeat.
- *Total loss frequency:* UK data shows BEV claims 25.5% costlier, 14% slower to repair. Malaysia has no data, but PIAM's own admissions suggest similar or worse outcomes.
- *Adoption target at risk:* Government targets 20% xEV share by 2030. If repair costs make EVs uninsurable or unaffordable, this target is unreachable.

=== Quantified impact
- *Battery replacement cost:* RM11,000–106,000 by brand (main.typ line 32)
- *ADAS calibration:* RM5,000–15,000 per incident (industry estimate)
- *EV premium gap:* 10–30% above comparable ICE (main.typ line 30)
- *Motor underwriting loss:* RM289.3 million in 2025 (PIAM, May 2026)
- *Workshop gap:* Only 37 Level 2 certified e.MAS technicians nationwide (Aug 2026)
- *Claims data:* Zero published Malaysian EV claims frequency/severity data

== Root Causes (not just observations)

1. *OEM parts and diagnostics monopoly.* Battery modules, BMS data, and HV system diagnostics are locked to 4S dealerships. Independent workshops cannot access repair information or source parts at competitive prices. This inflates repair costs in every market (China, UK, Australia).

2. *No repairer certification framework.* JPJ is drafting standards, but no national EV repairer accreditation exists yet. Technicians need high-voltage safety training (IMI Level 2–3 equivalent). Current supply: 37 certified technicians for 44,813+ EVs on road.

3. *No shared claims and repair data.* Insurers price blind. PIAM admits using ICE-based models with "unknown adequacy" (PIAM, 2025). Without model-level repair cost data, segmented pricing is impossible.

4. *CKD timing window closing.* Proton e.MAS, Perodua, and BYD CKD plants are launching now. If repairability standards are not embedded at design stage, Malaysia will inherit a decade of retrofitting costs (China's anti-pattern).

== Solution Proposal

*PIAM-led EV Repairability & Data Coordination Framework*

A three-part solution that coordinates risk management across the ecosystem:

=== Part 1: National EV Claims + Battery Data Pool
- *What:* Mandatory data sharing platform for all motor insurers — model-level repair costs, battery damage severity, total loss triggers, fire incidents
- *Who mandates:* Bank Negara Malaysia (BNM) through semi-regulated pricing framework
- *Who operates:* PIAM as industry custodian
- *Precedent:* China's CAA-CBIT national insurance data exchange

=== Part 2: Repairer Accreditation + OEM Data Access
- *What:* National EV repairer certification program (build on JPJ's in-progress standards); mandate OEMs to share diagnostic data and parts pricing with accredited independent workshops
- *Who leads:* PIAM + JPJ + MARii
- *Precedent:* EU Right to Repair Directive; UK Thatcham Insurability Blueprint

=== Part 3: Repairability-Linked CKD Incentives
- *What:* Condition CKD tax incentives (import/excise/sales tax exemption until 2027) on repairability compliance — modular battery design, accessible HV diagnostics, standardized repair protocols
- *Who implements:* MITI (NEVTF) as CKD approval condition
- *Precedent:* China's Jan 2025 four-ministry reform linking pricing to repairability

== Implementation Approach

#set text(size: 9pt)
#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  table.header(
    [Phase], [Timeline], [Lead], [Deliverable]
  ),
  [*Phase 1: Data Foundation*],
  [Months 1–6],
  [BNM + PIAM],
  [Mandatory EV claims data reporting template; pilot with 5 major insurers],
  [*Phase 2: Standards*],
  [Months 3–12],
  [JPJ + MARii + PIAM],
  [EV repairer accreditation framework; OEM diagnostic data access MOU],
  [*Phase 3: Policy Integration*],
  [Months 6–18],
  [MITI + BNM],
  [CKD repairability conditions; model-level repairability ratings],
  [*Phase 4: Scale*],
  [Months 12–24],
  [Industry-wide],
  [Full data pool operational; segmented pricing by repairability; national rollout]
)
#set text(size: 10pt)

== Key Trade-offs and Limitations

- *OEM resistance:* Manufacturers protect IP and dealer margins. Mitigation: use CKD incentive conditionality (Malaysia's leverage) rather than voluntary compliance.
- *Data sensitivity:* Insurers reluctant to share claims data. Mitigation: BNM mandate through existing semi-regulated pricing framework.
- *Short-term cost:* Accreditation and data systems require investment. Mitigation: motor segment already at 102.2% combined ratio — status quo is more expensive.
- *Scale limitation:* Malaysia's market (44,813 EVs) is small vs China (43.6m insured NEVs). Mitigation: policy leverage (CKD conditions) compensates for limited market gravity.

== Track-Led Reasoning

This solution directly addresses Track 3's core question: *how do we coordinate risk management across the ecosystem so that EV adoption is financially sustainable, resilient, and scalable?*

- *Resilience:* Data pool enables accurate pricing, preventing underwriting losses that could destabilize motor insurance.
- *Sustainability:* Repairability standards reduce total loss frequency, contain premium growth, and protect consumer affordability.
- *Scalability:* CKD conditions embed repairability before mass adoption — avoiding China's decade of retrofitting costs.

The solution does not require new legislation. It uses existing levers: BNM's pricing framework, PIAM's convening power, JPJ's in-progress standards, and MITI's CKD incentives. Malaysia can act now, not after a decade of losses.

= Supporting Evidence

== Market proof: Malaysia's EV adoption trajectory
- 278 EVs (2021) → 44,813 registered (end-2025) → ~50,000+ cumulative projected end-2026
- EV share of new registrations: 3.6% (2024) → 5.1% (2025) → 9.18% (Jan 2026)
- Government targets: xEV 20% of TIV by 2030, 80% by 2050
- *But:* Malaysia trails ASEAN peers — Singapore 45%, Thailand 18–21%, Vietnam 40% (Ember, 2025)

== Insurance industry stress signals
- Motor combined ratio: 102.2% — industry-wide underwriting loss
- Motor GWP: RM5.3b (1H2025), 42.8% of total industry premiums
- EV premiums: 10–30% above comparable ICE; in open markets (UK) ~2x
- PIAM admission: "motor insurance industry may not be ready" (Oct 2025)
- PIAM admission: "EV accidents far more complex and costly, sometimes unrepairable" (May 2026)

== Repair ecosystem data
- Battery replacement: RM11,000–106,000 by brand; battery = 30–50% of vehicle value
- ADAS calibration: RM5,000–15,000 per incident
- UK Thatcham benchmark: BEV claims 25.5% costlier, 14% slower to repair
- Certified technicians: 37 Level 2 e.MAS technicians nationwide (Aug 2026)
- Independent workshop capability: 7 of 10 in Klang Valley decline EV repairs (FMT, May 2026)

== Charging infrastructure status
- 5,839 public chargers (31 Mar 2026) — 56% of 10,000 target
- DC fast chargers: 2,143 (exceeded 1,500 target by 28%)
- AC chargers: 4,273 (50% of 8,500 target)
- Charger-to-vehicle ratio: 1:16 (worsening from 1:13)
- Geographic gap: East Malaysia and East Coast underserved

== Policy and incentive landscape
- CKD tax exemption active until 31 Dec 2027
- CBU tax exemption expired 31 Dec 2025; RM200,000 minimum CIF from Jul 2026
- Road tax: kW-based structure from Jan 2026 (85% lower than petrol equivalent)
- JPJ workshop standards: in progress (live policy hook)
- Battery passport MS 2818: launched Nov 2025 (ASEAN first)

= Global Benchmarks: Transferable Lessons

No country has fully solved the EV ecosystem problem. Each solved one slice. Malaysia can adopt all four pillars simultaneously — cheaper than retrofitting later.

#set text(size: 9pt)
#table(
  columns: (1fr, 1.5fr, 1.5fr),
  table.header(
    [Pillar], [Global Precedent], [Transferable to Malaysia]
  ),
  [*Data Platforms*],
  [China CAA-CBIT exchange: national claims data, model-level risk classification. EU Battery Passport: lifecycle transparency, SoH data.],
  [Build national EV claims + battery data pool via BNM mandate. Price by repairability, not "EV vs ICE."],
  [*Repair-Friendly Design*],
  [UK Thatcham Insurability Blueprint (2026): replaceable battery casings, accessible HV diagnostics. China: modular batteries, standardized repair protocols.],
  [Embed repairability at CKD stage (Proton e.MAS, Perodua). Late-mover advantage: cheaper than UK/China retrofitting.],
  [*Independent Repairer Access*],
  [EU Right to Repair Directive: fair-price parts, no software locks, diagnostic access. EU Data Act: vehicle data for independent aftermarket.],
  [Legislate OEM data/parts access for accredited workshops. Feed into JPJ repair standards (in progress).],
  [*Segmented Repairability Pricing*],
  [Norway: profitability-first pricing. UK: insurance-group ratings. China: repairability-based reform.],
  [Skip blanket EV-vs-ICE pricing. Introduce model-level repairability ratings linked to premiums.]
)
#set text(size: 10pt)

== Anti-patterns to avoid
- *China's sequencing:* Subsidies and mass adoption arrived before insurance data infrastructure — a decade of underwriting losses. Malaysia can build the data layer first.
- *Norway's scale trap:* Market too small to influence OEM design. Malaysia must use policy leverage (CKD conditions) rather than market gravity.
- *UK's affordability deterrence:* Premium shock suppresses uptake. Containing repair costs now protects the 20%-by-2030 xEV target.

= Key Stakeholders for Our Solution

== Core actors (direct implementation)
- *PIAM* — Convenes insurers, operates data pool, leads accreditation program
- *Bank Negara Malaysia* — Mandates data sharing through semi-regulated pricing framework
- *JPJ* — Repair workshop standards (in progress), technician certification
- *MITI (NEVTF)* — CKD incentive conditionality, repairability requirements

== Supporting actors
- *MARii* — Battery passport implementation, technician training standards
- *OEMs (Proton, Perodua, BYD)* — Repairability compliance at CKD design stage
- *Independent workshops* — Accreditation uptake, repair capability building
- *General insurers* — Data reporting, premium segmentation by repairability

== Advisory/oversight
- *Energy Commission* — Charging infrastructure safety standards
- *JBPM* — EV fire response, charging bay fire safety
- *ZEVA/MyZEVA* — Owner advocacy, safety awareness

#bibliography("work.bib", style: "harvard-cite-them-right")
