"""
Calculate Distances to Transit
===============================
This script calculates the distance from each parcel to the nearest
light rail station and updates the database.

For 240K parcels, this uses a spatial join approach without PostGIS.
"""

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from shapely.geometry import shape
import json
import os
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("CALCULATING DISTANCES TO TRANSIT")
print("="*70)

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

DB_USER = os.environ.get('USER')
DATABASE_URL = f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"

print("\n1. Connecting to database...")
engine = create_engine(DATABASE_URL)

# ============================================================================
# CHECK/LOAD TRANSIT STATIONS
# ============================================================================

print("\n2. Checking for transit station data...")

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM light_rail_stations;"))
    station_count = result.fetchone()[0]

if station_count == 0:
    print("   No stations found, loading from GeoJSON...")
    
    try:
        # Load stations
        try:
            stations_gdf = gpd.read_file('rtd_lightrail_stations.geojson')
        except AttributeError:
            # Fallback for older geopandas
            with open('rtd_lightrail_stations.geojson', 'r') as f:
                data = json.load(f)
            features = data['features']
            geometries = [shape(f['geometry']) for f in features]
            properties = [f['properties'] for f in features]
            stations_gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs='EPSG:4326')
        
        # Prepare station data
        stations_data = []
        for idx, row in stations_gdf.iterrows():
            stations_data.append({
                'station_id': f'station_{idx}',
                'name': row.get('NAME', f'Station {idx}'),
                'geometry_geojson': json.dumps(row.geometry.__geo_interface__)
            })
        
        # Insert stations
        df_stations = pd.DataFrame(stations_data)
        df_stations.to_sql('light_rail_stations', engine, if_exists='append', index=False)
        
        print(f"   ✓ Loaded {len(stations_data)} stations")
        station_count = len(stations_data)
        
    except FileNotFoundError:
        print("   ✗ rtd_lightrail_stations.geojson not found!")
        print("   Cannot calculate distances without station data.")
        exit(1)
else:
    print(f"   ✓ Found {station_count} stations in database")

# ============================================================================
# LOAD STATIONS INTO GEODATAFRAME
# ============================================================================

print("\n3. Loading station geometries...")

# Get stations from database
with engine.connect() as conn:
    result = conn.execute(text("SELECT station_id, name, geometry_geojson FROM light_rail_stations;"))
    stations_data = result.fetchall()

# Convert to GeoDataFrame
stations_list = []
for row in stations_data:
    geom = shape(json.loads(row[2]))
    stations_list.append({
        'station_id': row[0],
        'name': row[1],
        'geometry': geom
    })

stations_gdf = gpd.GeoDataFrame(stations_list, geometry='geometry', crs='EPSG:4326')

# Convert to meters for accurate distance calculation
stations_gdf = stations_gdf.to_crs('EPSG:32613')  # UTM Zone 13N (Denver)

print(f"   ✓ Loaded {len(stations_gdf)} stations for distance calculation")

# ============================================================================
# CALCULATE DISTANCES IN BATCHES
# ============================================================================

print("\n4. Calculating distances (this will take 10-15 minutes for 240K parcels)...")

# Get total parcel count
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM parcels;"))
    total_parcels = result.fetchone()[0]

print(f"   Total parcels to process: {total_parcels:,}")

# Process in batches
batch_size = 5000
total_batches = (total_parcels + batch_size - 1) // batch_size

for batch_num in range(total_batches):
    offset = batch_num * batch_size
    
    # Load batch of parcels
    query = f"""
        SELECT id, parcel_id, geometry_geojson 
        FROM parcels 
        ORDER BY id 
        LIMIT {batch_size} OFFSET {offset};
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        parcels_batch = result.fetchall()
    
    if not parcels_batch:
        break
    
    # Convert to GeoDataFrame
    parcels_list = []
    for row in parcels_batch:
        try:
            geom = shape(json.loads(row[2]))
            parcels_list.append({
                'id': row[0],
                'parcel_id': row[1],
                'geometry': geom
            })
        except:
            # Skip parcels with invalid geometry
            continue
    
    if not parcels_list:
        print(f"   ⚠ Batch {batch_num + 1}/{total_batches}: No valid geometries, skipping")
        continue
    
    parcels_gdf = gpd.GeoDataFrame(parcels_list, geometry='geometry', crs='EPSG:4326')
    parcels_gdf = parcels_gdf.to_crs('EPSG:32613')  # Convert to meters
    
    # Calculate distance to nearest station for each parcel
    distances = []
    nearest_stations = []
    
    for idx, parcel in parcels_gdf.iterrows():
        # Calculate distance to all stations
        dists = stations_gdf.geometry.distance(parcel.geometry)
        min_dist_meters = dists.min()
        min_dist_feet = min_dist_meters * 3.28084  # Convert to feet
        nearest_station_idx = dists.idxmin()
        nearest_station_id = stations_gdf.loc[nearest_station_idx, 'station_id']
        
        distances.append(min_dist_feet)
        nearest_stations.append(nearest_station_id)
    
    parcels_gdf['distance_to_light_rail'] = distances
    parcels_gdf['nearest_station_id'] = nearest_stations
    
    # Update database
    updates = []
    for idx, row in parcels_gdf.iterrows():
        updates.append({
            'id': row['id'],
            'distance': row['distance_to_light_rail']
        })
    
    # Batch update
    update_query = """
        UPDATE parcels 
        SET distance_to_light_rail = :distance 
        WHERE id = :id;
    """
    
    with engine.connect() as conn:
        for update in updates:
            conn.execute(text(update_query), update)
        conn.commit()
    
    # Progress update
    parcels_processed = min((batch_num + 1) * batch_size, total_parcels)
    percent = (parcels_processed / total_parcels) * 100
    print(f"   ✓ Batch {batch_num + 1}/{total_batches} ({parcels_processed:,}/{total_parcels:,} parcels - {percent:.1f}%)")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

print("\n5. Distance calculation summary:")

with engine.connect() as conn:
    # Count parcels with distances
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM parcels 
        WHERE distance_to_light_rail IS NOT NULL;
    """))
    count_with_distance = result.fetchone()[0]
    
    print(f"   Parcels with calculated distances: {count_with_distance:,}")
    
    # Distance statistics
    result = conn.execute(text("""
        SELECT 
            MIN(distance_to_light_rail) as min_dist,
            AVG(distance_to_light_rail) as avg_dist,
            MAX(distance_to_light_rail) as max_dist
        FROM parcels 
        WHERE distance_to_light_rail IS NOT NULL;
    """))
    row = result.fetchone()
    print(f"\n   Distance statistics (feet):")
    print(f"     - Minimum: {row[0]:.0f}")
    print(f"     - Average: {row[1]:.0f}")
    print(f"     - Maximum: {row[2]:.0f}")
    
    # Count by transit proximity
    result = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE distance_to_light_rail <= 660) as within_660,
            COUNT(*) FILTER (WHERE distance_to_light_rail > 660 AND distance_to_light_rail <= 1320) as within_1320,
            COUNT(*) FILTER (WHERE distance_to_light_rail > 1320 AND distance_to_light_rail <= 1980) as within_1980,
            COUNT(*) FILTER (WHERE distance_to_light_rail > 1980 AND distance_to_light_rail <= 2640) as within_half_mile
        FROM parcels 
        WHERE distance_to_light_rail IS NOT NULL;
    """))
    row = result.fetchone()
    
    print(f"\n   Parcels by distance to light rail:")
    print(f"     - Within 660ft (Ring 1): {row[0]:,}")
    print(f"     - Within 1,320ft (Ring 2): {row[1]:,}")
    print(f"     - Within 1,980ft (Ring 3 - Ballot): {row[2]:,}")
    print(f"     - Within 2,640ft (1/2 mile): {row[3]:,}")

print("\n" + "="*70)
print("DISTANCE CALCULATION COMPLETE!")
print("="*70)
print("\nYou can now run policy analysis using distance filters!")
print("\nExample query:")
print("  SELECT COUNT(*) FROM parcels WHERE distance_to_light_rail <= 1980;")
print("")
