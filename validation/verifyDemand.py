#!/usr/bin/env python3
"""
Demand Estimation Validation Tests
Tests for estDemand.py - currently has NO validation!
"""
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple
import pandas as pd
import csv


# Get repo root (parent of validation folder)
REPO_ROOT = Path(__file__).resolve().parent.parent
DEMAND_CSV = REPO_ROOT / "starlinkAdoption" / "demandEstimate.csv"

TYPES = [
    "Container","Bulk_Carrier","Tanker_Total","RoRo_Vehicle",
    "Passenger_Cruise","General_Cargo","Livestock","Reefer",
]

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


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"[OK] {msg}")


def run_demand_script(repo_root: Path) -> Tuple[str, str, int]:
    """Run estDemand.py from repo root."""
    proc = subprocess.run(
        [sys.executable, "starlinkAdoption/estDemand.py"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout, proc.stderr, proc.returncode


def test_output_schema():
    """Test that demandEstimate.csv has all required columns."""
    print("\n=== Test: Output Schema ===")
    
    demand_csv = DEMAND_CSV
    if not demand_csv.exists():
        fail(f"demandEstimate.csv not found at {demand_csv}")
    
    df = pd.read_csv(demand_csv)
    
    # Check required columns
    required = ["Label", "Unique_Total", "Unique_Total_Low", "Unique_Total_High",
                "LEO_Unique_Total_Low", "LEO_Unique_Total_High"]
    
    for vtype in TYPES:
        required.extend([
            f"{vtype}_Share",
            f"{vtype}_Unique",
            f"{vtype}_Unique_Low",
            f"{vtype}_Unique_High",
            f"{vtype}_LEO_Unique_Low",
            f"{vtype}_LEO_Unique_High",
        ])
    
    missing = [c for c in required if c not in df.columns]
    if missing:
        fail(f"Missing columns: {missing}")
    
    ok("All required columns present")


def test_adoption_rates_applied():
    """Test that adoption rates are correctly applied to unique ships."""
    print("\n=== Test: Adoption Rates Applied Correctly ===")
    
    demand_csv = DEMAND_CSV
    df = pd.read_csv(demand_csv)
    row = df.iloc[0]
    
    errors = []
    for vtype in TYPES:
        unique_low = row[f"{vtype}_Unique_Low"]
        unique_high = row[f"{vtype}_Unique_High"]
        leo_low = row[f"{vtype}_LEO_Unique_Low"]
        leo_high = row[f"{vtype}_LEO_Unique_High"]
        
        adopt_low, adopt_high = ADOPTION[vtype]
        
        # Expected LEO = Unique * Adoption
        expected_leo_low = unique_low * adopt_low
        expected_leo_high = unique_high * adopt_high
        
        # Allow rounding tolerance
        if abs(leo_low - expected_leo_low) > 1.5:
            errors.append(f"{vtype}_LEO_Low: got {leo_low}, expected ~{expected_leo_low:.1f}")
        if abs(leo_high - expected_leo_high) > 1.5:
            errors.append(f"{vtype}_LEO_High: got {leo_high}, expected ~{expected_leo_high:.1f}")
    
    if errors:
        fail("Adoption rate mismatches:\n  " + "\n  ".join(errors))
    
    ok("Adoption rates correctly applied to all vessel types")


def test_share_sum_to_one():
    """Test that type shares sum to ~1.0."""
    print("\n=== Test: Type Shares Sum to 1.0 ===")
    
    demand_csv = DEMAND_CSV
    df = pd.read_csv(demand_csv)
    row = df.iloc[0]
    
    share_sum = sum(row[f"{vtype}_Share"] for vtype in TYPES)
    
    if abs(share_sum - 1.0) > 0.001:
        fail(f"Type shares sum to {share_sum:.6f}, expected 1.0")
    
    ok(f"Type shares sum to {share_sum:.6f} ≈ 1.0")


def test_unique_totals_match_sum():
    """Test that Unique_Total equals sum of per-type uniques."""
    print("\n=== Test: Unique Totals Match Per-Type Sums ===")
    
    demand_csv = DEMAND_CSV
    df = pd.read_csv(demand_csv)
    row = df.iloc[0]
    
    unique_total = row["Unique_Total"]
    unique_sum = sum(row[f"{vtype}_Unique"] for vtype in TYPES)
    
    if abs(unique_total - unique_sum) > 1:
        fail(f"Unique_Total ({unique_total}) != sum of type uniques ({unique_sum})")
    
    ok(f"Unique_Total ({unique_total}) matches sum of type uniques ({unique_sum})")


def test_leo_totals_match_sum():
    """Test that LEO_Unique totals match sum of per-type LEO uniques."""
    print("\n=== Test: LEO Totals Match Per-Type Sums ===")
    
    demand_csv = DEMAND_CSV
    df = pd.read_csv(demand_csv)
    row = df.iloc[0]
    
    leo_low_total = row["LEO_Unique_Total_Low"]
    leo_high_total = row["LEO_Unique_Total_High"]
    
    leo_low_sum = sum(row[f"{vtype}_LEO_Unique_Low"] for vtype in TYPES)
    leo_high_sum = sum(row[f"{vtype}_LEO_Unique_High"] for vtype in TYPES)
    
    if abs(leo_low_total - leo_low_sum) > 1:
        fail(f"LEO_Unique_Total_Low ({leo_low_total}) != sum ({leo_low_sum})")
    if abs(leo_high_total - leo_high_sum) > 1:
        fail(f"LEO_Unique_Total_High ({leo_high_total}) != sum ({leo_high_sum})")
    
    ok(f"LEO totals match: Low {leo_low_total} ≈ {leo_low_sum}, High {leo_high_total} ≈ {leo_high_sum}")


def test_range_monotonicity():
    """Test that Low <= Mid <= High for all types."""
    print("\n=== Test: Range Monotonicity (Low <= Mid <= High) ===")
    
    demand_csv = DEMAND_CSV
    df = pd.read_csv(demand_csv)
    row = df.iloc[0]
    
    errors = []
    for vtype in TYPES:
        low = row[f"{vtype}_Unique_Low"]
        mid = row[f"{vtype}_Unique"]
        high = row[f"{vtype}_Unique_High"]
        
        if not (low <= mid <= high):
            errors.append(f"{vtype}: {low} <= {mid} <= {high} violated")
        
        leo_low = row[f"{vtype}_LEO_Unique_Low"]
        leo_high = row[f"{vtype}_LEO_Unique_High"]
        
        if not (leo_low <= leo_high):
            errors.append(f"{vtype} LEO: {leo_low} <= {leo_high} violated")
    
    if errors:
        fail("Monotonicity violations:\n  " + "\n  ".join(errors))
    
    ok("All types maintain Low <= Mid <= High")


def test_reasonable_adoption_results():
    """Sanity check: LEO adoption should be reasonable fraction of total."""
    print("\n=== Test: Reasonable Adoption Results ===")
    
    demand_csv = DEMAND_CSV
    df = pd.read_csv(demand_csv)
    row = df.iloc[0]
    
    leo_low = row["LEO_Unique_Total_Low"]
    leo_high = row["LEO_Unique_Total_High"]
    unique_total = row["Unique_Total"]
    
    # Overall adoption should be between 0% and 100%
    adoption_low_pct = (leo_low / unique_total) * 100 if unique_total > 0 else 0
    adoption_high_pct = (leo_high / unique_total) * 100 if unique_total > 0 else 0
    
    if adoption_low_pct < 0 or adoption_low_pct > 100:
        fail(f"Adoption low {adoption_low_pct:.1f}% out of range [0, 100]")
    if adoption_high_pct < 0 or adoption_high_pct > 100:
        fail(f"Adoption high {adoption_high_pct:.1f}% out of range [0, 100]")
    if adoption_low_pct > adoption_high_pct:
        fail(f"Adoption low ({adoption_low_pct:.1f}%) > high ({adoption_high_pct:.1f}%)")
    
    ok(f"Overall adoption reasonable: {adoption_low_pct:.1f}% – {adoption_high_pct:.1f}%")


def main():
    print("=" * 60)
    print("Demand Estimation Validator (estDemand.py)")
    print("=" * 60)
    
    try:
        test_output_schema()
        test_adoption_rates_applied()
        test_share_sum_to_one()
        test_unique_totals_match_sum()
        test_leo_totals_match_sum()
        test_range_monotonicity()
        test_reasonable_adoption_results()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0
        
    except SystemExit:
        print("\n" + "=" * 60)
        print("❌ TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

