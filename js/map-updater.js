/**
 * Map Updater
 * Handles updating the Leaflet map with policy evaluation results
 */

class MapUpdater {
    constructor(map) {
        this.map = map;
        this.parcelLayer = null;
        
        // Colors for different parcels based on ring density 
        this.colors = {
            ring_high: '#FF0000',  // Red
            ring_med: '#FF8C00',  // Orange
            ring_low: '#FFD700',  // Yellow/Gold
        };
        
        // Policy colors for multi-policy mode buffers
        this.policyColors = {
            'TOD': '#667eea',           // Purple
            'POD': '#009483',           // Green
            'POD-Regional': '#009483',
            'POD-Community': '#009483',
            'BOD': '#FF6A00',           // Orange
        };
        
        console.log('Map Updater initialized');
    }

    /**
     * Update map with policy results
     * @param {Object} results - GeoJSON FeatureCollection from API
     */
    async updateWithResults(results) {
        // Clear existing parcel layer
        if (this.parcelLayer) {
            this.map.removeLayer(this.parcelLayer);
        }
        
        // Check if we have GeoJSON features
        if (results.type === 'FeatureCollection' && results.features) {
            // Add parcels to map with animation
            this.parcelLayer = L.geoJSON(results, {
                style: (feature) => {
                    const style = this.getParcelStyle(feature);
                    // Start with 0 opacity for animation
                    style.fillOpacity = 0;
                    style.opacity = 0;
                    return style;
                },
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
            
            // Animate parcels fading in
            setTimeout(() => {
                this.parcelLayer.eachLayer((layer) => {
                    const style = this.getParcelStyle(layer.feature);
                    layer.setStyle({
                        fillOpacity: style.fillOpacity || 0.6,
                        opacity: style.opacity || 0.8
                    });
                });
            }, 50);
            
            console.log(`Added ${results.features.length} parcels to map`);
        } else {
            console.warn('No GeoJSON features in results');
        }
        
        console.log('Map updated successfully');
    }
    
    /**
     * Update parcels - alias for updateWithResults for compatibility
     */
    updateParcels(geojson) {
        return this.updateWithResults(geojson);
    }
    
    /**
     * Get Leaflet style for a parcel based on its ring or policy source
     */
    getParcelStyle(feature) {
        let color;

        const ring_density = feature.properties.ring_density;
        color = this.getColorForRing(ring_density);
        
        return {
            fillColor: color,
            weight: 1,
            opacity: 0.8,
            color: 'white', /* outline color of parcel box */
            fillOpacity: 0.6,
            // Add smooth transition for animation
            className: 'parcel-animated'
        };
    }

    /**
     * Update stats display in title card
     */
    updateTitleStats(results) {
        const unitsEl = document.getElementById('stat-total-units');
        const parcelsEl = document.getElementById('stat-total-parcels');

        // Helper to format 106531 -> 106,531
        const format = (val) => Number(val || 0).toLocaleString();

        //,format(results.summary.total_units), format(results.summary.total_parcels) )
        if (unitsEl) unitsEl.textContent = format(results.summary.total_units);
        if (parcelsEl) parcelsEl.textContent = format(results.summary.total_parcels);
    }

    /**
     * Get color for a parcel based on which ring it's in
     */
    getColorForRing(ringDensity) {
        switch(ringDensity) {
            case "high": return this.colors.ring_high;
            case "med": return this.colors.ring_med;
            case "low": return this.colors.ring_low;
            default: return '#999999';
        }
    }

    /**
     * Create popup content for a parcel
     */
    createPopupContent(parcel) {
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
        
        // Determine distance label based on policy source
        let distanceLabel = 'Distance to Transit:';
        let distanceValue = parcel.distance_to_light_rail;
        
        if (parcel.policy_source) {
            if (parcel.policy_source.startsWith('POD')) {
                distanceLabel = 'Distance to Park:';
                distanceValue = parcel.distance || parcel.distance_to_regional_park || parcel.distance_to_community_park;
            } else if (parcel.policy_source.startsWith('BOD')) {
                distanceLabel = 'Distance to Bus:';
                distanceValue = parcel.distance;
            }
        }
        
        return `
            <div style="padding: 0; width: 330px;">
                <!-- Red Header with Address -->
                <div style="background: #DC2626; color: white; padding: 12px; font-size: 18px; font-weight: 700;">
                    ${headerText}
                </div>
                
                <!-- Property Information -->
                <div style="padding: 14px; background: white;">
                    <table style="width: 100%; font-size: 14px; color: #333; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Property Type:</td>
                            <td style="padding: 4px 0; text-align: right; text-transform: capitalize;">${parcel.property_type || 'N/A'}</td>
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
                            <td style="padding: 4px 0; text-align: right;">${(parcel.land_area_acres || 0).toFixed(2)} acres (${formatNumber(Math.round((parcel.land_area_acres || 0) * 43560))} sq ft)</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Owner Type:</td>
                            <td style="padding: 4px 0; text-align: right; text-transform: capitalize;">${parcel.owner_type || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Owner:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.owner_name || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Building Age:</td>
                            <td style="padding: 4px 0; text-align: right;">${parcel.building_age || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Building SF:</td>
                            <td style="padding: 4px 0; text-align: right;">${formatNumber(parcel.building_sqft) || 'N/A'}</td>
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
                            <td style="padding: 4px 8px 4px 0; font-weight: 600; color: #666;">Current Units:</td>
                            <td style="padding: 4px 0; text-align: right;">${formatNumber(parcel.current_units)}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Development Potential Section -->
                <div style="background: #EEF2FF; padding: 12px; border-top: 1px solid #e5e7eb;">
                    <div style="font-size: 14px; font-weight: 700; color: #333; margin-bottom: 10px;">
                        Development Potential
                    </div>
                    <table style="width: 100%; font-size: 14px; color: #333; border-collapse: collapse;">
                        ${parcel.policy_source ? `
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666; width: 140px;">Policy:</td>
                            <td style="padding: 3px 0; text-align: right; font-weight: 700;">${parcel.policy_source}</td>
                        </tr>
                        ` : ''}
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666; width: 140px;">Proposed Density:</td>
                            <td style="padding: 3px 0; text-align: right; font-weight: 700; text-transform: capitalize;">${parcel.ring_density}</td>
                        </tr>
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666; width: 140px;">Proposed Height:</td>
                            <td style="padding: 3px 0; text-align: right; font-weight: 700;">${parcel.assigned_height} stories</td>
                        </tr>
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666;">Proposed Zone:</td>
                            <td style="padding: 3px 0; text-align: right; font-weight: 700;">${parcel.assigned_zone}</td>
                        </tr>
                        ${distanceValue ? `
                        <tr>
                            <td style="padding: 3px 8px 3px 0; font-weight: 600; color: #666;">${distanceLabel}</td>
                            <td style="padding: 3px 0; text-align: right;">${Math.round(distanceValue)} ft</td>
                        </tr>
                        ` : ''}
                    </table>
                    
                    <!-- Highlighted Units -->
                    <div style="background: white; border: 2px solid #3B82F6; border-radius: 6px; padding: 10px; margin-top: 6px; text-align: center;">
                        <div style="color: #3B82F6; font-size: 16px; font-weight: 900;">
                            ~${formatNumber(parcel.potential_units)} potential units
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

// Will be initialized by TOD controller
console.log('Map Updater module loaded');
