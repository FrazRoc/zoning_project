"""
Download RTD Light Rail Stations and Lines from RTD's Open Data Portal
"""
import requests
import json

print("="*70)
print("DOWNLOADING RTD LIGHT RAIL DATA FROM OPEN DATA PORTAL")
print("="*70)

# RTD OpenData Portal - Direct GeoJSON download links
# These are the dataset IDs from gis-rtd-denver.opendata.arcgis.com

# ============================================================================
# DOWNLOAD STATIONS (LightrailStations dataset)
# ============================================================================

print("\n1. Downloading light rail stations...")
# Dataset ID: e14366d810644a3c95a4f3770799bd54_1
station_url = "https://opendata.arcgis.com/api/v3/datasets/e14366d810644a3c95a4f3770799bd54_1/downloads/data?format=geojson&spatialRefId=4326"

try:
    print("   Requesting data from RTD Open Data Portal...")
    response = requests.get(station_url, timeout=60)
    
    if response.status_code == 200:
        stations = response.json()
        
        station_count = len(stations.get('features', []))
        print(f"   ✓ Downloaded {station_count} stations")
        
        # Save to file
        with open('rtd_lightrail_stations.geojson', 'w') as f:
            json.dump(stations, f, indent=2)
        
        print(f"   ✓ Saved to: rtd_lightrail_stations.geojson")
        
        # Show sample
        if stations.get('features'):
            first = stations['features'][0]['properties']
            print(f"\n   Sample station:")
            print(f"     Name: {first.get('NAME', first.get('name'))}")
            print(f"     Address: {first.get('ADDRESS', first.get('address'))}")
    else:
        print(f"   ✗ Error: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   ✗ Error downloading stations: {e}")

# ============================================================================
# DOWNLOAD RAIL LINES (LightrailLines_Offset dataset)
# ============================================================================

print("\n2. Downloading light rail lines...")
# Dataset ID: e14366d810644a3c95a4f3770799bd54_3
lines_url = "https://opendata.arcgis.com/api/v3/datasets/e14366d810644a3c95a4f3770799bd54_3/downloads/data?format=geojson&spatialRefId=4326"

try:
    print("   Requesting data from RTD Open Data Portal...")
    response = requests.get(lines_url, timeout=60)
    
    if response.status_code == 200:
        lines = response.json()
        
        line_count = len(lines.get('features', []))
        print(f"   ✓ Downloaded {line_count} line segments")
        
        # Save to file
        with open('rtd_lightrail_lines.geojson', 'w') as f:
            json.dump(lines, f, indent=2)
        
        print(f"   ✓ Saved to: rtd_lightrail_lines.geojson")
        
        # Show unique lines
        if lines.get('features'):
            unique_lines = set()
            for feature in lines['features']:
                route = feature['properties'].get('ROUTE') or feature['properties'].get('route')
                name = feature['properties'].get('NAME') or feature['properties'].get('name')
                if route:
                    unique_lines.add(f"{route} Line")
            
            print(f"\n   Rail lines found ({len(unique_lines)}):")
            for line in sorted(unique_lines):
                print(f"     - {line}")
    else:
        print(f"   ✗ Error: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   ✗ Error downloading lines: {e}")

print("\n" + "="*70)
print("✓ DOWNLOAD COMPLETE")
print("="*70)
print("\nNext: Run add_parcels_to_map.py to create the full visualization")
