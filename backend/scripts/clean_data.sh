#!/bin/bash
# Data Cleanup Script
# Cleans test data and temporary files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo "🧹 Data Cleanup Script"
echo ""

# Parse command line arguments
CLEAN_TYPE="${1:-all}"

case $CLEAN_TYPE in
    data)
        print_warning "This will delete all user data in data/ directory"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cleaning data/ directory..."
            rm -rf data/*
            print_success "User data cleaned!"
        else
            print_info "Cancelled."
        fi
        ;;
    output)
        print_warning "This will delete all generated project ZIPs in output/ directory"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cleaning output/ directory..."
            rm -rf output/*
            print_success "Output files cleaned!"
        else
            print_info "Cancelled."
        fi
        ;;
    cache)
        print_info "Cleaning Python cache files..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        find . -type f -name "*.pyo" -delete 2>/dev/null || true
        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name ".coverage" -delete 2>/dev/null || true
        rm -rf htmlcov/ 2>/dev/null || true
        print_success "Cache files cleaned!"
        ;;
    logs)
        print_info "Cleaning log files..."
        find . -type f -name "*.log" -delete 2>/dev/null || true
        print_success "Log files cleaned!"
        ;;
    all)
        print_warning "This will clean:"
        echo "  - User data (data/)"
        echo "  - Generated projects (output/)"
        echo "  - Python cache files"
        echo "  - Log files"
        echo ""
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cleaning all data..."
            
            # Clean data
            rm -rf data/* 2>/dev/null || true
            
            # Clean output
            rm -rf output/* 2>/dev/null || true
            
            # Clean cache
            find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            find . -type f -name "*.pyc" -delete 2>/dev/null || true
            find . -type f -name "*.pyo" -delete 2>/dev/null || true
            find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
            find . -type f -name ".coverage" -delete 2>/dev/null || true
            rm -rf htmlcov/ 2>/dev/null || true
            
            # Clean logs
            find . -type f -name "*.log" -delete 2>/dev/null || true
            
            print_success "All data cleaned!"
        else
            print_info "Cancelled."
        fi
        ;;
    *)
        print_error "Unknown clean type: $CLEAN_TYPE"
        echo ""
        echo "Usage: $0 [data|output|cache|logs|all]"
        echo ""
        echo "Options:"
        echo "  data    - Clean user data (data/)"
        echo "  output  - Clean generated projects (output/)"
        echo "  cache   - Clean Python cache files"
        echo "  logs    - Clean log files"
        echo "  all     - Clean everything"
        exit 1
        ;;
esac

echo ""
print_success "Cleanup complete!"
