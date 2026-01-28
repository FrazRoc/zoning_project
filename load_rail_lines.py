"""
Load RTD Light Rail Lines from local GeoJSON file into PostgreSQL database
"""
import json
import os
from sqlalchemy import create_engine, text

print("="*70)
print("LOADING RTD LIGHT RAIL LINES")
print("="*70)

# Load from local file
rail_lines_file = 'rtd_lightrail_lines.geojson'

print(f"\n1. Loading rail line data from {rail_lines_file}...")
with open(rail_lines_file, 'r') as f:
    lines_geojson = json.load(f)

print(f"   ✓ Loaded {len(lines_geojson.get('features', []))} line segments")

# Connect to database
DB_USER = os.environ.get('USER')
DATABASE_URL = f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
print("\n2. Connecting to database...")
engine = create_engine(DATABASE_URL)

# Create table for rail lines
print("\n3. Creating light_rail_lines table...")
with engine.connect() as conn:
    conn.execute(text("""
        DROP TABLE IF EXISTS light_rail_lines CASCADE;
        
        CREATE TABLE light_rail_lines (
            id SERIAL PRIMARY KEY,
            route VARCHAR(50),
            type VARCHAR(50),
            name VARCHAR(100),
            geometry JSONB
        );
        
        CREATE INDEX idx_rail_lines_route ON light_rail_lines(route);
    """))
    conn.commit()
print("   ✓ Table created")

# Insert rail line segments
print("\n4. Inserting rail line segments...")
inserted = 0
with engine.connect() as conn:
    for feature in lines_geojson['features']:
        props = feature['properties']
        geom = feature['geometry']
        
        conn.execute(text("""
            INSERT INTO light_rail_lines (route, type, name, geometry)
            VALUES (:route, :type, :name, :geometry)
        """), {
            'route': props.get('ROUTE'),
            'type': props.get('TYPE'),
            'name': props.get('NAME'),
            'geometry': json.dumps(geom)
        })
        inserted += 1
    
    conn.commit()
print(f"   ✓ Inserted {inserted} rail line segments")

# Show summary
print("\n5. Rail lines summary:")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT route, COUNT(*) as segment_count
        FROM light_rail_lines
        WHERE route IS NOT NULL
        GROUP BY route
        ORDER BY route
    """))
    for row in result:
        print(f"   - {row[0]}: {row[1]} segments")

print("\n" + "="*70)
print("✓ RAIL LINES LOADED SUCCESSFULLY")
print("="*70)