"""
Generate About Page with Dynamic Statistics
============================================
This script reads the ballot measure data and generates about.html
with current statistics embedded in the page.
"""

import geopandas as gpd

print("="*70)
print("GENERATING ABOUT PAGE WITH CURRENT STATISTICS")
print("="*70)

# ============================================================================
# LOAD DATA AND CALCULATE STATS
# ============================================================================

print("\n1. Loading data...")
parcels = gpd.read_file('ballot_measure_parcels.geojson')

print(f"   ✓ Loaded {len(parcels):,} parcels")

# Calculate stats
current_parcels = parcels[parcels['opportunity_type'] != 'Industrial Near Transit'].copy()
ballot_parcels = parcels.copy()

current_units = current_parcels['potential_units'].sum()
ballot_units = ballot_parcels['ballot_potential_units'].sum()
increase = ballot_units - current_units
increase_pct = (increase / current_units) * 100

print(f"\n   Current scenario: {len(current_parcels):,} parcels, {current_units:,.0f} units")
print(f"   Ballot scenario: {len(ballot_parcels):,} parcels, {ballot_units:,.0f} units")
print(f"   Increase: +{increase:,.0f} units (+{increase_pct:.1f}%)")

# Calculate industrial parcels excluded from current
industrial_excluded = len(ballot_parcels) - len(current_parcels)

# ============================================================================
# GENERATE HTML
# ============================================================================

print("\n2. Generating about.html...")

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About - Mile High Potential</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem 2rem;
            text-align: center;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            font-weight: 800;
        }}
        
        header p {{
            font-size: 1.1rem;
            opacity: 0.95;
        }}
        
        nav {{
            background: #5a67d8;
            padding: 1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        nav a {{
            color: white;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            transition: background 0.3s;
        }}
        
        nav a:hover {{
            background: rgba(255,255,255,0.1);
        }}
        
        .container {{
            max-width: 900px;
            margin: 2rem auto;
            padding: 0 2rem;
        }}
        
        .content-section {{
            background: white;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        h2 {{
            color: #2d3748;
            font-size: 1.8rem;
            margin-bottom: 1rem;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.5rem;
        }}
        
        h3 {{
            color: #4a5568;
            font-size: 1.3rem;
            margin: 1.5rem 0 1rem;
        }}
        
        p {{
            margin-bottom: 1rem;
        }}
        
        ul {{
            margin-left: 2rem;
            margin-bottom: 1rem;
        }}
        
        li {{
            margin-bottom: 0.5rem;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}
        
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .stat-box .number {{
            display: block;
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        
        .stat-box .label {{
            display: block;
            font-size: 0.9rem;
            opacity: 0.9;
        }}
        
        .highlight-box {{
            background: #edf2f7;
            border-left: 4px solid #667eea;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        }}
        
        .cta-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 8px;
            text-align: center;
        }}
        
        .cta-section h2 {{
            color: white;
            border-bottom: none;
        }}
        
        .btn {{
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 0.75rem 2rem;
            margin: 0.5rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        
        footer {{
            background: #2d3748;
            color: white;
            padding: 2rem;
            text-align: center;
            margin-top: 3rem;
        }}
        
        footer a {{
            color: #90cdf4;
            text-decoration: none;
        }}
        
        footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Mile High Potential</h1>
        <p>Understanding transit-oriented development opportunities in Denver</p>
    </header>
    
    <nav>
        <a href="denver_tod_with_parcels_v2.html">← Back to Interactive Map</a>
    </nav>
    
    <div class="container">
        <!-- Overview Section -->
        <section class="content-section">
            <h2>What is This?</h2>
            <p>
                Mile High Potential is an interactive mapping tool that visualizes development opportunities near Denver's 
                RTD light rail stations. It compares current zoning with a proposed ballot measure that would allow more 
                housing near transit.
            </p>
            
            <div class="highlight-box">
                <strong>Current Zoning:</strong> Shows {len(current_parcels):,} parcels that are legally developable today with potential for 
                approximately {int(current_units):,} housing units near RTD light rail stations (within 3/8 mile).<br><br>
                <strong>After Ballot Measure:</strong> Shows {len(ballot_parcels):,} parcels (including {industrial_excluded} newly upzoned industrial parcels) with 
                potential for approximately {int(ballot_units):,} housing units — an increase of <strong>+{int(increase):,} units (+{increase_pct:.1f}%)</strong>.
            </div>
            
            <p>
                By comparing these scenarios side-by-side, you can see exactly how the ballot measure would unlock 
                housing potential across Denver's transit network. Toggle between views to explore the differences 
                and click individual parcels to see detailed information.
            </p>
            
            <div class="stats">
                <div class="stat-box">
                    <span class="number">{len(current_parcels):,}</span>
                    <span class="label">Current Opportunity Parcels</span>
                </div>
                <div class="stat-box">
                    <span class="number">{len(ballot_parcels):,}</span>
                    <span class="label">After Ballot Measure</span>
                </div>
                <div class="stat-box">
                    <span class="number">+{increase_pct:.1f}%</span>
                    <span class="label">Housing Capacity Increase</span>
                </div>
            </div>
        </section>
        
        <!-- How It Works Section -->
        <section class="content-section">
            <h2>How It Works</h2>
            
            <h3>The Interactive Map</h3>
            <p>
                The map shows parcels color-coded by opportunity type. Use the toggle at the top to switch between 
                "Current Zoning" and "After Ballot Measure" scenarios.
            </p>
            
            <h3>Opportunity Categories</h3>
            <ul>
                <li><strong>Large Vacant Land:</strong> Vacant parcels over 0.5 acres ready for development</li>
                <li><strong>SF on Multi-Unit Zoning:</strong> Single-family homes on land zoned for apartments</li>
                <li><strong>Commercial on Mixed-Use Zoning:</strong> Commercial buildings in mixed-use zones that could add housing</li>
                <li><strong>Industrial Conversion:</strong> Industrial properties already zoned for residential conversion</li>
                <li><strong>Industrial Needs Rezoning:</strong> Industrial land that would be upzoned by the ballot measure</li>
                <li><strong>Teardown Candidates:</strong> Aging structures where land value exceeds building value</li>
            </ul>
            
            <h3>The Ballot Measure</h3>
            <p>The proposed ballot measure would create three zoning tiers based on distance from RTD light rail stations:</p>
            <ul>
                <li><strong>Tier 1 (≤660 feet):</strong> C-MX-8x zoning → 8 stories allowed</li>
                <li><strong>Tier 2 (≤1,320 feet):</strong> G-RX-5x zoning → 5 stories allowed</li>
                <li><strong>Tier 3 (≤1,980 feet):</strong> G-MU-3x zoning → 3 stories allowed</li>
            </ul>
            
            <div class="highlight-box">
                <strong>Important:</strong> The ballot measure only upzones — it never downzones. If existing zoning 
                already allows more height, that zoning is preserved.
            </div>
        </section>
        
        <!-- Methodology Section -->
        <section class="content-section">
            <h2>Methodology</h2>
            
            <h3>Unit Calculations</h3>
            <p>
                Potential housing units are calculated using empirical "units per acre" ratios based on real-world 
                development patterns. These ratios account for building efficiency, parking, setbacks, and common areas.
            </p>
            
            <p><strong>Units per Acre by Building Height:</strong></p>
            <ul>
                <li>2-3 stories: 30-60 units/acre (townhomes, walk-ups)</li>
                <li>5 stories: 100 units/acre (mid-rise, no elevator required)</li>
                <li>7-10 stories: 160 units/acre (mid-rise with elevators)</li>
                <li>12+ stories: 220-450 units/acre (high-rise)</li>
            </ul>
            
            <h3>Two Scenarios</h3>
            
            <p><strong>Current Zoning Scenario:</strong></p>
            <ul>
                <li>Includes only parcels that are <em>legally developable today</em> for residential use</li>
                <li>Excludes {industrial_excluded} industrial-zoned parcels that would require rezoning (I-A/I-B zones)</li>
                <li>Based on existing Denver zoning code height limits and development rights</li>
                <li>Total: {len(current_parcels):,} parcels with approximately {int(current_units):,} potential units</li>
            </ul>
            
            <p><strong>After Ballot Measure Scenario:</strong></p>
            <ul>
                <li>Applies ballot measure upzoning tiers based on distance to rail stations (3 tiers within 3/8 mile)</li>
                <li>Includes formerly industrial parcels that would be upzoned to residential/mixed-use</li>
                <li>Preserves existing zoning if it's already more permissive (never downzones)</li>
                <li>Total: {len(ballot_parcels):,} parcels with approximately {int(ballot_units):,} potential units (+{increase_pct:.1f}%)</li>
            </ul>
            
            <div class="highlight-box">
                <strong>Note:</strong> These are theoretical maximums based on zoning. Actual development would be constrained 
                by economic feasibility, site conditions, parking requirements, historic preservation, and community input.
            </div>
            
            <h3>Data Sources</h3>
            <ul>
                <li><strong>Parcel Data:</strong> Denver Open Data Catalog</li>
                <li><strong>Zoning Data:</strong> Denver Open Data Catalog</li>
                <li><strong>Transit Data:</strong> RTD GIS Services</li>
            </ul>
        </section>
        
        <!-- Limitations Section -->
        <section class="content-section">
            <h2>Limitations & Considerations</h2>
            <ul>
                <li><strong>Market Feasibility:</strong> Not all opportunities are economically viable to develop</li>
                <li><strong>Site Constraints:</strong> Flood zones, contamination, slopes, and other physical limitations not considered</li>
                <li><strong>Owner Intent:</strong> Property owners may not wish to sell or redevelop</li>
                <li><strong>Community Impact:</strong> Development must balance growth with neighborhood character and displacement concerns</li>
                <li><strong>Infrastructure:</strong> Water, sewer, and utilities may require upgrades</li>
                <li><strong>Theoretical Maximum:</strong> Calculations assume full buildout to zoning limits, which rarely occurs in practice</li>
            </ul>
        </section>
        
        <!-- Call to Action -->
        <section class="cta-section">
            <h2>Explore the Data</h2>
            <p>Ready to dive in? The interactive map lets you click on individual parcels to see detailed information about each opportunity.</p>
            <a href="denver_tod_with_parcels_v2.html" class="btn">View Interactive Map</a>
        </section>
    </div>
    
    <footer>
        <p>
            Created for <strong>YIMBY Denver</strong> | 
            <a href="https://github.com/FrazRoc/zoning_project" target="_blank">View on GitHub</a>
        </p>
        <p style="margin-top: 0.5rem; font-size: 0.9rem; opacity: 0.8;">
            Last updated: {ballot_parcels['ballot_zone'].iloc[0] if len(ballot_parcels) > 0 else 'Unknown'}
        </p>
    </footer>
</body>
</html>
'''

# ============================================================================
# SAVE HTML FILE
# ============================================================================

output_file = 'about.html'
with open(output_file, 'w') as f:
    f.write(html_content)

print(f"\n✓ Generated {output_file}")
print(f"   Current: {len(current_parcels):,} parcels, ~{int(current_units/1000)}K units")
print(f"   Ballot: {len(ballot_parcels):,} parcels, ~{int(ballot_units/1000)}K units (+{increase_pct:.1f}%)")
print("\n" + "="*70)
