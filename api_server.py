"""
Mile High Potential - FastAPI Backend
======================================
API server for evaluating transit-oriented development policies.
Refactored to support TOD, POD, and BOD with shared logic and "Highest Height Wins" resolution.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
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

# Helper to provide a database session
def get_db():
    with engine.connect() as connection:
        yield connection

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

# ============================================================================
# DATA MODELS
# ============================================================================

class RingConfig(BaseModel):
    distance: int = Field(..., example=500)
    height: int = Field(..., example=8)
    zone: str = Field(..., example="C-MX-8")
    density: str = Field(..., example="high") 

class TODPolicyConfig(BaseModel):
    enabled: bool = True
    rings: List[RingConfig] = Field(default=[
        RingConfig(distance=500, height=8, zone="C-MX-8", density="high"),
        RingConfig(distance=1000, height=5, zone="C-MX-5", density="med")
    ])

class PODPolicyConfig(BaseModel):
    enabled: bool = True
    regional_parks: List[RingConfig] = Field(default=[
        RingConfig(distance=750, height=3, zone="U-MX-3", density="low")
    ])
    community_parks: List[RingConfig] = Field(default=[
        RingConfig(distance=250, height=3, zone="U-MX-3", density="low")
    ])

class BODPolicyConfig(BaseModel):
    enabled: bool = False 
    rings: List[RingConfig] = Field(default=[
        RingConfig(distance=250, height=5, zone="MS-5", density="med")
    ])

class MultiPolicyConfig(BaseModel):
    tod: TODPolicyConfig = TODPolicyConfig()
    pod: PODPolicyConfig = PODPolicyConfig()
    bod: Optional[BODPolicyConfig] = BODPolicyConfig()
    exclude_unlikely: bool = True

# ============================================================================
# CORE LOGIC HELPERS
# ============================================================================

def evaluate_spatial_policy(
    db, 
    policy_name: str, 
    rings: List[RingConfig], 
    distance_column: str, 
    global_registry: Dict[str, Any],
    exclude_unlikely: bool = True,
    min_il_ratio: float = 1.5
):
    if not rings:
        return

    #Get max distance and sort rings (closest first)
    max_dist = max(r.distance for r in rings)
    sorted_rings = sorted(rings, key=lambda x: x.distance)

    # Build the unlikely development filter
    unlikely_clause = ""
    if exclude_unlikely:
        unlikely_clause = """
        AND (owner_type NOT IN ('school', 'govt') OR owner_type IS NULL)
        AND (
            (res_orig_year_built IS NULL AND com_orig_year_built IS NULL)
            OR LEAST(COALESCE(res_orig_year_built, 9999), COALESCE(com_orig_year_built, 9999)) <= 2011
        )
        AND (
            improvement_value IS NULL 
            OR land_value IS NULL 
            OR land_value = 0 
            OR (improvement_value / NULLIF(land_value, 0)) < :min_il_ratio
        )
        """

    # Query parcels within the max distance
    query = text(f"""
        SELECT 
            parcel_id, address, zone_district, land_area_acres,
            geometry_geojson, improvement_value, land_value,
            property_type, property_class, owner_name, owner_type,
            res_above_grade_area, com_gross_area,
            res_orig_year_built, com_orig_year_built,
            current_units, opportunity_type, {distance_column}
        FROM parcels
        WHERE {distance_column} <= :max_dist
        AND zone_district NOT LIKE 'CMP%'
        AND zone_district NOT LIKE 'H-%'
        AND zone_district NOT LIKE 'CPV%'
        AND zone_district NOT LIKE 'DIA%'
        AND zone_district NOT LIKE 'OS-%'
        AND zone_district NOT LIKE 'PUD%'
        AND zone_district NOT IN ('I-A', 'I-B', 'FX-1', 'FX-2')
        AND property_class NOT LIKE '%CONDOMINIUM%'
        AND property_class != 'VACANT LAND /GENERAL COMMON ELEMENTS'
        {unlikely_clause}
    """)
    
    result = db.execute(query, {"max_dist": max_dist, "min_il_ratio": min_il_ratio})
    
    for parcel in result.mappings():
        geom = json.loads(parcel['geometry_geojson'])
        
        # Compactness Filter (Filter out roads/rails)
        if calculate_polsby_popper(geom) < 0.3:
            continue

        # Find the best applicable ring
        applicable_ring = next((r for r in sorted_rings if parcel[distance_column] <= r.distance), None)

        # UPZONE FILTER: Only include if proposed height > current max height
        current_max_stories = get_max_stories_from_zone(parcel['zone_district'])
        if applicable_ring.height <= current_max_stories:
            # Not an upzone - skip this parcel
            continue
        
        if applicable_ring:
            p_id = parcel['parcel_id']
            new_height = applicable_ring.height
            
            # Winner Logic: Only add/update if this policy offers a taller building
            if p_id not in global_registry or new_height > global_registry[p_id]['properties']['assigned_height']:
                
                upa = STORIES_TO_UPA.get(new_height, new_height * 20)
                potential_units = int(float(parcel['land_area_acres']) * upa)

                bldg_sqft = float(parcel['res_above_grade_area'] or 0)
                if bldg_sqft == 0:
                    bldg_sqft = float(parcel['com_gross_area'] or 0)
                
                bldg_age_year = parcel['res_orig_year_built'] or parcel['com_orig_year_built']

                global_registry[p_id] = {
                    "type": "Feature",
                    "geometry": json.loads(parcel['geometry_geojson']),
                    "properties": {
                        "parcel_id": p_id,
                        "address": parcel['address'],
                        "zone_district": parcel['zone_district'],
                        "land_area_acres": float(parcel['land_area_acres']),
                        "property_type": parcel['property_type'],
                        "property_class": parcel['property_class'],
                        "owner_name": parcel['owner_name'],
                        "owner_type": parcel['owner_type'],
                        "land_value": float(parcel['land_value']) if parcel['land_value'] else 0,
                        "improvement_value": float(parcel['improvement_value']) if parcel['improvement_value'] else 0,
                        "building_sqft": bldg_sqft,
                        "building_age": bldg_age_year,
                        "current_units": parcel['current_units'],
                        "opportunity_type": parcel['opportunity_type'],
                        "assigned_height": new_height,
                        "assigned_zone": applicable_ring.zone,
                        "potential_units": potential_units,
                        "policy_source": policy_name,
                        "ring_density": applicable_ring.density,
                        "distance_to_feature": float(parcel[distance_column])
                    }
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
async def get_stats(db: Session = Depends(get_db)):
    """Get overall database statistics using shared connection"""
    # Total parcels
    total_parcels = db.execute(text("SELECT COUNT(*) FROM parcels;")).fetchone()[0]
    
    # Parcels near transit
    parcels_near_transit = db.execute(text("""
        SELECT COUNT(*) 
        FROM parcels 
        WHERE distance_to_light_rail IS NOT NULL 
        AND distance_to_light_rail <= 1980;
    """)).fetchone()[0]
    
    # Property types
    result = db.execute(text("""
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

@app.get("/api/stations")
async def get_stations(db: Session = Depends(get_db)):
    """Get all light rail stations using shared connection"""
    try:
        # Improved JSON extraction for station coordinates
        result = db.execute(text("""
            SELECT name, 
                   (geometry_geojson::json->'coordinates'->>0)::float as lon,
                   (geometry_geojson::json->'coordinates'->>1)::float as lat
            FROM light_rail_stations
            ORDER BY name
        """))
        
        return [
            {'name': row[0], 'lon': row[1], 'lat': row[2]} 
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/rail-lines")
async def get_rail_lines(db: Session = Depends(get_db)):
    """Get all light rail lines using shared connection"""
    try:
        result = db.execute(text("""
            SELECT route, name, geometry
            FROM light_rail_lines
            WHERE route IS NOT NULL
            ORDER BY route, id
        """))
        
        return [
            {'route': row[0], 'name': row[1], 'geometry': row[2]} 
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/parks")
async def get_parks(db: Session = Depends(get_db)):
    """Get all parks over 10 acres as a GeoJSON FeatureCollection"""
    try:
        # 2. Ordered by size so smaller parks don't get 'hidden' by larger ones in rendering
        result = db.execute(text("""
            SELECT formal_name, ballot_park_type, land_area_acres, geometry
            FROM parks
            WHERE ballot_park_type in ('community', 'regional')
            ORDER BY land_area_acres ASC;
        """))
        
        features = []
        for row in result:
            # Parse the geojson string into a dict so it nests correctly
            geom = json.loads(row[3])
            
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "name": row[0],
                    "park_type": row[1],
                    "land_area_acres": float(row[2])
                }
            })
            
        return {
            "type": "FeatureCollection",
            "features": features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/evaluate-policies")
async def evaluate_policies(config: MultiPolicyConfig, db: Session = Depends(get_db)):
    # Registry to handle "Highest Height Wins" across different policy types
    global_registry = {}

    # --- 1) Evaluate Transit (TOD) ---
    if config.tod.enabled:
        evaluate_spatial_policy(
            db, "TOD", config.tod.rings, "distance_to_light_rail", global_registry, config.exclude_unlikely
        )

    # --- 2) Evaluate Parks (POD) ---
    if config.pod.enabled:
        evaluate_spatial_policy(
            db, "POD-Regional", config.pod.regional_parks, "distance_to_regional_park", global_registry, config.exclude_unlikely
        )
        evaluate_spatial_policy(
            db, "POD-Community", config.pod.community_parks, "distance_to_community_park", global_registry, config.exclude_unlikely
        )

    # --- 3) Evaluate Bus (BOD) ---
    if config.bod and config.bod.enabled:
        evaluate_spatial_policy(
            db, "BOD", config.bod.rings, "distance_to_brt", global_registry, config.exclude_unlikely
        )

    # Construct Final Response
    features = list(global_registry.values())
    total_units = sum(f['properties']['potential_units'] for f in features)

    return {
        "total_units": total_units,
        "total_parcels": len(features),
        "geojson": {
            "type": "FeatureCollection",
            "features": features
        }
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
