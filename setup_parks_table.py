import os
from sqlalchemy import create_engine, text, Table, Column, Integer, String, Float, MetaData
import json

# Database connection
DB_USER = os.environ.get('USER')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f"postgresql://{DB_USER}@localhost:5432/mile_high_potential_db"
)
engine = create_engine(DATABASE_URL)

# Define the table schema
metadata = MetaData()

parks_table = Table(
    'parks',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String),
    Column('formal_name', String),
    Column('park_type', String),
    Column('park_class', String),
    Column('ballot_park_type', String),
    Column('land_area_acres', Float),
    Column('address_line1', String),
    Column('address_line2', String),
    Column('city', String),
    Column('state', String),
    Column('zip', String),
    Column('latitude', Float),
    Column('longitude', Float),
    Column('facilities', String),
    Column('geometry', String)  # Storing geometry as text/JSON
)

def create_table():
    """Drop existing table if it exists and create new table"""
    with engine.connect() as conn:
        # Drop table if exists
        conn.execute(text("DROP TABLE IF EXISTS parks CASCADE"))
        conn.commit()
        
        # Create table
        metadata.create_all(engine)
        print("Table 'parks' created successfully")

def load_data(geojson_file):
    """Load data from GeoJSON file into parks table"""
    with open(geojson_file, 'r') as f:
        data = json.load(f)
    
    features = data['features']
    print(f"Found {len(features)} features to load")
    
    with engine.connect() as conn:
        
        def classify_ballot_type(p_class, acres):
            p_class = str(p_class).lower() if p_class else ""
            if p_class == 'regional' and acres > 75:
                return 'regional'
            elif p_class in ['regional', 'neighborhood', 'community', 'linear'] and 10 <= acres <= 75:
                return 'community'
            return 'ineligible'

        for feature in features:
            props = feature['properties']
            geometry = json.dumps(feature['geometry'])  # Convert geometry to JSON string
            
            # Insert data
            insert_query = text("""
                INSERT INTO parks (
                    name, formal_name, park_type, park_class, ballot_park_type,
                    land_area_acres, address_line1, address_line2,
                    city, state, zip, latitude, longitude, facilities, geometry
                ) VALUES (
                    :name, :formal_name, :park_type, :park_class, :ballot_park_type,
                    :land_area_acres, :address_line1, :address_line2,
                    :city, :state, :zip, :latitude, :longitude, :facilities, :geometry
                )
            """)
            
            conn.execute(insert_query, {
                'name': props.get('LOCATION'),
                'formal_name': props.get('FORMAL_NAME'),
                'park_type': props.get('PARK_TYPE'),
                'park_class': props.get('PARK_CLASS'),
                'ballot_park_type': classify_ballot_type(props.get('PARK_CLASS'), props.get('GIS_ACRES')),
                'land_area_acres': props.get('GIS_ACRES'),
                'address_line1': props.get('ADDRESS_LINE1'),
                'address_line2': props.get('ADDRESS_LINE2'),
                'city': props.get('CITY'),
                'state': props.get('STATE'),
                'zip': props.get('ZIP'),
                'latitude': props.get('LATITUDE'),
                'longitude': props.get('LONGITUDE'),
                'facilities': props.get('FACILITIES'),
                'geometry': geometry
            })
        
        conn.commit()
        print(f"Successfully loaded {len(features)} records into parks table")

def verify_data():
    """Verify the data was loaded correctly"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM parks"))
        count = result.scalar()
        print(f"\nVerification: Total records in parks table: {count}")
        
        # Show a sample record
        result = conn.execute(text("SELECT id, name, formal_name, park_type, park_class, ballot_park_type, land_area_acres FROM parks LIMIT 10"))
        print("\nSample records:")
        for row in result:
            print(f"  ID: {row[0]}, Location: {row[1]}, Name: {row[2]},  Type: {row[3]}, Class: {row[4]}, Ballot: {row[5]}, Acres: {row[6]}")

if __name__ == "__main__":
    geojson_file = 'ODC_PARK_PARKLAND_A_-209021382844435935.geojson'
    
    print("Creating parks table...")
    create_table()
    
    print("\nLoading data from GeoJSON file...")
    load_data(geojson_file)
    
    print("\nVerifying data...")
    verify_data()
    
    print("\n✓ Complete!")