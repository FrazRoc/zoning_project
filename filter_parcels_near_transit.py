# filter_parcels_near_transit.py
# Extract only parcels within 3/8 mile of transit stations (matching ballot measure scope)

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

print("=" * 70)
print("FILTERING PARCELS NEAR TRANSIT (3/8 MILE)")
print("=" * 70)

# Load stations
print("\n1. Loading RTD stations...")
stations_url = "https://services5.arcgis.com/1fZoXlzLW6FCIUcE/arcgis/rest/services/RTD_GIS_Current_Runboard/FeatureServer/1/query?where=1%3D1&outFields=*&f=geojson"
stations = gpd.read_file(stations_url)
print(f"   Loaded {len(stations)} stations")

# Project to meters for buffering
print("\n2. Creating 3/8 mile buffer around all stations...")
stations_proj = stations.to_crs('EPSG:32613')  # UTM Zone 13N

# Create buffers and merge - 3/8 mile = 1,980 feet = 603.5 meters
buffers = [station.geometry.buffer(603.5) for idx, station in stations_proj.iterrows()]
merged_buffer = unary_union(buffers)

# Create a GeoDataFrame with the merged buffer
buffer_gdf = gpd.GeoDataFrame({'geometry': [merged_buffer]}, crs='EPSG:32613')
buffer_wgs84 = buffer_gdf.to_crs('EPSG:4326')

print(f"   Created merged buffer covering transit-accessible area (3/8 mile)")

# Save the buffer for reference
buffer_wgs84.to_file('parcels_near_transit.geojson', driver='GeoJSON')
print(f"   Saved buffer to: parcels_near_transit.geojson")

# Now filter parcels
print("\n3. Loading and filtering parcels...")
print("   (This may take 1-2 minutes with 770MB file...)")

parcel_file = 'ODC_PROP_PARCELS_A_4007222418780288709.geojson'

# Use spatial filter directly when reading
parcels_near_transit = gpd.read_file(
    parcel_file,
    mask=buffer_wgs84,  # This filters spatially during read!
    engine='pyogrio'
)

print(f"\n✓ Filtered to {len(parcels_near_transit):,} parcels near transit")
print(f"   Original file: ~770MB")
print(f"   Filtered dataset: {len(parcels_near_transit):,} parcels")
print(f"   Reduction: {(1 - len(parcels_near_transit)/200000) * 100:.1f}% (estimated)")

# Save the filtered dataset
output_file = 'parcels_near_transit.geojson'
print(f"\n4. Saving filtered parcels to: {output_file}")
parcels_near_transit.to_file(output_file, driver='GeoJSON')

import os
output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
print(f"   File size: {output_size_mb:.1f} MB")

print("\n" + "=" * 70)
print("FILTERED PARCEL SUMMARY:")
print("=" * 70)

# Property types
print("\nProperty Types:")
print(parcels_near_transit['D_CLASS_CN'].value_counts().head(10))

# Zoning
print("\nTop Zoning Districts:")
print(parcels_near_transit['ZONE_10'].value_counts().head(10))

# Building presence
has_res_building = (parcels_near_transit['RES_ABOVE_GRADE_AREA'] > 0).sum()
has_com_building = (parcels_near_transit['COM_GROSS_AREA'] > 0).sum()
no_building = ((parcels_near_transit['RES_ABOVE_GRADE_AREA'].isna() | (parcels_near_transit['RES_ABOVE_GRADE_AREA'] == 0)) & 
               (parcels_near_transit['COM_GROSS_AREA'].isna() | (parcels_near_transit['COM_GROSS_AREA'] == 0))).sum()

print(f"\nBuilding Status:")
print(f"  Residential buildings: {has_res_building:,}")
print(f"  Commercial buildings: {has_com_building:,}")
print(f"  No buildings (vacant/parking): {no_building:,}")

# Units
total_units = parcels_near_transit['TOT_UNITS'].sum()
print(f"\nTotal dwelling units near transit: {total_units:,.0f}")

# Land area
total_land_sqft = parcels_near_transit['LAND_AREA'].sum()
total_land_acres = total_land_sqft / 43560
print(f"\nTotal land area near transit:")
print(f"  {total_land_sqft:,.0f} sq ft")
print(f"  {total_land_acres:,.1f} acres")
print(f"  {total_land_acres / 640:.1f} sq miles")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("""
Now we can analyze:
1. Underutilized parcels (large land, small/no building)
2. Single-family on multi-unit zoning
3. Old buildings (redevelopment candidates)
4. Vacant land / parking lots near stations
5. Land value vs improvement value (tear-down potential)

The filtered dataset is much more manageable!
Ready to continue with analysis?
""")