"""
Add Polsby-Popper Compactness Scores to Parcels
================================================
Calculates and stores compactness scores for all parcels using pure Python.
This eliminates the need to calculate it on every API request.
"""

import os
import json
import math
from sqlalchemy import create_engine, text

print("="*70)
print("ADDING POLSBY-POPPER COMPACTNESS SCORES")
print("="*70)

# Database connection
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)

engine = create_engine(DATABASE_URL)

def calculate_polsby_popper(geometry_json: dict) -> float:
    """
    Calculate Polsby-Popper compactness score.
    
    PP = (4π × Area) / (Perimeter²)
    
    Returns:
        1.0 = perfect circle (very compact)
        <0.3 = very elongated/thin strip (roads/railroads)
    """
    try:
        # Get coordinates
        if geometry_json['type'] == 'Polygon':
            coords = geometry_json['coordinates'][0]
        elif geometry_json['type'] == 'MultiPolygon':
            coords = geometry_json['coordinates'][0][0]
        else:
            return 1.0
        
        if len(coords) < 3:
            return 1.0
        
        # Calculate area using shoelace formula
        area = 0
        for i in range(len(coords) - 1):
            area += coords[i][0] * coords[i + 1][1]
            area -= coords[i + 1][0] * coords[i][1]
        area = abs(area) / 2.0
        
        # Calculate perimeter
        perimeter = 0
        for i in range(len(coords) - 1):
            x1, y1 = coords[i][0], coords[i][1]
            x2, y2 = coords[i + 1][0], coords[i + 1][1]
            dx = x2 - x1
            dy = y2 - y1
            perimeter += (dx**2 + dy**2)**0.5
        
        # Polsby-Popper score
        if perimeter > 0 and area > 0:
            pp_score = (4 * math.pi * area) / (perimeter ** 2)
            return pp_score
        
        return 1.0  # Assume compact if calculation fails
        
    except Exception as e:
        print(f"  Error calculating PP: {e}")
        return 1.0  # Assume compact if error

# ============================================================================
# STEP 1: Add column if it doesn't exist
# ============================================================================

print("\n1. Adding polsby_popper_score column...")

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE parcels 
        ADD COLUMN IF NOT EXISTS polsby_popper_score NUMERIC;
    """))
    conn.commit()
    
print("   ✓ Column added")

# ============================================================================
# STEP 2: Get total count
# ============================================================================

print("\n2. Counting parcels to process...")

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM parcels WHERE geometry_geojson IS NOT NULL;"))
    total_parcels = result.scalar()
    
print(f"   ✓ Found {total_parcels:,} parcels with geometry")

# ============================================================================
# STEP 3: Calculate scores in batches
# ============================================================================

print("\n3. Calculating Polsby-Popper scores...")

BATCH_SIZE = 1000
offset = 0
processed = 0
updated = 0
errors = 0

while offset < total_parcels:
    # Fetch batch
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT parcel_id, geometry_geojson
            FROM parcels
            WHERE geometry_geojson IS NOT NULL
            ORDER BY id
            LIMIT {BATCH_SIZE} OFFSET {offset};
        """))
        
        parcels = result.fetchall()
    
    # Calculate scores for this batch
    updates = []
    
    for parcel_id, geom_json in parcels:
        try:
            geom = json.loads(geom_json)
            pp_score = calculate_polsby_popper(geom)
            updates.append({
                'parcel_id': parcel_id,
                'pp_score': pp_score
            })
        except Exception as e:
            errors += 1
            # Default to 1.0 (compact) if error
            updates.append({
                'parcel_id': parcel_id,
                'pp_score': 1.0
            })
    
    # Batch update
    with engine.connect() as conn:
        for update in updates:
            conn.execute(text("""
                UPDATE parcels
                SET polsby_popper_score = :pp_score
                WHERE parcel_id = :parcel_id;
            """), update)
        
        conn.commit()
    
    processed += len(parcels)
    updated += len(updates)
    offset += BATCH_SIZE
    
    # Progress update
    pct = (processed / total_parcels) * 100
    print(f"   Progress: {processed:,} / {total_parcels:,} ({pct:.1f}%)")

print(f"\n   ✓ Calculated scores for {updated:,} parcels")
if errors > 0:
    print(f"   ⚠️  {errors} errors (defaulted to 1.0)")

# ============================================================================
# STEP 4: Create index
# ============================================================================

print("\n4. Creating index on polsby_popper_score...")

with engine.connect() as conn:
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS parcels_polsby_popper_idx 
        ON parcels(polsby_popper_score);
    """))
    conn.commit()
    
print("   ✓ Index created")

# ============================================================================
# STEP 5: Show statistics
# ============================================================================

print("\n5. Compactness statistics:")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE polsby_popper_score < 0.3) as linear,
            COUNT(*) FILTER (WHERE polsby_popper_score >= 0.3 AND polsby_popper_score < 0.5) as elongated,
            COUNT(*) FILTER (WHERE polsby_popper_score >= 0.5 AND polsby_popper_score < 0.8) as rectangular,
            COUNT(*) FILTER (WHERE polsby_popper_score >= 0.8) as compact,
            AVG(polsby_popper_score) as avg_score,
            MIN(polsby_popper_score) as min_score,
            MAX(polsby_popper_score) as max_score
        FROM parcels
        WHERE polsby_popper_score IS NOT NULL;
    """))
    
    row = result.fetchone()
    
    print(f"\n   Total parcels: {row[0]:,}")
    print(f"   Linear/Roads (< 0.3):     {row[1]:,} ({row[1]/row[0]*100:.1f}%)")
    print(f"   Elongated (0.3-0.5):      {row[2]:,} ({row[2]/row[0]*100:.1f}%)")
    print(f"   Rectangular (0.5-0.8):    {row[3]:,} ({row[3]/row[0]*100:.1f}%)")
    print(f"   Compact (0.8+):           {row[4]:,} ({row[4]/row[0]*100:.1f}%)")
    print(f"\n   Average score: {row[5]:.3f}")
    print(f"   Min score: {row[6]:.3f}")
    print(f"   Max score: {row[7]:.3f}")

print("\n" + "="*70)
print("COMPACTNESS SCORES COMPLETE")
print("="*70)
print("\nNext step: Update api_server.py to use pre-calculated scores:")
print("  1. Remove calculate_polsby_popper() function call in loop")
print("  2. Add 'AND polsby_popper_score >= 0.3' to WHERE clause")
print("  3. Expect 2-3x speedup!")
