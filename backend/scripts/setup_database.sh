#!/bin/bash
# Database Setup Script
# Initializes the platform PostgreSQL database

set -e

echo "🗄️  Setting up platform database..."

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running. Please start PostgreSQL first."
    exit 1
fi

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
else
    echo "⚠️  No .env file found. Using default values."
fi

# Database connection details
DB_HOST="${PLATFORM_DB_HOST:-localhost}"
DB_PORT="${PLATFORM_DB_PORT:-5432}"
DB_NAME="${PLATFORM_DB_NAME:-platform_db}"
DB_USER="${PLATFORM_DB_USER:-postgres}"

echo "📍 Database: $DB_NAME on $DB_HOST:$DB_PORT"

# Check if database exists
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "⚠️  Database '$DB_NAME' already exists."
    read -p "Do you want to drop and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Dropping existing database..."
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE $DB_NAME;"
    else
        echo "ℹ️  Keeping existing database. Running schema updates only..."
    fi
fi

# Create database if it doesn't exist
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "📦 Creating database '$DB_NAME'..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"
fi

# Run schema setup
echo "📋 Running schema setup..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f config/database_setup.sql

echo "✅ Database setup complete!"
echo ""
echo "Connection string: postgresql://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
