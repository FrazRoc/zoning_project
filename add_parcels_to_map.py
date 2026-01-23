"""
UPDATED INTERACTIVE MAP WITH PARCELS
=====================================
Creates an interactive map showing:
- Zoning districts (colored by category)
- RTD rail stations (clickable)
- 6 categories of redevelopment opportunities:
  1. Large Vacant Land (red)
  2. SF on Multi-Unit Zoning (orange)
  3. Commercial on Mixed-Use Zoning (cyan)
  4. Industrial Conversion (purple)
  5. Industrial Near Transit (hot pink) <- NEW!
  6. Teardown Candidates (yellow)
"""

import geopandas as gpd
import folium
from folium import GeoJson
import json

print("="*70)
print("CREATING INTERACTIVE MAP WITH IMPROVED PARCEL CATEGORIES")
print("="*70)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n1. Loading data...")
zoning = gpd.read_file('ODC_ZONE_ZONING_A_-6072697703037489513.geojson')
parcels = gpd.read_file('ballot_measure_parcels.geojson')

print(f"   ✓ Loaded {len(zoning):,} zoning districts")
print(f"   ✓ Loaded {len(parcels):,} parcels (with ballot measure data)")

# Create two datasets for toggle
# Current: exclude Industrial Near Transit (not legally developable)
current_parcels = parcels[parcels['opportunity_type'] != 'Industrial Near Transit'].copy()

# Ballot: include all parcels
ballot_parcels = parcels.copy()

# Calculate stats
current_units = current_parcels['potential_units'].sum()
ballot_units = ballot_parcels['ballot_potential_units'].sum()
increase = ballot_units - current_units
increase_pct = (increase / current_units) * 100

print(f"   Current scenario: {len(current_parcels):,} parcels, {current_units:,.0f} units")
print(f"   Ballot scenario: {len(ballot_parcels):,} parcels, {ballot_units:,.0f} units (+{increase_pct:.1f}%)")

# ============================================================================
# OFFICIAL DENVER ZONING COLORS
# ============================================================================

ZONE_COLORS = {
    # Downtown zones
    'D-C': '#E60000',      # Downtown Core
    'D-TD': '#E60000',     # Downtown Theater District  
    'D-CV': '#E60000',     # Downtown Civic
    'D-AS': '#E60000',     # Downtown Arapahoe Square
    
    # Mixed-use zones
    'C-MX-3': '#FF6A00',   'C-MX-5': '#FF6A00',  'C-MX-8': '#FF6A00',
    'C-MX-12': '#FF6A00',  'C-MX-16': '#FF6A00', 'C-MX-20': '#FF6A00',
    'G-MU-3': '#FF6A00',   'G-MU-5': '#FF6A00',  'G-MU-8': '#FF6A00',
    'U-MX-2': '#FF6A00',   'U-MX-2X': '#FF6A00', 'U-MX-3': '#FF6A00',
    'U-MX-5': '#FF6A00',   'U-MX-8': '#FF6A00',  'U-MX-12': '#FF6A00',
    'S-MX-3': '#FF6A00',   'S-MX-5': '#FF6A00',  'S-MX-8': '#FF6A00',
    
    # Multi-unit zones
    'U-RH-2.5': '#FFD700', 'U-RH-3': '#FFD700',  'U-RH-3A': '#FFD700',
    'C-RX-3': '#FFD700',   'C-RX-5': '#FFD700',  'C-RX-8': '#FFD700',
    'C-RX-12': '#FFD700',  'G-RX-3': '#FFD700',  'G-RX-5': '#FFD700',
    'U-RX-3': '#FFD700',   'U-RX-5': '#FFD700',  'U-RX-8': '#FFD700',
    'U-RX-12': '#FFD700',  'C-MS-2': '#FFD700',  'C-MS-3': '#FFD700',
    'C-MS-5': '#FFD700',   'U-MS-2': '#FFD700',  'U-MS-3': '#FFD700',
    'U-MS-5': '#FFD700',   'G-MS-3': '#FFD700',  'G-MS-5': '#FFD700',
    'R-MU-20': '#FFD700',  'R-MU-30': '#FFD700', 'C-MU-20': '#FFD700',
    'C-MU-30': '#FFD700',
    
    # Single-unit zones
    'U-SU-A': '#FFF4C3',   'U-SU-A1': '#FFF4C3', 'U-SU-A2': '#FFF4C3',
    'U-SU-B': '#FFF4C3',   'U-SU-B1': '#FFF4C3', 'U-SU-B2': '#FFF4C3',
    'U-SU-C': '#FFF4C3',   'U-SU-C1': '#FFF4C3', 'U-SU-D': '#FFF4C3',
    'S-SU-D': '#FFF4C3',   'S-SU-D1': '#FFF4C3', 'S-SU-E': '#FFF4C3',
    'S-SU-F1': '#FFF4C3',  'S-SU-F2': '#FFF4C3', 'S-SU-F': '#FFF4C3',
    'U-TU-A': '#FFF4C3',   'U-TU-B': '#FFF4C3',  'U-TU-C': '#FFF4C3',
    
    # Industrial zones
    'I-A': '#C9BDFF',      'I-B': '#C9BDFF',     'I-MX-3': '#C9BDFF',
    'I-MX-5': '#C9BDFF',   'IMX-3': '#C9BDFF',   'IMX-5': '#C9BDFF',
    
    # Open space and other
    'OS-A': '#90EE90',     'OS-B': '#90EE90',    'OS-C': '#90EE90',
    'PUD': '#FFB6C1',      'FBA': '#808080',
}

def get_zone_color(zone_dist):
    """Get color for zone, with fallback"""
    return ZONE_COLORS.get(zone_dist, '#CCCCCC')

# ============================================================================
# CREATE BASE MAP
# ============================================================================

print("\n2. Creating base map...")
denver_center = [39.7392, -104.9903]
m = folium.Map(
    location=denver_center,
    zoom_start=12,
    tiles='CartoDB positron',
    control_scale=True
)

# ============================================================================
# ADD ZONING LAYER
# ============================================================================

print("\n3. Adding zoning districts...")
def zone_style(feature):
    return {
        'fillColor': get_zone_color(feature['properties']['ZONE_DISTRICT']),
        'color': '#666666',
        'weight': 0.5,
        'fillOpacity': 0.4
    }

zone_layer = folium.FeatureGroup(name='Zoning Districts', show=True)
GeoJson(
    zoning,
    style_function=zone_style,
    tooltip=folium.GeoJsonTooltip(fields=['ZONE_DISTRICT'], aliases=['Zone:'])
).add_to(zone_layer)
zone_layer.add_to(m)

# ============================================================================
# ADD OPPORTUNITY PARCELS
# ============================================================================

print("\n4. Adding opportunity parcels...")

# Define colors for each category
PARCEL_COLORS = {
    'Large Vacant Land': '#FF0000',                    # Red
    'SF on Multi-Unit Zoning': '#FF8C00',              # Orange  
    'Commercial on Mixed-Use Zoning': '#00CED1',       # Cyan
    'Industrial Conversion': '#9370DB',                 # Purple
    'Industrial Near Transit': '#FF69B4',               # Hot Pink (needs rezoning)
    'Teardown Candidate': '#FFD700'                     # Yellow
}

# Map internal names to display names
DISPLAY_NAMES = {
    'Large Vacant Land': 'Large Vacant Land',
    'SF on Multi-Unit Zoning': 'SF on Multi-Unit Zoning',
    'Commercial on Mixed-Use Zoning': 'Commercial on Mixed-Use Zoning',
    'Industrial Conversion': 'Industrial Conversion',
    'Industrial Near Transit': 'Industrial Needs Rezoning',
    'Teardown Candidate': 'Teardown Candidate'
}

# Create CURRENT scenario layers (hidden by default)
print("\n4a. Adding CURRENT scenario parcel layers...")
for opp_type, color in PARCEL_COLORS.items():
    layer_parcels = current_parcels[current_parcels['opportunity_type'] == opp_type]
    
    if len(layer_parcels) == 0:
        continue
    
    print(f"   - {opp_type} (Current): {len(layer_parcels):,} parcels")
    
    # Use display name for the layer
    display_name = DISPLAY_NAMES[opp_type]
    layer = folium.FeatureGroup(name=f'{display_name} (Current)', show=True)
    
    for idx, row in layer_parcels.iterrows():
        # Create popup with details
        zone = row.get('ZONE_DISTRICT', 'N/A')
        max_far = row.get('max_far', 2.0)
        
        # Denver zoning: numbers in zone names indicate story height, not FAR
        # Exception: I-A and I-B have actual FAR limits of 2.0
        if str(zone).upper() in ['I-A', 'I-B']:
            far_explanation = f"Max FAR: {max_far:.1f}"
        elif max_far > 0 and max_far != 2.0:
            # Zones with numbers (MX-8, I-MX-5, MS-3, etc.) indicate story height
            far_explanation = f"Max Height: {max_far:.0f} stories"
        else:
            # Default case (FAR 2.0 zones without explicit height in name)
            far_explanation = f"Max FAR: {max_far:.1f}"
        
        popup_html = f"""
        <div class="w-80 font-sans">
            <div class="px-4 py-3 rounded-t-lg" style="background-color: {color};">
                <h4 class="text-white font-bold text-base m-0 pr-8">{row.get('SITUS_ADDRESS_LINE1', 'No Address')}</h4>
            </div>
            <div class="text-sm space-y-2 p-4">
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Opportunity:</span>
                    <span class="text-gray-900 font-sans" title="{display_name}">{display_name}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Current Zoning:</span>
                    <span class="text-gray-900 font-sans" title="{zone}">{zone}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Size:</span>
                    <span class="text-gray-900 font-sans" title="{row.get('land_area_acres', 0):.2f} acres ({row.get('land_area_sf', 0):,.0f} sq ft)">{row.get('land_area_acres', 0):.2f} acres ({row.get('land_area_sf', 0):,.0f} sq ft)</span>
                </div>
                
                <div class="border-t border-gray-200 pt-2 mt-2"></div>
                
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Property Type:</span>
                    <span class="text-gray-900 font-sans truncate" title="{row.get('D_CLASS_CN', 'N/A')}">{row.get('D_CLASS_CN', 'N/A')}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Owner:</span>
                    <span class="text-gray-900 font-sans truncate" title="{str(row.get('OWNER_NAME', 'N/A'))}">{str(row.get('OWNER_NAME', 'N/A'))[:45]}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Building Value:</span>
                    <span class="text-gray-900 font-sans" title="${row.get('APPRAISED_IMP_VALUE', 0):,.0f}">${row.get('APPRAISED_IMP_VALUE', 0):,.0f}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Land Value:</span>
                    <span class="text-gray-900 font-sans" title="${row.get('APPRAISED_LAND_VALUE', 0):,.0f}">${row.get('APPRAISED_LAND_VALUE', 0):,.0f}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Total Building SF:</span>
                    <span class="text-gray-900 font-sans" title="{row.get('total_bldg_sf', 0):,.0f}">{row.get('total_bldg_sf', 0):,.0f}</span>
                </div>
                
                <div class="border-t border-gray-200 pt-2 mt-2"></div>
                
                <div class="bg-blue-50 rounded-lg p-3 border border-blue-200">
                    <div class="font-semibold text-gray-800 mb-1">Development Potential</div>
                    <div class="text-gray-700">{far_explanation}</div>
                    <div class="text-lg font-bold text-blue-600 mt-1">~{int(row.get('potential_units', 0)):,} units</div>
                </div>
            </div>
        </div>
        """
        
        folium.GeoJson(
            row.geometry,
            style_function=lambda x, c=color: {
                'fillColor': c,
                'color': '#FFFFFF',  # White border for better visibility
                'weight': 2,
                'fillOpacity': 0.6
            },
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(layer)
    
    layer.add_to(m)

# Create BALLOT scenario layers (visible by default)
print("\n4b. Adding BALLOT scenario parcel layers...")
for opp_type, color in PARCEL_COLORS.items():
    layer_parcels = ballot_parcels[ballot_parcels['opportunity_type'] == opp_type]
    
    if len(layer_parcels) == 0:
        continue
    
    print(f"   - {opp_type} (Ballot): {len(layer_parcels):,} parcels")
    
    # Use display name for the layer
    display_name = DISPLAY_NAMES[opp_type]
    layer = folium.FeatureGroup(name=f'{display_name} (Ballot)', show=False)
    
    for idx, row in layer_parcels.iterrows():
        # Create popup with details
        zone = row.get('ZONE_DISTRICT', 'N/A')
        ballot_zone = row.get('ballot_zone', zone)
        max_far = row.get('max_far', 2.0)
        ballot_far = row.get('ballot_far', max_far)
        
        # Convert to float to avoid type errors
        try:
            ballot_far = float(ballot_far) if ballot_far is not None else 2.0
        except (ValueError, TypeError):
            ballot_far = 2.0
        
        # Denver zoning: numbers in zone names indicate story height, not FAR
        # Exception: I-A and I-B have actual FAR limits of 2.0
        if str(ballot_zone).upper() in ['I-A', 'I-B']:
            far_explanation = f"Max FAR: {ballot_far:.1f}"
        elif ballot_far > 0 and ballot_far != 2.0:
            # Zones with numbers (MX-8, I-MX-5, MS-3, etc.) indicate story height
            far_explanation = f"Max Height: {ballot_far:.0f} stories"
        else:
            # Default case (FAR 2.0 zones without explicit height in name)
            far_explanation = f"Max FAR: {ballot_far:.1f}"
        
        popup_html = f"""
        <div class="w-80 font-sans">
            <div class="px-4 py-3 rounded-t-lg" style="background-color: {color};">
                <h4 class="text-white font-bold text-base m-0 pr-8">{row.get('SITUS_ADDRESS_LINE1', 'No Address')}</h4>
            </div>
            <div class="text-sm space-y-2 p-4">
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Opportunity:</span>
                    <span class="text-gray-900 font-sans" title="{display_name}">{display_name}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Current Zoning:</span>
                    <span class="text-gray-900 font-sans" title="{zone}">{zone}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Ballot Zoning:</span>
                    <span class="text-orange-600 font-bold font-sans" title="{ballot_zone}">{ballot_zone}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Size:</span>
                    <span class="text-gray-900 font-sans" title="{row.get('land_area_acres', 0):.2f} acres ({row.get('land_area_sf', 0):,.0f} sq ft)">{row.get('land_area_acres', 0):.2f} acres ({row.get('land_area_sf', 0):,.0f} sq ft)</span>
                </div>
                
                <div class="border-t border-gray-200 pt-2 mt-2"></div>
                
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Property Type:</span>
                    <span class="text-gray-900 font-sans truncate" title="{row.get('D_CLASS_CN', 'N/A')}">{row.get('D_CLASS_CN', 'N/A')}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Owner:</span>
                    <span class="text-gray-900 font-sans truncate" title="{str(row.get('OWNER_NAME', 'N/A'))}">{str(row.get('OWNER_NAME', 'N/A'))[:45]}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Building Value:</span>
                    <span class="text-gray-900 font-sans" title="${row.get('APPRAISED_IMP_VALUE', 0):,.0f}">${row.get('APPRAISED_IMP_VALUE', 0):,.0f}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Land Value:</span>
                    <span class="text-gray-900 font-sans" title="${row.get('APPRAISED_LAND_VALUE', 0):,.0f}">${row.get('APPRAISED_LAND_VALUE', 0):,.0f}</span>
                </div>
                <div class="grid grid-cols-2 gap-x-2">
                    <span class="font-semibold text-gray-700">Total Building SF:</span>
                    <span class="text-gray-900 font-sans" title="{row.get('total_bldg_sf', 0):,.0f}">{row.get('total_bldg_sf', 0):,.0f}</span>
                </div>
                
                <div class="border-t border-gray-200 pt-2 mt-2"></div>
                
                <div class="bg-green-50 rounded-lg p-3 border border-green-200">
                    <div class="font-semibold text-gray-800 mb-1">Development Potential (Ballot)</div>
                    <div class="text-gray-700">{far_explanation}</div>
                    <div class="text-lg font-bold text-green-600 mt-1">~{int(row.get('ballot_potential_units', 0)):,} units</div>
                </div>
            </div>
        </div>
        """
        
        folium.GeoJson(
            row.geometry,
            style_function=lambda x, c=color: {
                'fillColor': c,
                'color': '#FFFFFF',  # White border for better visibility
                'weight': 2,
                'fillOpacity': 0.6
            },
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(layer)
    
    layer.add_to(m)

# ============================================================================
# ADD RAIL LINES AND STATIONS (OPTIONAL)
# ============================================================================

print("\n5. Adding rail lines and stations (if available)...")

# Create feature groups for ALL layers
# Rail lines and stations won't be passed to LayerControl (always visible)
rail_lines_group = folium.FeatureGroup(name='RTD Rail Lines', show=True)
stations_group = folium.FeatureGroup(name='RTD Stations', show=True)
buffer_three_eighths_mile_group = folium.FeatureGroup(name='3/8 Mile from Transit', show=True)

# Load rail lines (optional)
try:
    rail_lines = gpd.read_file('rtd_lightrail_lines.geojson')
    
    # OFFICIAL RTD Rail Line Colors from RTD Brand Guide
    # Source: https://www.rtd-denver.com/about-rtd/media-resources/brand-elements
    rail_colors = {
        'A-Line': '#54C0E8',      # Light Blue (A Line - to airport)
        'B-Line': '#4C9C2E',      # Green (B Line)
        'C-Line': '#F7931E',      # Orange (C Line) - not in brand guide, using estimate
        'D-Line': '#047835',      # Dark Green (D Line)
        'E-Line': '#691F74',      # Purple (E Line)
        'F-Line': '#E57200',      # Dark Orange (F Line - Flatiron Flyer alternative)
        'G-Line': '#F4B223',      # Gold (G Line)
        'H-Line': '#0055B8',      # Blue (H Line)
        'L-Line': '#FFCD00',      # Yellow (L Line)
        'N-Line': '#904199',      # Purple/Magenta (N Line)
        'R-Line': '#C1D32F',      # Lime Green (R Line)
        'W-Line': '#0091B3',      # Teal (W Line)
        '101': '#047835',         # Route 101 (D-H-L combined) - use D-Line green
        '117': '#904199',         # Route 117 (N-Line segments) - use N-Line purple
    }
    
    for idx, line in rail_lines.iterrows():
        # RTD uses 'ROUTE' field like 'A-Line', 'B-Line', etc.
        route = line.get('ROUTE', '')
        name = line.get('NAME', route)
        
        # Get color from official brand guide, default to magenta for unknown routes
        line_color = rail_colors.get(route, '#FF00FF')
        
        # Create a GeoJSON and add to the rail lines group
        folium.GeoJson(
            line.geometry,
            style_function=lambda x, color=line_color: {
                'color': color,      # Use the captured color variable
                'weight': 4,
                'opacity': 0.9
            },
            tooltip=name if name else route
        ).add_to(rail_lines_group)  # Add to feature group to avoid macro_element spam
    
    rail_lines_group.add_to(m)
    print("   ✓ Added rail lines with official RTD colors")
except Exception as e:
    print(f"   - Rail lines not found, skipping")

# Add stations (optional)
try:
    stations = gpd.read_file('rtd_lightrail_stations.geojson')
    
    print(f"   Creating merged station buffers for {len(stations)} stations...")
    
    # Project stations to calculate buffers properly
    stations_projected = stations.to_crs('EPSG:32613')  # UTM Zone 13N for Denver
    
    # Create buffer polygons
    three_eighths_mile_buffers = []  # 3/8 mile = 1,980 ft
    
    # NEW: Ballot measure tier buffers
    tier_1_buffers = []  # 660ft (C-MX-8x)
    tier_2_buffers = []  # 1,320ft (G-RX-5x)
    tier_3_buffers = []  # 1,980ft (G-MU-3x)
    
    for idx, station in stations_projected.iterrows():
        # Create buffer in projected CRS (meters)
        three_eighths_mile_buffers.append(station.geometry.buffer(603.50))  # 3/8 mile = 1,980ft
        
        # Ballot measure tiers
        tier_1_buffers.append(station.geometry.buffer(201.17))   # 660ft
        tier_2_buffers.append(station.geometry.buffer(402.34))   # 1,320ft
        tier_3_buffers.append(station.geometry.buffer(603.50))   # 1,980ft
    
    # Merge overlapping buffers using unary_union
    from shapely.ops import unary_union
    merged_three_eighths_mile = unary_union(three_eighths_mile_buffers)
    
    # Merge ballot measure tiers
    merged_tier_1 = unary_union(tier_1_buffers)
    merged_tier_2 = unary_union(tier_2_buffers)
    merged_tier_3 = unary_union(tier_3_buffers)
    
    # Convert back to WGS84 for display
    merged_three_eighths_gdf = gpd.GeoDataFrame({'geometry': [merged_three_eighths_mile]}, crs='EPSG:32613').to_crs('EPSG:4326')
    
    # Convert ballot tiers to WGS84
    merged_tier_1_gdf = gpd.GeoDataFrame({'geometry': [merged_tier_1]}, crs='EPSG:32613').to_crs('EPSG:4326')
    merged_tier_2_gdf = gpd.GeoDataFrame({'geometry': [merged_tier_2]}, crs='EPSG:32613').to_crs('EPSG:4326')
    merged_tier_3_gdf = gpd.GeoDataFrame({'geometry': [merged_tier_3]}, crs='EPSG:32613').to_crs('EPSG:4326')
    
    # Add merged 3/8 mile buffer (solid line)
    folium.GeoJson(
        merged_three_eighths_gdf,
        style_function=lambda x: {
            'fillColor': 'none',
            'color': '#0066CC',
            'weight': 2,
            'opacity': 0.4
        },
        tooltip="3/8 Mile from Transit (Ballot Measure Scope)"
    ).add_to(buffer_three_eighths_mile_group)
    
    print("   ✓ Added merged buffer zone (3/8 mile)")
    
    # NEW: Create ballot measure tier circle groups (hidden by default)
    ballot_tier_1_group = folium.FeatureGroup(name='Tier 1: C-MX-8x (660ft)', show=False)
    ballot_tier_2_group = folium.FeatureGroup(name='Tier 2: G-RX-5x (1,320ft)', show=False)
    ballot_tier_3_group = folium.FeatureGroup(name='Tier 3: G-MU-3x (1,980ft)', show=False)
    
    # Add Tier 1 (innermost - red)
    folium.GeoJson(
        merged_tier_1_gdf,
        style_function=lambda x: {
            'fillColor': 'none',
            'fill': False,
            'color': '#C92A2A',
            'weight': 2,
            'opacity': 0.4
        },
        tooltip="Tier 1: C-MX-8x (8 stories, ≤660ft from station)"
    ).add_to(ballot_tier_1_group)
    
    # Add Tier 2 (middle - orange)
    folium.GeoJson(
        merged_tier_2_gdf,
        style_function=lambda x: {
            'fillColor': 'none',
            'fill': False,
            'color': '#E67700',
            'weight': 2,
            'opacity': 0.4
        },
        tooltip="Tier 2: G-RX-5x (5 stories, ≤1,320ft from station)"
    ).add_to(ballot_tier_2_group)
    
    # Add Tier 3 (outermost - yellow)
    folium.GeoJson(
        merged_tier_3_gdf,
        style_function=lambda x: {
            'fillColor': 'none',
            'fill': False,
            'color': '#F59F00',
            'weight': 2,
            'opacity': 0.4
        },
        tooltip="Tier 3: G-MU-3x (3 stories, ≤1,980ft from station)"
    ).add_to(ballot_tier_3_group)
    
    # Add tier groups to map
    ballot_tier_1_group.add_to(m)
    ballot_tier_2_group.add_to(m)
    ballot_tier_3_group.add_to(m)
    
    print("   ✓ Added ballot measure tier circles")
    
    # Add individual station markers
    for idx, station in stations.iterrows():
        station_name = station.get('NAME', 'Unknown Station')
        station_address = station.get('ADDRESS', 'Unknown')
        
        popup_html = f"""
        <div style="width: 250px">
            <h4 style="margin-bottom: 10px;">{station_name}</h4>
            <p><b>Address:</b> {station_address}</p>
        </div>
        """
        
        # Use smaller Leaflet marker (60% of default size)
        small_icon = folium.Icon(
            icon='info-sign',
            prefix='glyphicon',
            color='blue',
            icon_color='white'
        )
        
        folium.Marker(
            location=[station.geometry.y, station.geometry.x],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=station_name,
            icon=small_icon
        ).add_to(stations_group)
    
    stations_group.add_to(m)
    buffer_three_eighths_mile_group.add_to(m)
    print("   ✓ Added stations with merged buffer circles")
except Exception as e:
    print(f"   - Stations not found, skipping: {e}")

# ============================================================================
# ADD LEGEND
# ============================================================================

print("\n6. Adding legend...")

legend_html = '''
<div id="legend" class="fixed bottom-3 left-3 w-72 bg-white rounded-lg shadow-lg z-[9999]">
    <div id="legend-content" class="p-4">
        <h4 class="text-base font-bold text-gray-800 mb-3 pb-2 border-b border-gray-200 cursor-pointer flex items-center justify-between" 
            onclick="this.parentElement.style.display = 'none'; document.getElementById('legend-toggle').style.display = 'block';">
            <span>Upzoning Opportunities</span>
            <span class="text-gray-400">▼</span>
        </h4>
        
        <!-- Opportunity Types -->
        <div class="space-y-2 mb-3">
            <div class="flex items-center gap-2">
                <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #FF0000;"></span>
                <span class="text-sm text-gray-700">Large Vacant Land ({:,})</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #FF8C00;"></span>
                <span class="text-sm text-gray-700">SF on Multi-Unit Zoning ({:,})</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #00CED1;"></span>
                <span class="text-sm text-gray-700">Commercial on Mixed-Use ({:,})</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #9370DB;"></span>
                <span class="text-sm text-gray-700">Industrial Conversion ({:,})</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #FF69B4;"></span>
                <span class="text-sm text-gray-700">Industrial Needs Rezoning ({:,})</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #FFD700;"></span>
                <span class="text-sm text-gray-700">Teardown Candidates ({:,})</span>
            </div>
        </div>
        
        <!-- Zoning Categories -->
        <div class="border-t border-gray-200 pt-3 mb-3">
            <h5 class="text-sm font-semibold text-gray-700 mb-2">Zoning Categories</h5>
            <div class="space-y-1.5">
                <div class="flex items-center gap-2">
                    <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #E60000;"></span>
                    <span class="text-sm text-gray-600">Downtown</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #FF6A00;"></span>
                    <span class="text-sm text-gray-600">Mixed Use</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #FFD700;"></span>
                    <span class="text-sm text-gray-600">Multi Unit</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #FFF4C3;"></span>
                    <span class="text-sm text-gray-600">Single Unit</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-4 h-4 rounded border border-gray-300" style="background-color: #C9BDFF;"></span>
                    <span class="text-sm text-gray-600">Industrial</span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Collapsed state -->
    <div id="legend-toggle" class="hidden p-3 cursor-pointer text-center bg-gray-50 rounded-b-lg border-t border-gray-200 hover:bg-gray-100 transition-colors"
         onclick="document.getElementById('legend-content').style.display = 'block'; this.style.display = 'none';">
        <span class="text-xs text-gray-600">▲ Show Legend</span>
    </div>
</div>
'''.format(
    len(parcels[parcels['opportunity_type'] == 'Large Vacant Land']),
    len(parcels[parcels['opportunity_type'] == 'SF on Multi-Unit Zoning']),
    len(parcels[parcels['opportunity_type'] == 'Commercial on Mixed-Use Zoning']),
    len(parcels[parcels['opportunity_type'] == 'Industrial Conversion']),
    len(parcels[parcels['opportunity_type'] == 'Industrial Near Transit']),
    len(parcels[parcels['opportunity_type'] == 'Teardown Candidate']),
    len(current_parcels),  # Use current_parcels for default display
    int(current_parcels['potential_units'].sum())  # Use current units for default display
)

m.get_root().html.add_child(folium.Element(legend_html))

# ============================================================================
# ADD LAYER CONTROL
# ============================================================================

# Layer control collapsed by default to keep interface clean
folium.LayerControl(collapsed=True, position='topright').add_to(m)

# ============================================================================
# SAVE MAP
# ============================================================================

output_file = 'denver_tod_with_parcels_v2.html'
print(f"\n7. Saving map to: {output_file}")
m.save(output_file)

# Add title header to the HTML
print("   Adding title header...")
with open(output_file, 'r') as f:
    html_content = f.read()

# Insert title CSS and HTML right after the <body> tag
title_html = f'''
<script src="https://cdn.tailwindcss.com"></script>
<style>
    /* Move Leaflet zoom controls to top right */
    .leaflet-top.leaflet-left {{
        top: 10px;
        right: 60px;
        left: auto !important;
    }}
    
    /* Fix Leaflet popup padding and style close button */
    .leaflet-popup-content-wrapper {{
        padding: 0 !important;
        border-radius: 0.75rem !important;
        overflow: hidden;
    }}
    
    .leaflet-popup-content {{
        margin: 0 !important;
        width: 100% !important;
    }}
    
    /* Style and reposition Leaflet's default close button */
    .leaflet-popup-close-button {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        position: absolute !important;
        top: 0 !important;
        bottom: 0 !important;
        right: 16px !important;
        margin: auto !important;
        z-index: 10 !important;
        color: white !important;
        font-size: 28px !important;
        font-weight: 300 !important;
        text-shadow: none !important;
        width: auto !important;
        height: fit-content !important;
        padding: 0 !important;
        background: none !important;
        border: none !important;
        line-height: 1 !important;
    }}
    
    .leaflet-popup-close-button:hover {{
        color: rgba(255, 255, 255, 0.8) !important;
    }}
</style>
<script>
    // Toggle between current and ballot measure scenarios
    var currentScenario = 'current';  // Start with CURRENT zoning visible

    function toggleScenario(scenario) {{
        if (scenario === currentScenario) return; // Already on this scenario
        
        currentScenario = scenario;
        
        // Update button styles
        var currentBtn = document.getElementById('btn-current');
        var ballotBtn = document.getElementById('btn-ballot');
        var statsBox = document.getElementById('stats-box');
        
        if (scenario === 'current') {{
            // Style current button as active
            currentBtn.className = 'px-4 py-2 rounded-lg text-sm font-semibold transition-all bg-white text-blue-600 shadow-md';
            ballotBtn.className = 'px-4 py-2 rounded-lg text-sm font-semibold transition-all text-white hover:bg-white/10';
            
            // Update stats
            statsBox.innerHTML = '<div class="text-sm text-blue-100 space-y-0.5"><div><span class="text-white font-bold text-xl">{len(current_parcels):,}</span> <span class="text-blue-200">developable parcels</span></div><div><span class="text-white font-bold text-xl">~{int(current_units/1000)}K</span> <span class="text-blue-200">potential housing units</span></div></div>';
            
            // Hide ballot layers, show current layers
            document.querySelectorAll('.leaflet-control-layers-overlays label').forEach(function(label) {{
                var text = label.textContent.trim();
                var checkbox = label.querySelector('input[type="checkbox"]');
                if (text.includes('(Ballot)')) {{
                    if (checkbox && checkbox.checked) checkbox.click();
                }} else if (text.includes('(Current)')) {{
                    if (checkbox && !checkbox.checked) checkbox.click();
                }} else if (text.includes('Tier 1:') || text.includes('Tier 2:') || text.includes('Tier 3:')) {{
                    // Hide ballot measure tier circles
                    if (checkbox && checkbox.checked) checkbox.click();
                }} else if (text.includes('3/8 Mile')) {{
                    // Show standard 3/8 mile buffer
                    if (checkbox && !checkbox.checked) checkbox.click();
                }}
            }});
            
            // Update legend
            document.getElementById('legend-units').innerHTML = '{int(current_units):,}';
            document.getElementById('legend-parcels').innerHTML = '{len(current_parcels):,}';
            document.getElementById('legend-note').innerHTML = 'Legally developable today';
            
        }} else {{
            // Style ballot button as active
            currentBtn.className = 'px-4 py-2 rounded-lg text-sm font-semibold transition-all text-white hover:bg-white/10';
            ballotBtn.className = 'px-4 py-2 rounded-lg text-sm font-semibold transition-all bg-white text-blue-600 shadow-md';
            
            // Update stats
            statsBox.innerHTML = '<div class="text-sm text-blue-100 space-y-0.5"><div><span class="text-white font-bold text-xl">{len(ballot_parcels):,}</span> <span class="text-blue-200">developable parcels</span></div><div><span class="text-white font-bold text-xl">~{int(ballot_units/1000)}K</span> <span class="text-blue-200">potential housing units</span></div><div class="text-green-300 font-semibold mt-1">+{int(increase/1000)}K units (+{increase_pct:.0f}%)</div></div>';
            
            // Hide current layers, show ballot layers
            document.querySelectorAll('.leaflet-control-layers-overlays label').forEach(function(label) {{
                var text = label.textContent.trim();
                var checkbox = label.querySelector('input[type="checkbox"]');
                if (text.includes('(Current)')) {{
                    if (checkbox && checkbox.checked) checkbox.click();
                }} else if (text.includes('(Ballot)')) {{
                    if (checkbox && !checkbox.checked) checkbox.click();
                }} else if (text.includes('Tier 1:') || text.includes('Tier 2:') || text.includes('Tier 3:')) {{
                    // Show ballot measure tier circles
                    if (checkbox && !checkbox.checked) checkbox.click();
                }} else if (text.includes('3/8 Mile')) {{
                    // Hide standard 3/8 mile buffer
                    if (checkbox && checkbox.checked) checkbox.click();
                }}
            }});
            
            // Update legend
            document.getElementById('legend-units').innerHTML = '{int(ballot_units):,}';
            document.getElementById('legend-parcels').innerHTML = '{len(ballot_parcels):,}';
            document.getElementById('legend-note').innerHTML = '<strong>+{int(increase):,} units (+{increase_pct:.1f}%)</strong> vs. current zoning';
        }}
    }}

    // Remove rail lines and stations from layer control after page loads
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            // Find all layer control labels
            var labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(function(label) {{
                var text = label.textContent.trim();
                // Hide RTD Rail Lines and RTD Stations from control
                if (text === 'RTD Rail Lines' || text === 'RTD Stations') {{
                    label.style.display = 'none';
                }}
            }});
        }}, 100);
    }});
</script>

<!-- Unified Title & Toggle Component -->
<div class="fixed top-3 left-3 z-[1000] bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-xl shadow-2xl max-w-md">
    <div class="p-4">
        <!-- Title -->
        <div class="mb-3">
            <h1 class="text-4xl font-black mb-1">Mile High Potential</h1>
            <p class="text-base text-blue-100 leading-tight">Transit-oriented development opportunities in Denver</p>
        </div>
        
        <!-- Segmented Control Toggle -->
        <div class="bg-blue-800/40 rounded-lg p-1 mb-3 backdrop-blur-sm">
            <div class="grid grid-cols-2 gap-1">
                <button id="btn-current" 
                        onclick="toggleScenario('current')"
                        class="px-4 py-2 rounded-lg text-base font-semibold transition-all bg-white text-blue-600 shadow-md">
                    Current Zoning
                </button>
                <button id="btn-ballot"
                        onclick="toggleScenario('ballot')"
                        class="px-4 py-2 rounded-lg text-base font-semibold transition-all text-white hover:bg-white/10">
                    After Ballot
                </button>
            </div>
        </div>
        
        <!-- Stats Display -->
        <div id="stats-box" class="text-center px-2">
            <div class="text-sm text-blue-100 space-y-0.5">
                <div><span class="text-white font-bold text-xl">{len(current_parcels):,}</span> <span class="text-blue-200">developable parcels</span></div>
                <div><span class="text-white font-bold text-xl">~{int(current_units/1000)}K</span> <span class="text-blue-200">potential housing units</span></div>
            </div>
        </div>
        
        <!-- About Link -->
        <div class="mt-3 pt-3 border-t border-blue-500/30">
            <a href="about.html" class="text-base text-blue-100 hover:text-white font-medium transition-colors flex items-center justify-center gap-1">
                <span>About this project</span>
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                </svg>
            </a>
        </div>
    </div>
</div>
'''

# Insert after <body> tag
html_content = html_content.replace('<body>', '<body>' + title_html)

with open(output_file, 'w') as f:
    f.write(html_content)

print("\n" + "="*70)
print("✓ MAP CREATED SUCCESSFULLY")
print("="*70)
print(f"\nOpen {output_file} in your browser to view the interactive map!")
print("\nThe map includes:")
print("  - 5 categories of redevelopment opportunities")
print("  - Toggle layers on/off in the top right")
print("  - Click on parcels for details")
print("  - Click on stations for TOD analysis")