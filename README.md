# Starlink-Turkey Maritime Research Project

Quantifying potential Starlink Maritime demand and revenue opportunities for ships transiting Turkish territorial waters, with a flagship focus on the Istanbul (Bosphorus) and Çanakkale (Dardanelles) straits.

## Objectives
- Compile annual vessel-transit counts for Istanbul and Çanakkale since 2010.
- Estimate **unique ships** vs total transits for Istanbul.
- Split totals into **vessel categories** and infer **LEO-capable** adoption.
- Size potential demand for Starlink Maritime by type.
- Convert demand into monthly revenue under current Starlink Maritime pricing.
- Provide simple, reproducible Python workflows and text/CSV outputs.

## Repo structure
```
/straitsUsage/                # Yearly transit counts (Istanbul & Çanakkale)
/uniqueShipEstimator/         # Estimation of unique ships in Istanbul
/starlinkAdoption/            # LEO adoption by vessel type + projections
/revenueProjection/           # Revenue estimation from demand (multiple models)
/figures/                     # Optional charts saved as PNG (no GUI deps)
/docs/                        # Notes, references, and reports
```
*(Folders may be created as scripts run.)*

## Data used
- Annual vessel transits for Istanbul and Çanakkale, 2010–2024.
- One anchor year with **observed unique ships** for Istanbul, plus a ratio used to estimate unique counts for other years.
- Vessel-type splits for Bosphorus traffic (container, tanker, bulk, general cargo, Ro-Ro/vehicle, passenger/cruise, livestock, reefer).
- Literature-based **typical monthly internet usage** per ship type (GB/TB).
- Current Starlink Maritime pricing tiers, including **Global Priority** plans and the **merchant unlimited** program for IMO cargo/tanker.

## Methodology (high-level)

### 1) Transit series (Istanbul & Çanakkale)
- Ingest yearly totals since 2010.
- Keep **Istanbul** series separate for downstream modeling (unique ships and demand).

### 2) Unique-ship estimation (Istanbul)
- Use the year with known **unique ships** to compute a **unique/transit ratio**.
- Apply ratio smoothing across years (no monthly breakdown required).
- Output per-year: `Est_Unique`, `Est_Unique_Low`, `Est_Unique_High` in `uniqueShipEstimator/istanbul_unique_estimates.csv`.

### 3) Type allocation for unique ships
- Use observed **type distribution from total transits** as a proxy.
- Proportionally allocate `Est_Unique` into types:
  ```
  Unique_by_type_y = Est_Unique_y × (TypeShare_y from total transits)
  ```
- Emit low/high bands using the same proportional shares.

### 4) LEO adoption
- Assign **LEO adoption ranges** by type (low–high) grounded in sector uptake and use-cases.
- Compute **LEO-unique** ships by type and year:
  ```
  LEO_Unique_{low,high} = Unique_by_type × Adoption_{low,high}
  ```
- Write `demandEstimate.csv` and `demandEstimate.txt`. Export a bar chart PNG using a non-interactive backend.

### 5) Revenue estimation
Two complementary approaches exist in the repo. Use either, or both as cross-checks.

**A) Capacity-driven plan count**
- For each type, set a **typical monthly usage per ship** (TB).
- Map type → **Starlink plan** and its **priority cap** (TB).
- **Subscriptions per ship** = `ceil(usage_tb / plan_cap_tb)`; **unlimited** = 1.
- Revenue per type:
  ```
  MRR_{low,high} = LEO_Unique_{low,high} × Subs_per_ship × Plan_fee
  ```
- Outputs: `revenueProjection/revenueCapacity.csv`, `revenueProjection/revenueCapacity.txt` (column-aligned; includes Usage/ship TB).

**B) Line/TAC model (optional)**
- Treat Global Priority as **per-service-line** with an optional terminal access charge (TAC).
- One line supports up to two terminals. Add lines only if needed (usage or redundancy).
- Merchant unlimited (IMO cargo/tanker) modeled as one flat line (two terminals included).
- Useful for sensitivity testing. Keep off by default if you want a pure capacity→subscriptions mapping.

## Key scripts

### `starlinkAdoption/estDemand.py`
- Reads Bosphorus type counts (CSV) and adoption ranges by type.
- Optional manual per-type counts for a target year; otherwise uses `TARGET_YEAR` (2024 by default).
- Writes:
  - `demandEstimate.csv` with per-type **LEO-unique** low/high.
  - `demandEstimate.txt` summary.
  - `bosphorus_leo_projection_single.png` chart.

Run:
```bash
python estDemand.py
```

Config highlights:
- `ADOPTION`: low/high fractions by type.
- `MANUAL_COUNTS`: optional manual entry for a scenario.
- Non-GUI matplotlib backend for PNG export.

### `revenueProjection/estimateRevenueCapacity.py`
Capacity-first, simple and transparent.

- Loads `demandEstimate.csv` (LEO-unique ships by type).
- Uses **per-ship average TB** and **plan priority cap TB** to compute **subscriptions per ship**.
- Multiplies by plan fee and ship counts for **MRR low/high** ranges.
- Writes a column-aligned TXT that includes: Plan, Cap (TB), **Usage/ship (TB)**, Subs/ship, Fee/mo, MRR Low/High.
- Also writes `revenueCapacity.csv`.

Run:
```bash
python estimateRevenueCapacity.py
```

Edit at the top:
- `PLAN_CAP_TB`, `PLAN_FEE`
- `PLAN_MAP` (type → plan)
- `USAGE_TB` (average monthly demand per ship)
- Optional `AVAIL` multipliers if you want to discount for near-shore geofencing or adoption friction.

### (Optional) `revenueProjection/estimateRevenue.py`
- More detailed service-line/TAC modeling with toggles for TAC per line vs per terminal, minimum lines, and two-terminal shares by type.
- Keep when you want to mirror network design choices or reseller billing policies.

## Assumptions and dials
- **Unique ratio stability:** one observed year anchors the unique/transit ratio. Smoothing keeps yearly swings reasonable without monthly data.
- **Type shares:** unique allocation follows total-transit shares when true unique-by-type is unknown.
- **Adoption ranges:** conservative for cargo, higher for passenger/cruise. Adjust with fleet evidence.
- **Usage TB per ship:** from sector reports and field evidence. Tune per trade lane or company policy.
- **Plan mapping:** defaults are sensible; move bulk → 2TB on heavier trades, etc.
- **Unlimited eligibility:** merchant unlimited applies to **IMO cargo/tanker**. Passenger uses multiple Global Priority subscriptions.

## Reproduce
1) Ensure input CSVs exist:
```
straitsUsage/istanbul_canakkale_yearly.csv
uniqueShipEstimator/istanbul_unique_estimates.csv
starlinkAdoption/bosphorus_vessel_types_2020_2024.csv
```
2) Compute LEO demand:
```bash
cd starlinkAdoption
python estDemand.py
```
3) Compute revenue (capacity model):
```bash
cd ../revenueProjection
python estimateRevenueCapacity.py
```
4) Adjust parameters and re-run as needed.

## Outputs
- CSV tables for unique ships, LEO-unique by type, and revenue by type.
- Readable TXT summaries.
- PNG chart for type-level LEO demand.

## Limitations
- Annual level only; no monthly breakdown.
- Unique-by-type distribution inferred from total-transit shares.
- Adoption and usage are ranges/averages; fleets vary by policy, crew size, and route profile.
- Turkey licensing/geofencing can suppress near-shore usage; use `AVAIL` to reflect this in MRR.

## Roadmap
- AIS-derived type/unique counts for multiple anchor years.
- Crew-policy model (per-user caps) to refine usage TB/ship.
- Scenario runner (base/conservative/aggressive) over 10–20 years.
- Hardware CAPEX and support costs for net revenue.
- Economics for top-ups vs extra lines under Global Priority.

## License
Apache-2.0. See `LICENSE`.

## Contact
Open an issue for bugs or feature requests. PRs welcome.
