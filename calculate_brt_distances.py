"""
Calculate Distances from Parcels to BRT Corridors
===================================================
Calculates distance from each parcel to nearest BRT corridor polygon.
Uses the same approach as calculate_park_distances.py.
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

# 2. LOAD BRT CORRIDORS FROM GEOJSON
print("Loading BRT corridors from geojson...")

# Load the brt_corridors.geojson file (should be in same directory or provide path)
BRT_FILE = os.path.join(os.path.dirname(__file__), "data/brt_lines.geojson")
with open(BRT_FILE) as f:
    brt_data = json.load(f)

brt_geoms = []
brt_names = []

for feature in brt_data['features']:
    geom = shape(feature['geometry'])
    geom_feet = to_feet(geom)
    brt_geoms.append(geom_feet)
    brt_names.append(feature['properties']['name'])
    print(f"  Loaded: {feature['properties']['name']} ({feature['geometry']['type']}, {feature['properties'].get('investment_level', 'N/A')})")

print(f"\n  Total: {len(brt_geoms)} BRT corridor geometries")

# Build Spatial Index
brt_tree = STRtree(brt_geoms)

# 3. ADD COLUMN IF NOT EXISTS
print("\nEnsuring distance_to_brt column exists...")
with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE parcels ADD COLUMN IF NOT EXISTS distance_to_brt FLOAT;
    """))
    conn.commit()

# 4. CALCULATE DISTANCES
print("Processing parcels...")
with engine.connect() as conn:
    parcels = conn.execute(text("SELECT id, geometry_geojson FROM parcels")).fetchall()
    
    updates = []
    for i, (p_id, p_geom_json) in enumerate(parcels):
        parcel_geom_feet = to_feet(shape(json.loads(p_geom_json)))

        # Find nearest BRT corridor (edge-to-edge distance)
        nearest_idx = brt_tree.nearest(parcel_geom_feet)
        nearest_geom = brt_geoms[nearest_idx]
        dist_brt = parcel_geom_feet.distance(nearest_geom)

        updates.append({
            "id": p_id,
            "dist_brt": round(dist_brt, 2)
        })

        if i % 5000 == 0:
            print(f"  Calculated {i} of {len(parcels)}...")

    # 5. BATCH UPDATE DATABASE
    print("Writing distances back to database...")
    conn.execute(text("""
        UPDATE parcels 
        SET distance_to_brt = :dist_brt
        WHERE id = :id
    """), updates)
    conn.commit()

print("Done!")

# 6. SHOW STATISTICS
print("\n" + "="*70)
print("BRT DISTANCE STATISTICS")
print("="*70)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE distance_to_brt <= 250) as within_250ft,
            COUNT(*) FILTER (WHERE distance_to_brt <= 750) as within_750ft,
            COUNT(*) FILTER (WHERE distance_to_brt <= 1000) as within_1000ft,
            COUNT(*) FILTER (WHERE distance_to_brt <= 1500) as within_1500ft,
            AVG(distance_to_brt) as avg_distance,
            MIN(distance_to_brt) as min_distance
        FROM parcels
        WHERE distance_to_brt IS NOT NULL;
    """))
    
    row = result.fetchone()
    print(f"\n  Parcels within 250ft:  {row[0]:,}")
    print(f"  Parcels within 750ft:  {row[1]:,}")
    print(f"  Parcels within 1000ft: {row[2]:,}")
    print(f"  Parcels within 1500ft: {row[3]:,}")
    print(f"  Average distance:      {row[4]:.0f} ft")
    print(f"  Minimum distance:      {row[5]:.0f} ft")

print("\n" + "="*70)
print("BRT DISTANCE CALCULATIONS COMPLETE")
print("="*70)
