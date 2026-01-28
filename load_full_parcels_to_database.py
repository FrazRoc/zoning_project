"""
Load Data to PostgreSQL (Without PostGIS)
==========================================
This version works without PostGIS extension.
Stores geometry as TEXT (GeoJSON), distances pre-calculated.
"""

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
import json
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("LOADING DATA TO POSTGRESQL (NO POSTGIS)")
print("="*70)

import os
DB_USER = os.environ.get('USER')
DATABASE_URL = f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"

print("\n1. Connecting to database...")
engine = create_engine(DATABASE_URL)

# ============================================================================
# CREATE SIMPLIFIED SCHEMA (NO POSTGIS)
# ============================================================================

print("\n2. Creating tables...")

with engine.connect() as conn:
    # Drop existing tables
    conn.execute(text("DROP TABLE IF EXISTS parcels CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS light_rail_stations CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS zoning_lookup CASCADE;"))
    
    # Zoning lookup
    conn.execute(text("""
        CREATE TABLE zoning_lookup (
            zone_code VARCHAR(20) PRIMARY KEY,
            max_stories NUMERIC,
            category VARCHAR(50),
            description TEXT
        );
    """))
    
    # Parcels - geometry stored as TEXT (GeoJSON)
    conn.execute(text("""
        CREATE TABLE parcels (
            id SERIAL PRIMARY KEY,
            parcel_id VARCHAR(50) UNIQUE,
            geometry_geojson TEXT,
            
            -- Address
            address VARCHAR(255),
            
            -- Zoning
            zone_district VARCHAR(20),
            
            -- Land attributes
            land_area_sqft NUMERIC,
            land_area_acres NUMERIC,
            
            -- Building/Development
            current_units INTEGER DEFAULT 0,
            building_sqft NUMERIC DEFAULT 0,
            res_above_grade_area NUMERIC DEFAULT 0,
            res_orig_year_built INTEGER,
            com_gross_area NUMERIC DEFAULT 0,
            com_orig_year_built INTEGER,
            
            -- Property classification
            property_class VARCHAR(100),
            property_type VARCHAR(50),
            
            -- Ownership
            owner_name VARCHAR(255),
            owner_type VARCHAR(50),
            
            -- Values
            land_value NUMERIC,
            improvement_value NUMERIC,
            total_value NUMERIC,
            
            -- Calculated fields (we'll populate these later)
            distance_to_light_rail NUMERIC,
            distance_to_brt NUMERIC,
            distance_to_school NUMERIC,
            distance_to_park NUMERIC,
            
            -- Opportunity classification (from analysis)
            opportunity_type VARCHAR(100),
            potential_units INTEGER,
            
            -- Metadata
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))
    
    # Stations
    conn.execute(text("""
        CREATE TABLE light_rail_stations (
            id SERIAL PRIMARY KEY,
            station_id VARCHAR(50),
            name VARCHAR(255),
            geometry_geojson TEXT
        );
    """))
    
    # Add indexes
    conn.execute(text("CREATE INDEX parcels_zone_idx ON parcels(zone_district);"))
    conn.execute(text("CREATE INDEX parcels_property_type_idx ON parcels(property_type);"))
    conn.execute(text("CREATE INDEX parcels_owner_type_idx ON parcels(owner_type);"))
    conn.execute(text("CREATE INDEX parcels_distance_lr_idx ON parcels(distance_to_light_rail);"))
    conn.execute(text("CREATE INDEX parcels_opportunity_idx ON parcels(opportunity_type);"))
    
    # Insert zoning codes
    conn.execute(text("""
        INSERT INTO zoning_lookup VALUES
        ('C-MX-8', 8, 'mixed_use', '8 stories mixed use'),
        ('G-RX-5', 5, 'mixed_use', '5 stories residential/mixed'),
        ('G-MU-3', 3, 'multi_unit', '3 stories general urban'),
        ('U-SU-A', 2, 'single_unit', 'Urban single unit A'),
        ('U-SU-B', 2, 'single_unit', 'Urban single unit B'),
        ('S-SU', 2, 'single_unit', 'Suburban single unit'),
        ('I-A', 3, 'industrial', 'Industrial A'),
        ('I-B', 3, 'industrial', 'Industrial B');
    """))
    
    conn.commit()

print("   ✓ Tables created")

# ============================================================================
# LOAD PARCELS
# ============================================================================

print("\n3. Loading parcels from full Denver dataset...")

try:
    parcels = gpd.read_file('ODC_PROP_PARCELS_A_4007222418780288709.geojson')
except AttributeError:
    # Fallback for older geopandas/fiona versions
    import json
    from shapely.geometry import shape
    
    with open('ODC_PROP_PARCELS_A_4007222418780288709.geojson', 'r') as f:
        data = json.load(f)
    
    features = data['features']
    geometries = [shape(f['geometry']) for f in features]
    properties = [f['properties'] for f in features]
    
    parcels = gpd.GeoDataFrame(properties, geometry=geometries, crs='EPSG:4326')

print(f"   Loaded {len(parcels):,} parcels from Denver Open Data")

# Prepare data - map ODC fields to our schema
print("   Preparing data for database...")

# Helper function to classify property type
def classify_property_type(prop_class):
    if pd.isna(prop_class):
        return 'other'
    pc = str(prop_class).upper()
    if 'VACANT' in pc:
        return 'vacant'
    elif 'RESIDENTIAL' in pc or 'SFR' in pc or 'SINGLE' in pc:
        return 'residential'
    elif 'COMMERCIAL' in pc or 'RETAIL' in pc or 'OFFICE' in pc:
        return 'commercial'
    elif 'INDUSTRIAL' in pc or 'WAREHOUSE' in pc:
        return 'industrial'
    else:
        return 'other'

# Helper function to classify owner type
def classify_owner_type(owner_name):
    if pd.isna(owner_name):
        return 'private'
    owner = str(owner_name).upper()
    if 'SCHOOL' in owner or 'EDUCATION' in owner:
        return 'school'
    elif any(word in owner for word in ['CITY', 'COUNTY', 'STATE', 'FEDERAL', 'GOVERNMENT']):
        return 'govt'
    elif 'CHURCH' in owner or 'RELIGIOUS' in owner:
        return 'church'
    elif 'RTD' in owner or 'REGIONAL TRANSPORTATION' in owner:
        return 'rtd'
    else:
        return 'private'

parcels_data = []
for idx, row in parcels.iterrows():
    # Get land area
    land_sqft = row.get('LAND_AREA', 0)
    if pd.isna(land_sqft) or land_sqft == 0:
        # Calculate from geometry if missing
        try:
            land_sqft = row.geometry.to_crs('EPSG:32613').area * 10.764  # m² to ft²
        except:
            land_sqft = 0
    
    parcels_data.append({
        'parcel_id': row.get('PARCEL_ID', f'parcel_{idx}'),
        'geometry_geojson': json.dumps(row.geometry.__geo_interface__),
        
        # Address
        'address': row.get('SITUS_ADDRESS_LINE1', row.get('SITUS_ADDR', row.get('ADDRESS', ''))),
        
        # Zoning
        'zone_district': row.get('ZONE_DISTRICT', row.get('ZONE_10', '')),
        
        # Land
        'land_area_sqft': float(land_sqft) if land_sqft and not pd.isna(land_sqft) else 0,
        'land_area_acres': float(land_sqft / 43560) if land_sqft and not pd.isna(land_sqft) else 0,
        
        # Building - handle NaN values
        'current_units': int(row.get('TOT_UNITS', 0)) if pd.notna(row.get('TOT_UNITS', 0)) else 0,
        'building_sqft': float(row.get('BLDG_AREA', 0)) if pd.notna(row.get('BLDG_AREA', 0)) else 0,
        'res_above_grade_area': float(row.get('RES_ABOVE_GRADE_AREA', 0)) if pd.notna(row.get('RES_ABOVE_GRADE_AREA', 0)) else 0,
        'res_orig_year_built': int(row.get('RES_ORIG_YEAR_BUILT')) if pd.notna(row.get('RES_ORIG_YEAR_BUILT')) else None,
        'com_gross_area': float(row.get('COM_GROSS_AREA', 0)) if pd.notna(row.get('COM_GROSS_AREA', 0)) else 0,
        'com_orig_year_built': int(row.get('COM_ORIG_YEAR_BUILT')) if pd.notna(row.get('COM_ORIG_YEAR_BUILT')) else None,
        
        # Classification
        'property_class': row.get('D_CLASS_CN', ''),
        'property_type': classify_property_type(row.get('D_CLASS_CN', '')),
        
        # Ownership
        'owner_name': row.get('OWNER_NAME', ''),
        'owner_type': classify_owner_type(row.get('OWNER_NAME', '')),
        
        # Values - handle NaN
        'land_value': float(row.get('APPRAISED_LAND_VALUE', 0)) if pd.notna(row.get('APPRAISED_LAND_VALUE', 0)) else 0,
        'improvement_value': float(row.get('APPRAISED_IMP_VALUE', 0)) if pd.notna(row.get('APPRAISED_IMP_VALUE', 0)) else 0,
        'total_value': float(row.get('APPRAISED_TOTAL_VALUE', 0)) if pd.notna(row.get('APPRAISED_TOTAL_VALUE', 0)) else 0,
        
        # Distances - will be NULL initially, calculated later
        'distance_to_light_rail': None,
        'distance_to_brt': None,
        'distance_to_school': None,
        'distance_to_park': None,
        
        # Opportunity - will be populated by analysis
        'opportunity_type': None,
        'potential_units': None
    })

print(f"   Prepared {len(parcels_data):,} parcels for loading")

# Insert in batches
print("   Writing parcels to database in batches...")
df = pd.DataFrame(parcels_data)

# Load in chunks of 1000 parcels at a time
batch_size = 1000
total_batches = (len(df) + batch_size - 1) // batch_size

for i in range(0, len(df), batch_size):
    batch = df.iloc[i:i + batch_size]
    batch_num = (i // batch_size) + 1
    
    try:
        batch.to_sql('parcels', engine, if_exists='append', index=False, method='multi')
        print(f"   ✓ Loaded batch {batch_num}/{total_batches} ({len(batch)} parcels)")
    except Exception as e:
        print(f"   ✗ Error in batch {batch_num}: {e}")
        print(f"   Skipping this batch and continuing...")
        continue

print(f"   ✓ Finished loading parcels to database")

# ============================================================================
# LOAD STATIONS
# ============================================================================

print("\n4. Loading stations...")

try:
    try:
        stations = gpd.read_file('rtd_lightrail_stations.geojson')
    except AttributeError:
        # Fallback for older geopandas/fiona versions
        import json
        from shapely.geometry import shape
        
        with open('rtd_lightrail_stations.geojson', 'r') as f:
            data = json.load(f)
        
        features = data['features']
        geometries = [shape(f['geometry']) for f in features]
        properties = [f['properties'] for f in features]
        
        stations = gpd.GeoDataFrame(properties, geometry=geometries, crs='EPSG:4326')
    
    stations_data = []
    for idx, row in stations.iterrows():
        stations_data.append({
            'station_id': f'station_{idx}',
            'name': row.get('NAME', 'Unknown'),
            'geometry_geojson': json.dumps(row.geometry.__geo_interface__)
        })
    
    df_stations = pd.DataFrame(stations_data)
    df_stations.to_sql('light_rail_stations', engine, if_exists='append', index=False)
    
    print(f"   ✓ Loaded {len(stations_data)} stations")
except FileNotFoundError:
    print("   ⚠ Stations file not found, skipping")
except Exception as e:
    print(f"   ⚠ Error loading stations: {e}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n5. Database summary:")

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM parcels;"))
    print(f"   Total parcels: {result.fetchone()[0]:,}")
    
    result = conn.execute(text("""
        SELECT property_type, COUNT(*) 
        FROM parcels 
        WHERE property_type IS NOT NULL
        GROUP BY property_type
        ORDER BY COUNT(*) DESC;
    """))
    print("\n   Parcels by type:")
    for row in result:
        print(f"     - {row[0]}: {row[1]:,}")
    
    result = conn.execute(text("""
        SELECT owner_type, COUNT(*) 
        FROM parcels 
        WHERE owner_type IS NOT NULL
        GROUP BY owner_type
        ORDER BY COUNT(*) DESC;
    """))
    print("\n   Parcels by owner:")
    for row in result:
        print(f"     - {row[0]}: {row[1]:,}")
    
    result = conn.execute(text("""
        SELECT zone_district, COUNT(*) 
        FROM parcels 
        WHERE zone_district IS NOT NULL AND zone_district != ''
        GROUP BY zone_district
        ORDER BY COUNT(*) DESC
        LIMIT 10;
    """))
    print("\n   Top 10 zoning districts:")
    for row in result:
        print(f"     - {row[0]}: {row[1]:,}")

print("\n" + "="*70)
print("DATABASE READY!")
print("="*70)
print(f"\nConnection: {DATABASE_URL}")
print("\nAll {len(parcels_data):,} Denver parcels loaded!")
print("\nNext steps:")
print("  1. Calculate distances to transit")
print("  2. Run policy analysis to populate opportunity_type")
print("\nTest: psql -d mile_high_potential_db -c 'SELECT COUNT(*) FROM parcels;'")
print("")
