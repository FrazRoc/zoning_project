"""
Mile High Potential - FastAPI Backend
======================================
API server for evaluating transit-oriented development policies.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text
import os
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

# Database URL - supports both local development and Render deployment
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    # Fallback for local development
    f"postgresql://{os.environ.get('USER')}@localhost:5432/mile_high_potential_db"
)

# Create database engine
engine = create_engine(DATABASE_URL)

# Stories to Units per Acre lookup (from your YIMBY formula)
STORIES_TO_UPA = {
    2: 30,
    2.5: 35,
    3: 60,
    5: 100,
    7: 160,
    8: 160,
    10: 160,
    12: 220,
    16: 280,
    20: 350,
    30: 450
}

def calculate_units_from_stories(land_area_acres: float, stories: float) -> int:
    """Calculate potential units using stories-to-units-per-acre lookup"""
    # Find closest story height in lookup table
    if stories in STORIES_TO_UPA:
        units_per_acre = STORIES_TO_UPA[stories]
    else:
        # Find nearest
        story_heights = sorted(STORIES_TO_UPA.keys())
        if stories < min(story_heights):
            units_per_acre = STORIES_TO_UPA[min(story_heights)]
        elif stories > max(story_heights):
            units_per_acre = STORIES_TO_UPA[max(story_heights)]
        else:
            nearest = min(story_heights, key=lambda x: abs(x - stories))
            units_per_acre = STORIES_TO_UPA[nearest]
    
    return round(land_area_acres * units_per_acre)

def calculate_polsby_popper(geometry_json: dict) -> float:
    """
    Calculate Polsby-Popper compactness score to detect linear parcels.
    
    PP = (4π × Area) / (Perimeter²)
    
    Returns:
        1.0 = perfect circle (very compact)
        0.8+ = square/round shape
        0.5-0.8 = rectangular
        0.3-0.5 = elongated
        <0.3 = very elongated/thin strip (roads/railroads)
    """
    try:
        import math
        
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
        
    except:
        return 1.0  # Assume compact if error

def get_max_stories_from_zone(zone_district: str) -> float:
    """
    Determine maximum allowed stories from current zone district.
    Returns the max stories allowed by the current zoning.
    """
    if not zone_district:
        return 0
    
    zone = zone_district.upper()
    
    # Downtown zones - very permissive (12-30 stories typically)
    if zone.startswith('D-'):
        return 20  # Conservative estimate, most downtown is 12+ stories
    
    # Mixed Use zones - extract number
    # Examples: C-MX-8, G-MX-5, MX-12
    if 'MX-' in zone or zone.startswith('MX'):
        import re
        match = re.search(r'MX-(\d+)', zone)
        if match:
            return float(match.group(1))
    
    # RX zones - extract number
    # Examples: G-RX-5, C-RX-8
    if 'RX-' in zone:
        import re
        match = re.search(r'RX-(\d+)', zone)
        if match:
            return float(match.group(1))
    
    # MS zones - extract number
    # Examples: G-MS-3, MS-5
    if 'MS-' in zone:
        import re
        match = re.search(r'MS-(\d+)', zone)
        if match:
            return float(match.group(1))
    
    # MU zones - extract number
    # Examples: G-MU-3, E-MU-5
    if 'MU-' in zone:
        import re
        match = re.search(r'MU-(\d+)', zone)
        if match:
            return float(match.group(1))
    
    # CC zones - extract number
    # Examples: CC-3, CC-5
    if 'CC-' in zone:
        import re
        match = re.search(r'CC-(\d+)', zone)
        if match:
            return float(match.group(1))
    
    # Row House zones - typically 2.5-3 stories
    if 'RH-' in zone or 'TH-' in zone:
        import re
        match = re.search(r'(?:RH|TH)-(\d+(?:\.\d+)?)', zone)
        if match:
            return float(match.group(1))
        return 2.5
    
    # Two Unit zones - typically 2.5 stories
    if 'TU-' in zone or zone.startswith('TU'):
        import re
        match = re.search(r'TU-(\d+(?:\.\d+)?)', zone)
        if match:
            return float(match.group(1))
        return 2.5
    
    # Single Unit zones - typically 2.5 stories
    if 'SU-' in zone or zone.startswith('SU'):
        return 2.5
    
    # Industrial zones - typically 3-5 stories
    if zone.startswith('I-'):
        return 5
    
    # Special districts - assume permissive
    if zone.startswith('PUD') or zone.startswith('GDP'):
        return 10
    
    # Default: assume 2.5 stories (conservative)
    return 2.5

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Mile High Potential API",
    description="API for evaluating transit-oriented development policies in Denver",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DATA MODELS
# ============================================================================

class RingConfig(BaseModel):
    """Configuration for a single policy ring"""
    distance: int  # Distance in feet
    height: int    # Building height in stories
    zone: str      # Zoning code (e.g., 'C-MX-8x')

class TODPolicyConfig(BaseModel):
    """Configuration for TOD policy evaluation"""
    enabled: bool = True
    rings: List[RingConfig]
    include_light_rail: bool = True
    include_brt: bool = False
    include_frequent_bus: bool = False

class PODPolicyConfig(BaseModel):
    """Configuration for POD (Park-Oriented Development) policy"""
    enabled: bool = True
    regional_parks: List[RingConfig]  # Inner: 250ft, Outer: 750ft
    community_parks: List[RingConfig]  # Inner: 250ft only

class BODPolicyConfig(BaseModel):
    """Configuration for BOD (Bus-Oriented Development) policy"""
    enabled: bool = True
    brt_lines: List[RingConfig]  # Inner: 250ft, Outer: 750ft
    medium_freq_bus: List[RingConfig]  # Inner: 250ft only

class MultiPolicyConfig(BaseModel):
    """Configuration for evaluating multiple policies"""
    tod: Optional[TODPolicyConfig] = None
    pod: Optional[PODPolicyConfig] = None
    bod: Optional[BODPolicyConfig] = None
    exclude_unlikely: bool = True

class ParcelSummary(BaseModel):
    """Summary information for a parcel"""
    parcel_id: str
    address: Optional[str]
    zone_district: Optional[str]
    land_area_acres: float
    distance_to_light_rail: float
    assigned_height: int
    assigned_zone: str
    potential_units: int
    policy_source: str  # 'TOD', 'POD', 'BOD', or 'TOD+POD' for overlaps

class PolicyResult(BaseModel):
    """Result of policy evaluation"""
    total_parcels: int
    total_units: int
    parcels_by_ring: Dict[str, int]
    units_by_ring: Dict[str, int]
    parcels: List[ParcelSummary]

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Mile High Potential API",
        "version": "1.0.0"
    }

@app.get("/api/stats")
async def get_stats():
    """Get overall database statistics"""
    with engine.connect() as conn:
        # Total parcels
        result = conn.execute(text("SELECT COUNT(*) FROM parcels;"))
        total_parcels = result.fetchone()[0]
        
        # Parcels near transit
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM parcels 
            WHERE distance_to_light_rail IS NOT NULL 
            AND distance_to_light_rail <= 1980;
        """))
        parcels_near_transit = result.fetchone()[0]
        
        # Property types
        result = conn.execute(text("""
            SELECT property_type, COUNT(*) 
            FROM parcels 
            GROUP BY property_type
            ORDER BY COUNT(*) DESC;
        """))
        property_types = {row[0]: row[1] for row in result}
        
        return {
            "total_parcels": total_parcels,
            "parcels_near_transit": parcels_near_transit,
            "property_types": property_types
        }

@app.post("/api/evaluate-tod")
async def evaluate_tod(config: TODPolicyConfig) -> Dict:
    """
    Evaluate a TOD policy configuration.
    
    Returns parcels with GeoJSON geometries and calculates
    potential housing units based on height allowances.
    """
    
    # Sort rings by distance (innermost first)
    sorted_rings = sorted(config.rings, key=lambda r: r.distance)
    
    # Get outer ring distance (maximum distance we care about)
    max_distance = sorted_rings[-1].distance
    
    # Build SQL query with geometry
    ring_cases = []
    for i, ring in enumerate(sorted_rings):
        if i == 0:
            condition = f"distance_to_light_rail <= {ring.distance}"
        else:
            prev_distance = sorted_rings[i-1].distance
            condition = f"distance_to_light_rail > {prev_distance} AND distance_to_light_rail <= {ring.distance}"
        
        ring_cases.append(f"WHEN {condition} THEN {ring.height}")
    
    case_statement = " ".join(ring_cases)
    
    query = f"""
        SELECT 
            parcel_id,
            address,
            zone_district,
            land_area_acres,
            distance_to_light_rail,
            geometry_geojson,
            property_type,
            property_class,
            owner_name,
            owner_type,
            land_value,
            improvement_value,
            building_sqft,
            current_units,
            res_above_grade_area,
            opportunity_type,
            CASE 
                {case_statement}
            END as assigned_height,
            -- Assign new zone based on ballot language
            CASE 
                -- Ring 1: Within 500ft -> MX-8 (keep context)
                WHEN distance_to_light_rail <= 500 THEN 
                    COALESCE(SPLIT_PART(zone_district, '-', 1), 'G') || '-MX-8'
                
                -- Ring 2: Within 1000ft -> RX-5x or MX-5 (special cases)
                WHEN distance_to_light_rail <= 1000 THEN
                    CASE 
                        -- Special cases get MX-5 instead of RX-5x
                        WHEN zone_district ~ '(MX-2|MX-2x|MX-3|MS-2|MS-3|CC-3|CC-3x)' THEN
                            COALESCE(SPLIT_PART(zone_district, '-', 1), 'G') || '-MX-5'
                        ELSE
                            COALESCE(SPLIT_PART(zone_district, '-', 1), 'G') || '-RX-5x'
                    END
                
                -- Ring 3: Within 1500ft -> MU-3x or MX-3 (special cases)
                WHEN distance_to_light_rail <= 1500 THEN
                    CASE 
                        -- Special cases get MX-3 instead of MU-3x
                        WHEN zone_district ~ '(MX-2|MX-2x|MS-2)' THEN
                            COALESCE(SPLIT_PART(zone_district, '-', 1), 'G') || '-MX-3'
                        ELSE
                            COALESCE(SPLIT_PART(zone_district, '-', 1), 'G') || '-MU-3x'
                    END
                
                ELSE 'UNKNOWN'
            END as assigned_zone
        FROM parcels
        WHERE distance_to_light_rail IS NOT NULL
        AND distance_to_light_rail <= {max_distance}
        AND land_area_acres > 0
        AND zone_district NOT LIKE 'CMP%'
        AND zone_district NOT LIKE 'H-%'
        AND zone_district NOT LIKE 'CPV%'
        AND zone_district NOT LIKE 'DIA%'
        AND zone_district NOT LIKE 'OS-%'
        AND zone_district NOT LIKE 'PUD%'
        AND zone_district NOT IN ('I-A', 'I-B', 'FX-1', 'FX-2')
        AND property_class NOT LIKE '%CONDOMINIUM%'
        AND property_class != 'VACANT LAND /GENERAL COMMON ELEMENTS'
    """
    
    # Add unlikely development filters if enabled
    if config.exclude_unlikely:
        query += """
        AND (owner_type NOT IN ('school', 'govt') OR owner_type IS NULL)
        AND (
            (res_orig_year_built IS NULL AND com_orig_year_built IS NULL)
            OR LEAST(COALESCE(res_orig_year_built, 9999), COALESCE(com_orig_year_built, 9999)) <= 2011
        )
        AND (
            improvement_value IS NULL 
            OR land_value IS NULL 
            OR land_value = 0 
            OR (improvement_value / NULLIF(land_value, 0)) < 1.5
        )
        """
    
    # Execute query
    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()
    
    # Process results into GeoJSON
    features = []
    total_units = 0
    parcels_by_ring = {f"Ring {i+1}": 0 for i in range(len(sorted_rings))}
    units_by_ring = {f"Ring {i+1}": 0 for i in range(len(sorted_rings))}
    
    for row in rows:
        parcel_id = row[0]
        address = row[1]
        zone_district = row[2]
        land_area_acres = float(row[3])
        distance = float(row[4])
        geometry_geojson = json.loads(row[5])
        property_type = row[6]
        property_class = row[7]
        owner_name = row[8]
        owner_type = row[9]
        land_value = float(row[10]) if row[10] else 0
        improvement_value = float(row[11]) if row[11] else 0
        building_sqft = float(row[12]) if row[12] else 0
        current_units = int(row[13]) if row[13] else 0
        res_above_grade_area = float(row[14]) if row[14] else 0
        opportunity_type = row[15]
        assigned_height = int(row[16])
        assigned_zone = row[17]  # Now from SQL query
        
        # Determine which ring this parcel belongs to
        ring_num = None
        for i, ring in enumerate(sorted_rings):
            if i == 0:
                if distance <= ring.distance:
                    ring_num = i + 1
                    break
            else:
                prev_distance = sorted_rings[i-1].distance
                if prev_distance < distance <= ring.distance:
                    ring_num = i + 1
                    break
        
        if ring_num is None:
            continue
        
        # UPZONE FILTER: Only include if proposed height > current max height
        current_max_stories = get_max_stories_from_zone(zone_district)
        if assigned_height <= current_max_stories:
            # Not an upzone - skip this parcel
            continue
        
        # POLSBY-POPPER FILTER: Exclude long skinny parcels (roads/railroads)
        pp_score = calculate_polsby_popper(geometry_geojson)
        if pp_score < 0.3:
            # Very elongated - likely a road, railroad, or thin strip
            continue
        
        # Calculate units
        potential_units = calculate_units_from_stories(land_area_acres, assigned_height)
        total_units += potential_units
        
        # Update ring statistics
        ring_key = f"Ring {ring_num}"
        parcels_by_ring[ring_key] += 1
        units_by_ring[ring_key] += potential_units
        
        # Create GeoJSON feature
        features.append({
            "type": "Feature",
            "geometry": geometry_geojson,
            "properties": {
                "parcel_id": parcel_id,
                "address": address,
                "zone_district": zone_district,
                "land_area_acres": land_area_acres,
                "distance_to_light_rail": distance,
                "property_type": property_type,
                "property_class": property_class,
                "owner_name": owner_name,
                "owner_type": owner_type,
                "land_value": land_value,
                "improvement_value": improvement_value,
                "building_sqft": building_sqft,
                "current_units": current_units,
                "res_above_grade_area": res_above_grade_area,
                "opportunity_type": opportunity_type,
                "assigned_height": assigned_height,
                "assigned_zone": assigned_zone,
                "potential_units": potential_units,
                "ring": ring_num
            }
        })
    
    # Return GeoJSON FeatureCollection
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_parcels": len(features),
            "total_units": total_units,
            "parcels_by_ring": parcels_by_ring,
            "units_by_ring": units_by_ring
        }
    }

@app.get("/api/parcel/{parcel_id}")
async def get_parcel(parcel_id: str):
    """Get detailed information for a specific parcel"""
    query = """
        SELECT 
            parcel_id,
            address,
            zone_district,
            land_area_sqft,
            land_area_acres,
            current_units,
            property_type,
            owner_type,
            land_value,
            improvement_value,
            distance_to_light_rail
        FROM parcels
        WHERE parcel_id = :parcel_id;
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query), {"parcel_id": parcel_id})
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Parcel not found")
    
    return {
        "parcel_id": row[0],
        "address": row[1],
        "zone_district": row[2],
        "land_area_sqft": float(row[3]) if row[3] else 0,
        "land_area_acres": float(row[4]) if row[4] else 0,
        "current_units": int(row[5]) if row[5] else 0,
        "property_type": row[6],
        "owner_type": row[7],
        "land_value": float(row[8]) if row[8] else 0,
        "improvement_value": float(row[9]) if row[9] else 0,
        "distance_to_light_rail": float(row[10]) if row[10] else None
    }

# ============================================================================
# RUN SERVER
# ============================================================================

@app.get("/api/stations")
async def get_stations():
    """Get all light rail stations"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT name, 
                       (geometry_geojson::json->'coordinates'->>0)::float as lon,
                       (geometry_geojson::json->'coordinates'->>1)::float as lat
                FROM light_rail_stations
                ORDER BY name
            """))
            
            stations = []
            for row in result:
                stations.append({
                    'name': row[0],
                    'lon': row[1],
                    'lat': row[2]
                })
            
            return stations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rail-lines")
async def get_rail_lines():
    """Get all light rail lines with geometry"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT route, name, geometry
                FROM light_rail_lines
                WHERE route IS NOT NULL
                ORDER BY route, id
            """))
            
            lines = []
            for row in result:
                lines.append({
                    'route': row[0],
                    'name': row[1],
                    'geometry': row[2]
                })
            
            return lines
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evaluate-policies")
async def evaluate_policies(config: MultiPolicyConfig) -> Dict:
    """
    Evaluate multiple policies (TOD, POD, BOD) and combine results.
    When policies overlap, the highest zoning wins.
    """
    
    all_parcels = {}  # parcel_id -> {height, zone, policy_source, ...}
    policy_stats = {}
    
    # Build the unlikely development filter
    unlikely_filter = ""
    if config.exclude_unlikely:
        unlikely_filter = """
        AND (owner_type NOT IN ('school', 'govt') OR owner_type IS NULL)
        AND (
            (res_orig_year_built IS NULL AND com_orig_year_built IS NULL)
            OR LEAST(COALESCE(res_orig_year_built, 9999), COALESCE(com_orig_year_built, 9999)) <= 2011
        )
        AND (
            improvement_value IS NULL 
            OR land_value IS NULL 
            OR land_value = 0 
            OR (improvement_value / NULLIF(land_value, 0)) < 1.5
        )
        """
    
    # ========================================================================
    # POD (Park-Oriented Development)
    # ========================================================================
    if config.pod and config.pod.enabled:
        print("Evaluating POD policy...")
        
        # Process Regional Parks
        for ring in config.pod.regional_parks:
            query = f"""
                SELECT 
                    parcel_id,
                    address,
                    zone_district,
                    land_area_acres,
                    distance_to_regional_park,
                    geometry_geojson
                FROM parcels
                WHERE distance_to_regional_park IS NOT NULL
                AND distance_to_regional_park <= {ring.distance}
                AND land_area_acres > 0
                AND zone_district NOT LIKE 'CMP%'
                AND zone_district NOT LIKE 'H-%'
                AND zone_district NOT LIKE 'CPV%'
                AND zone_district NOT LIKE 'DIA%'
                AND zone_district NOT LIKE 'OS-%'
                AND zone_district NOT LIKE 'PUD%'
                AND zone_district NOT IN ('I-A', 'I-B', 'FX-1', 'FX-2')
                AND property_class NOT LIKE '%CONDOMINIUM%'
                AND property_class != 'VACANT LAND /GENERAL COMMON ELEMENTS'
                {unlikely_filter};
            """
            
            with engine.connect() as conn:
                result = conn.execute(text(query))
                for row in result:
                    parcel_id = row[0]
                    
                    # Only update if this is higher than existing
                    if parcel_id not in all_parcels or ring.height > all_parcels[parcel_id]['height']:
                        all_parcels[parcel_id] = {
                            'parcel_id': parcel_id,
                            'address': row[1],
                            'zone_district': row[2],
                            'land_area_acres': float(row[3]),
                            'distance': float(row[4]),
                            'height': ring.height,
                            'zone': ring.zone,
                            'policy_source': 'POD-Regional',
                            'geometry_geojson': row[5]
                        }
        
        # Process Community Parks
        for ring in config.pod.community_parks:
            query = f"""
                SELECT 
                    parcel_id,
                    address,
                    zone_district,
                    land_area_acres,
                    distance_to_community_park,
                    geometry_geojson
                FROM parcels
                WHERE distance_to_community_park IS NOT NULL
                AND distance_to_community_park <= {ring.distance}
                AND land_area_acres > 0
                AND zone_district NOT LIKE 'CMP%'
                AND zone_district NOT LIKE 'H-%'
                AND zone_district NOT LIKE 'CPV%'
                AND zone_district NOT LIKE 'DIA%'
                AND zone_district NOT LIKE 'OS-%'
                AND zone_district NOT LIKE 'PUD%'
                AND zone_district NOT IN ('I-A', 'I-B', 'FX-1', 'FX-2')
                AND property_class NOT LIKE '%CONDOMINIUM%'
                AND property_class != 'VACANT LAND /GENERAL COMMON ELEMENTS'
                {unlikely_filter};
            """
            
            with engine.connect() as conn:
                result = conn.execute(text(query))
                for row in result:
                    parcel_id = row[0]
                    
                    # Only update if this is higher than existing
                    if parcel_id not in all_parcels or ring.height > all_parcels[parcel_id]['height']:
                        all_parcels[parcel_id] = {
                            'parcel_id': parcel_id,
                            'address': row[1],
                            'zone_district': row[2],
                            'land_area_acres': float(row[3]),
                            'distance': float(row[4]),
                            'height': ring.height,
                            'zone': ring.zone,
                            'policy_source': 'POD-Community',
                            'geometry_geojson': row[5]
                        }
        
        policy_stats['POD'] = {'parcels': 0, 'units': 0}
    
    # ========================================================================
    # TOD (Transit-Oriented Development)
    # ========================================================================
    if config.tod and config.tod.enabled:
        print("Evaluating TOD policy...")
        
        # Sort rings by distance
        sorted_rings = sorted(config.tod.rings, key=lambda r: r.distance)
        max_distance = sorted_rings[-1].distance
        
        query = f"""
            SELECT 
                parcel_id,
                address,
                zone_district,
                land_area_acres,
                distance_to_light_rail,
                geometry_geojson
            FROM parcels
            WHERE distance_to_light_rail IS NOT NULL
            AND distance_to_light_rail <= {max_distance}
            AND land_area_acres > 0
            AND zone_district NOT LIKE 'CMP%'
            AND zone_district NOT LIKE 'H-%'
            AND zone_district NOT LIKE 'CPV%'
            AND zone_district NOT LIKE 'DIA%'
            AND zone_district NOT LIKE 'OS-%'
            AND zone_district NOT LIKE 'PUD%'
            AND zone_district NOT IN ('I-A', 'I-B', 'FX-1', 'FX-2')
            AND property_class NOT LIKE '%CONDOMINIUM%'
            AND property_class != 'VACANT LAND /GENERAL COMMON ELEMENTS'
            {unlikely_filter};
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for row in result:
                parcel_id = row[0]
                distance = float(row[4])
                
                # Find which ring this parcel belongs to
                assigned_ring = None
                for ring in sorted_rings:
                    if distance <= ring.distance:
                        assigned_ring = ring
                        break
                
                if assigned_ring:
                    # Only update if this is higher than existing
                    if parcel_id not in all_parcels or assigned_ring.height > all_parcels[parcel_id]['height']:
                        all_parcels[parcel_id] = {
                            'parcel_id': parcel_id,
                            'address': row[1],
                            'zone_district': row[2],
                            'land_area_acres': float(row[3]),
                            'distance': distance,
                            'height': assigned_ring.height,
                            'zone': assigned_ring.zone,
                            'policy_source': 'TOD',
                            'geometry_geojson': row[5]
                        }
        
        policy_stats['TOD'] = {'parcels': 0, 'units': 0}
    
    # ========================================================================
    # Calculate units and aggregate stats
    # ========================================================================
    features = []
    total_units = 0
    
    for parcel_id, parcel in all_parcels.items():
        # Calculate potential units
        height = parcel['height']
        acres = parcel['land_area_acres']
        upa = STORIES_TO_UPA.get(height, height * 20)  # Default fallback
        potential_units = int(acres * upa)
        
        parcel['potential_units'] = potential_units
        total_units += potential_units
        
        # Update policy stats
        source = parcel['policy_source'].split('-')[0]  # 'POD-Regional' -> 'POD'
        if source in policy_stats:
            policy_stats[source]['parcels'] += 1
            policy_stats[source]['units'] += potential_units
        
        # Create GeoJSON feature
        features.append({
            'type': 'Feature',
            'geometry': json.loads(parcel['geometry_geojson']),
            'properties': {
                'parcel_id': parcel['parcel_id'],
                'address': parcel['address'],
                'assigned_height': parcel['height'],
                'assigned_zone': parcel['zone'],
                'potential_units': potential_units,
                'policy_source': parcel['policy_source']
            }
        })
    
    return {
        'total_parcels': len(all_parcels),
        'total_units': total_units,
        'by_policy': policy_stats,
        'geojson': {
            'type': 'FeatureCollection',
            'features': features
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
