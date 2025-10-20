#!/usr/bin/env python3
"""
End-to-End Integration Test
Tests the full pipeline: estShips → estDemand → estimateRevenue
"""
import sys
import subprocess
from pathlib import Path
import pandas as pd


# Get repo root (parent of validation folder)
REPO_ROOT = Path(__file__).resolve().parent.parent


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"[OK] {msg}")


def run_command(cmd: list, cwd: Path) -> tuple:
    """Run a command and return stdout, stderr, returncode."""
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=60)
    return proc.stdout, proc.stderr, proc.returncode


def test_pipeline_files_exist():
    """Check that all expected input files exist."""
    print("\n=== Test: Input Files Exist ===")
    
    required_files = [
        "uniqueShipEstimator/istanbul_strait_transits.csv",
        "uniqueShipEstimator/istanbul_unique_estimates.csv",
        "starlinkAdoption/bosphorus_vessel_types_2020_2024.csv",
    ]
    
    repo_root = REPO_ROOT
    missing = []
    
    for file_path in required_files:
        full_path = repo_root / file_path
        if not full_path.exists():
            missing.append(file_path)
    
    if missing:
        fail(f"Missing required input files:\n  " + "\n  ".join(missing))
    
    ok("All required input files exist")


def test_ship_estimator():
    """Test unique ship estimator runs successfully."""
    print("\n=== Test: Unique Ship Estimator (estShips.py) ===")
    
    repo_root = REPO_ROOT
    est_ships_path = repo_root / "uniqueShipEstimator" / "estShips.py"
    
    if not est_ships_path.exists():
        print("[SKIP] estShips.py not found, skipping test")
        return
    
    out, err, code = run_command(
        [sys.executable, str(est_ships_path)],
        repo_root / "uniqueShipEstimator"
    )
    
    if code != 0:
        fail(f"estShips.py failed:\n{err or out}")
    
    # Check output was created
    output_path = repo_root / "uniqueShipEstimator" / "istanbul_unique_estimates.csv"
    if not output_path.exists():
        fail("istanbul_unique_estimates.csv was not created")
    
    ok("estShips.py ran successfully")


def test_demand_estimator():
    """Test demand estimator runs successfully."""
    print("\n=== Test: Demand Estimator (estDemand.py) ===")
    
    repo_root = REPO_ROOT
    est_demand_path = repo_root / "starlinkAdoption" / "estDemand.py"
    
    out, err, code = run_command(
        [sys.executable, str(est_demand_path)],
        repo_root / "starlinkAdoption"
    )
    
    if code != 0:
        fail(f"estDemand.py failed:\n{err or out}")
    
    # Check outputs were created
    demand_csv = repo_root / "starlinkAdoption" / "demandEstimate.csv"
    demand_txt = repo_root / "starlinkAdoption" / "demandEstimate.txt"
    
    if not demand_csv.exists():
        fail("demandEstimate.csv was not created")
    if not demand_txt.exists():
        fail("demandEstimate.txt was not created")
    
    ok("estDemand.py ran successfully")


def test_revenue_estimator():
    """Test revenue estimator runs successfully."""
    print("\n=== Test: Revenue Estimator (estimateRevenue.py) ===")
    
    repo_root = REPO_ROOT
    est_revenue_path = repo_root / "revenueProjection" / "estimateRevenue.py"
    
    out, err, code = run_command(
        [sys.executable, str(est_revenue_path)],
        repo_root / "revenueProjection"
    )
    
    if code != 0:
        fail(f"estimateRevenue.py failed:\n{err or out}")
    
    # Check outputs were created
    revenue_csv = repo_root / "revenueProjection" / "revenueCapacity.csv"
    revenue_txt = repo_root / "revenueProjection" / "revenueCapacity.txt"
    
    if not revenue_csv.exists():
        fail("revenueCapacity.csv was not created")
    if not revenue_txt.exists():
        fail("revenueCapacity.txt was not created")
    
    ok("estimateRevenue.py ran successfully")


def test_data_consistency():
    """Test that data flows consistently through the pipeline."""
    print("\n=== Test: Pipeline Data Consistency ===")
    
    repo_root = REPO_ROOT
    
    # Load demand estimate
    demand_csv = repo_root / "starlinkAdoption" / "demandEstimate.csv"
    revenue_csv = repo_root / "revenueProjection" / "revenueCapacity.csv"
    
    df_demand = pd.read_csv(demand_csv)
    df_revenue = pd.read_csv(revenue_csv)
    
    # Check that all vessel types in revenue are in demand
    revenue_types = set(df_revenue["Type"])
    
    EXPECTED_TYPES = {
        "Container", "Bulk_Carrier", "Tanker_Total", "RoRo_Vehicle",
        "Passenger_Cruise", "General_Cargo", "Livestock", "Reefer"
    }
    
    if revenue_types != EXPECTED_TYPES:
        fail(f"Type mismatch. Expected {EXPECTED_TYPES}, got {revenue_types}")
    
    # Check that ship counts in revenue match demand
    errors = []
    for _, row in df_revenue.iterrows():
        vtype = row["Type"]
        ships_low = row["Ships_Low"]
        ships_high = row["Ships_High"]
        
        demand_low = df_demand.iloc[0][f"{vtype}_LEO_Unique_Low"]
        demand_high = df_demand.iloc[0][f"{vtype}_LEO_Unique_High"]
        
        # Allow for rounding
        if abs(ships_low - demand_low) > 1:
            errors.append(f"{vtype}_Low: revenue has {ships_low}, demand has {demand_low}")
        if abs(ships_high - demand_high) > 1:
            errors.append(f"{vtype}_High: revenue has {ships_high}, demand has {demand_high}")
    
    if errors:
        fail("Ship count mismatches between demand and revenue:\n  " + "\n  ".join(errors))
    
    ok("Data flows consistently from demand → revenue")


def test_reasonable_output_values():
    """Sanity check on final output values."""
    print("\n=== Test: Reasonable Output Values ===")
    
    repo_root = REPO_ROOT
    revenue_csv = repo_root / "revenueProjection" / "revenueCapacity.csv"
    
    df = pd.read_csv(revenue_csv)
    
    # Check no negative values
    if (df["MRR_Low_USD"] < 0).any() or (df["MRR_High_USD"] < 0).any():
        fail("Found negative MRR values")
    
    # Check subscriptions per ship are reasonable (1-10 for most, up to 20 for cruise)
    if (df["Subs_per_ship"] < 1).any():
        fail("Found subscriptions per ship < 1")
    if (df["Subs_per_ship"] > 20).any():
        fail("Found subscriptions per ship > 20 (suspiciously high)")
    
    # Check total MRR is reasonable
    total_low = df["MRR_Low_USD"].sum()
    total_high = df["MRR_High_USD"].sum()
    
    if total_low < 10_000:
        fail(f"Total MRR Low (${total_low:,.0f}) seems unrealistically low")
    if total_high > 100_000_000:
        fail(f"Total MRR High (${total_high:,.0f}) seems unrealistically high")
    if total_low > total_high:
        fail(f"Total MRR Low > High")
    
    ok(f"Output values reasonable: Total MRR ${total_low:,.0f} – ${total_high:,.0f}")


def main():
    print("=" * 70)
    print("END-TO-END INTEGRATION TEST")
    print("Testing: estShips → estDemand → estimateRevenue pipeline")
    print("=" * 70)
    
    try:
        test_pipeline_files_exist()
        test_ship_estimator()
        test_demand_estimator()
        test_revenue_estimator()
        test_data_consistency()
        test_reasonable_output_values()
        
        print("\n" + "=" * 70)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 70)
        print("\nThe complete pipeline executed successfully:")
        print("  1. Unique ship estimation ✓")
        print("  2. Demand estimation ✓")
        print("  3. Revenue projection ✓")
        print("  4. Data consistency ✓")
        return 0
        
    except SystemExit:
        print("\n" + "=" * 70)
        print("❌ INTEGRATION TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

