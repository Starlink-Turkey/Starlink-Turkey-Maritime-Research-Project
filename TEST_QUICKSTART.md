# Testing Quick Start Guide

### Test Files (All in `validation/` folder)

1. **`validation/verifyRevenue.py`** - 8 comprehensive revenue tests
2. **`validation/verifyDemand.py`** - 7 demand estimation tests (previously had NONE!)
3. **`validation/verifyIntegration.py`** - 6 end-to-end pipeline tests
4. **`validation/verifyShips.py`** - 5 ship estimation validation tests
5. **`run_all_tests.sh`** - Convenient script to run all tests from repo root


## Running Tests
### Option 1: Run All Tests at Once (Recommended)

```bash
./run_all_tests.sh
```

This runs all 32 tests and gives you a comprehensive report.

### Option 2: Run Individual Test Suites

All validation scripts are now in the `validation/` folder:

**Ship Estimation:**
```bash
python3 validation/verifyShips.py
```

**Demand Estimation:**
```bash
python3 validation/verifyDemand.py
```

**Revenue Validation:**
```bash
python3 validation/verifyRevenue.py
```

**Integration Test:**
```bash
python3 validation/verifyIntegration.py
```

---

## What Each Test Suite Validates

### 1. Ship Estimation (`verifyShips.py`)
- ✅ Input CSV schemas are correct
- ✅ Anchor year (2021) data is consistent
- ✅ Confidence bands maintain Low ≤ Est ≤ High
- ✅ Sensitivity to delta parameter is reasonable

### 2. Demand Estimation (`verifyDemand.py`)
- ✅ All required output columns exist
- ✅ Adoption rates correctly applied (10-20% for containers, 60-90% for cruise, etc.)
- ✅ Type shares sum to 1.0
- ✅ Totals match sum of per-type values
- ✅ LEO adoption totals are consistent
- ✅ Range monotonicity maintained
- ✅ Overall adoption is reasonable (7-18%)

### 3. Revenue Validation (`verifyRevenue.py`)
- ✅ **All 8 vessel types** calculate correctly
- ✅ Passenger_Cruise multi-subscription (8 subs for 15TB usage)
- ✅ Ceiling function boundaries work correctly
- ✅ Zero ships handled properly
- ✅ All 5 plan types covered (GP_50, GP_500, GP_1TB, GP_2TB, IMO_UNL)
- ✅ MRR_Low ≤ MRR_High for all types
- ✅ Total MRR is in reasonable range ($100K-$50M)
- ✅ Large numbers (10K ships) don't cause overflow

### 4. Integration Test (`verifyIntegration.py`)
- ✅ All required input files exist
- ✅ Ship estimator runs successfully
- ✅ Demand estimator runs successfully
- ✅ Revenue estimator runs successfully
- ✅ Data flows correctly through pipeline (demand → revenue)
- ✅ Final output values are reasonable

---

## Test Results Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| Ship estimation | 5 | ✅ All Pass |
| Demand estimation | 7 | ✅ All Pass |
| Revenue validation | 8 | ✅ All Pass |
| Integration | 6 | ✅ All Pass |
| **TOTAL** | **26** | **✅ All Pass** |

**Current total MRR estimate:** $4.5M – $9.5M monthly (for 2024 data)

---

## When to Run Tests

### ✅ Always run tests:
- Before committing code changes
- After modifying assumptions (adoption rates, pricing, usage)
- After updating input data
- Before generating results for presentations/papers

### 🔴 Tests will catch:
- Broken data pipeline
- Calculation errors
- Invalid input data
- Edge cases that break logic
- Unreasonable outputs

---

## Understanding Test Failures

### If `verify_demand.py` fails:
- Check `demandEstimate.csv` exists
- Verify adoption rates in `estDemand.py` match test expectations
- Check that type shares sum to 1.0

### If `verify_revenue.py` fails:
- Check `demandEstimate.csv` exists in `starlinkAdoption/`
- Verify pricing constants match between script and tests
- Check for path issues (script should work from any directory now)

### If `test_integration.py` fails:
- Check all input CSVs exist
- Run individual scripts manually to see detailed errors
- Verify virtual environment is activated

---

## Modifying Tests

### When you change assumptions:

**Example: Changing adoption rates**

1. Edit `starlinkAdoption/estDemand.py`:
```python
ADOPTION = {
    "Container": (0.15, 0.25),  # Changed from (0.10, 0.20)
    ...
}
```

2. Update `validation/verifyDemand.py`:
```python
ADOPTION = {
    "Container": (0.15, 0.25),  # Match the change
    ...
}
```

3. Run tests to verify:
```bash
python3 validation/verifyDemand.py
```

---

## Adding New Tests

### Template for a new revenue test:

```python
def test_my_new_feature(script_src: Path) -> TestResult:
    """Description of what this tests."""
    name = "Category: Test name"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        mk_repo_skeleton(tmp)
        shutil.copy(script_src, tmp / "revenueProjection" / "estimateRevenue.py")
        
        # Set up test data
        write_demand_csv(
            tmp / "starlinkAdoption" / "demandEstimate.csv",
            {"Container_LEO_Unique_Low": 10, "Container_LEO_Unique_High": 20}
        )
        
        # Run the script
        out, err, code = run_revenue(tmp)
        if code != 0:
            return fail_(name, f"Non-zero exit:\n{err or out}")
        
        # Validate results
        df = pd.read_csv(tmp / "revenueProjection" / "revenueCapacity.csv")
        # ... your validation logic ...
        
        return pass_(name, "Success message")
```

Then add to the `tests` list in `main()`.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "FileNotFoundError: demandEstimate.csv"
Run the demand estimator first:
```bash
cd starlinkAdoption && python3 estDemand.py
```

### "Validation reports not found in old locations"
All validation reports now save to the `validation/` folder:
- `validation/verifyRevenue_report.txt`

### "Command not found: python"
On macOS, use `python3` instead of `python`.

### Tests pass but outputs look wrong
- Check `revenueCapacity.csv` manually
- Compare with `demandEstimate.csv` to verify ship counts
- Review `Assumptions.md` for parameter values

---

## Next Steps

1. ✅ **Run tests now:** `./run_all_tests.sh`
2. 📖 **Read full strategy:** See `TESTING_STRATEGY.md`
3. 🔧 **Customize:** Adjust test parameters to match your assumptions
4. 🚀 **Integrate:** Add test runs to your Git pre-commit hooks

---

## Questions?

- Full details: See `TESTING_STRATEGY.md`
- Code assumptions: See `Assumptions.md`
- Project overview: See `README.md`

**Happy testing!** 🎉

