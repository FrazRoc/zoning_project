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
parcels = gpd.read_file('high_opportunity_parcels_v2.geojson')

print(f"   ✓ Loaded {len(zoning):,} zoning districts")
print(f"   ✓ Loaded {len(parcels):,} opportunity parcels")

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

# Create separate layer for each opportunity type
for opp_type, color in PARCEL_COLORS.items():
    layer_parcels = parcels[parcels['opportunity_type'] == opp_type]
    
    if len(layer_parcels) == 0:
        continue
    
    print(f"   - {opp_type}: {len(layer_parcels):,} parcels")
    
    # Use display name for the layer
    display_name = DISPLAY_NAMES[opp_type]
    layer = folium.FeatureGroup(name=display_name, show=True)
    
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
        <div style="width: 320px; font-family: Arial, sans-serif;">
            <div style="background-color: {color}; padding: 8px; margin: -10px -10px 10px -10px;">
                <h4 style="margin: 0; color: white;">{row.get('SITUS_ADDRESS_LINE1', 'No Address')}</h4>
            </div>
            <div style="font-size: 13px;">
                <b>Opportunity:</b> {display_name}<br>
                <b>Zoning:</b> {zone}<br>
                <b>Size:</b> {row.get('land_area_acres', 0):.2f} acres ({row.get('land_area_sf', 0):,.0f} sq ft)<br>
                <hr style="margin: 8px 0;">
                <b>Property Type:</b> {row.get('D_CLASS_CN', 'N/A')}<br>
                <b>Owner:</b> {str(row.get('OWNER_NAME', 'N/A'))[:45]}<br>
                <b>Building Value:</b> ${row.get('APPRAISED_IMP_VALUE', 0):,.0f}<br>
                <b>Land Value:</b> ${row.get('APPRAISED_LAND_VALUE', 0):,.0f}<br>
                <b>Total Building SF:</b> {row.get('total_bldg_sf', 0):,.0f}<br>
                <hr style="margin: 8px 0;">
                <b>Development Potential:</b><br>
                {far_explanation}<br>
                Est. Units: ~{int(row.get('potential_units', 0)):,}
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
buffer_half_mile_group = folium.FeatureGroup(name='1/2 Mile from Transit', show=True)
buffer_quarter_mile_group = folium.FeatureGroup(name='1/4 Mile from Transit', show=True)

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
    half_mile_buffers = []
    quarter_mile_buffers = []
    
    for idx, station in stations_projected.iterrows():
        # Create buffers in projected CRS (meters)
        half_mile_buffers.append(station.geometry.buffer(804.67))  # 1/2 mile
        quarter_mile_buffers.append(station.geometry.buffer(402.34))  # 1/4 mile
    
    # Merge overlapping buffers using unary_union
    from shapely.ops import unary_union
    merged_half_mile = unary_union(half_mile_buffers)
    merged_quarter_mile = unary_union(quarter_mile_buffers)
    
    # Convert back to WGS84 for display
    merged_half_gdf = gpd.GeoDataFrame({'geometry': [merged_half_mile]}, crs='EPSG:32613').to_crs('EPSG:4326')
    merged_quarter_gdf = gpd.GeoDataFrame({'geometry': [merged_quarter_mile]}, crs='EPSG:32613').to_crs('EPSG:4326')
    
    # Add merged 1/2 mile buffer (dashed line)
    folium.GeoJson(
        merged_half_gdf,
        style_function=lambda x: {
            'fillColor': 'none',
            'color': '#0066CC',
            'weight': 2,
            'opacity': 0.7,
            'dashArray': '5, 5'  # Dashed line pattern
        },
        tooltip="1/2 Mile from Transit"
    ).add_to(buffer_half_mile_group)
    
    # Add merged 1/4 mile buffer (solid line)
    folium.GeoJson(
        merged_quarter_gdf,
        style_function=lambda x: {
            'fillColor': 'none',
            'color': '#0044AA',
            'weight': 2,
            'opacity': 0.9
        },
        tooltip="1/4 Mile from Transit"
    ).add_to(buffer_quarter_mile_group)
    
    print("   ✓ Added merged buffer zones")
    
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
        
        # Add station marker to feature group to avoid macro_element spam
        # Use custom HTML icon for smaller size (50% of default)
        icon_html = '''
        <div style="font-size: 18px; color: #d63031; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;">
            <i class="fa fa-train"></i>
        </div>
        '''
        
        folium.Marker(
            location=[station.geometry.y, station.geometry.x],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=station_name,
            icon=folium.DivIcon(html=icon_html)
        ).add_to(stations_group)
    
    stations_group.add_to(m)
    buffer_half_mile_group.add_to(m)
    buffer_quarter_mile_group.add_to(m)
    print("   ✓ Added stations with merged buffer circles")
except Exception as e:
    print(f"   - Stations not found, skipping: {e}")

# ============================================================================
# ADD LEGEND
# ============================================================================

print("\n6. Adding legend...")

legend_html = '''
<div id="legend" style="position: fixed; bottom: 10px; left: 10px; width: 260px; 
     background-color: white; border: 2px solid grey; z-index: 9999; 
     font-size: 12px; border-radius: 5px;">
    <div id="legend-content" style="padding: 8px;">
        <h4 style="margin: 0 0 5px 0; font-size: 14px; cursor: pointer;" 
            onclick="this.parentElement.style.display = 
                     this.parentElement.style.display === 'none' ? 'block' : 'none'; 
                     document.getElementById('legend-toggle').style.display = 'block';">
            Upzoning Opportunities <span style="float: right; font-size: 12px;">▼</span>
        </h4>
        <div style="margin-bottom: 4px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #FF0000; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Large Vacant Land ({:,})</span>
        </div>
        <div style="margin-bottom: 4px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #FF8C00; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">SF on Multi-Unit Zoning ({:,})</span>
        </div>
        <div style="margin-bottom: 4px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #00CED1; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Commercial on Mixed-Use ({:,})</span>
        </div>
        <div style="margin-bottom: 4px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #9370DB; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Industrial Conversion ({:,})</span>
        </div>
        <div style="margin-bottom: 4px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #FF69B4; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Industrial Needs Rezoning ({:,})</span>
        </div>
        <div style="margin-bottom: 6px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #FFD700; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Teardown Candidates ({:,})</span>
        </div>
        <hr style="margin: 6px 0;">
        <h4 style="margin: 5px 0 4px 0; font-size: 13px;">Zoning Categories</h4>
        <div style="margin-bottom: 3px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #E60000; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Downtown</span>
        </div>
        <div style="margin-bottom: 3px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #FF6A00; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Mixed Use</span>
        </div>
        <div style="margin-bottom: 3px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #FFD700; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Multi Unit</span>
        </div>
        <div style="margin-bottom: 3px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #FFF4C3; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Single Unit</span>
        </div>
        <div style="margin-bottom: 6px; display: flex; align-items: center;">
            <span style="display: inline-block; width: 16px; height: 16px; background-color: #C9BDFF; margin-right: 6px; border: 1px solid #ccc;"></span>
            <span style="font-size: 11px;">Industrial</span>
        </div>
        <hr style="margin: 6px 0;">
        <div style="font-size: 10px; color: #666; line-height: 1.4;">
            <b>Total:</b> {:,} parcels, {:,} acres<br>
            <b>Potential Units:</b> ~{:,}<br>
            <span style="font-size: 9px; font-style: italic;">
            (1,500 sf/unit incl. common areas)
            </span>
        </div>
    </div>
    <div id="legend-toggle" style="display: none; padding: 8px; cursor: pointer; text-align: center; background-color: #f0f0f0; border-top: 1px solid grey;"
         onclick="document.getElementById('legend-content').style.display = 'block'; this.style.display = 'none';">
        <span style="font-size: 12px;">▲ Show Legend</span>
    </div>
</div>
'''.format(
    len(parcels[parcels['opportunity_type'] == 'Large Vacant Land']),
    len(parcels[parcels['opportunity_type'] == 'SF on Multi-Unit Zoning']),
    len(parcels[parcels['opportunity_type'] == 'Commercial on Mixed-Use Zoning']),
    len(parcels[parcels['opportunity_type'] == 'Industrial Conversion']),
    len(parcels[parcels['opportunity_type'] == 'Industrial Near Transit']),
    len(parcels[parcels['opportunity_type'] == 'Teardown Candidate']),
    len(parcels),
    int(parcels['land_area_acres'].sum()),
    int(parcels['potential_units'].sum())
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
title_html = '''
<style>
    /* Move Leaflet zoom controls to top right */
    .leaflet-top.leaflet-left {
        top: 10px;
        right: 60px;
        left: auto !important;
    }
    
    .map-title {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 1000;
        background-color: white;
        padding: 10px 15px;
        border-radius: 5px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        font-family: Arial, sans-serif;
        max-width: 280px;
    }
    .map-title h1 {
        margin: 0;
        font-size: 16px;
        color: #333;
        font-weight: bold;
        line-height: 1.3;
    }
    .map-title p {
        margin: 3px 0 0 0;
        font-size: 11px;
        color: #666;
        line-height: 1.2;
    }
    .map-title .nav-links {
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #e0e0e0;
        display: flex;
        gap: 12px;
        font-size: 11px;
    }
    .map-title .nav-links a {
        color: #3498db;
        text-decoration: none;
        font-weight: 500;
    }
    .map-title .nav-links a:hover {
        text-decoration: underline;
    }
</style>
<script>
    // Remove rail lines and stations from layer control after page loads
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            // Find all layer control labels
            var labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(function(label) {
                var text = label.textContent.trim();
                // Hide RTD Rail Lines and RTD Stations from control
                if (text === 'RTD Rail Lines' || text === 'RTD Stations') {
                    label.style.display = 'none';
                }
            });
        }, 100);
    });
</script>
<div class="map-title">
    <h1>Mile High Potential</h1>
    <p>Finding development opportunities in Denver among its transit network</p>
    <div class="nav-links">
        <a href="about.html">About</a>
        <a href="https://github.com/FrazRoc/zoning_project" target="_blank">GitHub</a>
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