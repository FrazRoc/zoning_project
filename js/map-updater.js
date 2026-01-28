/**
 * Map Updater
 * Handles updating the Leaflet map with policy evaluation results
 */

class MapUpdater {
    constructor(map) {
        this.map = map;
        this.parcelLayer = null;
        
        // Colors for different rings
        this.colors = {
            ring1: '#FF0000',  // Red
            ring2: '#FF8C00',  // Orange
            ring3: '#FFD700',  // Yellow/Gold
        };
        
        console.log('Map Updater initialized');
    }

    /**
     * Update map with policy results
     * @param {Object} results - GeoJSON FeatureCollection from API
     */
    async updateWithResults(results) {
        console.log('Updating map with results:', results);
        
        // Clear existing parcel layer
        if (this.parcelLayer) {
            this.map.removeLayer(this.parcelLayer);
        }
        
        // Check if we have GeoJSON features
        if (results.type === 'FeatureCollection' && results.features) {
            // Add parcels to map
            this.parcelLayer = L.geoJSON(results, {
                style: (feature) => this.getParcelStyle(feature),
                onEachFeature: (feature, layer) => {
                    // Add popup
                    layer.bindPopup(this.createPopupContent(feature.properties), {
                        maxWidth: 300,
                        className: 'parcel-popup'
                    });
                    
                    // Add hover effect
                    layer.on('mouseover', function() {
                        this.setStyle({
                            weight: 3,
                            opacity: 1
                        });
                    });
                    
                    layer.on('mouseout', function() {
                        this.setStyle({
                            weight: 1,
                            opacity: 0.8
                        });
                    });
                }
            }).addTo(this.map);
            
            console.log(`Added ${results.features.length} parcels to map`);
            
            // Update stats using metadata
            if (results.metadata) {
                this.updateStats(results.metadata);
                this.updateLegend(results.metadata);
            }
        } else {
            console.warn('No GeoJSON features in results');
        }
        
        console.log('Map updated successfully');
    }
    
    /**
     * Get Leaflet style for a parcel based on its ring
     */
    getParcelStyle(feature) {
        const ring = feature.properties.ring;
        const color = this.getColorForRing(ring);
        
        return {
            fillColor: color,
            weight: 1,
            opacity: 0.8,
            color: 'white',
            fillOpacity: 0.6
        };
    }

    /**
     * Update stats display in title card
     */
    updateStats(results) {
        const formatNumber = (num) => {
            if (num >= 1000) {
                return `~${Math.round(num / 1000)}K`;
            }
            return num.toLocaleString();
        };
        
        document.getElementById('stat-parcels').textContent = 
            results.total_parcels.toLocaleString();
        
        document.getElementById('stat-units').textContent = 
            formatNumber(results.total_units);
    }

    /**
     * Update legend with ring counts
     */
    updateLegend(results) {
        document.getElementById('legend-ring1-count').textContent = 
            (results.parcels_by_ring['Ring 1'] || 0).toLocaleString();
        
        document.getElementById('legend-ring2-count').textContent = 
            (results.parcels_by_ring['Ring 2'] || 0).toLocaleString();
        
        document.getElementById('legend-ring3-count').textContent = 
            (results.parcels_by_ring['Ring 3'] || 0).toLocaleString();
    }

    /**
     * Get color for a parcel based on which ring it's in
     */
    getColorForRing(ringNumber) {
        switch(ringNumber) {
            case 1: return this.colors.ring1;
            case 2: return this.colors.ring2;
            case 3: return this.colors.ring3;
            default: return '#999999';
        }
    }

    /**
     * Create popup content for a parcel
     */
    createPopupContent(parcel) {
        // Log parcel data for debugging
        //console.log('Popup parcel data:', parcel);
        
        // Format currency
        const formatCurrency = (val) => {
            if (!val || val === 0) return '$0';
            return '$' + val.toLocaleString();
        };
        
        // Format number with commas
        const formatNumber = (val) => {
            if (!val) return '0';
            return val.toLocaleString();
        };
        
        // Determine what to show in header
        let headerText = 'Address not available';
        if (parcel.address && parcel.address.trim() !== '') {
            headerText = parcel.address;
        } else if (parcel.parcel_id) {
            headerText = `Parcel ${parcel.parcel_id}`;
        }
        
        return `
            <div style="padding: 0; width: 350px;">
                <!-- Red Header with Address -->
                <div style="background: #DC2626; color: white; padding: 16px; font-size: 18px; font-weight: 700;">
                    ${headerText}
                </div>
                
                <!-- Property Information -->
                <div style="padding: 16px; background: white;">
                    <table style="width: 100%; font-size: 14px; color: #333; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666; width: 140px;">Opportunity:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.opportunity_type || 'TOD Opportunity'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Property Class:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.property_class || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Current Zoning:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.zone_district || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Size:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.land_area_acres.toFixed(2)} acres (${formatNumber(Math.round(parcel.land_area_acres * 43560))} sq ft)</td>
                        </tr>
                        <tr style="border-top: 1px solid #e5e7eb;">
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Property Type:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.property_type || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Owner Type:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.owner_type || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Owner:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.owner_name || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Current Units:</td>
                            <td style="padding: 4px 0; text-align: right;">${formatNumber(parcel.current_units)}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Res Above Grade:</td>
                            <td style="padding: 4px 0; text-align: right;">${formatNumber(parcel.res_above_grade_area)} sq ft</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Building Value:</td>
                            <td style="padding: 4px 0; text-align: right;">${formatCurrency(parcel.improvement_value)}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Land Value:</td>
                            <td style="padding: 4px 0; text-align: right;">${formatCurrency(parcel.land_value)}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Total Building SF:</td>
                            <td style="padding: 4px 0; text-align: right;">${formatNumber(parcel.building_sqft)}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Development Potential Section -->
                <div style="background: #EEF2FF; padding: 16px; border-top: 1px solid #e5e7eb;">
                    <div style="font-size: 15px; font-weight: 700; color: #333; margin-bottom: 10px;">
                        Development Potential
                    </div>
                    <table style="width: 100%; font-size: 14px; color: #333; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666; width: 140px;">Proposed Height:</td>
                            <td style="padding: 3px 0; text-align: right; font-weight: 700;">${parcel.assigned_height} stories</td>
                        </tr>
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666;">Proposed Zone:</td>
                            <td style="padding: 3px 0; text-align: right; font-weight: 700;">${parcel.assigned_zone}</td>
                        </tr>
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666;">Distance to Transit:</td>
                            <td style="padding: 3px 0; text-align: right;">${Math.round(parcel.distance_to_light_rail)} ft</td>
                        </tr>
                    </table>
                    
                    <!-- Highlighted Units -->
                    <div style="background: white; border: 2px solid #3B82F6; border-radius: 6px; padding: 12px; margin-top: 10px; text-align: center;">
                        <div style="color: #3B82F6; font-size: 24px; font-weight: 900;">
                            ~${formatNumber(parcel.potential_units)} units
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

// Will be initialized by TOD controller
console.log('Map Updater module loaded');
