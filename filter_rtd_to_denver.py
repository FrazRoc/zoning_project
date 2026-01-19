import geopandas as gpd
import pandas as pd
import requests

print("="*70)
print("FILTERING RTD DATA TO DENVER CITY LIMITS ONLY")
print("="*70)

# Use existing zoning data to define Denver boundary
print("\n1. Loading Denver boundary from zoning data...")
try:
    zoning = gpd.read_file('ODC_ZONE_ZONING_A_-6072697703037489513.geojson')
    print(f"   ✓ Loaded {len(zoning)} zoning districts")
    
    # Create a boundary by dissolving all zoning districts into one polygon
    denver = zoning.dissolve()
    print(f"   ✓ Created Denver boundary from zoning data")
    print(f"   CRS: {denver.crs}")
except Exception as e:
    print(f"   ✗ Error loading zoning data: {e}")
    print("   Trying to download Denver boundary...")
    
    # Fallback: try to download Denver boundary
    denver_boundary_url = "https://www.denvergov.org/media/gis/DataCatalog/city_boundary/shape/city_boundary.zip"
    try:
        response = requests.get(denver_boundary_url, timeout=30)
        with open('denver_boundary.zip', 'wb') as f:
            f.write(response.content)
        
        denver = gpd.read_file('denver_boundary.zip')
        print(f"   ✓ Loaded Denver boundary from download")
    except Exception as e2:
        print(f"   ✗ Download failed: {e2}")
        # Last resort: use approximate bounding box
        from shapely.geometry import box
        denver_bounds = box(-105.11, 39.61, -104.60, 39.91)
        denver = gpd.GeoDataFrame({'geometry': [denver_bounds]}, crs='EPSG:4326')
        print(f"   ✓ Using approximate Denver bounding box")

# Load RTD stations
print("\n2. Filtering RTD stations to Denver only...")
stations = gpd.read_file('rtd_lightrail_stations.geojson')
print(f"   Original stations: {len(stations)}")

# Ensure same CRS
stations = stations.to_crs(denver.crs)

# Spatial join to keep only stations within Denver
stations_denver = gpd.sjoin(stations, denver, how='inner', predicate='within')

# Drop ALL columns from the right (denver) to avoid duplicate column issues
cols_to_drop = [col for col in stations_denver.columns if col.endswith('_left') or col.endswith('_right') or col == 'index_right']
stations_denver = stations_denver.drop(columns=cols_to_drop, errors='ignore')

# Also drop any duplicate column names by keeping only the first occurrence
stations_denver = stations_denver.loc[:, ~stations_denver.columns.duplicated()]

# ALSO keep all A-Line stations (even if outside Denver, due to TOD zones crossing into Denver)
# Match any station with these keywords (covers all A-Line stations)
a_line_stations = stations[stations['NAME'].str.contains('61st.*Peña|40th.*Airport|Peoria|Central Park|40th.*Ave|38th.*Blake|Union Station', case=False, na=False, regex=True)]
print(f"   Keeping {len(a_line_stations)} A-Line stations (TOD zones cross Denver boundary)")

# Reset indices before concatenating to avoid duplicate index issues
stations_denver = stations_denver.reset_index(drop=True)
a_line_stations = a_line_stations.reset_index(drop=True)

# Combine: Denver stations + all A-Line stations, remove duplicates based on NAME
stations_combined = pd.concat([stations_denver, a_line_stations], ignore_index=True)
stations_combined = stations_combined.drop_duplicates(subset=['NAME'])

print(f"   ✓ Filtered to {len(stations_combined)} stations (Denver + A-Line)")
print(f"   Removed {len(stations) - len(stations_combined)} stations outside Denver")

# Save filtered stations
stations_combined.to_file('rtd_lightrail_stations.geojson', driver='GeoJSON')
print(f"   ✓ Saved to rtd_lightrail_stations.geojson")

# Load RTD rail lines
print("\n3. Filtering RTD rail lines to Denver only...")
rail_lines = gpd.read_file('rtd_lightrail_lines.geojson')
print(f"   Original line segments: {len(rail_lines)}")

# Ensure same CRS
rail_lines = rail_lines.to_crs(denver.crs)

# Separate A-Line from other lines
a_line = rail_lines[rail_lines['ROUTE'] == 'A-Line'].copy()
other_lines = rail_lines[rail_lines['ROUTE'] != 'A-Line'].copy()

print(f"   A-Line segments: {len(a_line)} (keeping all - TOD zones cross Denver boundary)")
print(f"   Other line segments: {len(other_lines)} (clipping to Denver boundary)")

# Clip non-A-Line segments to Denver boundary
print("   Clipping non-A-Line rail lines to Denver boundary...")
other_lines_denver = gpd.clip(other_lines, denver)

# Reset indices before combining
a_line = a_line.reset_index(drop=True)
other_lines_denver = other_lines_denver.reset_index(drop=True)

# Combine: all A-Line + clipped other lines
rail_lines_combined = pd.concat([a_line, other_lines_denver], ignore_index=True)

print(f"   ✓ Result: {len(rail_lines_combined)} line segments (A-Line + Denver portions of other lines)")
print(f"   Removed {len(rail_lines) - len(rail_lines_combined)} line segments outside Denver")

# Save combined lines
rail_lines_combined.to_file('rtd_lightrail_lines.geojson', driver='GeoJSON')
print(f"   ✓ Saved to rtd_lightrail_lines.geojson")

# Show which stations were removed
print("\n4. Stations removed (outside Denver):")
stations_removed = stations[~stations.index.isin(stations_denver.index)]
for idx, station in stations_removed.iterrows():
    station_name = station.get('NAME', 'Unknown')
    print(f"   - {station_name}")

print("\n" + "="*70)
print("✓ FILTERING COMPLETE")
print("="*70)
print("\nThe RTD files have been filtered to Denver city limits only.")
print("Next: Run 'python add_parcels_to_map.py' to regenerate the map.")
