"""
Calculate Development Potential AFTER Ballot Measure
=====================================================
This script calculates what Denver's development potential would look like
after the YIMBY Denver ballot measure passes, which rezones areas near transit:

- 660ft from rail stations → C-MX-8x (8 stories, no FAR limit)
- 1,320ft from rail stations → G-RX-5x (5 stories, FAR 3.0)
- 1,980ft from rail stations → G-MU-3x (3 stories, FAR 1.5)

(Plus similar distances for BRT and parks, but we'll focus on rail for now)
"""

import geopandas as gpd
import pandas as pd

print("="*70)
print("CALCULATING POST-BALLOT MEASURE DEVELOPMENT POTENTIAL")
print("="*70)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n1. Loading data...")
parcels = gpd.read_file('high_opportunity_parcels_v2.geojson')
stations = gpd.read_file('rtd_lightrail_stations.geojson')

print(f"   ✓ Loaded {len(parcels):,} current opportunity parcels")
print(f"   ✓ Loaded {len(stations)} RTD stations")

# ============================================================================
# CALCULATE DISTANCES TO TRANSIT
# ============================================================================

print("\n2. Calculating distances to nearest RTD station...")

# Project to meters for accurate distance calculation
parcels_proj = parcels.to_crs('EPSG:32613')
stations_proj = stations.to_crs('EPSG:32613')

# Calculate distance from each parcel to nearest station
def distance_to_nearest_station(parcel_geom):
    """Calculate distance in feet to nearest RTD station"""
    distances = stations_proj.geometry.distance(parcel_geom)
    min_distance_meters = distances.min()
    min_distance_feet = min_distance_meters * 3.28084  # Convert to feet
    return min_distance_feet

print("   Calculating distances (this may take a minute)...")
parcels_proj['distance_to_station_ft'] = parcels_proj.geometry.apply(distance_to_nearest_station)

# Convert back to WGS84
parcels_with_distance = parcels_proj.to_crs('EPSG:4326')

print(f"   ✓ Calculated distances for {len(parcels_with_distance):,} parcels")

# ============================================================================
# ASSIGN POST-BALLOT MEASURE ZONING
# ============================================================================

print("\n3. Assigning post-ballot measure zoning...")

def get_ballot_measure_zoning(distance_ft, current_zone, current_far):
    """
    Determine zoning after ballot measure based on distance to transit
    
    Key rule: "unless they are otherwise more permissively zoned"
    - Only upzones, never downzones
    - Keeps existing zoning if it's already better
    
    Returns tuple: (new_zone, new_far, new_stories)
    """
    # Determine what ballot measure would assign
    if distance_ft <= 660:  # Within 660ft of station
        ballot_zone = 'C-MX-8x'
        ballot_far = 8.0
        ballot_stories = 8
    elif distance_ft <= 1320:  # Within 1/4 mile of station
        ballot_zone = 'G-RX-5x'
        ballot_far = 3.0
        ballot_stories = 5
    elif distance_ft <= 1980:  # Within 3/8 mile of station
        ballot_zone = 'G-MU-3x'
        ballot_far = 1.5
        ballot_stories = 3
    else:
        # Outside ballot measure zones - keep current zoning
        return (current_zone, current_far, None)
    
    # Compare with current zoning - only upzone if ballot measure is MORE permissive
    # Use FAR as proxy for "more permissive" (higher FAR = more permissive)
    if current_far is not None and current_far >= ballot_far:
        # Current zoning is already equal or better - keep it
        return (current_zone, current_far, None)
    
    # Ballot measure provides more permissive zoning - apply it
    return (ballot_zone, ballot_far, ballot_stories)

# Apply ballot measure zoning
parcels_with_distance['ballot_zone'] = None
parcels_with_distance['ballot_far'] = None
parcels_with_distance['ballot_stories'] = None

for idx, row in parcels_with_distance.iterrows():
    new_zone, new_far, new_stories = get_ballot_measure_zoning(
        row['distance_to_station_ft'], 
        row.get('ZONE_DISTRICT', ''),
        row.get('max_far', None)  # Pass current FAR for comparison
    )
    parcels_with_distance.at[idx, 'ballot_zone'] = new_zone
    parcels_with_distance.at[idx, 'ballot_far'] = new_far if new_far is not None else row.get('max_far', None)
    parcels_with_distance.at[idx, 'ballot_stories'] = new_stories

# Count parcels by new zone
print("\n   Parcels by ballot measure zone:")
zone_counts = parcels_with_distance['ballot_zone'].value_counts()
for zone, count in zone_counts.items():
    print(f"     {zone}: {count:,} parcels")

# ============================================================================
# CALCULATE NEW POTENTIAL UNITS
# ============================================================================

print("\n4. Calculating new development potential...")

# Use the same conservative assumption: 1,500 gross sq ft per unit
# This accounts for common areas, lobbies, elevators, parking, etc.

def calculate_ballot_potential(row):
    """Calculate potential units under ballot measure zoning"""
    land_area_sf = row.get('land_area_sf', 0)
    
    # Use the HIGHER of current FAR or ballot measure FAR (never downzone)
    current_far = row.get('max_far', 0)
    ballot_far = row.get('ballot_far', current_far)
    
    # Use whichever is higher
    effective_far = max(current_far, ballot_far) if ballot_far is not None else current_far
    
    # Calculate: land_area_sf × FAR ÷ 1,500 sf/unit
    potential_units = (land_area_sf * effective_far) / 1500
    
    return round(potential_units)

parcels_with_distance['ballot_potential_units'] = parcels_with_distance.apply(
    calculate_ballot_potential, axis=1
)

# ============================================================================
# CALCULATE STATISTICS
# ============================================================================

print("\n5. Comparing current vs. ballot measure potential...")

# IMPORTANT: Exclude "Industrial Needs Rezoning" from current stats
# These parcels require rezoning and shouldn't count in pre-ballot scenario
current_opportunities = parcels_with_distance[
    parcels_with_distance['opportunity_type'] != 'Industrial Near Transit'
].copy()

print(f"   Note: Excluding {len(parcels_with_distance) - len(current_opportunities):,} 'Industrial Needs Rezoning' parcels from current scenario")
print(f"         (These are on I-A/I-B zoning which doesn't allow residential without rezoning)")

# Current stats (excluding Industrial Needs Rezoning)
current_parcels = len(current_opportunities)
current_acres = current_opportunities['land_area_acres'].sum()
current_units = current_opportunities['potential_units'].sum()

# Ballot measure stats (includes everything - Industrial parcels would be upzoned)
ballot_parcels = len(parcels_with_distance)
ballot_acres = parcels_with_distance['land_area_acres'].sum()
ballot_units = parcels_with_distance['ballot_potential_units'].sum()

print("\n" + "="*70)
print("CURRENT ZONING (Excluding Industrial Needs Rezoning):")
print(f"  Parcels: {current_parcels:,}")
print(f"  Acres: {current_acres:,.0f}")
print(f"  Potential Units: {current_units:,.0f}")

print("\n" + "="*70)
print("AFTER BALLOT MEASURE (All parcels, including upzoned industrial):")
print(f"  Parcels: {ballot_parcels:,}")
print(f"  Acres: {ballot_acres:,.0f}")
print(f"  Potential Units: {ballot_units:,.0f}")

print("\n" + "="*70)
print("INCREASE:")
print(f"  Additional Parcels: {ballot_parcels - current_parcels:+,}")
print(f"  Additional Units: {ballot_units - current_units:+,.0f} ({((ballot_units/current_units - 1) * 100):+.1f}%)")

# ============================================================================
# SAVE RESULTS
# ============================================================================

print("\n6. Saving results...")

# Save as new GeoJSON file
parcels_with_distance.to_file('ballot_measure_parcels.geojson', driver='GeoJSON')
print(f"   ✓ Saved to: ballot_measure_parcels.geojson")

# Also create a summary CSV
summary_data = []
for idx, row in parcels_with_distance.iterrows():
    summary_data.append({
        'address': row.get('SITUS_ADDRESS_LINE1', ''),
        'current_zone': row.get('ZONE_DISTRICT', ''),
        'current_potential_units': row.get('potential_units', 0),
        'distance_to_station_ft': row['distance_to_station_ft'],
        'ballot_zone': row.get('ballot_zone', 'No change'),
        'ballot_potential_units': row['ballot_potential_units'],
        'additional_units': row['ballot_potential_units'] - row.get('potential_units', 0)
    })

summary_df = pd.DataFrame(summary_data)
summary_df.to_csv('ballot_measure_summary.csv', index=False)
print(f"   ✓ Saved summary to: ballot_measure_summary.csv")

print("\n" + "="*70)
print("✓ CALCULATION COMPLETE")
print("="*70)
print("\nNext steps:")
print("1. Review ballot_measure_parcels.geojson")
print("2. Update map to add toggle between current and ballot measure scenarios")
