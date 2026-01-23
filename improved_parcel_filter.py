"""
IMPROVED PARCEL FILTERING SCRIPT
=================================
This script applies better filtering to remove false positives:
1. Railroads (owner-based and geometry-based detection)
2. Open Space parcels (OS zoning)
3. Roads/ROW (narrow linear parcels)
4. Existing apartments (10+ units or FAR > 0.25)
5. Public/government parcels
6. Separates commercial buildings on mixed-use zoning

Run this script in your zoning_project directory.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("IMPROVED PARCEL FILTERING - REMOVING FALSE POSITIVES")
print("="*70)

# ============================================================================
# CONFIGURATION
# ============================================================================

# File paths - adjust if needed
PARCELS_FILE = 'parcels_near_transit.geojson'
OUTPUT_FILE = 'high_opportunity_parcels_v2.geojson'

# Thresholds
MIN_VACANT_LAND_ACRES = 0.5
MIN_TEARDOWN_SIZE_SF = 3000  # Minimum lot size for teardown potential
# Using Polsby-Popper compactness score to detect narrow parcels:
# PP < 0.3 for RTD/railroad/city vacant land (thin strips)
# PP < 0.15 for general narrow ROW parcels

# NEW: Stories to Units per Acre lookup (based on real-world development patterns)
STORIES_TO_UPA = {
    2: 30,
    2.5: 35,
    3: 60,
    5: 100,
    7: 160,
    8: 160,
    10: 160,
    12: 220,
    16: 280,
    20: 350,
    30: 450
}

def calculate_units_from_stories(land_area_acres, stories):
    """
    Calculate potential units using stories-to-units-per-acre lookup.
    
    Args:
        land_area_acres: Land area in acres
        stories: Number of stories (height limit from zoning)
        
    Returns:
        Estimated potential units (rounded to nearest integer)
    """
    # Find closest story height in lookup table
    if stories in STORIES_TO_UPA:
        units_per_acre = STORIES_TO_UPA[stories]
    else:
        # Interpolate or use nearest value
        story_heights = sorted(STORIES_TO_UPA.keys())
        if stories < min(story_heights):
            units_per_acre = STORIES_TO_UPA[min(story_heights)]
        elif stories > max(story_heights):
            units_per_acre = STORIES_TO_UPA[max(story_heights)]
        else:
            # Find nearest story height
            nearest = min(story_heights, key=lambda x: abs(x - stories))
            units_per_acre = STORIES_TO_UPA[nearest]
    
    return round(land_area_acres * units_per_acre)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n1. Loading data...")
parcels = gpd.read_file(PARCELS_FILE)
print(f"   Loaded {len(parcels):,} parcels near transit")

# Parcels already have ZONE_10 field, so we don't need to load zoning
# Just rename ZONE_10 to ZONE_DISTRICT for consistency
parcels['ZONE_DISTRICT'] = parcels['ZONE_10']

print(f"   ✓ Using existing ZONE_10 field from parcels")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_polsby_popper(geom):
    """Calculate Polsby-Popper compactness score
    
    PP = (4π × Area) / (Perimeter²)
    
    Returns:
        1.0 = perfect circle (very compact)
        0.8+ = square/round shape
        0.5-0.8 = rectangular
        0.3-0.5 = elongated
        <0.3 = very elongated/thin strip
    """
    try:
        import math
        
        # Get the polygon's exterior coordinates
        if hasattr(geom, 'exterior'):
            coords = list(geom.exterior.coords)
        else:
            return 1.0  # Assume compact if can't calculate
        
        if len(coords) < 3:
            return 1.0
        
        # Calculate area using shoelace formula
        area = 0
        for i in range(len(coords) - 1):
            area += coords[i][0] * coords[i + 1][1]
            area -= coords[i + 1][0] * coords[i][1]
        area = abs(area) / 2.0
        
        # Calculate perimeter
        perimeter = 0
        for i in range(len(coords) - 1):
            x1, y1 = coords[i][0], coords[i][1]
            x2, y2 = coords[i + 1][0], coords[i + 1][1]
            dx = x2 - x1
            dy = y2 - y1
            perimeter += (dx**2 + dy**2)**0.5
        
        # Polsby-Popper score
        if perimeter > 0 and area > 0:
            pp_score = (4 * math.pi * area) / (perimeter ** 2)
            return pp_score
        
        return 1.0  # Assume compact if calculation fails
        
    except Exception as e:
        return 1.0  # Assume compact if error

# Test geometry access with first parcel
print("   Testing geometry compactness...")
test_row = parcels.iloc[0]
test_geom = test_row.get('geometry') if 'geometry' in test_row else test_row['geometry']
test_pp = calculate_polsby_popper(test_geom)
print(f"   Test parcel Polsby-Popper score: {test_pp:.3f}")

def is_railroad(row):
    """Detect railroad parcels"""
    owner = str(row.get('OWNER_NAME', '')).upper()
    d_class = str(row.get('D_CLASS_CN', '')).upper()
    
    # Check owner - look for railroad companies (including abbreviations)
    railroad_terms = [
        'RAILROAD', 'RAILWAY',
        'UNION PACIFIC', 'UP RR',
        'BNSF', 'BURLINGTON NORTHERN', 'BN RR',
        ' RR CO', ' RR PROPERTY', ' RR TAX'  # Catches "X RR CO", "X RR PROPERTY", etc.
    ]
    if any(term in owner for term in railroad_terms):
        return True
    
    # Check property class
    if 'RAILROAD' in d_class or 'RAIL' in d_class or 'RAILWAY' in d_class:
        return True
    
    # Check geometry (very elongated parcels using Polsby-Popper)
    try:
        geom = row.get('geometry') if 'geometry' in row else None
        if geom is not None:
            pp_score = calculate_polsby_popper(geom)
            # PP < 0.15 indicates very thin strip (likely rail ROW)
            if pp_score < 0.15:
                return True
    except:
        pass
    
    return False

def is_road_or_row(row):
    """Detect road/right-of-way parcels"""
    d_class = str(row.get('D_CLASS_CN', '')).upper()
    owner = str(row.get('OWNER_NAME', '')).upper()
    
    # GENERAL COMMON ELEMENTS is a key indicator of ROW/infrastructure
    if 'GENERAL COMMON ELEMENTS' in d_class:
        return True
    
    # Check for ROW in description
    if 'RIGHT' in d_class and 'WAY' in d_class:
        return True
    if 'ROW' in d_class or 'ROAD' in d_class or 'STREET' in d_class:
        return True
    
    # Check geometry using Polsby-Popper compactness score
    try:
        geom = row.get('geometry') if 'geometry' in row else None
        if geom is not None:
            pp_score = calculate_polsby_popper(geom)
            land_area_sf = row.get('LAND_AREA', 0)
            
            # For RTD, railroad, or city-owned VACANT LAND: use stricter geometry filter
            # These are likely rail corridors, not developable sites
            if 'VACANT LAND' in d_class and not 'COMMERCIAL' in d_class and not 'INDUSTRIAL' in d_class:
                if any(term in owner for term in ['REGIONAL TRANSPORTATION DISTRICT', 'BURLINGTON NORTHERN', 'BN RR', ' RR CO', 'CITY & COUNTY']):
                    # PP score < 0.3 indicates thin strip/corridor
                    if pp_score < 0.3:
                        return True
            
            # General case: very elongated parcels (PP < 0.15)
            if pp_score < 0.15 and land_area_sf < 50000:  # Less than ~1 acre
                return True
    except:
        pass
    
    return False

def is_open_space(row):
    """Detect parks and open space"""
    zone = str(row.get('ZONE_DISTRICT', '')).upper()
    d_class = str(row.get('D_CLASS_CN', '')).upper()
    owner = str(row.get('OWNER_NAME', '')).upper()
    
    # Open space zoning
    if zone.startswith('OS-'):
        return True
    
    # Park ownership
    if 'PARK' in owner or 'RECREATION' in owner:
        return True
    
    # Park classification
    if 'PARK' in d_class or 'RECREATION' in d_class:
        return True
    
    return False

def is_public_government(row):
    """Detect public/government parcels we should exclude"""
    owner = str(row.get('OWNER_NAME', '')).upper()
    d_class = str(row.get('D_CLASS_CN', '')).upper()
    
    # City & County ownership - only exclude actual government facilities
    if 'CITY & COUNTY' in owner or 'CITY AND COUNTY' in owner:
        # Check property type - only exclude if it's clearly a facility
        if any(term in d_class for term in ['SCHOOL', 'GOVERNMENT', 'PUBLIC', 'FIRE', 'POLICE']):
            return True
        # Note: GENERAL COMMON ELEMENTS is caught by is_road_or_row filter
    
    # State/Federal government
    if any(term in owner for term in ['STATE OF COLORADO', 'US GOVT', 'FEDERAL', 'DEPT OF']):
        if 'VACANT' not in d_class:  # Allow vacant state land near transit
            return True
    
    # Schools, government buildings (regardless of owner)
    if any(term in d_class for term in ['SCHOOL', 'GOVERNMENT BUILDING']):
        return True
    
    return False

def is_existing_apartment(row):
    """Detect existing apartment buildings (not redevelopment opportunities)"""
    units = row.get('TOT_UNITS', 0) or 0
    assessed_bldg = row.get('ASSESSED_BLDG_VALUE_LOCAL', 0) or 0
    assessed_land = row.get('ASSESSED_LAND_VALUE_LOCAL', 1) or 1
    land_area = row.get('LAND_AREA', 0) or 0
    
    # Has significant units already
    if units >= 10:
        return True
    
    # High building value suggests substantial development
    if assessed_bldg > 0 and land_area > 0:
        # Calculate rough FAR from assessed values
        # If building value >> land value, it's developed
        if assessed_bldg / assessed_land > 2:
            return True
    
    return False

# ============================================================================
# APPLY EXCLUSIONS
# ============================================================================

print("\n2. Applying exclusion filters...")
initial_count = len(parcels)

# Add filtering flags
print("   Calculating filter flags...")
parcels['is_railroad'] = parcels.apply(is_railroad, axis=1)
parcels['is_road'] = parcels.apply(is_road_or_row, axis=1)
parcels['is_open_space'] = parcels.apply(is_open_space, axis=1)
parcels['is_public_govt'] = parcels.apply(is_public_government, axis=1)
parcels['is_existing_apt'] = parcels.apply(is_existing_apartment, axis=1)

# Count exclusions
print(f"\n   Exclusion counts:")
print(f"   - Railroads: {parcels['is_railroad'].sum():,}")
print(f"   - Roads/ROW: {parcels['is_road'].sum():,}")
print(f"   - Open Space/Parks: {parcels['is_open_space'].sum():,}")
print(f"   - Public/Government: {parcels['is_public_govt'].sum():,}")
print(f"   - Existing Apartments: {parcels['is_existing_apt'].sum():,}")

# Debug: Check RTD vacant land specifically
rtd_vacant = parcels[
    (parcels['OWNER_NAME'].str.contains('REGIONAL TRANSPORTATION DISTRICT', na=False)) &
    (parcels['D_CLASS_CN'].str.contains('VACANT LAND', na=False))
]
print(f"\n   DEBUG: RTD Vacant Land parcels: {len(rtd_vacant)}")
print(f"   DEBUG: RTD Vacant Land flagged as road: {rtd_vacant['is_road'].sum()}")

# Apply exclusions
parcels_filtered = parcels[
    ~parcels['is_railroad'] &
    ~parcels['is_road'] &
    ~parcels['is_open_space'] &
    ~parcels['is_public_govt'] &
    ~parcels['is_existing_apt']
].copy()

excluded_count = initial_count - len(parcels_filtered)
print(f"\n   ✓ Excluded {excluded_count:,} parcels ({excluded_count/initial_count*100:.1f}%)")
print(f"   ✓ Remaining: {len(parcels_filtered):,} parcels")

# ============================================================================
# CATEGORIZE OPPORTUNITIES
# ============================================================================

print("\n3. Categorizing redevelopment opportunities...")

def get_max_stories(zone_district):
    """Extract maximum story height from zone district
    
    Special handling:
    - I-MX zones: I-MX-3 = 3 stories, I-MX-5 = 5 stories, I-MX-8 = 8 stories, I-MX-12 = 12 stories
    - I-A, I-B zones: 3 stories (typical for industrial conversions)
    - C-MX, G-MU, G-RX, etc with numbers: Extract story height from zone name
    """
    try:
        zone = str(zone_district).upper()
        
        # I-A and I-B: assume 3 stories if converted to residential
        if zone in ['I-A', 'I-B']:
            return 3
        
        # All zones with numbers: extract the number as story height
        # Examples: I-MX-8 = 8 stories, C-MX-12 = 12 stories, G-RX-5 = 5 stories
        import re
        matches = re.findall(r'(\d+)', zone)
        if matches:
            # Get the last number (e.g., C-MX-12 -> 12, G-RX-5 -> 5)
            return int(matches[-1])
    except:
        pass
    return 3  # Default assumption (3 stories = walk-up)

# Calculate current FAR
parcels_filtered['land_area_sf'] = parcels_filtered['LAND_AREA'].fillna(0)
parcels_filtered['land_area_acres'] = parcels_filtered['land_area_sf'] / 43560

# Estimate current FAR from building area
parcels_filtered['res_bldg_sf'] = parcels_filtered['RES_ABOVE_GRADE_AREA'].fillna(0)
parcels_filtered['com_bldg_sf'] = parcels_filtered['COM_GROSS_AREA'].fillna(0)
parcels_filtered['total_bldg_sf'] = parcels_filtered['res_bldg_sf'] + parcels_filtered['com_bldg_sf']
parcels_filtered['current_far'] = parcels_filtered.apply(
    lambda x: x['total_bldg_sf'] / x['land_area_sf'] if x['land_area_sf'] > 0 else 0,
    axis=1
)

# Get max stories from zoning
parcels_filtered['max_stories'] = parcels_filtered['ZONE_DISTRICT'].apply(get_max_stories)

# Get units
parcels_filtered['current_units'] = parcels_filtered['TOT_UNITS'].fillna(0)

# ============================================================================
# OPPORTUNITY CATEGORIES
# ============================================================================

opportunities = []

# Category 1: Large Vacant Land
large_vacant = parcels_filtered[
    (parcels_filtered['D_CLASS_CN'].str.contains('VACANT', na=False, case=False)) &
    (parcels_filtered['land_area_acres'] >= MIN_VACANT_LAND_ACRES) &
    (parcels_filtered['current_units'] == 0)
].copy()
large_vacant['opportunity_type'] = 'Large Vacant Land'
# NEW: Calculate potential units using stories-to-units-per-acre lookup
large_vacant['potential_units'] = large_vacant.apply(
    lambda row: calculate_units_from_stories(row['land_area_acres'], row['max_stories']), 
    axis=1
)
opportunities.append(large_vacant)
print(f"   - Large Vacant Land: {len(large_vacant):,} parcels ({large_vacant['land_area_acres'].sum():.0f} acres)")

# Category 2: Single-Family on Multi-Unit Zoning
# Must have: residential use, low density, multi-unit zoning
sf_on_mu = parcels_filtered[
    (parcels_filtered['D_CLASS_CN'].str.contains('SFR|SINGLE', na=False, case=False)) &
    (parcels_filtered['ZONE_DISTRICT'].str.contains('MU|MX|RH|RX|MS', na=False, case=False)) &
    (parcels_filtered['current_units'] <= 1) &
    (parcels_filtered['current_far'] < 0.25)  # Very low density
].copy()
sf_on_mu['opportunity_type'] = 'SF on Multi-Unit Zoning'
sf_on_mu['potential_units'] = sf_on_mu.apply(
    lambda row: calculate_units_from_stories(row['land_area_acres'], row['max_stories']), 
    axis=1
)
opportunities.append(sf_on_mu)
print(f"   - SF on Multi-Unit Zoning: {len(sf_on_mu):,} parcels ({sf_on_mu['land_area_acres'].sum():.0f} acres)")

# Category 3: Commercial on Mixed-Use Zoning (NEW!)
# Must have: 0 units, commercial use, mixed-use zoning
comm_on_mu = parcels_filtered[
    (parcels_filtered['current_units'] == 0) &
    (parcels_filtered['D_CLASS_CN'].str.contains('COMMERCIAL|RETAIL|OFFICE', na=False, case=False)) &
    (parcels_filtered['ZONE_DISTRICT'].str.contains('MU|MX', na=False, case=False)) &
    (parcels_filtered['land_area_acres'] >= 0.25)  # At least quarter acre
].copy()
comm_on_mu['opportunity_type'] = 'Commercial on Mixed-Use Zoning'
comm_on_mu['potential_units'] = comm_on_mu.apply(
    lambda row: calculate_units_from_stories(row['land_area_acres'], row['max_stories']), 
    axis=1
)
opportunities.append(comm_on_mu)
print(f"   - Commercial on Mixed-Use Zoning: {len(comm_on_mu):,} parcels ({comm_on_mu['land_area_acres'].sum():.0f} acres)")

# Category 4: Industrial Conversion (on mixed-use zoning)
industrial = parcels_filtered[
    (parcels_filtered['D_CLASS_CN'].str.contains('INDUSTRIAL|WAREHOUSE', na=False, case=False)) &
    (parcels_filtered['ZONE_DISTRICT'].str.contains('MU|MX|MS|IMX', na=False, case=False)) &
    (parcels_filtered['land_area_acres'] >= 0.25)
].copy()
industrial['opportunity_type'] = 'Industrial Conversion'
industrial['potential_units'] = industrial.apply(
    lambda row: calculate_units_from_stories(row['land_area_acres'], row['max_stories']), 
    axis=1
)
opportunities.append(industrial)
print(f"   - Industrial Conversion: {len(industrial):,} parcels ({industrial['land_area_acres'].sum():.0f} acres)")

# Category 5: Industrial Near Transit (NEW! - I-A, I-B zoning near stations)
# These are industrial-zoned parcels that could be upzoned for TOD
industrial_transit = parcels_filtered[
    (parcels_filtered['D_CLASS_CN'].str.contains('INDUSTRIAL|WAREHOUSE|COMMERCIAL', na=False, case=False)) &
    (parcels_filtered['ZONE_DISTRICT'].str.contains('I-A|I-B', na=False, case=False)) &
    (parcels_filtered['land_area_acres'] >= 0.25)
].copy()
industrial_transit['opportunity_type'] = 'Industrial Near Transit'
# These would need rezoning - assume 3 stories if upzoned to residential
industrial_transit['potential_units'] = industrial_transit.apply(
    lambda row: calculate_units_from_stories(row['land_area_acres'], 3), 
    axis=1
)
opportunities.append(industrial_transit)
print(f"   - Industrial Near Transit: {len(industrial_transit):,} parcels ({industrial_transit['land_area_acres'].sum():.0f} acres)")

# Category 6: Teardown Candidates
# Small SF homes in high-value zones
teardowns = parcels_filtered[
    (parcels_filtered['D_CLASS_CN'].str.contains('SFR|SINGLE', na=False, case=False)) &
    (parcels_filtered['land_area_sf'] >= MIN_TEARDOWN_SIZE_SF) &
    (parcels_filtered['current_units'] <= 1) &
    (parcels_filtered['APPRAISED_LAND_VALUE'] > parcels_filtered['APPRAISED_IMP_VALUE'] * 2) &  # Land worth more than building
    (parcels_filtered['ZONE_DISTRICT'].str.contains('MU|MX|RH|RX', na=False, case=False))
].copy()
teardowns['opportunity_type'] = 'Teardown Candidate'
teardowns['potential_units'] = teardowns.apply(
    lambda row: calculate_units_from_stories(row['land_area_acres'], row['max_stories']), 
    axis=1
)
opportunities.append(teardowns)
print(f"   - Teardown Candidates: {len(teardowns):,} parcels ({teardowns['land_area_acres'].sum():.0f} acres)")

# ============================================================================
# COMBINE AND SAVE
# ============================================================================

print("\n4. Combining results...")
all_opportunities = pd.concat(opportunities, ignore_index=True)

print(f"\n   Total opportunity parcels: {len(all_opportunities):,}")
print(f"   Total opportunity land: {all_opportunities['land_area_acres'].sum():.0f} acres")
print(f"   Estimated potential units: {all_opportunities['potential_units'].sum():.0f} @ FAR 2.0")

# Save
print(f"\n5. Saving to: {OUTPUT_FILE}")
all_opportunities.to_file(OUTPUT_FILE, driver='GeoJSON')

print("\n" + "="*70)
print("✓ FILTERING COMPLETE")
print("="*70)
print(f"\nNext step: Run the map visualization script with the new filtered parcels!")