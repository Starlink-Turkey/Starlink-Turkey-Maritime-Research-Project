# Run all validation tests for the Starlink Turkey Maritime Research Project

set -e  # Exit on first error

echo "=========================================="
echo "Starlink Turkey Maritime - Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not detected. Activating...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
    else
        echo -e "${RED}✗ Virtual environment not found. Run: python3 -m venv venv${NC}"
        exit 1
    fi
fi

# Track overall success
FAILED=0

echo ""
echo "=========================================="
echo "Test 1: Ship Estimation"
echo "=========================================="
if python3 validation/verifyShips.py; then
    echo -e "${GREEN}✓ Ship estimation tests passed${NC}"
else
    echo -e "${RED}✗ Ship estimation tests failed${NC}"
    FAILED=1
fi

echo ""
echo "=========================================="
echo "Test 2: Demand Estimation"
echo "=========================================="
if python3 validation/verifyDemand.py; then
    echo -e "${GREEN}✓ Demand estimation tests passed${NC}"
else
    echo -e "${RED}✗ Demand estimation tests failed${NC}"
    FAILED=1
fi

echo ""
echo "=========================================="
echo "Test 3: Revenue Projection"
echo "=========================================="
if python3 validation/verifyRevenue.py; then
    echo -e "${GREEN}✓ Revenue projection tests passed${NC}"
else
    echo -e "${RED}✗ Revenue projection tests failed${NC}"
    FAILED=1
fi

echo ""
echo "=========================================="
echo "Test 4: End-to-End Integration"
echo "=========================================="
if python3 validation/verifyIntegration.py; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
    FAILED=1
fi

echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "Test Summary:"
    echo "  • Ship estimation: ✓"
    echo "  • Demand estimation: ✓"
    echo "  • Revenue projection: ✓"
    echo "  • Pipeline integration: ✓"
    echo ""
    echo "Your codebase is validated and ready for research!"
    echo "Test reports saved in: validation/"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please review the errors above and fix before committing."
    exit 1
fi
