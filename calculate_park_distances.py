"""
Calculate Distances from Parcels to Parks
==========================================
Calculates distance from each parcel to nearest community and regional park.
"""

import os
import json
import pyproj
from sqlalchemy import create_engine, text
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree

# 1. SETUP DATABASE AND PROJECTION
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)
engine = create_engine(DATABASE_URL)

# Transform from Lat/Long (4326) to Denver Feet (2232)
project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:2232", always_xy=True).transform

def to_feet(geom):
    return transform(project, geom)

# 2. LOAD AND PROJECT PARKS
print("Loading and projecting parks into feet...")
with engine.connect() as conn:
    # Fetch parks that qualify for the ballot
    result = conn.execute(text("SELECT ballot_park_type, geometry FROM parks WHERE ballot_park_type != 'ineligible'"))
    parks = result.fetchall()

regional_geoms = []
community_geoms = []

for p_type, g_json in parks:
    geom_feet = to_feet(shape(json.loads(g_json)))
    if p_type == 'regional':
        regional_geoms.append(geom_feet)
    else:
        community_geoms.append(geom_feet)

# Build Spatial Indexes
reg_tree = STRtree(regional_geoms)
com_tree = STRtree(community_geoms)

# 3. CALCULATE DISTANCES
print("Processing parcels...")
with engine.connect() as conn:
    parcels = conn.execute(text("SELECT id, geometry_geojson FROM parcels")).fetchall()
    
    updates = []
    for i, (p_id, p_geom_json) in enumerate(parcels):
        # Full geometry to full geometry (Edge-to-Edge)
        parcel_geom_feet = to_feet(shape(json.loads(p_geom_json)))

        # Find nearest regional park index and look up the geometry
        nearest_reg_idx = reg_tree.nearest(parcel_geom_feet)
        nearest_reg_geom = regional_geoms[nearest_reg_idx]
        dist_reg = parcel_geom_feet.distance(nearest_reg_geom)

        # Find nearest community park index and look up the geometry
        nearest_com_idx = com_tree.nearest(parcel_geom_feet)
        nearest_com_geom = community_geoms[nearest_com_idx]
        dist_com = parcel_geom_feet.distance(nearest_com_geom)

        updates.append({
            "id": p_id,
            "dist_reg": round(dist_reg, 2),
            "dist_com": round(dist_com, 2)
        })

        if i % 5000 == 0:
            print(f"Calculated {i} of {len(parcels)}...")

    # 4. BATCH UPDATE DATABASE
    print("Writing distances back to database...")
    # Using a temp table for the update is often much faster for 200k rows
    conn.execute(text("""
        UPDATE parcels 
        SET distance_to_regional_park = :dist_reg,
            distance_to_community_park = :dist_com
        WHERE id = :id
    """), updates)
    conn.commit()

print("Done! Accuracy at 2255 N Vine St should now be ~130ft.")

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
