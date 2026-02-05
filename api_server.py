"""
Mile High Potential - FastAPI Backend
======================================
API server for evaluating transit-oriented development policies.
Refactored to support TOD, POD, and BOD with shared logic and "Highest Height Wins" resolution.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os
import json
import time
from contextlib import contextmanager
from functools import lru_cache

try:
    import orjson
    HAS_ORJSON = True
    print("✔ orjson available — using fast JSON serialization")
except ImportError:
    HAS_ORJSON = False
    print("ℹ️  orjson not installed — using standard json (pip install orjson for ~5x faster serialization)")

# ============================================================================
# PERFORMANCE TIMING
# ============================================================================

@contextmanager
def timer(label: str):
    """Context manager to time code blocks"""
    start = time.time()
    try:
        yield
    finally:
        elapsed = (time.time() - start) * 1000  # Convert to ms
        print(f"⏱️  {label}: {elapsed:.2f}ms")

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
    """Bus-Oriented Development with BRT and medium-frequency bus stops"""
    enabled: bool = True
    
    # BRT (Bus Rapid Transit) configuration
    brt_enabled: bool = False  # Set to False until we have BRT data
    brt_rings: List[RingConfig] = Field(default=[
        RingConfig(distance=250, height=5, zone="C-RX-5", density="med"),   # Inner: RX-5x
        RingConfig(distance=750, height=3, zone="U-MX-3", density="low")     # Outer: MU-3x
    ])
    
    # Medium-frequency bus stops configuration  
    bus_enabled: bool = True
    bus_rings: List[RingConfig] = Field(default=[
        RingConfig(distance=250, height=3, zone="U-MX-3", density="low")     # MU-3x
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

    with timer(f"{policy_name} - Setup & Query Building"):
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
            AND polsby_popper_score >= 0.3
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
    
    with timer(f"{policy_name} - Database Query Execution"):
        result = db.execute(query, {"max_dist": max_dist, "min_il_ratio": min_il_ratio})
    
    # Tracking stats
    parcel_count = 0
    filtered_by_compactness = 0
    filtered_by_upzone = 0
    added_to_registry = 0
    
    with timer(f"{policy_name} - Processing Parcels"):
        for parcel in result.mappings():
            parcel_count += 1
            
            # Parse geometry (already precision-truncated in DB)
            geom = json.loads(parcel['geometry_geojson'])
            
            # Compactness filtering now done in SQL query (polsby_popper_score >= 0.3)
            # No need to calculate it here anymore!

            # Find the best applicable ring
            applicable_ring = next((r for r in sorted_rings if parcel[distance_column] <= r.distance), None)

            # UPZONE FILTER: Only include if proposed height > current max height
            current_max_stories = get_max_stories_from_zone(parcel['zone_district'])
            if applicable_ring.height <= current_max_stories:
                # Not an upzone - skip this parcel
                filtered_by_upzone += 1
                continue
            
            if applicable_ring:
                p_id = parcel['parcel_id']
                new_height = applicable_ring.height
                
                # Winner Logic: Only add/update if this policy offers a taller building
                if p_id not in global_registry or new_height > global_registry[p_id]['properties']['assigned_height']:
                    added_to_registry += 1
                    
                    # Pre-convert numeric values once
                    land_area = float(parcel['land_area_acres'])
                    land_val = float(parcel['land_value']) if parcel['land_value'] else 0
                    improvement_val = float(parcel['improvement_value']) if parcel['improvement_value'] else 0
                    
                    upa = STORIES_TO_UPA.get(new_height, new_height * 20)
                    potential_units = int(land_area * upa)

                    bldg_sqft = float(parcel['res_above_grade_area'] or 0)
                    if bldg_sqft == 0:
                        bldg_sqft = float(parcel['com_gross_area'] or 0)
                    
                    bldg_age_year = parcel['res_orig_year_built'] or parcel['com_orig_year_built']

                    global_registry[p_id] = {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": {
                            "parcel_id": p_id,
                            "address": parcel['address'],
                            "zone_district": parcel['zone_district'],
                            "land_area_acres": round(land_area, 3),
                            "property_type": parcel['property_type'],
                            "property_class": parcel['property_class'],
                            "owner_name": parcel['owner_name'],
                            "owner_type": parcel['owner_type'],
                            "land_value": round(land_val),
                            "improvement_value": round(improvement_val),
                            "building_sqft": round(bldg_sqft),
                            "building_age": bldg_age_year,
                            "current_units": parcel['current_units'],
                            "opportunity_type": parcel['opportunity_type'],
                            "assigned_height": new_height,
                            "assigned_zone": applicable_ring.zone,
                            "potential_units": potential_units,
                            "policy_source": policy_name,
                            "ring_density": applicable_ring.density,
                            "distance_to_feature": round(float(parcel[distance_column]))
                        }
                    }
    
    # Print stats for this policy
    print(f"📊 {policy_name}: {parcel_count} parcels examined, {filtered_by_upzone} filtered by upzone, {added_to_registry} added to registry")

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

@lru_cache(maxsize=256)
def get_max_stories_from_zone(zone_district: str) -> float:
    """
    Determine maximum allowed stories from current zone district.
    Returns the max stories allowed by the current zoning.
    Handles modern Denver Zoning Code and Chapter 59 (Old Code) special cases.
    
    Cached with LRU cache for performance (same zones looked up repeatedly).
    """
    if not zone_district:
        return 0
    
    zone = zone_district.upper()

    # --- CHAPTER 59 / CENTRAL PARK SPECIAL CASES ---
    # R-MU-20 (55') -> ~5 stories
    if 'R-MU-20' in zone:
        return 5.0
    # R-MU-30 (140') -> ~12 stories
    if 'R-MU-30' in zone:
        return 12.0
    # C-MU zones (FAR 1.0) -> ~2.5 stories (conservative estimate for FAR 1.0)
    if 'C-MU-20' in zone or 'C-MU-30'in zone:
        return 2.5

    # --- CHAPTER 59 RESIDENTIAL OVERRIDES ---
    # R-2-A is a high-density legacy zone (110 feet)
    if 'R-2-A' in zone:
        return 10.0
        
    # R-0, R-1, R-2 are standard low-density (30-35 feet)
    # We use 2.5 to represent the typical 2-story + attic house
    if any(r_zone in zone for r_zone in ['R-0', 'R-1', 'R-2']) and 'R-2-A' not in zone and 'R-2-B' not in zone:
        return 2.5
        
    # R-2-B is slightly more permissive than R-2 but still low-rise
    if 'R-2-B' in zone:
        return 3.0

    # --- CHAPTER 59 "B" ZONES (Business Districts) ---
    # B-1, B-2, B-3 are 1.0 FAR -> ~2.5 stories
    if any(b_zone in zone for b_zone in ['B-1', 'B-2', 'B-3']):
        # Note: B-1 can be 2.0 FAR on >1 acre lots, but 2.5 is the safe baseline
        return 2.5
        
    # B-4 is 2.0 FAR -> ~5 stories
    if 'B-4' in zone:
        return 5.0

    # B-A zones (Business Agricultural) are very low density
    if 'B-A' in zone:
        return 2.5
    
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
        return 3
    
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

# this is supposed to Gzip the response to make it smaller for the browser
app.add_middleware(GZipMiddleware, minimum_size=1000)


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
            # Parse the geojson string (already precision-truncated in DB)
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
    
    print("\n" + "="*70)
    print("🚀 Starting evaluate_policies")
    print("="*70)
    
    with timer("TOTAL evaluate_policies"):
        # Registry to handle "Highest Height Wins" across different policy types
        global_registry = {}

        # --- 1) Evaluate Transit (TOD) ---
        if config.tod.enabled:
            with timer("TOD Policy - Total"):
                evaluate_spatial_policy(
                    db, "TOD", config.tod.rings, "distance_to_light_rail", global_registry, config.exclude_unlikely
                )

        # --- 2) Evaluate Parks (POD) ---
        if config.pod.enabled:
            with timer("POD-Regional Policy - Total"):
                evaluate_spatial_policy(
                    db, "POD-Regional", config.pod.regional_parks, "distance_to_regional_park", global_registry, config.exclude_unlikely
                )
            with timer("POD-Community Policy - Total"):
                evaluate_spatial_policy(
                    db, "POD-Community", config.pod.community_parks, "distance_to_community_park", global_registry, config.exclude_unlikely
                )

        # --- 3) Evaluate Bus (BOD) ---
        if config.bod and config.bod.enabled:
            # BOD-BRT: Bus Rapid Transit lines
            if config.bod.brt_enabled:
                with timer("BOD-BRT Policy - Total"):
                    evaluate_spatial_policy(
                        db, "BOD-BRT", config.bod.brt_rings, "distance_to_brt", global_registry, config.exclude_unlikely
                    )
            
            # BOD-Bus: Medium-frequency bus stops
            if config.bod.bus_enabled:
                with timer("BOD-Bus Policy - Total"):
                    evaluate_spatial_policy(
                        db, "BOD-Bus", config.bod.bus_rings, "distance_to_med_freq_bus", global_registry, config.exclude_unlikely
                    )

        # Construct Final Response
        with timer("Building GeoJSON Response"):
            features = list(global_registry.values())

        # --- 2) Aggregate Statistics ---
        with timer("Aggregating Statistics"):
            total_units = 0
            
            policy_stats = {}
            tier_stats = {
                "high": {"parcels": 0, "units": 0},
                "med": {"parcels": 0, "units": 0},
                "low": {"parcels": 0, "units": 0}
            }

            for f in features:
                p = f['properties']
                units = p['potential_units']
                height = p['assigned_height']
                source = p['policy_source']
                
                total_units += units

                # Determine the parent group (e.g., POD-Regional -> POD, BOD-BRT -> BOD)
                if "POD-" in source:
                    group = "POD"
                elif "BOD-" in source:
                    group = "BOD"
                else:
                    group = source
                
                # Track both the specific source and the roll-up group
                for key in [source, group]:
                    if key not in policy_stats:
                        policy_stats[key] = {"parcels": 0, "units": 0}
                    policy_stats[key]["parcels"] += 1
                    policy_stats[key]["units"] += units


                # the following is wrong. we need to calculate 
                # height based on the passed in params - not hard code to 8 and 5
                # B) Tier Breakdown
                if height >= 8:
                    tier = "high"
                elif height >= 5:
                    tier = "med"
                else:
                    tier = "low"
                    
                tier_stats[tier]["parcels"] += 1
                tier_stats[tier]["units"] += units
    
    print("="*70)
    print(f"✅ Completed: {len(features)} parcels, {total_units:,} units")
    print("="*70 + "\n")

    response_data = {
        "summary": {
            "total_units": total_units,
            "total_parcels": len(features),
            "by_policy": policy_stats,
            "by_density": tier_stats
        },
        "geojson": {
            "type": "FeatureCollection",
            "features": features
        }
    }

    # Use orjson for faster serialization of the large GeoJSON response
    if HAS_ORJSON:
        return ORJSONResponse(content=response_data)
    return response_data

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)