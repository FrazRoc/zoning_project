"""
Truncate GeoJSON Coordinate Precision in Database
==================================================
Reduces geometry_geojson coordinate precision from ~15 decimals to 6 decimals.
6 decimal places ≈ ~4 inch accuracy — more than enough for parcel visualization.

Run this ONCE against your database. It updates parcels and parks tables in place.

Usage:
    python truncate_geojson_precision.py

Expected result: ~40-50% reduction in geometry_geojson column size.
"""

import json
import os
import time
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{os.environ.get('USER')}@localhost:5432/mile_high_potential_db"
)

PRECISION = 6  # decimal places

def truncate_coords(coords, precision=PRECISION):
    """Recursively truncate coordinate precision."""
    if isinstance(coords[0], (int, float)):
        return [round(c, precision) for c in coords]
    else:
        return [truncate_coords(c, precision) for c in coords]

def simplify_geometry_json(geojson_str, precision=PRECISION):
    """Parse, truncate, and re-serialize a GeoJSON geometry string."""
    geom = json.loads(geojson_str)
    geom['coordinates'] = truncate_coords(geom['coordinates'], precision)
    # Use separators to remove unnecessary whitespace
    return json.dumps(geom, separators=(',', ':'))

def migrate_table(engine, table_name, id_column, geom_column='geometry_geojson'):
    """Truncate coordinate precision for all rows in a table."""
    
    with engine.connect() as conn:
        # 1. Check current size
        result = conn.execute(text(f"""
            SELECT 
                COUNT(*) as total,
                ROUND(SUM(LENGTH({geom_column})) / 1024.0 / 1024.0, 2) as total_mb
            FROM {table_name}
            WHERE {geom_column} IS NOT NULL
        """))
        row = result.fetchone()
        total_rows = row[0]
        before_mb = row[1]
        print(f"\n{'='*60}")
        print(f"Table: {table_name}")
        print(f"Rows with geometry: {total_rows:,}")
        print(f"Current {geom_column} size: {before_mb} MB")
        print(f"{'='*60}")
        
        if total_rows == 0:
            print("No rows to update, skipping.")
            return
        
        # 2. Process in batches
        BATCH_SIZE = 1000
        updated = 0
        start = time.time()
        
        # Fetch all rows
        rows = conn.execute(text(f"""
            SELECT {id_column}, {geom_column} 
            FROM {table_name} 
            WHERE {geom_column} IS NOT NULL
        """)).fetchall()
        
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            
            for row in batch:
                row_id = row[0]
                old_geom = row[1]
                
                try:
                    new_geom = simplify_geometry_json(old_geom, PRECISION)
                    
                    conn.execute(
                        text(f"UPDATE {table_name} SET {geom_column} = :geom WHERE {id_column} = :id"),
                        {"geom": new_geom, "id": row_id}
                    )
                    updated += 1
                except Exception as e:
                    print(f"  ⚠️  Skipped {row_id}: {e}")
            
            conn.commit()
            elapsed = time.time() - start
            pct = (i + len(batch)) / len(rows) * 100
            print(f"  Processed {i + len(batch):,}/{len(rows):,} ({pct:.0f}%) - {elapsed:.1f}s")
        
        # 3. Check new size
        result = conn.execute(text(f"""
            SELECT ROUND(SUM(LENGTH({geom_column})) / 1024.0 / 1024.0, 2) as total_mb
            FROM {table_name}
            WHERE {geom_column} IS NOT NULL
        """))
        after_mb = result.fetchone()[0]
        
        savings = before_mb - after_mb
        pct_savings = (savings / before_mb * 100) if before_mb > 0 else 0
        
        print(f"\n✅ {table_name} complete!")
        print(f"   Updated: {updated:,} rows")
        print(f"   Before:  {before_mb} MB")
        print(f"   After:   {after_mb} MB")
        print(f"   Saved:   {savings:.2f} MB ({pct_savings:.1f}%)")

def main():
    print("Truncating GeoJSON coordinate precision to 6 decimal places...")
    print(f"Database: {DATABASE_URL.split('@')[-1]}")  # Print DB host only, not credentials
    
    engine = create_engine(DATABASE_URL)
    
    # Migrate parcels table
    migrate_table(engine, 'parcels', 'parcel_id', 'geometry_geojson')
    
    # Migrate parks table  
    migrate_table(engine, 'parks', 'formal_name', 'geometry')
    
    print(f"\n{'='*60}")
    print("🎉 Done! Coordinate precision truncated.")
    print("You can now remove the runtime simplify_geometry() calls from api_server.py")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
