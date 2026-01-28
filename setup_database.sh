#!/bin/bash
# Database Setup Script for Mile High Potential
# This script sets up PostgreSQL + PostGIS and creates the database schema

set -e  # Exit on any error

echo "========================================================================"
echo "MILE HIGH POTENTIAL - DATABASE SETUP"
echo "========================================================================"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed. Installing..."
    echo ""
    echo "For macOS (using Homebrew):"
    echo "  brew install postgresql@15 postgis"
    echo ""
    echo "After installation, run:"
    echo "  brew services start postgresql@15"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

echo "✓ PostgreSQL is installed"
echo ""

# Database configuration
DB_NAME="mile_high_potential_db"
DB_USER="$USER"  # Use current system user instead of 'postgres'

echo "Creating database: $DB_NAME"
echo "Using database user: $DB_USER"
echo ""

# Drop database if it exists (for clean setup)
psql -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true

# Create database
psql -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;"

echo "✓ Database created"
echo ""

# Create schema
echo "Creating database schema..."
psql -U $DB_USER -d $DB_NAME -f create_schema.sql

echo "✓ Schema created"
echo ""

echo "========================================================================"
echo "DATABASE SETUP COMPLETE!"
echo "========================================================================"
echo ""
echo "Database: $DB_NAME"
echo "Connection string: postgresql://localhost:5432/$DB_NAME"
echo ""
echo "Next steps:"
echo "  1. Run: python load_data_to_database.py"
echo "  2. Test queries: psql -U $DB_USER -d $DB_NAME"
echo ""
