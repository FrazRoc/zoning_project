-- Mile High Potential Database Schema
-- PostgreSQL + PostGIS
-- ============================================================================

-- ============================================================================
-- ZONING LOOKUP TABLE
-- ============================================================================

CREATE TABLE zoning_lookup (
    zone_code VARCHAR(20) PRIMARY KEY,
    max_stories INTEGER,
    category VARCHAR(50),
    description TEXT
);

-- Seed common Denver zoning codes
INSERT INTO zoning_lookup (zone_code, max_stories, category, description) VALUES
    -- Downtown
    ('D-C', 20, 'downtown', 'Downtown Core'),
    ('D-AS', 16, 'downtown', 'Downtown Arapahoe Square'),
    ('D-GT', 12, 'downtown', 'Downtown Gateway'),
    
    -- Mixed Use
    ('C-MX-3', 3, 'mixed_use', '3 stories mixed use'),
    ('C-MX-5', 5, 'mixed_use', '5 stories mixed use'),
    ('C-MX-8', 8, 'mixed_use', '8 stories mixed use'),
    ('C-MX-12', 12, 'mixed_use', '12 stories mixed use'),
    ('C-MX-16', 16, 'mixed_use', '16 stories mixed use'),
    ('C-MX-20', 20, 'mixed_use', '20 stories mixed use'),
    
    -- General Urban (Multi-unit and Mixed-use)
    ('G-MU-2.5', 2.5, 'multi_unit', '2.5 stories general urban'),
    ('G-MU-3', 3, 'multi_unit', '3 stories general urban'),
    ('G-MU-5', 5, 'multi_unit', '5 stories general urban'),
    ('G-MU-8', 8, 'multi_unit', '8 stories general urban'),
    
    ('G-RX-3', 3, 'mixed_use', '3 stories residential mixed use'),
    ('G-RX-5', 5, 'mixed_use', '5 stories residential mixed use'),
    ('G-RX-8', 8, 'mixed_use', '8 stories residential mixed use'),
    
    ('G-MS-2.5', 2.5, 'main_street', '2.5 stories main street'),
    ('G-MS-3', 3, 'main_street', '3 stories main street'),
    ('G-MS-5', 5, 'main_street', '5 stories main street'),
    
    -- Residential
    ('U-SU-A', 2, 'single_unit', 'Urban single unit A'),
    ('U-SU-B', 2, 'single_unit', 'Urban single unit B'),
    ('U-SU-C', 2, 'single_unit', 'Urban single unit C'),
    ('U-TU-A', 2, 'two_unit', 'Urban two unit A'),
    ('U-TU-B', 2, 'two_unit', 'Urban two unit B'),
    ('U-TU-C', 2, 'two_unit', 'Urban two unit C'),
    
    -- Suburban
    ('S-SU', 2, 'single_unit', 'Suburban single unit'),
    ('S-TU', 2, 'two_unit', 'Suburban two unit'),
    
    -- Row House
    ('U-RH-2.5', 2.5, 'row_house', 'Urban row house 2.5'),
    ('U-RH-3', 3, 'row_house', 'Urban row house 3'),
    
    -- Industrial Mixed Use
    ('I-MX-3', 3, 'industrial_mixed', 'Industrial mixed 3 stories'),
    ('I-MX-5', 5, 'industrial_mixed', 'Industrial mixed 5 stories'),
    ('I-MX-8', 8, 'industrial_mixed', 'Industrial mixed 8 stories'),
    ('I-MX-12', 12, 'industrial_mixed', 'Industrial mixed 12 stories'),
    
    -- Industrial (for reference)
    ('I-A', 3, 'industrial', 'Industrial A (light)'),
    ('I-B', 3, 'industrial', 'Industrial B (heavy)'),
    
    -- Open Space
    ('OS-A', 0, 'open_space', 'Open space A'),
    ('OS-B', 0, 'open_space', 'Open space B');

-- ============================================================================
-- TRANSIT INFRASTRUCTURE TABLES
-- ============================================================================

CREATE TABLE light_rail_stations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    line VARCHAR(100),
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX light_rail_geom_idx ON light_rail_stations USING GIST (geometry);

-- ----

CREATE TABLE brt_stops (
    id SERIAL PRIMARY KEY,
    stop_id VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    route VARCHAR(100),
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX brt_geom_idx ON brt_stops USING GIST (geometry);

-- ----

CREATE TABLE frequent_bus_stops (
    id SERIAL PRIMARY KEY,
    stop_id VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    routes TEXT[], -- Array of route numbers
    frequency_minutes INTEGER, -- Headway in minutes
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX frequent_bus_geom_idx ON frequent_bus_stops USING GIST (geometry);

-- ============================================================================
-- AMENITY TABLES
-- ============================================================================

CREATE TABLE schools (
    id SERIAL PRIMARY KEY,
    school_id VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    school_type VARCHAR(50), -- 'elementary', 'middle', 'high', etc
    owner_type VARCHAR(50), -- 'public', 'charter', 'private'
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    land_area_sqft NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX schools_geom_idx ON schools USING GIST (geometry);

-- ----

CREATE TABLE parks (
    id SERIAL PRIMARY KEY,
    park_id VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    park_type VARCHAR(50), -- 'neighborhood', 'community', 'regional'
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    land_area_acres NUMERIC,
    has_playground BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX parks_geom_idx ON parks USING GIST (geometry);

-- ----

CREATE TABLE government_parcels (
    id SERIAL PRIMARY KEY,
    parcel_id VARCHAR(50) UNIQUE,
    name VARCHAR(255),
    govt_type VARCHAR(50), -- 'city', 'county', 'state', 'federal'
    use_type VARCHAR(50), -- 'office', 'facility', 'vacant', etc
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    land_area_sqft NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX govt_parcels_geom_idx ON government_parcels USING GIST (geometry);

-- ============================================================================
-- MAIN PARCELS TABLE
-- ============================================================================

CREATE TABLE parcels (
    id SERIAL PRIMARY KEY,
    parcel_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Geometry
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    
    -- Address
    address VARCHAR(255),
    
    -- Current Zoning
    zone_district VARCHAR(20),
    
    -- Land Attributes
    land_area_sqft NUMERIC NOT NULL,
    land_area_acres NUMERIC GENERATED ALWAYS AS (land_area_sqft / 43560.0) STORED,
    
    -- Current Development
    current_units INTEGER DEFAULT 0,
    building_sqft NUMERIC DEFAULT 0,
    res_above_grade_area NUMERIC DEFAULT 0,
    res_orig_year_built INTEGER,
    com_gross_area NUMERIC DEFAULT 0,
    com_orig_year_built INTEGER,
    building_age INTEGER GENERATED ALWAYS AS (
        2026 - LEAST(
            COALESCE(res_orig_year_built, 9999),
            COALESCE(com_orig_year_built, 9999)
        )
    ) STORED,
    
    -- Property Classification
    property_class VARCHAR(50), -- 'VACANT LAND', 'SFR', 'COMMERCIAL', etc
    property_type VARCHAR(50), -- Simplified: 'vacant', 'residential', 'commercial', 'industrial'
    
    -- Ownership
    owner_name VARCHAR(255),
    owner_type VARCHAR(50), -- 'private', 'school', 'govt', 'church', 'rtd', etc
    
    -- Values
    land_value NUMERIC,
    improvement_value NUMERIC,
    total_value NUMERIC,
    land_to_improvement_ratio NUMERIC GENERATED ALWAYS AS (
        CASE WHEN improvement_value > 0 
        THEN land_value / improvement_value 
        ELSE NULL END
    ) STORED,
    
    -- Calculated Attributes
    current_far NUMERIC, -- Floor Area Ratio
    
    -- Flags
    is_vacant BOOLEAN DEFAULT false,
    is_historic BOOLEAN DEFAULT false,
    is_in_historic_district BOOLEAN DEFAULT false,
    
    -- Distances (in feet, calculated and stored)
    distance_to_light_rail NUMERIC,
    nearest_light_rail_id INTEGER REFERENCES light_rail_stations(id),
    
    distance_to_brt NUMERIC,
    nearest_brt_id INTEGER REFERENCES brt_stops(id),
    
    distance_to_frequent_bus NUMERIC,
    nearest_bus_stop_id INTEGER REFERENCES frequent_bus_stops(id),
    
    distance_to_school NUMERIC,
    nearest_school_id INTEGER REFERENCES schools(id),
    
    distance_to_park NUMERIC,
    nearest_park_id INTEGER REFERENCES parks(id),
    
    -- Opportunity Classification (from current analysis)
    opportunity_type VARCHAR(100),
    potential_units INTEGER,
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX parcels_geom_idx ON parcels USING GIST (geometry);
CREATE INDEX parcels_zone_idx ON parcels (zone_district);
CREATE INDEX parcels_property_type_idx ON parcels (property_type);
CREATE INDEX parcels_owner_type_idx ON parcels (owner_type);
CREATE INDEX parcels_is_vacant_idx ON parcels (is_vacant);

-- Distance indexes for fast filtering
CREATE INDEX parcels_dist_light_rail_idx ON parcels (distance_to_light_rail);
CREATE INDEX parcels_dist_brt_idx ON parcels (distance_to_brt);
CREATE INDEX parcels_dist_school_idx ON parcels (distance_to_school);
CREATE INDEX parcels_dist_park_idx ON parcels (distance_to_park);

-- Composite indexes for common queries
CREATE INDEX parcels_zone_vacant_idx ON parcels (zone_district, is_vacant);
CREATE INDEX parcels_type_units_idx ON parcels (property_type, current_units);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to calculate potential units based on stories and land area
CREATE OR REPLACE FUNCTION calculate_potential_units(
    land_area_acres NUMERIC,
    stories INTEGER
)
RETURNS INTEGER AS $$
DECLARE
    units_per_acre INTEGER;
BEGIN
    -- Stories to Units per Acre lookup (from your YIMBY formula)
    units_per_acre := CASE
        WHEN stories <= 2 THEN 30
        WHEN stories <= 2.5 THEN 35
        WHEN stories <= 3 THEN 60
        WHEN stories <= 5 THEN 100
        WHEN stories <= 7 THEN 160
        WHEN stories <= 10 THEN 160
        WHEN stories <= 12 THEN 220
        WHEN stories <= 16 THEN 280
        WHEN stories <= 20 THEN 350
        ELSE 450 -- 30+ stories
    END;
    
    RETURN ROUND(land_area_acres * units_per_acre);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to update distances to nearest transit (call after loading data)
CREATE OR REPLACE FUNCTION update_transit_distances()
RETURNS void AS $$
BEGIN
    -- Update light rail distances
    UPDATE parcels p
    SET 
        distance_to_light_rail = subquery.distance,
        nearest_light_rail_id = subquery.station_id
    FROM (
        SELECT 
            p.id,
            MIN(ST_Distance(ST_Transform(p.geometry, 32613), 
                           ST_Transform(s.geometry, 32613)) * 3.28084) as distance,
            (
                SELECT s2.id 
                FROM light_rail_stations s2 
                ORDER BY ST_Distance(ST_Transform(p.geometry, 32613), 
                                   ST_Transform(s2.geometry, 32613))
                LIMIT 1
            ) as station_id
        FROM parcels p
        CROSS JOIN light_rail_stations s
        GROUP BY p.id
    ) subquery
    WHERE p.id = subquery.id;
    
    RAISE NOTICE 'Updated light rail distances';
    
    -- Update BRT distances (if BRT stops exist)
    IF EXISTS (SELECT 1 FROM brt_stops LIMIT 1) THEN
        UPDATE parcels p
        SET 
            distance_to_brt = subquery.distance,
            nearest_brt_id = subquery.stop_id
        FROM (
            SELECT 
                p.id,
                MIN(ST_Distance(ST_Transform(p.geometry, 32613), 
                               ST_Transform(s.geometry, 32613)) * 3.28084) as distance,
                (
                    SELECT s2.id 
                    FROM brt_stops s2 
                    ORDER BY ST_Distance(ST_Transform(p.geometry, 32613), 
                                       ST_Transform(s2.geometry, 32613))
                    LIMIT 1
                ) as stop_id
            FROM parcels p
            CROSS JOIN brt_stops s
            GROUP BY p.id
        ) subquery
        WHERE p.id = subquery.id;
        
        RAISE NOTICE 'Updated BRT distances';
    END IF;
    
    -- Update school distances (if schools exist)
    IF EXISTS (SELECT 1 FROM schools LIMIT 1) THEN
        UPDATE parcels p
        SET 
            distance_to_school = subquery.distance,
            nearest_school_id = subquery.school_id
        FROM (
            SELECT 
                p.id,
                MIN(ST_Distance(ST_Transform(p.geometry, 32613), 
                               ST_Transform(s.geometry, 32613)) * 3.28084) as distance,
                (
                    SELECT s2.id 
                    FROM schools s2 
                    ORDER BY ST_Distance(ST_Transform(p.geometry, 32613), 
                                       ST_Transform(s2.geometry, 32613))
                    LIMIT 1
                ) as school_id
            FROM parcels p
            CROSS JOIN schools s
            GROUP BY p.id
        ) subquery
        WHERE p.id = subquery.id;
        
        RAISE NOTICE 'Updated school distances';
    END IF;
    
    -- Update park distances (if parks exist)
    IF EXISTS (SELECT 1 FROM parks LIMIT 1) THEN
        UPDATE parcels p
        SET 
            distance_to_park = subquery.distance,
            nearest_park_id = subquery.park_id
        FROM (
            SELECT 
                p.id,
                MIN(ST_Distance(ST_Transform(p.geometry, 32613), 
                               ST_Transform(s.geometry, 32613)) * 3.28084) as distance,
                (
                    SELECT s2.id 
                    FROM parks s2 
                    ORDER BY ST_Distance(ST_Transform(p.geometry, 32613), 
                                       ST_Transform(s2.geometry, 32613))
                    LIMIT 1
                ) as park_id
            FROM parcels p
            CROSS JOIN parks s
            GROUP BY p.id
        ) subquery
        WHERE p.id = subquery.id;
        
        RAISE NOTICE 'Updated park distances';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Current opportunities (what shows by default)
CREATE OR REPLACE VIEW current_opportunities AS
SELECT 
    p.*,
    z.max_stories,
    z.category as zone_category,
    calculate_potential_units(p.land_area_acres, z.max_stories) as calculated_units
FROM parcels p
LEFT JOIN zoning_lookup z ON p.zone_district = z.zone_code
WHERE 
    p.distance_to_light_rail IS NOT NULL 
    AND p.distance_to_light_rail <= 1980 -- 3/8 mile
    AND p.opportunity_type IS NOT NULL
    AND p.opportunity_type != 'Industrial Near Transit'; -- Exclude industrial in current view

-- All parcels near transit (including industrial)
CREATE OR REPLACE VIEW all_parcels_near_transit AS
SELECT 
    p.*,
    z.max_stories,
    z.category as zone_category,
    calculate_potential_units(p.land_area_acres, z.max_stories) as calculated_units
FROM parcels p
LEFT JOIN zoning_lookup z ON p.zone_district = z.zone_code
WHERE 
    p.distance_to_light_rail IS NOT NULL 
    AND p.distance_to_light_rail <= 1980; -- 3/8 mile

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$ 
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Database schema created successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - zoning_lookup (% rows)', (SELECT COUNT(*) FROM zoning_lookup);
    RAISE NOTICE '  - parcels';
    RAISE NOTICE '  - light_rail_stations';
    RAISE NOTICE '  - brt_stops';
    RAISE NOTICE '  - frequent_bus_stops';
    RAISE NOTICE '  - schools';
    RAISE NOTICE '  - parks';
    RAISE NOTICE '  - government_parcels';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - calculate_potential_units(land_area, stories)';
    RAISE NOTICE '  - update_transit_distances()';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - current_opportunities';
    RAISE NOTICE '  - all_parcels_near_transit';
END $$;
