#!/bin/bash
# Run the complete Mile High Potential data pipeline
# This regenerates all data and visualizations from scratch

set -e  # Exit on any error

echo "========================================================================"
echo "MILE HIGH POTENTIAL - FULL DATA PIPELINE"
echo "========================================================================"
echo ""

echo "Step 1/5: Filtering parcels within 3/8 mile of transit..."
python filter_parcels_near_transit.py

echo ""
echo "Step 2/5: Classifying opportunity types..."
python improved_parcel_filter.py

echo ""
echo "Step 3/5: Calculating ballot measure impacts..."
python calculate_ballot_measure.py

echo ""
echo "Step 4/5: Generating About page..."
python generate_about_page.py

echo ""
echo "Step 5/5: Generating interactive map..."
python add_parcels_to_map.py

echo ""
echo "========================================================================"
echo "✓ PIPELINE COMPLETE!"
echo "========================================================================"
echo ""
echo "Generated files:"
echo "  - about.html"
echo "  - denver_tod_with_parcels_v2.html"
echo ""
echo "Open denver_tod_with_parcels_v2.html in your browser to view the map!"
