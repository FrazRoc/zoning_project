"""
Check and Add Database Indexes for Performance
===============================================
Checks existing indexes and adds missing ones for distance columns.
"""

import os
from sqlalchemy import create_engine, text

print("="*70)
print("CHECKING DATABASE INDEXES")
print("="*70)

# Database connection
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)

engine = create_engine(DATABASE_URL)

# ============================================================================
# STEP 1: Check existing indexes on parcels table
# ============================================================================

print("\n1. Checking existing indexes on parcels table...")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = 'parcels'
        ORDER BY indexname;
    """))
    
    indexes = result.fetchall()
    
    print(f"\n   Found {len(indexes)} indexes:")
    for idx_name, idx_def in indexes:
        print(f"   ✓ {idx_name}")
        # Show definition for distance-related indexes
        if 'distance' in idx_name.lower():
            print(f"      {idx_def}")

# ============================================================================
# STEP 2: Check if critical distance indexes exist
# ============================================================================

print("\n2. Checking critical distance column indexes...")

critical_columns = [
    'distance_to_light_rail',
    'distance_to_regional_park',
    'distance_to_community_park',
    'distance_to_brt',
    'polsby_popper_score'
]

existing_index_columns = []
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            a.attname as column_name
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = 'parcels'::regclass
        AND a.attname IN ('distance_to_light_rail', 'distance_to_regional_park', 
                          'distance_to_community_park', 'distance_to_brt', 
                          'polsby_popper_score');
    """))
    
    for row in result:
        existing_index_columns.append(row[0])

print("\n   Index status:")
for col in critical_columns:
    if col in existing_index_columns:
        print(f"   ✓ {col} - INDEXED")
    else:
        print(f"   ✗ {col} - MISSING")

# ============================================================================
# STEP 3: Add missing indexes
# ============================================================================

print("\n3. Adding missing indexes...")

indexes_to_add = []

with engine.connect() as conn:
    # Check and add each critical index
    for col in critical_columns:
        if col not in existing_index_columns:
            index_name = f"idx_parcels_{col}"
            
            print(f"\n   Creating index: {index_name}...")
            
            try:
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON parcels({col})
                    WHERE {col} IS NOT NULL;
                """))
                conn.commit()
                print(f"   ✓ {index_name} created")
                indexes_to_add.append(index_name)
            except Exception as e:
                print(f"   ✗ Failed to create {index_name}: {e}")

if not indexes_to_add:
    print("\n   ✓ All indexes already exist!")

# ============================================================================
# STEP 4: Check index sizes and statistics
# ============================================================================

print("\n4. Index sizes and statistics:")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public' 
        AND relname = 'parcels'
        ORDER BY pg_relation_size(indexrelid) DESC
        LIMIT 20;
    """))
    
    print("\n   Top indexes by size:")
    for idx_name, size in result:
        print(f"   {idx_name}: {size}")

# ============================================================================
# STEP 5: Analyze table to update statistics
# ============================================================================

print("\n5. Analyzing parcels table to update query planner statistics...")

with engine.connect() as conn:
    conn.execute(text("ANALYZE parcels;"))
    conn.commit()
    
print("   ✓ Table analyzed")

# ============================================================================
# STEP 6: Show query planner estimates
# ============================================================================

print("\n6. Sample query plans:")

test_queries = [
    ("TOD Query", "distance_to_light_rail <= 1500 AND polsby_popper_score >= 0.3"),
    ("POD-Regional Query", "distance_to_regional_park <= 750 AND polsby_popper_score >= 0.3"),
    ("POD-Community Query", "distance_to_community_park <= 250 AND polsby_popper_score >= 0.3")
]

with engine.connect() as conn:
    for name, where_clause in test_queries:
        result = conn.execute(text(f"""
            EXPLAIN 
            SELECT COUNT(*) 
            FROM parcels 
            WHERE {where_clause};
        """))
        
        print(f"\n   {name}:")
        for row in result:
            plan_line = row[0]
            if 'Index' in plan_line or 'Scan' in plan_line:
                print(f"   {plan_line}")

print("\n" + "="*70)
print("INDEX CHECK COMPLETE")
print("="*70)
print("\nNext steps:")
print("  1. If new indexes were created, restart your API server")
print("  2. Test query performance and check timing")
print("  3. Compare before/after database query times")
