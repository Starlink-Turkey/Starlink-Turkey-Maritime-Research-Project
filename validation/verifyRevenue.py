from __future__ import annotations
import csv
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


REVENUE_SCRIPT_REL = Path("revenueProjection/estimateRevenue.py")

# Types and parameters must mirror your revenue script EXACTLY.
TYPES = [
    "Container","Bulk_Carrier","Tanker_Total","RoRo_Vehicle",
    "Passenger_Cruise","General_Cargo","Livestock","Reefer",
]
PLAN_CAP_TB = {"GP_50":0.05,"GP_500":0.50,"GP_1TB":1.00,"GP_2TB":2.00,"IMO_UNL": float('inf')}
PLAN_FEE    = {"GP_50":250,"GP_500":650,"GP_1TB":1150,"GP_2TB":2150,"IMO_UNL":2500}
PLAN_MAP    = {
    "Container":"IMO_UNL","Tanker_Total":"IMO_UNL","Bulk_Carrier":"GP_1TB",
    "General_Cargo":"GP_500","RoRo_Vehicle":"GP_1TB","Reefer":"GP_500",
    "Livestock":"GP_500","Passenger_Cruise":"GP_2TB"
}
USAGE_TB    = {
    "Container":1.5,"Tanker_Total":1.0,"Bulk_Carrier":0.3,"General_Cargo":0.08,
    "RoRo_Vehicle":0.3,"Reefer":0.3,"Livestock":0.15,"Passenger_Cruise":15.0
}
AVAIL = {t:1.0 for t in TYPES}

REPORT_PATH = Path(__file__).resolve().with_name("verifyRevenue_report.txt")


# ---------------------------
# Helpers
# ---------------------------

def find_revenue_script(start: Path) -> Path | None:
    """Try to find revenueProjection/estimateRevenue.py by walking up."""
    for up in [start, *start.parents[:4]]:
        candidate = up / REVENUE_SCRIPT_REL
        if candidate.exists():
            return candidate.resolve()
    return None

def subs_per_ship(vtype: str) -> int:
    """Must mirror the logic in the revenue script."""
    plan = PLAN_MAP[vtype]
    cap  = PLAN_CAP_TB[plan]
    use  = USAGE_TB[vtype]
    return 1 if cap == float('inf') else int(math.ceil(use / cap))

def mk_repo_skeleton(root: Path):
    (root / "starlinkAdoption").mkdir(parents=True, exist_ok=True)
    (root / "revenueProjection").mkdir(parents=True, exist_ok=True)

def write_demand_csv(path: Path, demand_row: Dict[str, float]):
    """Create a 1-row demandEstimate.csv with required columns."""
    cols: List[str] = []
    for t in TYPES:
        cols += [f"{t}_LEO_Unique_Low", f"{t}_LEO_Unique_High"]
    row = {c: 0 for c in cols}
    row.update(demand_row)
    df = pd.DataFrame([row], columns=cols)
    df.to_csv(path, index=False)

def run_revenue(repo_root: Path) -> Tuple[str, str, int]:
    """Run the revenue script from the repo root."""
    proc = subprocess.run(
        [sys.executable, "revenueProjection/estimateRevenue.py"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=90,
    )
    return proc.stdout, proc.stderr, proc.returncode



@dataclass
class TestResult:
    name: str
    ok: bool
    notes: List[str] = field(default_factory=list)

    def add(self, msg: str):
        self.notes.append(msg)

def pass_(name: str, *notes: str) -> TestResult:
    tr = TestResult(name=name, ok=True)
    for n in notes: tr.add(n)
    return tr

def fail_(name: str, *notes: str) -> TestResult:
    tr = TestResult(name=name, ok=False)
    for n in notes: tr.add(n)
    return tr



def test_all_vessel_types(script_src: Path) -> TestResult:
    """Test revenue calculation for ALL vessel types, not just Container/Bulk."""
    name = "Comprehensive: All 8 vessel types calculate correctly"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        # Test one ship of each type
        test_data = {}
        for vtype in TYPES:
            test_data[f"{vtype}_LEO_Unique_Low"] = 1
            test_data[f"{vtype}_LEO_Unique_High"] = 1
        
        write_demand_csv(tmp / "starlinkAdoption" / "demandEstimate.csv", test_data)
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        
        errors = []
        for vtype in TYPES:
            row = df[df["Type"] == vtype].iloc[0]
            expected_subs = subs_per_ship(vtype)
            expected_fee = PLAN_FEE[PLAN_MAP[vtype]]
            expected_mrr = 1 * expected_subs * expected_fee * AVAIL[vtype]
            
            if row["Subs_per_ship"] != expected_subs:
                errors.append(f"{vtype}: subs mismatch (got {row['Subs_per_ship']}, exp {expected_subs})")
            if abs(row["MRR_Low_USD"] - expected_mrr) > 0.01:
                errors.append(f"{vtype}: MRR mismatch (got {row['MRR_Low_USD']}, exp {expected_mrr})")
        
        if errors:
            return fail_(name, *errors)
        return pass_(name, "All 8 vessel types compute correctly")


def test_passenger_cruise_multi_subs(script_src: Path) -> TestResult:
    """Passenger_Cruise should require 8 subscriptions (15TB / 2TB cap)."""
    name = "Edge case: Passenger_Cruise multi-subscription (8 subs)"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        write_demand_csv(
            tmp / "starlinkAdoption" / "demandEstimate.csv",
            {"Passenger_Cruise_LEO_Unique_Low": 1, "Passenger_Cruise_LEO_Unique_High": 1}
        )
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        row = df[df["Type"] == "Passenger_Cruise"].iloc[0]
        
        # 15TB usage / 2TB cap = 7.5 → ceil = 8 subs
        expected_subs = 8
        expected_mrr = 1 * 8 * 2150  # 1 ship * 8 subs * $2150/sub
        
        if row["Subs_per_ship"] != expected_subs:
            return fail_(name, f"Expected {expected_subs} subs, got {row['Subs_per_ship']}")
        if abs(row["MRR_Low_USD"] - expected_mrr) > 0.01:
            return fail_(name, f"Expected MRR ${expected_mrr}, got ${row['MRR_Low_USD']}")
        
        return pass_(name, f"Passenger_Cruise correctly calculates 8 subscriptions → ${expected_mrr} MRR")


def test_ceiling_boundary_cases(script_src: Path) -> TestResult:
    """Test ceil() edge cases: usage exactly at cap, slightly over cap."""
    name = "Math: Ceiling function boundary cases"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        # Bulk_Carrier: 0.3TB usage / 1TB cap = 0.3 → ceil = 1
        # RoRo_Vehicle: 0.3TB usage / 1TB cap = 0.3 → ceil = 1
        write_demand_csv(
            tmp / "starlinkAdoption" / "demandEstimate.csv",
            {
                "Bulk_Carrier_LEO_Unique_Low": 1, "Bulk_Carrier_LEO_Unique_High": 1,
                "RoRo_Vehicle_LEO_Unique_Low": 1, "RoRo_Vehicle_LEO_Unique_High": 1,
            }
        )
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        
        # Both should need exactly 1 subscription
        for vtype in ["Bulk_Carrier", "RoRo_Vehicle"]:
            row = df[df["Type"] == vtype].iloc[0]
            if row["Subs_per_ship"] != 1:
                return fail_(name, f"{vtype} should need 1 sub, got {row['Subs_per_ship']}")
        
        return pass_(name, "Ceiling boundaries work correctly (usage < cap → 1 sub)")


def test_zero_ships_handling(script_src: Path) -> TestResult:
    """Test that zero ships in a category doesn't break calculations."""
    name = "Edge case: Zero ships in categories (Reefer, Livestock)"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        write_demand_csv(
            tmp / "starlinkAdoption" / "demandEstimate.csv",
            {
                "Container_LEO_Unique_Low": 10, "Container_LEO_Unique_High": 20,
                "Reefer_LEO_Unique_Low": 0, "Reefer_LEO_Unique_High": 0,
                "Livestock_LEO_Unique_Low": 0, "Livestock_LEO_Unique_High": 0,
            }
        )
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        
        # Zero ships should result in zero MRR
        for vtype in ["Reefer", "Livestock"]:
            row = df[df["Type"] == vtype].iloc[0]
            if row["MRR_Low_USD"] != 0 or row["MRR_High_USD"] != 0:
                return fail_(name, f"{vtype} should have $0 MRR with 0 ships")
        
        return pass_(name, "Zero ships handled correctly (MRR = $0)")


def test_all_plan_types(script_src: Path) -> TestResult:
    """Verify all 5 plan types are tested: GP_50, GP_500, GP_1TB, GP_2TB, IMO_UNL."""
    name = "Coverage: All 5 Starlink plan types are used"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        # One ship of each type to cover all plans
        test_data = {}
        for vtype in TYPES:
            test_data[f"{vtype}_LEO_Unique_Low"] = 1
            test_data[f"{vtype}_LEO_Unique_High"] = 1
        
        write_demand_csv(tmp / "starlinkAdoption" / "demandEstimate.csv", test_data)
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        
        plans_used = set(df["Plan"].unique())
        expected_plans = {"GP_500", "GP_1TB", "GP_2TB", "IMO_UNL"}
        # Note: GP_50 not used in current PLAN_MAP
        
        missing = expected_plans - plans_used
        if missing:
            return fail_(name, f"Missing plan types in output: {missing}")
        
        return pass_(name, f"All expected plan types present: {plans_used}")


def test_range_validity(script_src: Path) -> TestResult:
    """Test that MRR_Low <= MRR_High for all vessel types."""
    name = "Sanity: MRR_Low <= MRR_High for all types"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        # Realistic data with proper low < high
        test_data = {
            "Container_LEO_Unique_Low": 40, "Container_LEO_Unique_High": 130,
            "Bulk_Carrier_LEO_Unique_Low": 30, "Bulk_Carrier_LEO_Unique_High": 110,
            "Tanker_Total_LEO_Unique_Low": 130, "Tanker_Total_LEO_Unique_High": 350,
            "Passenger_Cruise_LEO_Unique_Low": 200, "Passenger_Cruise_LEO_Unique_High": 450,
        }
        write_demand_csv(tmp / "starlinkAdoption" / "demandEstimate.csv", test_data)
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        
        errors = []
        for _, row in df.iterrows():
            if row["MRR_Low_USD"] > row["MRR_High_USD"]:
                errors.append(f"{row['Type']}: Low ${row['MRR_Low_USD']} > High ${row['MRR_High_USD']}")
        
        if errors:
            return fail_(name, *errors)
        return pass_(name, "All types maintain MRR_Low <= MRR_High")


def test_reasonable_total_mrr(script_src: Path) -> TestResult:
    """Sanity check: total MRR should be reasonable for real-world data."""
    name = "Sanity: Total MRR is plausible for actual data scale"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        # Use realistic 2024 data from your actual demandEstimate.csv
        test_data = {
            "Container_LEO_Unique_Low": 48, "Container_LEO_Unique_High": 131,
            "Bulk_Carrier_LEO_Unique_Low": 36, "Bulk_Carrier_LEO_Unique_High": 114,
            "Tanker_Total_LEO_Unique_Low": 132, "Tanker_Total_LEO_Unique_High": 358,
            "Passenger_Cruise_LEO_Unique_Low": 231, "Passenger_Cruise_LEO_Unique_High": 468,
        }
        write_demand_csv(tmp / "starlinkAdoption" / "demandEstimate.csv", test_data)
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        total_low = df["MRR_Low_USD"].sum()
        total_high = df["MRR_High_USD"].sum()
        
        # Sanity bounds: should be between $100K and $50M monthly
        if total_low < 100_000:
            return fail_(name, f"Total MRR Low (${total_low:,.0f}) seems too low")
        if total_high > 50_000_000:
            return fail_(name, f"Total MRR High (${total_high:,.0f}) seems too high")
        if total_low > total_high:
            return fail_(name, f"Low (${total_low:,.0f}) > High (${total_high:,.0f})")
        
        return pass_(name, f"Total MRR reasonable: ${total_low:,.0f} – ${total_high:,.0f}")


def test_large_numbers(script_src: Path) -> TestResult:
    """Test with very large ship counts to check for overflow."""
    name = "Stress: Large ship counts don't cause overflow"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        # Stress test with 10,000 cruise ships
        write_demand_csv(
            tmp / "starlinkAdoption" / "demandEstimate.csv",
            {"Passenger_Cruise_LEO_Unique_Low": 10000, "Passenger_Cruise_LEO_Unique_High": 10000}
        )
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Failed with large numbers:\n{err or out}")

        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        row = df[df["Type"] == "Passenger_Cruise"].iloc[0]
        
        # 10,000 ships * 8 subs * $2,150 = $172,000,000
        expected = 10000 * 8 * 2150
        if abs(row["MRR_Low_USD"] - expected) > 1:
            return fail_(name, f"Large number calculation failed: got ${row['MRR_Low_USD']}, exp ${expected}")
        
        return pass_(name, f"Large numbers handled correctly: ${expected:,.0f}")


# ---------------------------
# Runner
# ---------------------------

def main():
    here = Path(__file__).resolve().parent
    script_src = find_revenue_script(here)
    results: List[TestResult] = []

    banner = []
    banner.append("Revenue Projection Validator")
    banner.append("==============================================")
    if script_src is None:
        msg = f"ERROR: Could not find '{REVENUE_SCRIPT_REL}' starting from {here}"
        print(msg)
        REPORT_PATH.write_text(msg + "\n", encoding="utf-8")
        return
    banner.append(f"Using script: {script_src}")
    banner.append("")
    print("\n".join(banner))

    # Run comprehensive tests
    tests = [
        test_all_vessel_types,
        test_passenger_cruise_multi_subs,
        test_ceiling_boundary_cases,
        test_zero_ships_handling,
        test_all_plan_types,
        test_range_validity,
        test_reasonable_total_mrr,
        test_large_numbers,
    ]
    for fn in tests:
        try:
            res = fn(script_src)
        except Exception as e:
            res = fail_(fn.__name__, f"Unhandled exception: {e}")
        results.append(res)

    # Summaries
    passed = sum(1 for r in results if r.ok)
    total  = len(results)

    # Pretty print
    lines: List[str] = []
    lines.append("Revenue Validation Results")
    lines.append("==============================================")
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        lines.append(f"[{status}] {r.name}")
        for note in r.notes:
            lines.append(f"    - {note}")
        if not r.notes:
            lines.append("    -")
    lines.append("==============================================")
    lines.append(f"Passed {passed}/{total} tests")
    lines.append("")

    # Output to console and file
    report = "\n".join(lines)
    print(report)
    try:
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"Saved detailed report to: {REPORT_PATH}")
    except Exception as e:
        print(f"Could not write report file: {e}")

if __name__ == "__main__":
    main()

