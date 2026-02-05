"""
Setup Bus Stops Table
======================
Creates the bus_stops table and imports medium-frequency stops from GTFS analysis.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text

print("="*70)
print("SETTING UP BUS STOPS TABLE")
print("="*70)

# Database connection
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)

engine = create_engine(DATABASE_URL)

# ============================================================================
# STEP 1: Create bus_stops table
# ============================================================================

print("\n1. Creating bus_stops table...")

with engine.connect() as conn:
    conn.execute(text("""
        DROP TABLE IF EXISTS bus_stops CASCADE;
        
        CREATE TABLE bus_stops (
            id SERIAL PRIMARY KEY,
            stop_id VARCHAR(50) UNIQUE NOT NULL,
            stop_name VARCHAR(255),
            stop_lat NUMERIC(10, 8),
            stop_lon NUMERIC(11, 8),
            peak_frequency NUMERIC(5, 2),
            am_frequency NUMERIC(5, 2),
            pm_frequency NUMERIC(5, 2),
            geometry_geojson TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create spatial index on lat/lon
        CREATE INDEX bus_stops_lat_lon_idx ON bus_stops(stop_lat, stop_lon);
        
        -- Create index on frequency for filtering
        CREATE INDEX bus_stops_frequency_idx ON bus_stops(peak_frequency);
    """))
    conn.commit()

print("   ✓ bus_stops table created")

# ============================================================================
# STEP 2: Load CSV data
# ============================================================================

print("\n2. Loading medium-frequency bus stops data...")

csv_file = 'bus_stop_data/denver_medium_frequency_bus_stops.csv'

if not os.path.exists(csv_file):
    print(f"\n   ✗ File not found: {csv_file}")
    print("   Please run analyze_bus_frequencies.py first!")
    exit(1)

bus_stops_df = pd.read_csv(csv_file)
print(f"   ✓ Loaded {len(bus_stops_df):,} bus stops from CSV")

# ============================================================================
# STEP 3: Import data to database
# ============================================================================

print("\n3. Importing bus stops to database...")

imported = 0
errors = 0

with engine.connect() as conn:
    for _, stop in bus_stops_df.iterrows():
        try:
            # Create GeoJSON point
            geojson = {
                "type": "Point",
                "coordinates": [float(stop['stop_lon']), float(stop['stop_lat'])]
            }
            
            conn.execute(text("""
                INSERT INTO bus_stops (
                    stop_id, stop_name, stop_lat, stop_lon,
                    peak_frequency, am_frequency, pm_frequency,
                    geometry_geojson
                ) VALUES (
                    :stop_id, :stop_name, :stop_lat, :stop_lon,
                    :peak_frequency, :am_frequency, :pm_frequency,
                    :geometry_geojson
                )
            """), {
                'stop_id': stop['stop_id'],
                'stop_name': stop['stop_name'],
                'stop_lat': float(stop['stop_lat']),
                'stop_lon': float(stop['stop_lon']),
                'peak_frequency': float(stop['peak_frequency']),
                'am_frequency': float(stop['am_trips_per_hour']),
                'pm_frequency': float(stop['pm_trips_per_hour']),
                'geometry_geojson': str(geojson)
            })
            
            imported += 1
            
            if imported % 100 == 0:
                print(f"   Progress: {imported:,} stops imported...")
        
        except Exception as e:
            errors += 1
            print(f"   ✗ Error importing stop {stop['stop_id']}: {e}")
    
    conn.commit()

print(f"\n   ✓ Imported {imported:,} bus stops")
if errors > 0:
    print(f"   ⚠️  {errors} errors encountered")

# ============================================================================
# STEP 4: Verify data
# ============================================================================

print("\n4. Verifying data...")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total_stops,
            MIN(peak_frequency) as min_freq,
            AVG(peak_frequency) as avg_freq,
            MAX(peak_frequency) as max_freq
        FROM bus_stops;
    """))
    
    row = result.fetchone()
    print(f"\n   Total stops: {row[0]:,}")
    print(f"   Frequency range: {row[1]:.1f} - {row[3]:.1f} trips/hour")
    print(f"   Average frequency: {row[2]:.1f} trips/hour")

# ============================================================================
# STEP 5: Add distance columns to parcels table
# ============================================================================

print("\n5. Adding distance column to parcels table...")

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE parcels 
        ADD COLUMN IF NOT EXISTS distance_to_med_freq_bus NUMERIC;
        
        -- Create index for performance
        CREATE INDEX IF NOT EXISTS parcels_distance_med_freq_bus_idx 
        ON parcels(distance_to_med_freq_bus) 
        WHERE distance_to_med_freq_bus IS NOT NULL;
    """))
    conn.commit()

print("   ✓ distance_to_med_freq_bus column added to parcels")

print("\n" + "="*70)
print("BUS STOPS TABLE SETUP COMPLETE")
print("="*70)
print(f"\nNext step:")
print(f"Run calculate_bus_stop_distances.py to calculate distances from parcels to bus stops")
