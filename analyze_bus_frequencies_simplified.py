"""
RTD Medium-Frequency Bus Stop Analysis
=======================================
Analyzes RTD GTFS data to identify bus stops with ≥2 trips/hour during peak times.

REQUIRED FILES (must be in same directory):
- stops.txt
- stop_times.txt  
- calendar.txt
- trips.txt
- routes.txt

OPTIONAL FILES:
- calendar_dates.txt (service exceptions)

Requirements:
    pip install pandas
"""

import os
import pandas as pd
from datetime import datetime, time
from collections import defaultdict
import json

print("="*70)
print("RTD MEDIUM-FREQUENCY BUS STOP ANALYSIS")
print("="*70)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Peak hours definition (6-9am, 4-7pm)
MORNING_PEAK_START = time(6, 0)
MORNING_PEAK_END = time(9, 0)
EVENING_PEAK_START = time(16, 0)
EVENING_PEAK_END = time(19, 0)

# Frequency threshold
MIN_FREQUENCY = 2  # trips per hour. EF 2/4/2026 changed this to 4 stops per hour after talking to Pardo and Greer

# Target month/year (ballot language specifies January 2026)
TARGET_YEAR = 2026
TARGET_MONTH = 1

# GTFS data directory (current directory by default)
GTFS_DIR = '.'

# Output directory
OUTPUT_DIR = 'bus_stop_data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# STEP 1: Check for required files
# ============================================================================

print("\n1. Checking for required GTFS files...")

required_files = ['stops.txt', 'stop_times.txt', 'calendar.txt', 'trips.txt', 'routes.txt']
optional_files = ['calendar_dates.txt']

missing_required = []
for filename in required_files:
    filepath = os.path.join(GTFS_DIR, filename)
    if os.path.exists(filepath):
        print(f"   ✓ Found {filename}")
    else:
        print(f"   ✗ Missing {filename}")
        missing_required.append(filename)

for filename in optional_files:
    filepath = os.path.join(GTFS_DIR, filename)
    if os.path.exists(filepath):
        print(f"   ✓ Found {filename} (optional)")
    else:
        print(f"   ℹ {filename} not found (optional)")

if missing_required:
    print(f"\n✗ ERROR: Missing required files: {', '.join(missing_required)}")
    print("\nPlease download RTD GTFS data from:")
    print("https://www.rtd-denver.com/open-records/open-spatial-information/gtfs")
    print("\nExtract these files to the current directory:")
    for f in required_files:
        print(f"  - {f}")
    exit(1)

# ============================================================================
# STEP 2: Load GTFS Files
# ============================================================================

print("\n2. Loading GTFS files...")

try:
    stops = pd.read_csv(f'{GTFS_DIR}/stops.txt')
    stop_times = pd.read_csv(f'{GTFS_DIR}/stop_times.txt')
    trips = pd.read_csv(f'{GTFS_DIR}/trips.txt')
    calendar = pd.read_csv(f'{GTFS_DIR}/calendar.txt')
    routes = pd.read_csv(f'{GTFS_DIR}/routes.txt')
    
    print(f"   ✓ Loaded {len(stops):,} stops")
    print(f"   ✓ Loaded {len(stop_times):,} stop times")
    print(f"   ✓ Loaded {len(trips):,} trips")
    print(f"   ✓ Loaded {len(calendar):,} calendar entries")
    print(f"   ✓ Loaded {len(routes):,} routes")
    
    # Load calendar_dates if available
    calendar_dates_file = f'{GTFS_DIR}/calendar_dates.txt'
    if os.path.exists(calendar_dates_file):
        calendar_dates = pd.read_csv(calendar_dates_file)
        print(f"   ✓ Loaded {len(calendar_dates):,} calendar date exceptions")
    else:
        calendar_dates = None
        print("   ℹ No calendar_dates.txt (optional)")

except Exception as e:
    print(f"\n✗ ERROR loading files: {e}")
    exit(1)

# ============================================================================
# STEP 3: Filter for Bus Routes Only
# ============================================================================

print("\n3. Filtering for bus routes (excluding rail)...")

# GTFS route_type values:
# 0 = Tram/Light Rail
# 1 = Subway/Metro
# 2 = Rail (Commuter rail, intercity)
# 3 = Bus
# 4 = Ferry
# 700-799 = Bus subtypes
# 800-899 = Trolleybus

bus_route_types = [3, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 
                   710, 711, 712, 713, 714, 715, 716, 717, 800, 899]

bus_routes = routes[routes['route_type'].isin(bus_route_types)].copy()
print(f"   ✓ Found {len(bus_routes):,} bus routes (out of {len(routes):,} total routes)")
print(f"   ℹ Excluding light rail, commuter rail, and other non-bus modes")

# ============================================================================
# STEP 4: Filter for January 2026 Service
# ============================================================================

print(f"\n4. Filtering for January {TARGET_YEAR} service...")

# Convert date columns to datetime
calendar['start_date'] = pd.to_datetime(calendar['start_date'], format='%Y%m%d')
calendar['end_date'] = pd.to_datetime(calendar['end_date'], format='%Y%m%d')

# January 2026 date range
jan_start = datetime(TARGET_YEAR, TARGET_MONTH, 1)
jan_end = datetime(TARGET_YEAR, TARGET_MONTH, 31)

# Find service_ids active in January 2026
active_service_ids = calendar[
    (calendar['start_date'] <= jan_end) & 
    (calendar['end_date'] >= jan_start)
]['service_id'].unique()

print(f"   ✓ Found {len(active_service_ids)} service patterns active in January {TARGET_YEAR}")

# Service patterns breakdown
weekday_services = calendar[
    (calendar['service_id'].isin(active_service_ids)) &
    (calendar['monday'] == 1) & (calendar['tuesday'] == 1) & 
    (calendar['wednesday'] == 1) & (calendar['thursday'] == 1) & 
    (calendar['friday'] == 1)
]['service_id'].unique()

weekend_services = calendar[
    (calendar['service_id'].isin(active_service_ids)) &
    ((calendar['saturday'] == 1) | (calendar['sunday'] == 1))
]['service_id'].unique()

print(f"   ℹ Weekday-only services: {len(weekday_services)}")
print(f"   ℹ Weekend services: {len(weekend_services)}")

# ============================================================================
# STEP 5: Filter Trips for Bus Routes in January 2026
# ============================================================================

print("\n5. Filtering trips...")

# Filter trips for active services and bus routes
jan_bus_trips = trips[
    (trips['service_id'].isin(weekday_services)) &
    (trips['route_id'].isin(bus_routes['route_id']))
].copy()

print(f"   ✓ {len(jan_bus_trips):,} weekday bus trips during January {TARGET_YEAR}")

# ============================================================================
# STEP 6: Analyze Peak Hour Frequencies
# ============================================================================

print("\n6. Analyzing peak hour frequencies...")

# Filter stop_times for our selected trips
jan_stop_times = stop_times[stop_times['trip_id'].isin(jan_bus_trips['trip_id'])].copy()
print(f"   ✓ {len(jan_stop_times):,} stop times for bus trips")

# Parse arrival times
def parse_time(time_str):
    """Parse HH:MM:SS time string, handling times >= 24:00:00"""
    try:
        h, m, s = map(int, str(time_str).split(':'))
        # Handle times past midnight (e.g., 25:30:00)
        if h >= 24:
            h = h - 24
        return time(h, m, s)
    except:
        return None

jan_stop_times['arrival_time_parsed'] = jan_stop_times['arrival_time'].apply(parse_time)

# Remove invalid times
jan_stop_times = jan_stop_times[jan_stop_times['arrival_time_parsed'].notna()]
print(f"   ✓ {len(jan_stop_times):,} valid stop times")

# Identify peak hour trips
def is_peak_hour(t):
    """Check if time is during morning or evening peak"""
    if t is None:
        return False
    return (
        (MORNING_PEAK_START <= t < MORNING_PEAK_END) or
        (EVENING_PEAK_START <= t < EVENING_PEAK_END)
    )

jan_stop_times['is_peak'] = jan_stop_times['arrival_time_parsed'].apply(is_peak_hour)
peak_stop_times = jan_stop_times[jan_stop_times['is_peak']]

print(f"   ✓ {len(peak_stop_times):,} stop times during peak hours (6-9am, 4-7pm)")

# ============================================================================
# STEP 7: Calculate Trips Per Hour by Stop
# ============================================================================

print("\n7. Calculating trips per hour for each stop...")

# Separate AM and PM peak periods
am_peak_times = jan_stop_times[
    (jan_stop_times['arrival_time_parsed'] >= MORNING_PEAK_START) &
    (jan_stop_times['arrival_time_parsed'] < MORNING_PEAK_END)
]

pm_peak_times = jan_stop_times[
    (jan_stop_times['arrival_time_parsed'] >= EVENING_PEAK_START) &
    (jan_stop_times['arrival_time_parsed'] < EVENING_PEAK_END)
]

print(f"   ℹ Morning peak: {len(am_peak_times):,} stop times")
print(f"   ℹ Evening peak: {len(pm_peak_times):,} stop times")

# Count unique trips per stop
am_counts = am_peak_times.groupby('stop_id')['trip_id'].nunique()
pm_counts = pm_peak_times.groupby('stop_id')['trip_id'].nunique()

# Calculate trips per hour (3 hour windows)
am_freq = (am_counts / 3).round(2)
pm_freq = (pm_counts / 3).round(2)

# Create frequency dataframe
stop_frequencies = pd.DataFrame({
    'stop_id': stops['stop_id'],
    'am_trips_per_hour': stops['stop_id'].map(am_freq).fillna(0),
    'pm_trips_per_hour': stops['stop_id'].map(pm_freq).fillna(0)
})

# Take the maximum frequency (highest between AM and PM)
stop_frequencies['peak_frequency'] = stop_frequencies[['am_trips_per_hour', 'pm_trips_per_hour']].max(axis=1)

print(f"   ✓ Calculated frequencies for {len(stop_frequencies):,} stops")

# ============================================================================
# STEP 8: Identify Medium-Frequency Stops
# ============================================================================

print(f"\n8. Identifying medium-frequency stops (≥{MIN_FREQUENCY} trips/hour)...")

# Filter for stops meeting threshold
med_freq_stops = stop_frequencies[stop_frequencies['peak_frequency'] >= MIN_FREQUENCY]['stop_id']

# Join with stops data to get coordinates
med_freq_stops_data = stops[stops['stop_id'].isin(med_freq_stops)].copy()
med_freq_stops_data = med_freq_stops_data.merge(
    stop_frequencies[['stop_id', 'peak_frequency', 'am_trips_per_hour', 'pm_trips_per_hour']], 
    on='stop_id'
)

print(f"\n   Total bus stops: {len(stops):,}")
print(f"   Stops with ≥{MIN_FREQUENCY} trips/hour during peak: {len(med_freq_stops_data):,}")
print(f"   Percentage: {len(med_freq_stops_data)/len(stops)*100:.1f}%")

# ============================================================================
# STEP 9: Export Results
# ============================================================================

print("\n9. Exporting results...")

# Export to CSV
csv_file = f'{OUTPUT_DIR}/medium_frequency_bus_stops.csv'
med_freq_stops_data.to_csv(csv_file, index=False)
print(f"   ✓ Saved to {csv_file}")

# Export to GeoJSON for visualization
geojson = {
    "type": "FeatureCollection",
    "features": []
}

for _, stop in med_freq_stops_data.iterrows():
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(stop['stop_lon']), float(stop['stop_lat'])]
        },
        "properties": {
            "stop_id": str(stop['stop_id']),
            "stop_name": stop['stop_name'],
            "peak_frequency": float(stop['peak_frequency']),
            "am_frequency": float(stop['am_trips_per_hour']),
            "pm_frequency": float(stop['pm_trips_per_hour'])
        }
    }
    geojson['features'].append(feature)

geojson_file = f'{OUTPUT_DIR}/medium_frequency_bus_stops.geojson'
with open(geojson_file, 'w') as f:
    json.dump(geojson, f, indent=2)

print(f"   ✓ Saved to {geojson_file}")

# ============================================================================
# STEP 10: Summary Statistics
# ============================================================================

print("\n10. Summary Statistics:")
print("="*70)

print(f"\n   Frequency Distribution:")
freq_2_3 = len(med_freq_stops_data[(med_freq_stops_data['peak_frequency'] >= 2) & (med_freq_stops_data['peak_frequency'] < 3)])
freq_3_4 = len(med_freq_stops_data[(med_freq_stops_data['peak_frequency'] >= 3) & (med_freq_stops_data['peak_frequency'] < 4)])
freq_4_6 = len(med_freq_stops_data[(med_freq_stops_data['peak_frequency'] >= 4) & (med_freq_stops_data['peak_frequency'] < 6)])
freq_6_plus = len(med_freq_stops_data[med_freq_stops_data['peak_frequency'] >= 6])

print(f"   2-3 trips/hour:  {freq_2_3:,} stops ({freq_2_3/len(med_freq_stops_data)*100:.1f}%)")
print(f"   3-4 trips/hour:  {freq_3_4:,} stops ({freq_3_4/len(med_freq_stops_data)*100:.1f}%)")
print(f"   4-6 trips/hour:  {freq_4_6:,} stops ({freq_4_6/len(med_freq_stops_data)*100:.1f}%)")
print(f"   6+ trips/hour:   {freq_6_plus:,} stops ({freq_6_plus/len(med_freq_stops_data)*100:.1f}%)")

print(f"\n   Top 10 Highest Frequency Stops:")
top_stops = med_freq_stops_data.nlargest(10, 'peak_frequency')[['stop_name', 'peak_frequency', 'am_trips_per_hour', 'pm_trips_per_hour']]
for idx, row in top_stops.iterrows():
    print(f"   {row['stop_name'][:50]:50s}: {row['peak_frequency']:4.1f}/hr (AM: {row['am_trips_per_hour']:4.1f}, PM: {row['pm_trips_per_hour']:4.1f})")

# Show some example stops
print(f"\n   Sample Medium-Frequency Stops:")
sample_stops = med_freq_stops_data.sample(min(5, len(med_freq_stops_data)))[['stop_name', 'peak_frequency']]
for idx, row in sample_stops.iterrows():
    print(f"   - {row['stop_name']}: {row['peak_frequency']:.1f} trips/hour")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print(f"\nOutput files:")
print(f"  {csv_file}")
print(f"  {geojson_file}")
print(f"\nNext steps:")
print(f"1. Review the CSV file to verify results")
print(f"2. Visualize the GeoJSON in QGIS or geojson.io")
print(f"3. Run setup_bus_stops.py to import to database")
