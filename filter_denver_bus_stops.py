"""
Filter Bus Stops to Denver City Limits
========================================
Filters the medium-frequency bus stops to only include stops within Denver city boundaries.
Uses Denver zoning districts to define the exact city boundary (same method as rail stops).

This version uses direct JSON loading to avoid Fiona compatibility issues.

Requirements:
    pip install shapely
"""

import pandas as pd
import json
from shapely.geometry import shape, Point, MultiPolygon, Polygon

print("="*70)
print("FILTERING BUS STOPS TO DENVER CITY LIMITS")
print("="*70)

# ============================================================================
# STEP 1: Load Denver Boundary from Zoning Data
# ============================================================================

print("\n1. Loading Denver boundary from zoning data...")

try:
    # Load zoning districts GeoJSON directly
    with open('ODC_ZONE_ZONING_A_-6072697703037489513.geojson', 'r') as f:
        zoning_data = json.load(f)
    
    print(f"   ✓ Loaded zoning GeoJSON with {len(zoning_data['features'])} features")
    
    # Convert all zoning district geometries to Shapely objects
    print("   Creating Denver boundary by merging all zoning districts...")
    polygons = []
    skipped = 0
    
    for feature in zoning_data['features']:
        # Skip features with null geometry
        if feature.get('geometry') is None:
            skipped += 1
            continue
            
        try:
            geom = shape(feature['geometry'])
            if geom.is_valid:
                polygons.append(geom)
            else:
                # Try to fix invalid geometries
                geom = geom.buffer(0)
                if geom.is_valid:
                    polygons.append(geom)
        except Exception as e:
            skipped += 1
            continue
    
    print(f"   ✓ Processed {len(polygons)} valid zoning district geometries")
    if skipped > 0:
        print(f"   ℹ Skipped {skipped} features with null or invalid geometries")
    
    # Create a unified Denver boundary by taking the union of all polygons
    print("   Merging geometries (this may take a moment)...")
    from shapely.ops import unary_union
    denver_boundary = unary_union(polygons)
    
    print(f"   ✓ Created unified Denver boundary")
    print(f"   Boundary type: {denver_boundary.geom_type}")
    
except FileNotFoundError:
    print(f"   ✗ File not found: ODC_ZONE_ZONING_A_-6072697703037489513.geojson")
    print("   Please ensure the zoning GeoJSON file is in the current directory")
    exit(1)
except Exception as e:
    print(f"   ✗ Error loading zoning data: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ============================================================================
# STEP 2: Load Bus Stop Data
# ============================================================================

print("\n2. Loading bus stop data...")

csv_file = 'bus_stop_data/medium_frequency_bus_stops.csv'
try:
    bus_stops = pd.read_csv(csv_file)
    print(f"   ✓ Loaded {len(bus_stops):,} medium-frequency bus stops")
except FileNotFoundError:
    print(f"   ✗ File not found: {csv_file}")
    print("   Please run analyze_bus_frequencies_simplified.py first!")
    exit(1)

# ============================================================================
# STEP 3: Spatial Filter - Keep Only Stops Within Denver
# ============================================================================

print("\n3. Filtering stops to Denver boundary...")
print("   Checking each stop (this may take a moment)...")

denver_stops_list = []
processed = 0
interval = max(100, len(bus_stops) // 20)  # Progress updates

for idx, stop in bus_stops.iterrows():
    # Create point from stop coordinates
    point = Point(stop['stop_lon'], stop['stop_lat'])
    
    # Check if point is within Denver boundary
    if denver_boundary.contains(point):
        denver_stops_list.append(stop)
    
    processed += 1
    if processed % interval == 0:
        pct = (processed / len(bus_stops)) * 100
        print(f"   Progress: {processed:,} / {len(bus_stops):,} ({pct:.1f}%)")

denver_stops = pd.DataFrame(denver_stops_list)

print(f"\n   Total medium-frequency stops (all RTD): {len(bus_stops):,}")
print(f"   Stops within Denver boundary: {len(denver_stops):,}")
print(f"   Removed (outside Denver): {len(bus_stops) - len(denver_stops):,} stops ({(len(bus_stops) - len(denver_stops))/len(bus_stops)*100:.1f}%)")

# ============================================================================
# STEP 4: Export Denver-Only Results
# ============================================================================

print("\n4. Exporting Denver-only results...")

# Export to CSV
denver_csv = 'bus_stop_data/denver_medium_frequency_bus_stops.csv'
denver_stops.to_csv(denver_csv, index=False)
print(f"   ✓ Saved to {denver_csv}")

# Export to GeoJSON
geojson = {
    "type": "FeatureCollection",
    "features": []
}

for _, stop in denver_stops.iterrows():
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(stop['stop_lon']), float(stop['stop_lat'])]
        },
        "properties": {
            "stop_id": str(stop['stop_id']),
            "stop_name": stop['stop_name'],
            "peak_frequency": float(stop['peak_frequency']),
            "am_frequency": float(stop['am_trips_per_hour']),
            "pm_frequency": float(stop['pm_trips_per_hour'])
        }
    }
    geojson['features'].append(feature)

denver_geojson = 'bus_stop_data/denver_medium_frequency_bus_stops.geojson'
with open(denver_geojson, 'w') as f:
    json.dump(geojson, f, indent=2)

print(f"   ✓ Saved to {denver_geojson}")

# ============================================================================
# STEP 5: Statistics
# ============================================================================

print("\n5. Denver Bus Stop Statistics:")
print("="*70)

print(f"\n   Frequency Distribution (Denver only):")
freq_2_3 = len(denver_stops[(denver_stops['peak_frequency'] >= 2) & (denver_stops['peak_frequency'] < 3)])
freq_3_4 = len(denver_stops[(denver_stops['peak_frequency'] >= 3) & (denver_stops['peak_frequency'] < 4)])
freq_4_6 = len(denver_stops[(denver_stops['peak_frequency'] >= 4) & (denver_stops['peak_frequency'] < 6)])
freq_6_plus = len(denver_stops[denver_stops['peak_frequency'] >= 6])

if len(denver_stops) > 0:
    print(f"   2-3 trips/hour:  {freq_2_3:,} stops ({freq_2_3/len(denver_stops)*100:.1f}%)")
    print(f"   3-4 trips/hour:  {freq_3_4:,} stops ({freq_3_4/len(denver_stops)*100:.1f}%)")
    print(f"   4-6 trips/hour:  {freq_4_6:,} stops ({freq_4_6/len(denver_stops)*100:.1f}%)")
    print(f"   6+ trips/hour:   {freq_6_plus:,} stops ({freq_6_plus/len(denver_stops)*100:.1f}%)")

    print(f"\n   Top 10 Highest Frequency Stops (Denver):")
    top_denver = denver_stops.nlargest(min(10, len(denver_stops)), 'peak_frequency')[['stop_name', 'peak_frequency']]
    for idx, row in top_denver.iterrows():
        print(f"   {row['stop_name'][:60]:60s}: {row['peak_frequency']:4.1f}/hr")
else:
    print("   No stops found within Denver boundary!")

# ============================================================================
# STEP 6: Comparison
# ============================================================================

print(f"\n6. Comparison with Full RTD Dataset:")
print("="*70)

print(f"\n   Full RTD Coverage:")
print(f"   - Total stops: {len(bus_stops):,}")
print(f"   - Average frequency: {bus_stops['peak_frequency'].mean():.2f} trips/hour")
print(f"   - Median frequency: {bus_stops['peak_frequency'].median():.2f} trips/hour")

if len(denver_stops) > 0:
    print(f"\n   Denver Only:")
    print(f"   - Total stops: {len(denver_stops):,}")
    print(f"   - Average frequency: {denver_stops['peak_frequency'].mean():.2f} trips/hour")
    print(f"   - Median frequency: {denver_stops['peak_frequency'].median():.2f} trips/hour")

print(f"\n   Excluded (Boulder, Aurora, etc.):")
excluded = len(bus_stops) - len(denver_stops)
print(f"   - Total stops: {excluded:,}")
if excluded > 0:
    excluded_stops = bus_stops[~bus_stops['stop_id'].isin(denver_stops['stop_id'])]
    print(f"   - Average frequency: {excluded_stops['peak_frequency'].mean():.2f} trips/hour")

# ============================================================================
# STEP 7: Sample Locations
# ============================================================================

if len(denver_stops) > 0:
    print(f"\n7. Sample Stops by Location:")

    # Downtown area (approximate coordinates)
    downtown = denver_stops[
        (denver_stops['stop_lat'] >= 39.73) & 
        (denver_stops['stop_lat'] <= 39.76) &
        (denver_stops['stop_lon'] >= -105.01) &
        (denver_stops['stop_lon'] <= -104.98)
    ]

    if len(downtown) > 0:
        print(f"\n   Downtown ({len(downtown)} stops):")
        top_downtown = downtown.nlargest(min(3, len(downtown)), 'peak_frequency')[['stop_name', 'peak_frequency']]
        for idx, row in top_downtown.iterrows():
            print(f"   - {row['stop_name']}: {row['peak_frequency']:.1f}/hr")

    # Capitol Hill / Cheesman Park area
    capitol_hill = denver_stops[
        (denver_stops['stop_lat'] >= 39.72) & 
        (denver_stops['stop_lat'] <= 39.74) &
        (denver_stops['stop_lon'] >= -104.98) &
        (denver_stops['stop_lon'] <= -104.95)
    ]

    if len(capitol_hill) > 0:
        print(f"\n   Capitol Hill / Colfax ({len(capitol_hill)} stops):")
        top_capitol = capitol_hill.nlargest(min(3, len(capitol_hill)), 'peak_frequency')[['stop_name', 'peak_frequency']]
        for idx, row in top_capitol.iterrows():
            print(f"   - {row['stop_name']}: {row['peak_frequency']:.1f}/hr")

# ============================================================================
# COMPLETE
# ============================================================================

print("\n" + "="*70)
print("FILTERING COMPLETE")
print("="*70)

print(f"\nOutput files (Denver only):")
print(f"  {denver_csv}")
print(f"  {denver_geojson}")

print(f"\nNext steps:")
print(f"1. Visualize {denver_geojson} to verify boundaries look correct")
print(f"2. Update setup_bus_stops.py to use denver_medium_frequency_bus_stops.csv")
print(f"3. Run setup_bus_stops.py to import to database")
print(f"4. Run calculate_bus_stop_distances.py to calculate parcel distances")

print(f"\nNote: This uses the exact Denver zoning boundary (same as rail stops).")
print(f"This ensures perfect consistency across all TOD/POD/BOD policies.")
