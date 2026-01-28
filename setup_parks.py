"""
Identify and Classify Denver Parks for POD (Park-Oriented Development)
========================================================================
Extracts parks from parcels table and classifies them by size:
- Community Parks: OS-A zoned, city-owned, 10-75 acres
- Regional Parks: OS-A zoned, city-owned, 75+ acres
"""

import os
from sqlalchemy import create_engine, text
import json

print("="*70)
print("IDENTIFYING DENVER PARKS FROM PARCELS")
print("="*70)

# Database connection
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)

engine = create_engine(DATABASE_URL)

# ============================================================================
# STEP 1: Create parks table
# ============================================================================

print("\n1. Creating parks table...")

with engine.connect() as conn:
    # Drop existing table
    conn.execute(text("DROP TABLE IF EXISTS parks CASCADE;"))
    
    # Create parks table
    conn.execute(text("""
        CREATE TABLE parks (
            id SERIAL PRIMARY KEY,
            park_id VARCHAR(50) UNIQUE,
            name VARCHAR(255),
            park_type VARCHAR(50), -- 'community' or 'regional'
            geometry_geojson TEXT,
            land_area_acres NUMERIC,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))
    
    # Create index
    conn.execute(text("CREATE INDEX parks_type_idx ON parks(park_type);"))
    
    conn.commit()
    print("   ✓ Parks table created")

# ============================================================================
# STEP 2: Query and classify parks from parcels
# ============================================================================

print("\n2. Querying parcels for OS-A zoned city-owned land...")

with engine.connect() as conn:
    # Find all OS-A parcels owned by city/govt
    result = conn.execute(text("""
        SELECT 
            parcel_id,
            address,
            zone_district,
            owner_name,
            owner_type,
            land_area_acres,
            geometry_geojson
        FROM parcels
        WHERE zone_district LIKE 'OS-%'
        AND owner_type IN ('govt', 'city')
        AND land_area_acres >= 10
        ORDER BY land_area_acres DESC;
    """))
    
    parcels = result.fetchall()
    print(f"   ✓ Found {len(parcels)} OS-zoned government parcels >= 10 acres")

# ============================================================================
# STEP 3: Classify and insert parks
# ============================================================================

print("\n3. Classifying and inserting parks...")

community_parks = 0
regional_parks = 0
skipped = 0

with engine.connect() as conn:
    for row in parcels:
        parcel_id = row[0]
        address = row[1] or "Unnamed Park"
        zone_district = row[2]
        owner_name = row[3]
        owner_type = row[4]
        acres = float(row[5]) if row[5] else 0
        geometry_geojson = row[6]
        
        # Skip if too small
        if acres < 10:
            skipped += 1
            continue
        
        # Classify by size
        if acres >= 75:
            park_type = 'regional'
            regional_parks += 1
        elif acres >= 10:
            park_type = 'community'
            community_parks += 1
        else:
            skipped += 1
            continue
        
        # Create park name from address or owner name
        park_name = address
        if park_name.startswith('0 ') or park_name == 'Unnamed Park':
            park_name = owner_name or f"Park {parcel_id}"
        
        # Insert into parks table
        conn.execute(text("""
            INSERT INTO parks (park_id, name, park_type, geometry_geojson, land_area_acres)
            VALUES (:park_id, :name, :park_type, :geometry, :acres)
            ON CONFLICT (park_id) DO NOTHING;
        """), {
            'park_id': parcel_id,
            'name': park_name,
            'park_type': park_type,
            'geometry': geometry_geojson,
            'acres': acres
        })
    
    conn.commit()

print(f"   ✓ Community parks (10-75 acres): {community_parks}")
print(f"   ✓ Regional parks (75+ acres): {regional_parks}")
print(f"   ✓ Skipped (< 10 acres): {skipped}")

# ============================================================================
# STEP 4: Show summary
# ============================================================================

print("\n4. Parks summary:")

with engine.connect() as conn:
    # Community parks
    result = conn.execute(text("""
        SELECT COUNT(*), AVG(land_area_acres), MIN(land_area_acres), MAX(land_area_acres)
        FROM parks
        WHERE park_type = 'community';
    """))
    row = result.fetchone()
    print(f"\n   Community Parks:")
    print(f"   - Count: {row[0]}")
    print(f"   - Average size: {row[1]:.1f} acres")
    print(f"   - Size range: {row[2]:.1f} - {row[3]:.1f} acres")
    
    # Regional parks
    result = conn.execute(text("""
        SELECT COUNT(*), AVG(land_area_acres), MIN(land_area_acres), MAX(land_area_acres)
        FROM parks
        WHERE park_type = 'regional';
    """))
    row = result.fetchone()
    print(f"\n   Regional Parks:")
    print(f"   - Count: {row[0]}")
    print(f"   - Average size: {row[1]:.1f} acres")
    print(f"   - Size range: {row[2]:.1f} - {row[3]:.1f} acres")
    
    # Show largest parks
    print(f"\n   Largest Parks:")
    result = conn.execute(text("""
        SELECT name, park_type, land_area_acres
        FROM parks
        ORDER BY land_area_acres DESC
        LIMIT 10;
    """))
    
    for row in result:
        print(f"   - {row[0]}: {row[2]:.1f} acres ({row[1]})")

print("\n" + "="*70)
print("PARKS SETUP COMPLETE")
print("="*70)
print("\nNext steps:")
print("1. Run distance calculations to parcels")
print("2. Update API to handle POD policy")
print("3. Add park buffer visualization to map")
