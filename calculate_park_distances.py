"""
Calculate Distances from Parcels to Parks
==========================================
Calculates distance from each parcel to nearest community and regional park.
"""

import os
from sqlalchemy import create_engine, text
import json
from shapely.geometry import shape, Point
from shapely.ops import nearest_points

print("="*70)
print("CALCULATING PARCEL DISTANCES TO PARKS")
print("="*70)

# Database connection
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)

engine = create_engine(DATABASE_URL)

# ============================================================================
# STEP 1: Add distance columns to parcels table
# ============================================================================

print("\n1. Adding distance columns to parcels table...")

with engine.connect() as conn:
    # Add columns if they don't exist
    conn.execute(text("""
        ALTER TABLE parcels 
        ADD COLUMN IF NOT EXISTS distance_to_community_park NUMERIC,
        ADD COLUMN IF NOT EXISTS distance_to_regional_park NUMERIC;
    """))
    
    # Create indexes
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS parcels_dist_community_park_idx 
        ON parcels(distance_to_community_park);
    """))
    
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS parcels_dist_regional_park_idx 
        ON parcels(distance_to_regional_park);
    """))
    
    conn.commit()
    print("   ✓ Distance columns added")

# ============================================================================
# STEP 2: Load parks
# ============================================================================

print("\n2. Loading parks...")

with engine.connect() as conn:
    # Load community parks
    result = conn.execute(text("""
        SELECT id, formal_name, geometry
        FROM parks
        WHERE ballot_park_type = 'community';
    """))
    
    community_parks = []
    for row in result:
        geom = json.loads(row[2])
        community_parks.append({
            'id': row[0],
            'formal_name': row[1],
            'geometry': shape(geom)
        })
    
    print(f"   ✓ Loaded {len(community_parks)} community parks")
    
    # Load regional parks
    result = conn.execute(text("""
        SELECT id, formal_name, geometry
        FROM parks
        WHERE ballot_park_type = 'regional';
    """))
    
    regional_parks = []
    for row in result:
        geom = json.loads(row[2])
        regional_parks.append({
            'id': row[0],
            'formal_name': row[1],
            'geometry': shape(geom)
        })
    
    print(f"   ✓ Loaded {len(regional_parks)} regional parks")

# ============================================================================
# STEP 3: Calculate distances
# ============================================================================

print("\n3. Calculating distances (this may take a while)...")

# Get total parcel count
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM parcels;"))
    total_parcels = result.scalar()
    print(f"   Processing {total_parcels:,} parcels...")

# Process in batches
BATCH_SIZE = 1000
offset = 0
processed = 0

while offset < total_parcels:
    # Fetch batch of parcels
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT parcel_id, geometry_geojson
            FROM parcels
            ORDER BY id
            LIMIT {BATCH_SIZE} OFFSET {offset};
        """))
        
        parcels = result.fetchall()
    
    # Calculate distances for this batch
    updates = []
    
    for parcel_id, geom_json in parcels:
        if not geom_json:
            continue
        
        parcel_geom = shape(json.loads(geom_json))
        parcel_centroid = parcel_geom.centroid
        
        # Distance to nearest community park
        min_dist_community = None
        if community_parks:
            min_dist_community = min(
                parcel_centroid.distance(park['geometry']) * 364000  # degrees to feet approximation
                for park in community_parks
            )
        
        # Distance to nearest regional park
        min_dist_regional = None
        if regional_parks:
            min_dist_regional = min(
                parcel_centroid.distance(park['geometry']) * 364000  # degrees to feet approximation
                for park in regional_parks
            )
        
        updates.append({
            'parcel_id': parcel_id,
            'dist_community': min_dist_community,
            'dist_regional': min_dist_regional
        })
    
    # Update database
    with engine.connect() as conn:
        for update in updates:
            conn.execute(text("""
                UPDATE parcels
                SET distance_to_community_park = :dist_community,
                    distance_to_regional_park = :dist_regional
                WHERE parcel_id = :parcel_id;
            """), update)
        
        conn.commit()
    
    processed += len(parcels)
    offset += BATCH_SIZE
    
    # Progress update
    pct = (processed / total_parcels) * 100
    print(f"   Progress: {processed:,} / {total_parcels:,} ({pct:.1f}%)")

print(f"   ✓ Distances calculated for {processed:,} parcels")

# ============================================================================
# STEP 4: Show statistics
# ============================================================================

print("\n4. Distance statistics:")

with engine.connect() as conn:
    # Community park distances
    result = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE distance_to_community_park <= 250) as within_250ft,
            COUNT(*) FILTER (WHERE distance_to_community_park <= 750) as within_750ft,
            AVG(distance_to_community_park) as avg_distance
        FROM parcels
        WHERE distance_to_community_park IS NOT NULL;
    """))
    
    row = result.fetchone()
    print(f"\n   Community Parks:")
    print(f"   - Parcels within 250ft: {row[0]:,}")
    print(f"   - Parcels within 750ft: {row[1]:,}")
    print(f"   - Average distance: {row[2]:.0f} ft")
    
    # Regional park distances
    result = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE distance_to_regional_park <= 250) as within_250ft,
            COUNT(*) FILTER (WHERE distance_to_regional_park <= 750) as within_750ft,
            AVG(distance_to_regional_park) as avg_distance
        FROM parcels
        WHERE distance_to_regional_park IS NOT NULL;
    """))
    
    row = result.fetchone()
    print(f"\n   Regional Parks:")
    print(f"   - Parcels within 250ft: {row[0]:,}")
    print(f"   - Parcels within 750ft: {row[1]:,}")
    print(f"   - Average distance: {row[2]:.0f} ft")

print("\n" + "="*70)
print("DISTANCE CALCULATIONS COMPLETE")
print("="*70)
