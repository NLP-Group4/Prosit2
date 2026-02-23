#!/bin/bash
# Test Runner Script
# Runs different test suites with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Virtual environment not activated. Activating agents-env..."
    if [ -d "agents-env" ]; then
        source agents-env/bin/activate
    else
        print_error "Virtual environment 'agents-env' not found. Please create it first."
        exit 1
    fi
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

print_info "Running tests: $TEST_TYPE"
echo ""

# Function to run tests
run_tests() {
    local test_path=$1
    local test_name=$2
    
    print_info "Running $test_name tests..."
    
    if [ "$VERBOSE" = "-v" ] || [ "$VERBOSE" = "--verbose" ]; then
        pytest "$test_path" -v
    else
        pytest "$test_path"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "$test_name tests passed!"
    else
        print_error "$test_name tests failed!"
        return 1
    fi
    echo ""
}

# Run tests based on type
case $TEST_TYPE in
    unit)
        run_tests "tests/unit/" "Unit"
        ;;
    integration)
        run_tests "tests/integration/" "Integration"
        ;;
    e2e)
        run_tests "tests/e2e/" "End-to-End"
        ;;
    all)
        print_info "Running all test suites..."
        echo ""
        
        run_tests "tests/unit/" "Unit" || exit 1
        run_tests "tests/integration/" "Integration" || exit 1
        run_tests "tests/e2e/" "End-to-End" || exit 1
        
        print_success "All test suites passed!"
        ;;
    coverage)
        print_info "Running tests with coverage..."
        pytest tests/ --cov=app --cov=agents --cov-report=html --cov-report=term
        
        if [ $? -eq 0 ]; then
            print_success "Coverage report generated!"
            print_info "Open htmlcov/index.html to view the report"
        else
            print_error "Coverage tests failed!"
            exit 1
        fi
        ;;
    *)
        print_error "Unknown test type: $TEST_TYPE"
        echo ""
        echo "Usage: $0 [unit|integration|e2e|all|coverage] [-v|--verbose]"
        echo ""
        echo "Examples:"
        echo "  $0 unit              # Run unit tests"
        echo "  $0 integration -v    # Run integration tests with verbose output"
        echo "  $0 all               # Run all test suites"
        echo "  $0 coverage          # Run tests with coverage report"
        exit 1
        ;;
esac
