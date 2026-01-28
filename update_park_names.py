"""
Download Denver Parks with Names
=================================
Updates park names from official Denver parks GeoJSON file.
"""

import os
from sqlalchemy import create_engine, text
import json
from shapely.geometry import shape

print("="*70)
print("UPDATING DENVER PARKS WITH NAMES")
print("="*70)

# Database connection
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)

engine = create_engine(DATABASE_URL)

# ============================================================================
# STEP 1: Load parks from local GeoJSON file
# ============================================================================

print("\n1. Loading parks from GeoJSON file...")

# Read the file
PARKS_FILE = "ODC_PARK_PARKLAND_A_-209021382844435935.geojson"

with open(PARKS_FILE, 'r') as f:
    parks_data = json.load(f)

print(f"   ✓ Loaded {len(parks_data['features'])} parks from file")

# ============================================================================
# STEP 2: Update park names in our database
# ============================================================================

print("\n2. Matching and updating park names...")

# Load our existing parks
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT park_id, name, geometry_geojson, land_area_acres
        FROM parks;
    """))
    
    our_parks = []
    for row in result:
        geom = shape(json.loads(row[2]))
        our_parks.append({
            'park_id': row[0],
            'name': row[1],
            'geometry': geom,
            'acres': row[3]
        })

print(f"   Our database has {len(our_parks)} parks")

# Match by geometry overlap
updated = 0
no_match = 0

for our_park in our_parks:
    best_match = None
    best_overlap = 0
    
    for gis_feature in parks_data['features']:
        gis_geom = shape(gis_feature['geometry'])
        
        # Calculate overlap
        try:
            if our_park['geometry'].intersects(gis_geom):
                overlap = our_park['geometry'].intersection(gis_geom).area
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = gis_feature
        except:
            continue
    
    # If we found a good match (>50% overlap), update the name
    if best_match and best_overlap > (our_park['geometry'].area * 0.5):
        formal_name = best_match['properties']['FORMAL_NAME']
        
        if formal_name and formal_name.strip():
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE parks
                    SET name = :name
                    WHERE park_id = :park_id;
                """), {
                    'name': formal_name,
                    'park_id': our_park['park_id']
                })
                conn.commit()
            
            updated += 1
            print(f"   ✓ Updated: {formal_name} ({our_park['acres']:.1f} acres)")
        else:
            no_match += 1
    else:
        no_match += 1

print(f"\n   Updated {updated} park names")
print(f"   Could not match {no_match} parks (will keep parcel-based names)")

# ============================================================================
# STEP 3: Show updated parks
# ============================================================================

print("\n3. Parks summary:")

with engine.connect() as conn:
    # Community parks
    print("\n   Community Parks (10-75 acres):")
    result = conn.execute(text("""
        SELECT name, land_area_acres
        FROM parks
        WHERE park_type = 'community'
        ORDER BY land_area_acres DESC
        LIMIT 10;
    """))
    
    for row in result:
        print(f"   - {row[0]}: {row[1]:.1f} acres")
    
    # Regional parks
    print("\n   Regional Parks (75+ acres):")
    result = conn.execute(text("""
        SELECT name, land_area_acres
        FROM parks
        WHERE park_type = 'regional'
        ORDER BY land_area_acres DESC;
    """))
    
    for row in result:
        print(f"   - {row[0]}: {row[1]:.1f} acres")

print("\n" + "="*70)
print("PARK NAMES UPDATE COMPLETE")
print("="*70)
