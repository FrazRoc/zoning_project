"""
Calculate Distances from Parcels to Medium-Frequency Bus Stops
================================================================
Calculates edge-to-edge distance from each parcel to nearest medium-frequency bus stop.
Uses the same accurate method as park distances (edge-to-edge with STRtree).

Requirements:
    pip install shapely pyproj
"""

import os
import json
import pyproj
from sqlalchemy import create_engine, text
from shapely.geometry import shape, Point
from shapely.ops import transform
from shapely.strtree import STRtree

print("="*70)
print("CALCULATING DISTANCES TO MEDIUM-FREQUENCY BUS STOPS")
print("="*70)

# ============================================================================
# STEP 1: Setup Database and Projection
# ============================================================================

print("\n1. Setting up database connection and projection...")

DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)
engine = create_engine(DATABASE_URL)

# Transform from Lat/Long (4326) to Denver Feet (2232) for accurate distance
project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:2232", always_xy=True).transform

def to_feet(geom):
    """Convert geometry from lat/lon to Denver feet projection"""
    return transform(project, geom)

print("   ✓ Database connection ready")
print("   ✓ Projection: EPSG:4326 (WGS84) → EPSG:2232 (Denver feet)")

# ============================================================================
# STEP 2: Load and Project Bus Stops
# ============================================================================

print("\n2. Loading medium-frequency bus stops...")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT stop_id, stop_name, stop_lat, stop_lon
        FROM bus_stops
        ORDER BY stop_id;
    """))
    
    bus_stops = result.fetchall()

print(f"   ✓ Loaded {len(bus_stops):,} medium-frequency bus stops")

# Convert bus stops to Shapely points and project to feet
print("   Projecting bus stops to Denver feet...")
bus_stop_geoms = []
bus_stop_info = []

for stop_id, stop_name, stop_lat, stop_lon in bus_stops:
    # Create point in lat/lon
    point_latlon = Point(stop_lon, stop_lat)
    
    # Project to feet
    point_feet = to_feet(point_latlon)
    
    bus_stop_geoms.append(point_feet)
    bus_stop_info.append({
        'stop_id': stop_id,
        'stop_name': stop_name,
        'lat': stop_lat,
        'lon': stop_lon
    })

print(f"   ✓ Projected {len(bus_stop_geoms):,} bus stop points")

# ============================================================================
# STEP 3: Build Spatial Index
# ============================================================================

print("\n3. Building spatial index (STRtree)...")

bus_stop_tree = STRtree(bus_stop_geoms)

print("   ✓ STRtree index built for fast nearest-neighbor lookups")

# ============================================================================
# STEP 4: Calculate Distances for All Parcels
# ============================================================================

print("\n4. Calculating edge-to-edge distances...")
print("   (This will take 30-60 minutes for ~180k parcels)")

with engine.connect() as conn:
    # Get total count
    total_parcels = conn.execute(text("SELECT COUNT(*) FROM parcels WHERE geometry_geojson IS NOT NULL")).scalar()
    print(f"   Total parcels to process: {total_parcels:,}")
    
    # Process in batches
    BATCH_SIZE = 1000
    offset = 0
    processed = 0
    
    while offset < total_parcels:
        # Fetch batch of parcels
        result = conn.execute(text(f"""
            SELECT id, parcel_id, geometry_geojson
            FROM parcels
            WHERE geometry_geojson IS NOT NULL
            ORDER BY id
            LIMIT {BATCH_SIZE} OFFSET {offset};
        """))
        
        parcels_batch = result.fetchall()
        
        if not parcels_batch:
            break
        
        # Calculate distances for this batch
        updates = []
        
        for p_id, parcel_id, geom_json in parcels_batch:
            try:
                # Parse parcel geometry and project to feet
                parcel_geom_latlon = shape(json.loads(geom_json))
                parcel_geom_feet = to_feet(parcel_geom_latlon)
                
                # Find nearest bus stop using spatial index
                nearest_idx = bus_stop_tree.nearest(parcel_geom_feet)
                nearest_stop_geom = bus_stop_geoms[nearest_idx]
                
                # Calculate edge-to-edge distance in feet
                distance_feet = parcel_geom_feet.distance(nearest_stop_geom)
                
                updates.append({
                    'id': p_id,
                    'distance': round(distance_feet, 2)
                })
                
            except Exception as e:
                # Skip parcels with invalid geometry
                print(f"   ⚠️  Skipping parcel {parcel_id}: {e}")
                continue
        
        # Batch update database
        if updates:
            conn.execute(text("""
                UPDATE parcels 
                SET distance_to_med_freq_bus = :distance
                WHERE id = :id
            """), updates)
            conn.commit()
        
        processed += len(parcels_batch)
        offset += BATCH_SIZE
        
        # Progress update every 5000 parcels
        if processed % 5000 == 0 or processed == total_parcels:
            pct = (processed / total_parcels) * 100
            print(f"   Progress: {processed:,} / {total_parcels:,} ({pct:.1f}%)")

print(f"\n   ✓ Processed {processed:,} parcels")

# ============================================================================
# STEP 5: Statistics
# ============================================================================

print("\n5. Distance statistics:")
print("="*70)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(distance_to_med_freq_bus) as with_distance,
            MIN(distance_to_med_freq_bus) as min_dist,
            AVG(distance_to_med_freq_bus) as avg_dist,
            MAX(distance_to_med_freq_bus) as max_dist,
            COUNT(*) FILTER (WHERE distance_to_med_freq_bus <= 250) as within_250ft
        FROM parcels;
    """))
    
    row = result.fetchone()
    
    print(f"\n   Total parcels: {row[0]:,}")
    print(f"   With distance calculated: {row[1]:,}")
    
    if row[2] is not None:
        print(f"\n   Distance range:")
        print(f"   - Minimum: {row[2]:.0f} ft")
        print(f"   - Average: {row[3]:.0f} ft")
        print(f"   - Maximum: {row[4]:.0f} ft")
        
        print(f"\n   BOD Policy Qualification (250ft threshold):")
        print(f"   - Parcels within 250ft: {row[5]:,}")
        print(f"   - Percentage: {row[5]/row[0]*100:.2f}%")
        
        # Estimate potential units (rough estimate)
        # Assuming ~10 units per acre for medium-density
        result2 = conn.execute(text("""
            SELECT SUM(land_area_acres)
            FROM parcels
            WHERE distance_to_med_freq_bus <= 250;
        """))
        total_acres = result2.scalar()
        
        if total_acres:
            estimated_units = int(total_acres * 10)
            print(f"\n   Estimated Development Potential:")
            print(f"   - Total land area within 250ft: {total_acres:,.0f} acres")
            print(f"   - Estimated potential units (10/acre): ~{estimated_units:,}")

print("\n" + "="*70)
print("DISTANCE CALCULATIONS COMPLETE")
print("="*70)

print("\nNext steps:")
print("1. Verify distances look reasonable")
print("2. Test a few known parcels (e.g., downtown vs edges)")
print("3. Ready to update API to include BOD policy!")
