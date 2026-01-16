"""
Download Microsoft Building Footprints for Denver from GitHub
Then spatially filter to only buildings within our TOD parcel areas
"""
import requests
import geopandas as gpd
import json
from shapely.geometry import shape

print("="*70)
print("DOWNLOADING MICROSOFT BUILDING FOOTPRINTS FOR DENVER")
print("="*70)

# ============================================================================
# DOWNLOAD COLORADO BUILDING FOOTPRINTS
# ============================================================================

print("\n1. Downloading Colorado building footprints from Microsoft...")
print("   (This may take a few minutes - file is large)")

# Microsoft's GitHub repo for US Building Footprints
# Colorado file URL
url = "https://usbuildingdata.blob.core.windows.net/usbuildings-v2/Colorado.geojson.zip"

try:
    # Download the zip file
    print("   Downloading zip file...")
    response = requests.get(url, timeout=300, stream=True)
    
    if response.status_code == 200:
        # Save zip file
        with open('colorado_buildings.zip', 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("   ✓ Downloaded Colorado buildings zip file")
        
        # Extract and load the GeoJSON
        print("   Extracting and loading buildings...")
        import zipfile
        with zipfile.ZipFile('colorado_buildings.zip', 'r') as zip_ref:
            zip_ref.extractall('.')
        
        # Load the GeoJSON
        buildings = gpd.read_file('Colorado.geojson')
        print(f"   ✓ Loaded {len(buildings):,} buildings for Colorado")
        
    else:
        print(f"   ✗ Error: HTTP {response.status_code}")
        exit(1)
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    print("\n   Trying alternative method...")
    
    # Alternative: Load directly from the URL (slower but works)
    try:
        buildings = gpd.read_file(url)
        print(f"   ✓ Loaded {len(buildings):,} buildings for Colorado")
    except Exception as e2:
        print(f"   ✗ Alternative method also failed: {e2}")
        exit(1)

# ============================================================================
# FILTER TO DENVER AREA ONLY
# ============================================================================

print("\n2. Filtering to Denver/TOD area only...")

# Load our TOD parcels to get the bounding area
parcels = gpd.read_file('high_opportunity_parcels_v2.geojson')
print(f"   Loaded {len(parcels):,} TOD parcels")

# Create a buffer around all parcels (1/2 mile) to catch nearby buildings
parcels_projected = parcels.to_crs('EPSG:32613')
buffer_area = parcels_projected.buffer(804.67).unary_union  # 1/2 mile buffer
buffer_gdf = gpd.GeoDataFrame({'geometry': [buffer_area]}, crs='EPSG:32613')
buffer_gdf_wgs84 = buffer_gdf.to_crs('EPSG:4326')

# Spatial filter: keep only buildings within our buffer area
buildings_wgs84 = buildings.to_crs('EPSG:4326')
buildings_filtered = gpd.sjoin(buildings_wgs84, buffer_gdf_wgs84, how='inner', predicate='intersects')

print(f"   ✓ Filtered to {len(buildings_filtered):,} buildings near TOD parcels")

# ============================================================================
# SAVE FILTERED BUILDINGS
# ============================================================================

print("\n3. Saving filtered building footprints...")

# Drop the join index column
if 'index_right' in buildings_filtered.columns:
    buildings_filtered = buildings_filtered.drop(columns=['index_right'])

# Save as GeoJSON
buildings_filtered.to_file('denver_building_footprints.geojson', driver='GeoJSON')

print(f"   ✓ Saved to: denver_building_footprints.geojson")
print(f"   File contains {len(buildings_filtered):,} building polygons")

# Show sample
if len(buildings_filtered) > 0:
    print("\n4. Sample building:")
    first = buildings_filtered.iloc[0]
    print(f"   Geometry type: {first.geometry.geom_type}")
    print(f"   Area: {first.geometry.area * 111000 * 111000:.0f} sq meters (approx)")

print("\n" + "="*70)
print("✓ DOWNLOAD COMPLETE")
print("="*70)
print("\nNext: Update add_parcels_to_map.py to add building footprints layer")
