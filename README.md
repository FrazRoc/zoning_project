# Mile High Potential

Interactive mapping tool visualizing transit-oriented development opportunities in Denver, comparing current zoning vs. a proposed YIMBY ballot initiative.

## Overview

This project identifies over 2,000 parcels near RTD light rail stations with significant redevelopment potential, showing how a ballot measure could unlock an additional ~94,000 housing units through strategic upzoning.

**Live Demo:** [View the map](https://frazroc.github.io/zoning_project/denver_tod_with_parcels_v2.html)

## Features

- **Interactive Toggle:** Switch between "Current Zoning" and "After Ballot Measure" scenarios
- **6 Opportunity Categories:** Large Vacant Land, SF on Multi-Unit Zoning, Commercial on Mixed-Use, Industrial Conversion, Industrial Needs Rezoning, Teardown Candidates
- **Detailed Parcel Data:** Click any parcel to see zoning, size, property type, assessed values, and development potential
- **Ballot Measure Tiers:** Visualize the proposed 3-tier upzoning system (8, 5, and 3 stories based on distance from stations)
- **Professional UI:** Built with Tailwind CSS for a clean, modern interface

## Data Pipeline

The project uses a reproducible data pipeline to generate all analysis from source data.

### Prerequisites

```bash
# Install required Python packages
pip install geopandas pandas folium shapely pyogrio --break-system-packages

# Or create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install geopandas pandas folium shapely pyogrio
```

### Step 1: Filter Parcels Near Transit

Extract parcels within 3/8 mile (1,980 feet) of RTD light rail stations. This distance matches the ballot measure's maximum upzoning radius.

```bash
python filter_parcels_near_transit.py
```

**Input:**
- Downloads RTD station data from ArcGIS API
- Reads `ODC_PROP_PARCELS_A_4007222418780288709.geojson` (~770MB Denver parcel file)

**Output:**
- `transit_buffer_three_eighths_mile.geojson` - Buffer polygon showing 3/8 mile coverage
- `parcels_near_transit.geojson` - Filtered parcels within transit zone

**Duration:** ~1-2 minutes

### Step 2: Classify Opportunity Types

Analyze filtered parcels to identify redevelopment opportunities based on land use, zoning, and property characteristics.

```bash
python improved_parcel_filter.py
```

**Input:**
- `parcels_near_transit.geojson`
- Denver zoning district data

**Output:**
- `high_opportunity_parcels_v2.geojson` - Parcels classified by opportunity type with development potential calculations

**Classifications:**
1. **Large Vacant Land** - Vacant parcels over 0.5 acres
2. **SF on Multi-Unit Zoning** - Single-family homes on multi-unit zoned land
3. **Commercial on Mixed-Use Zoning** - Commercial buildings on mixed-use zones
4. **Industrial Conversion** - Industrial properties on residential/mixed-use zones
5. **Industrial Needs Rezoning** - Industrial parcels that would require rezoning
6. **Teardown Candidates** - Underutilized properties (low improvement-to-land value ratio)

**Duration:** ~30-60 seconds

### Step 3: Calculate Ballot Measure Impacts

Apply the proposed ballot measure's 3-tier upzoning system and calculate development potential for both scenarios.

```bash
python calculate_ballot_measure.py
```

**Input:**
- `high_opportunity_parcels_v2.geojson`
- `rtd_lightrail_stations.geojson`

**Output:**
- `ballot_measure_parcels.geojson` - Parcels with both current and ballot measure zoning/units
- `ballot_measure_summary.csv` - Summary statistics by opportunity type

**Ballot Measure Tiers:**
- **Tier 1 (≤660 ft):** C-MX-8x (8 stories, FAR 8.0)
- **Tier 2 (≤1,320 ft):** G-RX-5x (5 stories, FAR 3.0)
- **Tier 3 (≤1,980 ft):** G-MU-3x (3 stories, FAR 1.5)

**Key Rule:** Only upzones - existing more permissive zoning is preserved

**Duration:** ~20-30 seconds

### Step 4: Generate Interactive Map

Create the final interactive web map with toggle functionality.

```bash
python add_parcels_to_map.py
```

**Input:**
- `ballot_measure_parcels.geojson` (from Step 3)
- `rtd_lightrail_lines.geojson`
- `rtd_lightrail_stations.geojson`
- `ODC_ZONE_ZONING_A_-6072697703037489513.geojson`

**Output:**
- `denver_tod_with_parcels_v2.html` - Interactive map

**Duration:** ~60-90 seconds

## Complete Pipeline Example

```bash
cd ~/zoning_project

# Step 1: Filter to 3/8 mile radius
python filter_parcels_near_transit.py

# Step 2: Classify opportunities
python improved_parcel_filter.py

# Step 3: Calculate ballot measure impacts
python calculate_ballot_measure.py

# Step 4: Generate map
python add_parcels_to_map.py

# Open the result
open denver_tod_with_parcels_v2.html  # macOS
# or
xdg-open denver_tod_with_parcels_v2.html  # Linux
# or just double-click the file
```

## Results

### Current Zoning Scenario
- **2,131 parcels** are legally developable today for residential use
- **~440,000 potential housing units** based on current zoning
- Excludes 390 industrial parcels that would require rezoning

### After Ballot Measure Scenario
- **2,521 parcels** would be developable (includes upzoned industrial land)
- **~534,000 potential housing units** with ballot measure upzoning
- **+94,187 units (+21.4%)** increase in housing capacity

## Methodology

### Unit Calculations

Potential housing units are estimated using:
- **Floor Area Ratio (FAR)** or story height from Denver zoning code
- **1,500 sq ft per unit** (gross) - accounts for:
  - Average unit size: ~900 sq ft (mix of studios, 1BR, 2BR)
  - Building efficiency: ~60% (common areas, lobbies, elevators, parking, mechanical)

### Distance Calculations

All distances are measured to the nearest RTD light rail station using geodesic calculations projected to UTM Zone 13N.

### Data Sources

- **Parcel Data:** [Denver Open Data Catalog](https://www.denvergov.org/opendata) - Property boundaries, zoning, assessed values
- **Zoning Districts:** [Denver Open Data Catalog](https://www.denvergov.org/opendata) - Current zoning designations  
- **Transit Data:** [RTD GIS](https://www.rtd-denver.com/developer-resources) - Light rail lines and station locations

## Project Structure

```
zoning_project/
├── README.md                                    # This file
├── filter_parcels_near_transit.py              # Step 1: Initial spatial filter
├── improved_parcel_filter.py                   # Step 2: Opportunity classification
├── calculate_ballot_measure.py                 # Step 3: Ballot measure analysis
├── add_parcels_to_map.py                       # Step 4: Map generation
├── about.html                                   # About page
├── denver_tod_with_parcels_v2.html             # Generated map (output)
│
├── Data Files (generated):
├── transit_buffer_three_eighths_mile.geojson   # 3/8 mile buffer polygon
├── parcels_near_transit.geojson                # Spatially filtered parcels
├── high_opportunity_parcels_v2.geojson         # Classified opportunities
├── ballot_measure_parcels.geojson              # With ballot calculations
└── ballot_measure_summary.csv                  # Summary statistics
```

## Limitations

- **Market Feasibility:** Not all opportunities are economically viable to develop
- **Site Constraints:** Flood zones, contamination, slopes, and other physical limitations not considered
- **Owner Intent:** Property owners may not wish to sell or redevelop
- **Community Impact:** Development must balance growth with neighborhood character and displacement concerns
- **Infrastructure:** Water, sewer, and utilities may require upgrades
- **Theoretical Maximum:** Calculations assume full buildout to zoning limits

## Technologies

- **Python:** Data processing and analysis
- **GeoPandas:** Geospatial data manipulation
- **Folium:** Interactive web mapping
- **Tailwind CSS:** UI styling
- **GitHub Pages:** Hosting

## Contributing

This project was created for YIMBY Denver advocacy. Contributions, feedback, and suggestions are welcome!

## Future Enhancements

- [ ] Automated data refresh pipeline (backend service)
- [ ] Additional metrics (walkability scores, transit frequency, jobs access)
- [ ] Historical tracking of development activity
- [ ] Integration with Denver building permits
- [ ] Mobile-responsive improvements
- [ ] Comparison with other cities

## License

Data sources are from Denver Open Data and RTD, used under their respective open data licenses.

## Contact

Created by Evan Fraser for YIMBY Denver
- **GitHub:** [github.com/FrazRoc/zoning_project](https://github.com/FrazRoc/zoning_project)
- **Map:** [frazroc.github.io/zoning_project](https://frazroc.github.io/zoning_project/denver_tod_with_parcels_v2.html)

---

*Last updated: January 2026*
