import sys
from pathlib import Path
import pandas as pd
import math


# Get repo root (parent of validation folder)
REPO_ROOT = Path(__file__).resolve().parent.parent
TOTALS_CSV = REPO_ROOT / "uniqueShipEstimator" / "istanbul_strait_transits.csv"
ESTIMATES_CSV = REPO_ROOT / "uniqueShipEstimator" / "istanbul_unique_estimates.csv"

ANCHOR_YEAR = 2021
ANCHOR_UNIQUE = 6071            # known unique vessels in the anchor year
DELTA = 0.15                    # ± band (0<DELTA<1)
TOLERANCE = 1.0                 # rounding tolerance for anchor check

ANCHOR_TOTAL = None             # e.g., 38551 or None to auto-read from totals CSV


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def check_input_schema_totals(df_totals: pd.DataFrame) -> None:
    expected_cols = ["Year", "Istanbul_Strait_Total_Transits"]
    if list(df_totals.columns) != expected_cols:
        fail(f"Totals CSV columns must be exactly {expected_cols}, got {list(df_totals.columns)}")

    if df_totals["Year"].isnull().any() or df_totals["Istanbul_Strait_Total_Transits"].isnull().any():
        fail("Totals CSV contains missing values")

    if not pd.api.types.is_integer_dtype(df_totals["Year"]):
        if not (df_totals["Year"].dropna() % 1 == 0).all():
            fail("Year column must be integer-like")
        df_totals["Year"] = df_totals["Year"].astype(int)

    if (df_totals["Year"].duplicated().any()):
        fail("Year values must be unique in totals CSV")

    if (df_totals["Istanbul_Strait_Total_Transits"] <= 0).any():
        fail("Totals must be positive for all rows")

    ok("Input schema (totals CSV) is valid")


def check_input_schema_estimates(df_est: pd.DataFrame) -> None:
    expected_cols = [
        "Year",
        "Istanbul_Strait_Total_Transits",
        "Est_Unique",
        "Est_Unique_Low",
        "Est_Unique_High",
    ]
    missing = [c for c in expected_cols if c not in df_est.columns]
    if missing:
        fail(f"Estimates CSV missing columns: {missing}")

    if df_est[expected_cols].isnull().any().any():
        fail("Estimates CSV contains missing values in required columns")

    for c in ["Est_Unique", "Est_Unique_Low", "Est_Unique_High"]:
        if (df_est[c] <= 0).any():
            fail(f"{c} must be positive for all rows")

    ok("Input schema (estimates CSV) is valid")


def recompute_estimates(df_totals: pd.DataFrame, anchor_total: float, anchor_unique: float, delta: float) -> pd.DataFrame:
    r = anchor_total / anchor_unique
    if r <= 0 or math.isinf(r) or math.isnan(r):
        fail("Invalid repeat factor r computed from anchor_total/anchor_unique")

    out = df_totals.copy()
    out["Est_Unique_re"] = (out["Istanbul_Strait_Total_Transits"] / r)
    out["Est_Unique_Low_re"] = (out["Istanbul_Strait_Total_Transits"] / (r * (1 + delta)))
    out["Est_Unique_High_re"] = (out["Istanbul_Strait_Total_Transits"] / (r * (1 - delta)))
    return out, r


def check_anchor_consistency(df_totals: pd.DataFrame,
                             df_est: pd.DataFrame,
                             anchor_year: int,
                             anchor_total: float,
                             anchor_unique: float,
                             delta: float,
                             tolerance: float) -> None:
    merged = df_totals.merge(df_est, on=["Year", "Istanbul_Strait_Total_Transits"], how="inner")
    if anchor_year not in merged["Year"].values:
        fail(f"Anchor year {anchor_year} not present in both CSVs")

    df_anchor = merged[merged["Year"] == anchor_year].iloc[0]
    if abs(df_anchor["Istanbul_Strait_Total_Transits"] - anchor_total) > tolerance:
        warn(f"Anchor total in CSV ({df_anchor['Istanbul_Strait_Total_Transits']}) "
             f"differs from provided anchor_total ({anchor_total}) by > tolerance ({tolerance}). "
             f"Proceeding with provided anchor_total for recomputation.")

    recomputed, r = recompute_estimates(df_totals, anchor_total, anchor_unique, delta)
    row = recomputed[recomputed["Year"] == anchor_year].iloc[0]
    est_row = df_est[df_est["Year"] == anchor_year].iloc[0]

    for est_col, re_col in [
        ("Est_Unique", "Est_Unique_re"),
        ("Est_Unique_Low", "Est_Unique_Low_re"),
        ("Est_Unique_High", "Est_Unique_High_re"),
    ]:
        if abs(est_row[est_col] - round(row[re_col])) > tolerance:
            fail(f"Anchor consistency failed for {est_col}: "
                 f"estimated={est_row[est_col]} vs recomputed≈{round(row[re_col])} "
                 f"(tolerance {tolerance})")

    ok("Anchor consistency holds (estimates align with recomputation)")


def check_monotonic_bands(df_est: pd.DataFrame) -> None:
    bad = df_est[(df_est["Est_Unique_Low"] > df_est["Est_Unique"]) |
                 (df_est["Est_Unique"] > df_est["Est_Unique_High"])]
    if not bad.empty:
        fail("Monotonicity of bands violated in some rows (Low ≤ Est ≤ High).")
    ok("Band monotonicity holds for all rows")


def check_sensitivity(df_totals: pd.DataFrame, anchor_total: float, anchor_unique: float, deltas=(0.05, 0.10, 0.15, 0.20)):
    prev_widths = None
    for d in sorted(deltas, reverse=True):
        tmp, _ = recompute_estimates(df_totals, anchor_total, anchor_unique, d)
        width = (tmp["Est_Unique_High_re"] - tmp["Est_Unique_Low_re"]).abs()
        inside = (tmp["Est_Unique_re"] >= tmp["Est_Unique_Low_re"]) & (tmp["Est_Unique_re"] <= tmp["Est_Unique_High_re"])
        if not inside.all():
            fail(f"Sensitivity sanity failed: point estimate outside interval for delta={d}")
        if prev_widths is not None and not (width <= prev_widths + 1e-9).all():
            fail("Sensitivity sanity failed: interval width did not shrink when delta decreased.")
        prev_widths = width
    ok("Sensitivity sanity holds for tested deltas")


def main():
    # Load CSVs
    try:
        df_totals = pd.read_csv(TOTALS_CSV)
    except Exception as e:
        fail(f"Could not read totals CSV at {TOTALS_CSV}: {e}")
    try:
        df_est = pd.read_csv(ESTIMATES_CSV)
    except Exception as e:
        fail(f"Could not read estimates CSV at {ESTIMATES_CSV}: {e}")

    if ANCHOR_UNIQUE <= 0:
        fail("ANCHOR_UNIQUE must be positive")
    if not (0 < DELTA < 1):
        fail("DELTA must be between 0 and 1")

    check_input_schema_totals(df_totals)
    check_input_schema_estimates(df_est)

    if ANCHOR_TOTAL is None:
        if ANCHOR_YEAR not in df_totals["Year"].values:
            fail(f"ANCHOR_YEAR {ANCHOR_YEAR} not found in totals CSV; cannot infer ANCHOR_TOTAL")
        inferred = df_totals.loc[df_totals["Year"] == ANCHOR_YEAR, "Istanbul_Strait_Total_Transits"].iloc[0]
        anchor_total_used = float(inferred)
        ok(f"Inferred ANCHOR_TOTAL={anchor_total_used} for ANCHOR_YEAR={ANCHOR_YEAR} from totals CSV")
    else:
        anchor_total_used = float(ANCHOR_TOTAL)
        ok(f"Using provided ANCHOR_TOTAL={anchor_total_used} for ANCHOR_YEAR={ANCHOR_YEAR}")

    check_anchor_consistency(df_totals, df_est,
                             ANCHOR_YEAR, anchor_total_used, float(ANCHOR_UNIQUE),
                             float(DELTA), float(TOLERANCE))
    check_monotonic_bands(df_est)
    check_sensitivity(df_totals, anchor_total_used, float(ANCHOR_UNIQUE),
                      deltas=(DELTA/3, DELTA/2, DELTA))

    ok("All validations passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
