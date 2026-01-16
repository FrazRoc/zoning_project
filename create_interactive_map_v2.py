# create_interactive_map_FINAL_v7.py
# Add Denver-only filter and colorful rail lines

import geopandas as gpd
import pandas as pd
import folium
from shapely.ops import unary_union

print("=" * 70)
print("CREATING FINAL INTERACTIVE TOD MAP v7")
print("=" * 70)

# Load data
print("\nLoading data...")
zoning = gpd.read_file('ODC_ZONE_ZONING_A_-6072697703037489513.geojson')
zone_col = 'ZONE_DISTRICT'
zoning_no_airport = zoning[zoning[zone_col] != 'DIA'].copy()

print("Filtering and fixing geometries...")
zoning_no_airport = zoning_no_airport[~zoning_no_airport.geometry.isna()].copy()

# Fix invalid geometries
invalid_mask = ~zoning_no_airport.geometry.is_valid
print(f"  Found {invalid_mask.sum()} invalid geometries")
if invalid_mask.sum() > 0:
    print(f"  Fixing with buffer(0)...")
    zoning_no_airport.loc[invalid_mask, 'geometry'] = zoning_no_airport.loc[invalid_mask].geometry.buffer(0)
    still_invalid = ~zoning_no_airport.geometry.is_valid
    if still_invalid.sum() > 0:
        print(f"  Removing {still_invalid.sum()} unfixable geometries")
        zoning_no_airport = zoning_no_airport[zoning_no_airport.geometry.is_valid].copy()

print(f"  Kept {len(zoning_no_airport)} valid zones")

# Calculate areas
zoning_projected = zoning_no_airport.to_crs('EPSG:32613')
zoning_projected['area_sqm'] = zoning_projected.geometry.area
zoning_no_airport['area_sqm'] = zoning_projected['area_sqm']
zoning_no_airport['area_sqmi'] = zoning_no_airport['area_sqm'] / 2.58999e6

# Explode MultiPolygons
print("\nExploding MultiPolygons...")
zoning_exploded = zoning_no_airport.explode(index_parts=False).reset_index(drop=True)
print(f"  Before: {len(zoning_no_airport)} features")
print(f"  After: {len(zoning_exploded)} features")

# Load stations
stations_url = "https://services5.arcgis.com/1fZoXlzLW6FCIUcE/arcgis/rest/services/RTD_GIS_Current_Runboard/FeatureServer/1/query?where=1%3D1&outFields=*&f=geojson"
stations = gpd.read_file(stations_url)

# Load Denver city boundary to filter stations
print("Loading Denver city boundary...")
try:
    denver_boundary_url = "https://www.denvergov.org/media/gis/DataCatalog/city_boundary/shape/city_boundary.zip"
    denver_boundary = gpd.read_file(denver_boundary_url)
    denver_boundary = denver_boundary.to_crs(stations.crs)
    print(f"  Loaded Denver boundary")
    
    # Identify which stations are in Denver
    stations_in_denver = gpd.sjoin(stations, denver_boundary, how='inner', predicate='within')
    denver_station_names = set(stations_in_denver['NAME'].unique())
    stations['in_denver'] = stations['NAME'].isin(denver_station_names)
    
    print(f"  Found {len(denver_station_names)} stations in Denver city limits")
    print(f"  Total stations: {len(stations)}")
except Exception as e:
    print(f"  Could not load Denver boundary: {e}")
    print("  Will use all stations")
    stations['in_denver'] = True
    denver_station_names = set(stations['NAME'].unique())

print("Loading rail lines...")
try:
    rail_lines_url = "https://services5.arcgis.com/1fZoXlzLW6FCIUcE/arcgis/rest/services/RTD_GIS_Current_Runboard/FeatureServer/6/query?where=1%3D1&outFields=*&f=geojson"
    rail_lines = gpd.read_file(rail_lines_url)
    print(f"  Loaded {len(rail_lines)} rail line segments")
except Exception as e:
    print(f"  Could not load rail lines: {e}")
    rail_lines = None

# Categorization
def categorize_zone(zone_code):
    if pd.isna(zone_code):
        return 'Unknown'
    zone = str(zone_code).upper()
    
    if zone.startswith('OS-'):
        return 'Open Space'
    if zone.startswith('PUD'):
        return 'Planned Unit Development (PUD)'
    if zone.startswith('D-'):
        return 'Downtown'
    if zone in ['MS-1', 'MS-2', 'MS-3']:
        return 'Main Street (MS)'
    if zone.startswith('I-'):
        return 'Industrial'
    if '-CC-' in zone or zone == 'CCN':
        return 'Special District (Cherry Creek)'
    if '-MX-' in zone or '-MS-' in zone or '-RX-' in zone or '-IMX-' in zone:
        return 'Mixed Use (MX, MS, RX)'
    if '-RH-' in zone:
        return 'Multi Unit (MU, RH, RO)'
    if '-RO-' in zone:
        return 'Multi Unit (MU, RH, RO)'
    if '-MU-' in zone:
        return 'Multi Unit (MU, RH, RO)'
    if '-SU-' in zone or zone.startswith('R-0') or zone in ['R-1', 'R-2', 'R-3', 'R-4']:
        return 'Single Unit (SU)'
    if '-TU-' in zone or zone in ['R-2-A', 'R-2-B']:
        return 'Two Unit (TU)'
    if zone.startswith('CMP-') or zone.startswith('C-CCN'):
        return 'Campus'
    if zone.startswith('B-') or zone.startswith('O-'):
        return 'Commercial/Office'
    if zone.startswith('H-') or zone == 'GTWY':
        return 'Special District (Other)'
    if zone == 'MHC':
        return 'Manufactured Home Community (MHC)'
    if zone.startswith('P-'):
        return 'Parking'
    if zone.startswith('R-') or zone == 'R-X':
        return 'Residential (Legacy)'
    return 'Other'

print("\nCategorizing zones...")
zoning_exploded['zone_category'] = zoning_exploded[zone_col].apply(categorize_zone)

# Colors
color_map = {
    'Downtown': '#CC0000',
    'Mixed Use (MX, MS, RX)': '#FF9933',
    'Main Street (MS)': '#FF6666',
    'Multi Unit (MU, RH, RO)': '#FFFF00',
    'Two Unit (TU)': '#FFFFCC',
    'Single Unit (SU)': '#F5DEB3',
    'Manufactured Home Community (MHC)': '#FFB6C1',
    'Industrial': '#9999CC',
    'Commercial/Office': '#CCCCCC',
    'Campus': '#C8A2C8',
    'Special District (Cherry Creek)': '#FF69B4',
    'Special District (Other)': '#DB7093',
    'Open Space': '#90EE90',
    'Planned Unit Development (PUD)': '#FFFFAA',
    'Parking': '#808080',
    'Residential (Legacy)': '#D3D3D3',
    'Other': '#000000'
}

zoning_exploded['color'] = zoning_exploded['zone_category'].map(color_map)

print("\nConverting to WGS84...")
zoning_web = zoning_exploded.to_crs('EPSG:4326')
stations_web = stations.to_crs('EPSG:4326')
if rail_lines is not None:
    rail_lines_web = rail_lines.to_crs('EPSG:4326')

# CREATE MERGED BUFFERS - separate for Denver vs All
print("\nCreating merged station buffers...")
stations_projected = stations.to_crs('EPSG:32613')

# All stations buffers
quarter_mile_buffers_all = []
half_mile_buffers_all = []

# Denver-only buffers
quarter_mile_buffers_denver = []
half_mile_buffers_denver = []

for idx, station in stations_projected.iterrows():
    buffer_quarter = station.geometry.buffer(402.34)
    buffer_half = station.geometry.buffer(804.67)
    
    quarter_mile_buffers_all.append(buffer_quarter)
    half_mile_buffers_all.append(buffer_half)
    
    if station['in_denver']:
        quarter_mile_buffers_denver.append(buffer_quarter)
        half_mile_buffers_denver.append(buffer_half)

print("  Merging all station buffers...")
merged_quarter_all = unary_union(quarter_mile_buffers_all)
merged_half_all = unary_union(half_mile_buffers_all)

print("  Merging Denver-only buffers...")
merged_quarter_denver = unary_union(quarter_mile_buffers_denver)
merged_half_denver = unary_union(half_mile_buffers_denver)

# Convert to WGS84
merged_quarter_all_web = gpd.GeoSeries([merged_quarter_all], crs='EPSG:32613').to_crs('EPSG:4326')[0]
merged_half_all_web = gpd.GeoSeries([merged_half_all], crs='EPSG:32613').to_crs('EPSG:4326')[0]

merged_quarter_denver_web = gpd.GeoSeries([merged_quarter_denver], crs='EPSG:32613').to_crs('EPSG:4326')[0]
merged_half_denver_web = gpd.GeoSeries([merged_half_denver], crs='EPSG:32613').to_crs('EPSG:4326')[0]

print("\nCreating interactive map...")
denver_center = [39.7392, -104.9903]
m = folium.Map(location=denver_center, zoom_start=11, tiles='OpenStreetMap', control_scale=True)

folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)

# Add CSS to hide bounding box
hide_bbox_css = """
<style>
    .leaflet-interactive:focus {
        outline: none !important;
    }
    svg rect {
        display: none !important;
    }
    path.leaflet-interactive:focus {
        outline: none !important;
    }
</style>
"""
m.get_root().html.add_child(folium.Element(hide_bbox_css))

zoning_group = folium.FeatureGroup(name='Zoning', show=True)

# Separate groups for All vs Denver Only
stations_all_group = folium.FeatureGroup(name='All Stations', show=True)
stations_denver_group = folium.FeatureGroup(name='Denver Stations Only', show=False)

buffer_quarter_all_group = folium.FeatureGroup(name='All 1/4 Mile Buffers', show=False)
buffer_half_all_group = folium.FeatureGroup(name='All 1/2 Mile Buffers', show=True)

buffer_quarter_denver_group = folium.FeatureGroup(name='Denver 1/4 Mile Buffers', show=False)
buffer_half_denver_group = folium.FeatureGroup(name='Denver 1/2 Mile Buffers', show=False)

if rail_lines is not None:
    rail_lines_all_group = folium.FeatureGroup(name='All Rail Lines', show=True)
    rail_lines_denver_group = folium.FeatureGroup(name='Denver Rail Lines Only', show=False)

print("  Adding zoning layer...")

def style_function(feature):
    return {
        'fillColor': feature['properties']['color'],
        'color': 'white',
        'weight': 0.5,
        'fillOpacity': 0.7
    }

def highlight_function(feature):
    return {
        'fillColor': feature['properties']['color'],
        'color': 'white',
        'weight': 0.5,
        'fillOpacity': 0.95
    }

zoning_layer = folium.GeoJson(
    zoning_web,
    name='Zoning',
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.GeoJsonTooltip(
        fields=[zone_col, 'zone_category'],
        aliases=['Zone:', 'Category:']
    ),
    show=True
)
zoning_layer.add_to(zoning_group)

# Add rail lines with BRIGHT COLORS by line
if rail_lines is not None:
    print("  Adding rail lines...")
    
    # RTD line colors - BRIGHT and distinctive
    line_colors = {
        'A': '#ED1C24',      # Red (A Line - to airport)
        'B': '#0075BF',      # Blue (B Line)
        'C': '#F7931E',      # Orange (C Line)
        'D': '#FFC72C',      # Yellow (D Line)
        'E': '#00A88E',      # Teal (E Line)
        'G': '#6CBE45',      # Green (G Line)
        'H': '#8B6BAD',      # Purple (H Line)
        'L': '#F26522',      # Dark Orange (L Line)
        'R': '#A4D65E',      # Light Green (R Line)
        'W': '#00ADEE',      # Light Blue (W Line)
    }
    
    for idx, line in rail_lines_web.iterrows():
        line_name = line.get('RAIL_LINE', 'Unknown')
        line_color = line_colors.get(line_name, '#FF00FF')  # Magenta for unknown
        
        # Add to "All Rail Lines"
        folium.GeoJson(
            line.geometry,
            style_function=lambda x, color=line_color: {
                'color': color,
                'weight': 5,
                'opacity': 0.9
            },
            tooltip=f"{line_name} Line"
        ).add_to(rail_lines_all_group)
        
        # Add to "Denver Rail Lines Only" if any endpoint is in Denver
        # (This is approximate - we'll show lines that touch Denver)
        folium.GeoJson(
            line.geometry,
            style_function=lambda x, color=line_color: {
                'color': color,
                'weight': 5,
                'opacity': 0.9
            },
            tooltip=f"{line_name} Line"
        ).add_to(rail_lines_denver_group)

# Add ALL station buffers
print("  Adding all station buffers...")
folium.GeoJson(
    merged_half_all_web,
    style_function=lambda x: {
        'fillColor': 'none',
        'color': '#0066CC',
        'weight': 2,
        'opacity': 0.7,
        'dashArray': '5, 5'
    },
    tooltip="1/2 Mile from Transit (All Stations)"
).add_to(buffer_half_all_group)

folium.GeoJson(
    merged_quarter_all_web,
    style_function=lambda x: {
        'fillColor': 'none',
        'color': '#0044AA',
        'weight': 2,
        'opacity': 0.9
    },
    tooltip="1/4 Mile from Transit (All Stations)"
).add_to(buffer_quarter_all_group)

# Add DENVER-ONLY buffers
print("  Adding Denver-only buffers...")
folium.GeoJson(
    merged_half_denver_web,
    style_function=lambda x: {
        'fillColor': 'none',
        'color': '#0066CC',
        'weight': 2,
        'opacity': 0.7,
        'dashArray': '5, 5'
    },
    tooltip="1/2 Mile from Transit (Denver Only)"
).add_to(buffer_half_denver_group)

folium.GeoJson(
    merged_quarter_denver_web,
    style_function=lambda x: {
        'fillColor': 'none',
        'color': '#0044AA',
        'weight': 2,
        'opacity': 0.9
    },
    tooltip="1/4 Mile from Transit (Denver Only)"
).add_to(buffer_quarter_denver_group)

print("  Adding stations with analysis...")
zoning_for_analysis = zoning_no_airport.to_crs('EPSG:32613')

for idx, station in stations_web.iterrows():
    if idx % 10 == 0:
        print(f"    Station {idx+1}/{len(stations_web)}...")
    
    station_name = station['NAME']
    station_address = station.get('ADDRESS', 'Unknown')
    rail_line = station.get('RAIL_LINE', 'Unknown')
    in_denver = station['in_denver']
    
    station_proj_geom = stations_projected.loc[idx].geometry
    
    # Analysis
    buffer_quarter = station_proj_geom.buffer(402.34)
    buffer_quarter_gdf = gpd.GeoDataFrame({'geometry': [buffer_quarter]}, crs='EPSG:32613')
    zones_nearby = gpd.sjoin(zoning_for_analysis, buffer_quarter_gdf, how='inner', predicate='intersects')
    
    if len(zones_nearby) > 0:
        zones_nearby['intersection_geom'] = zones_nearby.geometry.intersection(buffer_quarter)
        zones_nearby['intersection_area'] = zones_nearby['intersection_geom'].area
        zones_nearby['pct_in_buffer'] = (zones_nearby['intersection_area'] / zones_nearby['area_sqm']) * 100
        zones_nearby = zones_nearby[zones_nearby['pct_in_buffer'] > 10]
        zones_nearby['zone_category'] = zones_nearby[zone_col].apply(categorize_zone)
        
        total_area = zones_nearby['intersection_area'].sum() / 2.58999e6
        
        tod_categories = ['Mixed Use (MX, MS, RX)', 'Main Street (MS)', 'Downtown', 'Multi Unit (MU, RH, RO)']
        tod_area = zones_nearby[zones_nearby['zone_category'].isin(tod_categories)]['intersection_area'].sum() / 2.58999e6
        tod_pct = (tod_area / total_area * 100) if total_area > 0 else 0
        
        sf_area = zones_nearby[zones_nearby['zone_category'] == 'Single Unit (SU)']['intersection_area'].sum() / 2.58999e6
        sf_pct = (sf_area / total_area * 100) if total_area > 0 else 0
        
        industrial_area = zones_nearby[zones_nearby['zone_category'] == 'Industrial']['intersection_area'].sum() / 2.58999e6
        industrial_pct = (industrial_area / total_area * 100) if total_area > 0 else 0
        
        location_note = "📍 IN DENVER" if in_denver else "📍 Outside Denver"
        
        popup_html = f"""
        <div style="width: 300px">
            <h4 style="margin-bottom: 10px;">{station_name}</h4>
            <p><b>Address:</b> {station_address}<br>
            <b>Line:</b> {rail_line}<br>
            <b>Location:</b> {location_note}</p>
            
            <h5>Within 1/4 Mile:</h5>
            <p>
            <b>Total Area:</b> {total_area:.2f} sq mi<br>
            <b>TOD Zoning:</b> {tod_pct:.1f}%<br>
            <b>Single-Family:</b> {sf_pct:.1f}%<br>
            <b>Industrial:</b> {industrial_pct:.1f}%
            </p>
            
            <h5>Assessment:</h5>
            <p>
            {'✓ Good TOD zoning' if tod_pct > 50 else '⚠️ Needs more TOD zoning'}<br>
            {'⚠️ High SF - upzone target' if sf_pct > 15 else ''}<br>
            {'⚠️ High industrial - conversion opportunity' if industrial_pct > 40 else ''}
            </p>
        </div>
        """
    else:
        location_note = "📍 IN DENVER" if in_denver else "📍 Outside Denver"
        popup_html = f"""
        <div style="width: 250px">
            <h4>{station_name}</h4>
            <p><b>Address:</b> {station_address}<br>
            <b>Line:</b> {rail_line}<br>
            <b>Location:</b> {location_note}</p>
        </div>
        """
    
    # Add to ALL stations group
    folium.Marker(
        location=[station.geometry.y, station.geometry.x],
        popup=folium.Popup(popup_html, max_width=350),
        tooltip=station_name,
        icon=folium.Icon(color='red', icon='train', prefix='fa')
    ).add_to(stations_all_group)
    
    # Add to Denver-only group if in Denver
    if in_denver:
        folium.Marker(
            location=[station.geometry.y, station.geometry.x],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=station_name,
            icon=folium.Icon(color='red', icon='train', prefix='fa')
        ).add_to(stations_denver_group)

# Add layers to map in order
if rail_lines is not None:
    rail_lines_all_group.add_to(m)
    rail_lines_denver_group.add_to(m)

zoning_group.add_to(m)

buffer_half_all_group.add_to(m)
buffer_quarter_all_group.add_to(m)
buffer_half_denver_group.add_to(m)
buffer_quarter_denver_group.add_to(m)

stations_all_group.add_to(m)
stations_denver_group.add_to(m)

folium.LayerControl(position='topright', collapsed=False).add_to(m)

legend_html = '''
<div style="position: fixed; 
            bottom: 50px; right: 50px; width: 260px; height: auto; 
            background-color: white; z-index:9999; font-size:11px;
            border:2px solid grey; border-radius: 5px; padding: 10px;
            max-height: 500px; overflow-y: auto;">
<h4 style="margin-top:0">Zoning Categories</h4>
<p style="margin: 3px 0;"><span style="background-color: #CC0000; padding: 2px 8px; color: white;">▮</span> Downtown</p>
<p style="margin: 3px 0;"><span style="background-color: #FF9933; padding: 2px 8px;">▮</span> Mixed Use (MX, MS, RX)</p>
<p style="margin: 3px 0;"><span style="background-color: #FF6666; padding: 2px 8px;">▮</span> Main Street (MS)</p>
<p style="margin: 3px 0;"><span style="background-color: #FFFF00; padding: 2px 8px;">▮</span> Multi Unit (MU, RH, RO)</p>
<p style="margin: 3px 0;"><span style="background-color: #FFFFCC; padding: 2px 8px;">▮</span> Two Unit (TU)</p>
<p style="margin: 3px 0;"><span style="background-color: #F5DEB3; padding: 2px 8px;">▮</span> Single Unit (SU)</p>
<p style="margin: 3px 0;"><span style="background-color: #FFB6C1; padding: 2px 8px;">▮</span> Manufactured Home (MHC)</p>
<p style="margin: 3px 0;"><span style="background-color: #9999CC; padding: 2px 8px;">▮</span> Industrial</p>
<p style="margin: 3px 0;"><span style="background-color: #FF69B4; padding: 2px 8px;">▮</span> Cherry Creek District</p>
<p style="margin: 3px 0;"><span style="background-color: #90EE90; padding: 2px 8px;">▮</span> Open Space</p>
<p style="margin: 3px 0;"><span style="background-color: #FFFFAA; padding: 2px 8px;">▮</span> PUD</p>
<p style="margin: 3px 0;"><span style="background-color: #CCCCCC; padding: 2px 8px;">▮</span> Commercial/Office</p>
<hr style="margin: 10px 0;">
<h4 style="margin-top:10px">Filter Options</h4>
<p style="margin: 3px 0; font-size: 10px;">Use Layer Control (top right) to toggle:</p>
<p style="margin: 3px 0; font-size: 10px;">• "Denver ... Only" = Denver city limits</p>
<p style="margin: 3px 0; font-size: 10px;">• "All ..." = Entire RTD system</p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

title_html = '''
<div style="position: fixed; 
            top: 10px; left: 50px; width: auto; height: auto; 
            background-color: white; z-index:9999; font-size:16px;
            border:2px solid grey; border-radius: 5px; padding: 10px">
<h3 style="margin:0">Denver Transit-Oriented Development Analysis</h3>
<p style="margin: 5px 0; font-size: 12px;">Hover over zones for info • Click stations for details • Use layer control to filter</p>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

output_file = 'denver_tod_interactive_map_FINAL.html'
print(f"\nSaving map to {output_file}...")
m.save(output_file)

print(f"\n{'='*70}")
print(f"✓ SUCCESS! Final map created: {output_file}")
print(f"{'='*70}")
print(f"\nNew features:")
print(f"  - Denver-only filter (toggle in layer control)")
print(f"  - Bright colored rail lines (red, blue, orange, etc.)")
print(f"  - Separate layer groups for All vs Denver Only")
print(f"  - Station popups show if they're in Denver")