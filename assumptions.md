````markdown
# ASSUMPTIONS

This file lists every working assumption used in the Starlink-Turkey Maritime Research Project. Edit in place as the project evolves. Each section states what we assume, why, where it is used, and the knobs you can tune.

_Last updated: <set date>_

---

## 1) Data scope and coverage
- **Geography:** Turkish territorial waters, with a flagship focus on the Istanbul (Bosphorus) and Çanakkale (Dardanelles) straits.
- **Horizon:** 2010–2024 for historical transits; projections 2025–2035 when scenarios are run.
- **Granularity:** Annual counts. No monthly breakdown unless AIS is added later.
- **Vessel universe:** Commercial traffic only in core modeling (Container, Tanker_Total, Bulk_Carrier, General_Cargo, RoRo_Vehicle, Passenger_Cruise, Livestock, Reefer).

**Used in:** all scripts  
**Knobs:** add monthly indices; add other vessel classes; switch target year.

---

## 2) Unique ship estimation (Istanbul)
- **Anchor year:** 2021 has an observed unique-ship count (6,071).
- **Method:** compute a unique/transit ratio from the anchor year and smooth across other years; no monthly inputs.
- **Outputs:** `Est_Unique`, `Est_Unique_Low`, `Est_Unique_High` per year.

**Used in:** `uniqueShipEstimator/istanbul_unique_estimates.csv`, consumed by downstream demand scripts  
**Knobs:** choice of smoothing method; width of low/high band; more anchor years when AIS arrives.

---

## 3) Type allocation for uniques
- **Assumption:** the type mix of unique ships follows the type mix of total transits for that year.
- **Computation:**  
  `Unique_by_type_y = Est_Unique_y × Share_of_type_in_total_transits_y`

**Used in:** `estDemand.py`  
**Knobs:** override per-type shares where evidence exists; add uncertainty by type.

---

## 4) LEO adoption by type
- **Ranges (fractions) used for Istanbul demand:**
  ```python
  ADOPTION = {
      "Container": (0.10, 0.20),
      "Bulk_Carrier": (0.03, 0.07),
      "Tanker_Total": (0.10, 0.20),
      "RoRo_Vehicle": (0.02, 0.05),
      "Passenger_Cruise": (0.60, 0.90),
      "General_Cargo": (0.01, 0.03),
      "Livestock": (0.00, 0.02),
      "Reefer": (0.00, 0.03),
  }
````

* **Interpretation:** fraction of unique ships in a type that are LEO-capable or willing to adopt soon.

**Used in:** `estDemand.py` output `demandEstimate.csv`
**Knobs:** adjust per-type bands; add time-varying adoption curves in scenarios.

---

## 5) Typical monthly data use per ship (TB)

* **Per-vessel averages for capacity sizing:**

  ```python
  USAGE_TB = {
      "Container":        1.5,
      "Tanker_Total":     1.0,
      "Bulk_Carrier":     0.3,
      "General_Cargo":    0.08,
      "RoRo_Vehicle":     0.3,
      "Reefer":           0.3,
      "Livestock":        0.15,
      "Passenger_Cruise": 15.0,
  }
  ```
* **Basis:** literature and operator evidence; cruise is far higher due to passengers.

**Used in:** `revenueProjection/estimateRevenueCapacity.py`
**Knobs:** tune by route, crew policy, or evidence log; add distributions instead of point means.

---

## 6) Plan mapping and caps

* **Plans and priority caps (TB/month):**

  ```python
  PLAN_CAP_TB = {"GP_50":0.05, "GP_500":0.50, "GP_1TB":1.00, "GP_2TB":2.00, "IMO_UNL": float("inf")}
  PLAN_FEE    = {"GP_50":250,  "GP_500":650,  "GP_1TB":1150, "GP_2TB":2150, "IMO_UNL":2500}
  PLAN_MAP    = {
      "Container":"IMO_UNL",
      "Tanker_Total":"IMO_UNL",
      "Bulk_Carrier":"GP_1TB",
      "General_Cargo":"GP_500",
      "RoRo_Vehicle":"GP_1TB",
      "Reefer":"GP_500",
      "Livestock":"GP_500",
      "Passenger_Cruise":"GP_2TB",
  }
  ```
* **Interpretation:** cargo/tanker on merchant unlimited if eligible; passenger uses Global Priority.

**Used in:** `estimateRevenueCapacity.py`
**Knobs:** move heavy bulk to GP_2TB; split cruise across multiple plan lines if you prefer line-based modeling.

---

## 7) Subscription scaling rule

* **Capacity model:** subscriptions per ship =
  `ceil(USAGE_TB[type] / PLAN_CAP_TB[PLAN_MAP[type]])`
  Unlimited plans count as 1.
* **No terminal math** in the capacity model; we count plans, not antennas.

**Used in:** `estimateRevenueCapacity.py`
**Knobs:** switch to a line/TAC model if you want service-line economics.

---

## 8) Availability and serviceability

* **Default availability multipliers:**

  ```python
  AVAIL = {
      "Container":1.0, "Tanker_Total":1.0, "Bulk_Carrier":1.0,
      "General_Cargo":1.0, "RoRo_Vehicle":1.0, "Reefer":1.0,
      "Livestock":1.0, "Passenger_Cruise":1.0
  }
  ```
* **Interpretation:** fraction of ships that actually subscribe or can use service given licensing and pattern of operation.

**Used in:** revenue scripts
**Knobs:** reduce for coastal trades or regulatory gating; set per type.

---

## 9) Revenue calculation

* **Per type, monthly MRR range:**

  ```
  MRR_low  = LEO_Unique_low  × Subs_per_ship × Plan_fee × Availability
  MRR_high = LEO_Unique_high × Subs_per_ship × Plan_fee × Availability
  ```
* **Totals:** sum across types.

**Used in:** `revenueCapacity.csv`, `revenueCapacity.txt`
**Knobs:** currency conversion; tax; reseller margins; hardware amortization if you move to net revenue.

---

## 10) Files, inputs, and precedence

* **Inputs expected:**

  * `straitsUsage/istanbul_canakkale_yearly.csv` (annual transits)
  * `uniqueShipEstimator/istanbul_unique_estimates.csv` (unique ships per year for Istanbul)
  * `starlinkAdoption/bosphorus_vessel_types_2020_2024.csv` (type counts for allocation)
* **Precedence:** manual overrides in code take priority over CSVs if present.

**Used in:** all scripts
**Knobs:** set `MANUAL_COUNTS` in `estDemand.py`; set `TARGET_YEAR`.

---

## 11) Forecasting and scenarios

* **Default:** single-year capacity revenue using 2024 unless a scenario file is added.
* **Scenarios (planned):** Base, Conservative, Aggressive with growth and adoption curves.

**Used in:** future `scenarios.yaml`, `run_forecast.py`
**Knobs:** growth per type; adoption S-curves; churn; plan price changes.

---

## 12) Validation stance

* **Backtests:** compare model uniques with the known 2021 unique count.
* **Sanity checks:** compare implied plan counts with public deployment anecdotes for cruise and cargo.
* **Data provenance:** keep links and notes in `docs/usage_evidence.md`.

**Used in:** tests folder (planned)
**Knobs:** thresholds for test pass/fail.

---

## 13) Known limitations

* Annual level only; no monthly seasonality applied yet.
* Unique-by-type uses transit shares as a proxy.
* Adoption and usage rely on ranges and anecdotes where public data is thin.
* No FX, VAT, capex, support cost in the base MRR. Those live in the roadmap.

---

## 14) Quick reference: parameters in code

**`starlinkAdoption/estDemand.py`**

```python
TARGET_YEAR = 2024
ADOPTION = { ... }  # see Section 4
# MANUAL_COUNTS = { ... }  # optional override for one scenario
```

**`revenueProjection/estimateRevenueCapacity.py`**

```python
PLAN_CAP_TB = { ... }       # Section 6
PLAN_FEE    = { ... }       # Section 6
PLAN_MAP    = { ... }       # Section 6
USAGE_TB    = { ... }       # Section 5
AVAIL       = { ... }       # Section 8

# subscriptions per ship
subs = 1 if cap == inf else ceil(USAGE_TB[type] / PLAN_CAP_TB[plan])
```

---

## 15) To-do to improve assumptions

* Add AIS anchor months for 2021 and 2024 to replace proxy shares and validate uniques.
* Build `usage_tb_priors.csv` with evidence weights by type.
* Add pricing profiles for reseller vs direct and a top-up vs extra-line comparison.
* Add FX, taxes, capex, support to move from gross MRR to net.
