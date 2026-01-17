import geopandas as gpd
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

# Drop the join index column
if 'index_right' in stations_denver.columns:
    stations_denver = stations_denver.drop(columns=['index_right'])

print(f"   ✓ Filtered to {len(stations_denver)} stations within Denver")
print(f"   Removed {len(stations) - len(stations_denver)} stations outside Denver")

# Save filtered stations
stations_denver.to_file('rtd_lightrail_stations.geojson', driver='GeoJSON')
print(f"   ✓ Saved to rtd_lightrail_stations.geojson")

# Load RTD rail lines
print("\n3. Filtering RTD rail lines to Denver only...")
rail_lines = gpd.read_file('rtd_lightrail_lines.geojson')
print(f"   Original line segments: {len(rail_lines)}")

# Ensure same CRS
rail_lines = rail_lines.to_crs(denver.crs)

# Clip rail lines to Denver boundary (not just intersect)
print("   Clipping rail lines to Denver boundary...")
rail_lines_denver = gpd.clip(rail_lines, denver)

print(f"   ✓ Clipped to {len(rail_lines_denver)} line segments within Denver")
print(f"   Removed {len(rail_lines) - len(rail_lines_denver)} line segments outside Denver")

# Save clipped lines
rail_lines_denver.to_file('rtd_lightrail_lines.geojson', driver='GeoJSON')
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