# Validation & Testing

This folder contains all validation and testing scripts for the Starlink Turkey Maritime Research Project.

### Test Scripts
| File | Tests | Purpose |
|------|-------|---------|
| `verifyShips.py` | 5 | Validates unique ship estimation methodology |
| `verifyDemand.py` | 7 | Validates demand estimation and adoption rates |
| `verifyRevenue.py` | 8 | Comprehensive revenue validation (all vessel types) |
| `verifyIntegration.py` | 6 | End-to-end pipeline integration tests |
| **TOTAL** | **26** | **Complete test coverage** |

### Output Reports

After running tests, the following report is generated in this folder:
- `verifyRevenue_report.txt` - Revenue validation results

## 🚀 Quick Start

### Run All Tests
From the **repository root**:
```bash
./run_all_tests.sh
```

### Run Individual Tests
From the **repository root**:

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

**Integration:**
```bash
python3 validation/verifyIntegration.py
```

## ✅ What Gets Validated

### Ship Estimation (`verifyShips.py`)
- ✅ Input CSV schemas
- ✅ Anchor year (2021) consistency
- ✅ Confidence band monotonicity (Low ≤ Est ≤ High)
- ✅ Sensitivity to delta parameter

### Demand Estimation (`verifyDemand.py`)
- ✅ Output schema correctness
- ✅ Adoption rate application (10-20% containers, 60-90% cruise, etc.)
- ✅ Type shares sum to 1.0
- ✅ Unique totals consistency
- ✅ LEO totals consistency
- ✅ Range monotonicity
- ✅ Reasonable adoption results (7-18% overall)

### Revenue Validation (`verifyRevenue.py`)
- ✅ **All 8 vessel types** (Container, Bulk_Carrier, Tanker_Total, RoRo_Vehicle, Passenger_Cruise, General_Cargo, Livestock, Reefer)
- ✅ Multi-subscription cases (Passenger_Cruise: 8 subs)
- ✅ Ceiling function boundaries
- ✅ Zero ships handling
- ✅ All 5 plan types (GP_50, GP_500, GP_1TB, GP_2TB, IMO_UNL)
- ✅ Range validity (MRR_Low ≤ MRR_High)
- ✅ Sanity checks on totals
- ✅ Large number stress tests

### Integration (`verifyIntegration.py`)
- ✅ All input files exist
- ✅ Each pipeline stage runs successfully
- ✅ Data flows correctly: estShips → estDemand → estimateRevenue
- ✅ Ship counts consistent across stages
- ✅ Final outputs are reasonable

## 📊 Test Status

All **26 tests** currently **PASS** ✅

**Latest validation results (2024 data):**
- Unique Ships: 6,514 (range: 5,664 - 7,663)
- LEO-Capable: 470 - 1,164 ships (7.2% - 17.9% adoption)
- Monthly Revenue: **$4.5M - $9.5M**

## 🔧 Path Configuration

All validation scripts use absolute paths relative to the repository root:

```python
# Get repo root (parent of validation folder)
REPO_ROOT = Path(__file__).resolve().parent.parent
```

This ensures tests work correctly regardless of where they're run from.

### File Locations Referenced
- `uniqueShipEstimator/istanbul_strait_transits.csv`
- `uniqueShipEstimator/istanbul_unique_estimates.csv`
- `starlinkAdoption/bosphorus_vessel_types_2020_2024.csv`
- `starlinkAdoption/demandEstimate.csv`
- `revenueProjection/estimateRevenue.py`
- `revenueProjection/revenueCapacity.csv`

## 📝 When to Run Tests

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

## 🛠️ Maintaining Tests

### When to Update

**Adoption Rate Changes:**
Update `ADOPTION` dict in `verifyDemand.py` to match `starlinkAdoption/estDemand.py`

**Pricing Changes:**
Update `PLAN_FEE`, `PLAN_CAP_TB` in `verifyRevenue.py` to match `revenueProjection/estimateRevenue.py`

**New Vessel Types:**
Add to `TYPES` array in all test files and add validation cases

**Plan Changes:**
Update `PLAN_MAP` in revenue test files

### Adding New Tests

Use the existing test functions as templates. Key patterns:

```python
def test_my_feature(script_src: Path) -> TestResult:
    """Description."""
    name = "Category: Test name"
    # ... test logic ...
    if condition_fails:
        return fail_(name, "Error message")
    return pass_(name, "Success message")
```

Add your test function to the `tests` list in `main()`.

## 📚 Documentation

For detailed information:
- **Quick guide:** `../TEST_QUICKSTART.md`
- **Full strategy:** `../TESTING_STRATEGY.md`
- **Assumptions:** `../Assumptions.md`
- **Project overview:** `../README.md`


1. **Run before committing:** `./run_all_tests.sh`
2. **Keep tests in sync:** Update tests when changing model assumptions
3. **Add tests for bugs:** When you fix a bug, add a test to prevent regression
4. **Use descriptive names:** Test names should clearly indicate what's being validated
5. **Check reports:** Review generated reports in this folder after test runs


