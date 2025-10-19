"""
MODES
-----
1) auto
   - Reads per-type *totals* from `bosphorus_vessel_types_2020_2024.csv` for TARGET_YEAR
   - Reads *unique totals* (mid/low/high) from `uniqueShipEstimator/istanbul_unique_estimates.csv` for TARGET_YEAR
   - Allocates uniques proportionally to type shares, then applies LEO adoption per type.

2) manual_totals
   - Use MANUAL_TOTAL_COUNTS (per-type totals) to derive shares.
   - Unique totals come from UNIQUE_TOTAL_OVERRIDE = (mid, low, high) if provided,
     else read from unique estimates CSV for TARGET_YEAR.
   - Allocate uniques proportionally, then apply LEO adoption.

3) manual_uniques
   - Use MANUAL_UNIQUE_COUNTS (per-type uniques) directly.
   - If UNIQUE_TOTAL_OVERRIDE is provided, it will be ignored (unique totals derive from manual uniques).
   - Apply LEO adoption per type directly (no proportional step).

OUTPUTS
-------
- demandEstimate.csv : one-row summary with per-type shares, uniques, and LEO-unique (low/high) + totals
- demandEstimate.txt : human-readable report of the same

"""
from pathlib import Path
import csv

# ==================== CONFIG ====================

MODE = "auto"  # one of: "auto", "manual_totals", "manual_uniques"
TARGET_YEAR = 2024

TRANSITS_CSV = Path("bosphorus_vessel_types_2020_2024.csv")
UNIQUE_EST_CSV = Path("../uniqueShipEstimator/istanbul_unique_estimates.csv")

# LEO adoption rates per vessel type (apply to UNIQUE ships)
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

# For "manual_totals": provide per-type TOTAL transits
MANUAL_TOTAL_COUNTS = None
# Example:
# MANUAL_TOTAL_COUNTS = {
#     "Container": 3533,
#     "Bulk_Carrier": 8777,
#     "Tanker_Total": 9669,
#     "RoRo_Vehicle": 613,
#     "Passenger_Cruise": 2806,
#     "General_Cargo": 15490,
#     "Livestock": 468,
#     "Reefer": 7,
# }

# For "manual_uniques": provide per-type UNIQUE ships directly
MANUAL_UNIQUE_COUNTS = None
# Example:
# MANUAL_UNIQUE_COUNTS = {
#     "Container": 420,
#     "Bulk_Carrier": 1180,
#     "Tanker_Total": 1260,
#     "RoRo_Vehicle": 50,
#     "Passenger_Cruise": 120,
#     "General_Cargo": 2500,
#     "Livestock": 70,
#     "Reefer": 5,
# }

# Optional unique total override (only used in "manual_totals" or "auto")
# Set to None to read from UNIQUE_EST_CSV (auto)
# or set to a tuple (mid, low, high) e.g. (6514, 5664, 7663)
UNIQUE_TOTAL_OVERRIDE = None

# Output filenames
OUT_CSV = Path("demandEstimate.csv")
OUT_TXT = Path("demandEstimate.txt")

# ==================== END CONFIG ====================


TYPE_COLS = list(ADOPTION.keys())


def fail(msg):
    raise SystemExit(f"[ERROR] {msg}")


def read_row_by_year(path: Path, year: int):
    if not path.exists():
        fail(f"Missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            try:
                if int(row["Year"]) == int(year):
                    return row
            except Exception:
                continue
    fail(f"Year {year} not found in {path}")


def get_totals_from_csv(year):
    row = read_row_by_year(TRANSITS_CSV, year)
    counts = {k: float(row[k]) for k in TYPE_COLS}
    total_transits = float(row["Total_Transits"])
    return counts, total_transits


def get_unique_totals(year):
    if UNIQUE_TOTAL_OVERRIDE is not None:
        mid, low, high = UNIQUE_TOTAL_OVERRIDE
        return float(mid), float(low), float(high)
    row = read_row_by_year(UNIQUE_EST_CSV, year)
    return float(row["Est_Unique"]), float(row["Est_Unique_Low"]), float(row["Est_Unique_High"])


def shares_from_totals(total_counts: dict):
    s = sum(total_counts.values())
    if s <= 0:
        return {k: 0.0 for k in TYPE_COLS}
    return {k: total_counts[k] / s for k in TYPE_COLS}


def allocate_uniques_by_share(uniq_mid, uniq_low, uniq_high, shares: dict):
    mid = {k: uniq_mid * shares[k] for k in TYPE_COLS}
    lo  = {k: uniq_low * shares[k] for k in TYPE_COLS}
    hi  = {k: uniq_high * shares[k] for k in TYPE_COLS}
    return mid, lo, hi


def apply_adoption_to_uniques(uniq_lo: dict, uniq_hi: dict):
    # conservative pairing low*low, high*high
    leo_lo  = {k: uniq_lo[k]  * ADOPTION[k][0] for k in TYPE_COLS}
    leo_hi  = {k: uniq_hi[k] * ADOPTION[k][1] for k in TYPE_COLS}
    return leo_lo, leo_hi


def round_dict(d):
    return {k: int(round(v)) for k, v in d.items()}


def write_outputs(label, shares, uniq_mid, uniq_lo, uniq_hi, leo_lo, leo_hi):
    # CSV
    headers = ["Label",
               "Unique_Total", "Unique_Total_Low", "Unique_Total_High",
               "LEO_Unique_Total_Low", "LEO_Unique_Total_High"]
    for k in TYPE_COLS:
        headers += [f"{k}_Share", f"{k}_Unique", f"{k}_Unique_Low", f"{k}_Unique_High",
                    f"{k}_LEO_Unique_Low", f"{k}_LEO_Unique_High"]

    row = {
        "Label": label,
        "Unique_Total": int(round(sum(uniq_mid.values()))),
        "Unique_Total_Low": int(round(sum(uniq_lo.values()))),
        "Unique_Total_High": int(round(sum(uniq_hi.values()))),
        "LEO_Unique_Total_Low": int(round(sum(leo_lo.values()))),
        "LEO_Unique_Total_High": int(round(sum(leo_hi.values()))),
    }
    for k in TYPE_COLS:
        row[f"{k}_Share"] = round(shares.get(k, 0.0), 6)
        row[f"{k}_Unique"] = int(round(uniq_mid.get(k, 0.0)))
        row[f"{k}_Unique_Low"] = int(round(uniq_lo.get(k, 0.0)))
        row[f"{k}_Unique_High"] = int(round(uniq_hi.get(k, 0.0)))
        row[f"{k}_LEO_Unique_Low"] = int(round(leo_lo.get(k, 0.0)))
        row[f"{k}_LEO_Unique_High"] = int(round(leo_hi.get(k, 0.0)))

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerow(row)

    # TXT
    lines = []
    lines.append("Estimated LEO Demand (Unique Vessels)\n")
    lines.append(f"Scenario: {label}")
    lines.append(f"Unique ships (point/low/high): {row['Unique_Total']} / {row['Unique_Total_Low']} / {row['Unique_Total_High']}")
    lines.append(f"LEO-unique ships (low–high): {row['LEO_Unique_Total_Low']} – {row['LEO_Unique_Total_High']}\n")
    lines.append("By Type: share, uniques [low, high], LEO_uniques [low, high] (adoption range)")
    for k in TYPE_COLS:
        a_lo, a_hi = ADOPTION[k]
        lines.append(f"- {k:<17} share={row[f'{k}_Share']:.4f}  "
                     f"unique={row[f'{k}_Unique']} [{row[f'{k}_Unique_Low']}, {row[f'{k}_Unique_High']}]  "
                     f"LEO_unique={row[f'{k}_LEO_Unique_Low']}–{row[f'{k}_LEO_Unique_High']}  "
                     f"(adopt {int(a_lo*100)}%–{int(a_hi*100)}%)")
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved:\n- {OUT_CSV.resolve()}\n- {OUT_TXT.resolve()}")


def main():
    label = None

    if MODE == "manual_uniques":
        if MANUAL_UNIQUE_COUNTS is None:
            fail("MODE=manual_uniques but MANUAL_UNIQUE_COUNTS is None")
        # derive shares from manual uniques for reporting
        total_u = sum(float(MANUAL_UNIQUE_COUNTS[k]) for k in TYPE_COLS)
        shares = {k: (float(MANUAL_UNIQUE_COUNTS[k]) / total_u) if total_u > 0 else 0.0 for k in TYPE_COLS}
        uniq_mid = {k: float(MANUAL_UNIQUE_COUNTS[k]) for k in TYPE_COLS}
        # For ranges, assume ±0 (unless user wants to add uncertainty)
        uniq_lo = {k: float(MANUAL_UNIQUE_COUNTS[k]) for k in TYPE_COLS}
        uniq_hi = {k: float(MANUAL_UNIQUE_COUNTS[k]) for k in TYPE_COLS}
        leo_lo, leo_hi = apply_adoption_to_uniques(uniq_lo, uniq_hi)
        label = "manual_uniques"

    elif MODE == "manual_totals":
        if MANUAL_TOTAL_COUNTS is None:
            fail("MODE=manual_totals but MANUAL_TOTAL_COUNTS is None")
        shares = shares_from_totals({k: float(MANUAL_TOTAL_COUNTS[k]) for k in TYPE_COLS})
        # unique totals source
        mid, low, high = get_unique_totals(TARGET_YEAR)
        uniq_mid, uniq_lo, uniq_hi = allocate_uniques_by_share(mid, low, high, shares)
        leo_lo, leo_hi = apply_adoption_to_uniques(uniq_lo, uniq_hi)
        label = "manual_totals"

    elif MODE == "auto":
        totals, _ = get_totals_from_csv(TARGET_YEAR)
        shares = shares_from_totals(totals)
        mid, low, high = get_unique_totals(TARGET_YEAR)
        uniq_mid, uniq_lo, uniq_hi = allocate_uniques_by_share(mid, low, high, shares)
        leo_lo, leo_hi = apply_adoption_to_uniques(uniq_lo, uniq_hi)
        label = f"auto_{TARGET_YEAR}"

    else:
        fail(f"Unknown MODE: {MODE}")

    write_outputs(label, shares, uniq_mid, uniq_lo, uniq_hi, leo_lo, leo_hi)


if __name__ == "__main__":
    main()
