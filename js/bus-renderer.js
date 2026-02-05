/**
 * Bus Renderer for Mile High Potential
 * Handles rendering of Bus stops and BRT lines
 */

class BusRenderer {
    constructor(map) {
        this.map = map;
        this.brtLinesLayer = null;
        this.stopsLayer = null;
        this.bufferRingsLayer = null;
        this.stops = []; // Store stops for buffer updates
    }

    /**
     * Load and render BRT lines
     */
    async loadBRTLines() {
        try {
            //const lines = await window.api.getRailLines();
            
            this.hideLines();
            
            // Convert to GeoJSON features
            const geojsonFeatures = lines.map(line => ({
                type: 'Feature',
                properties: {
                    route: line.route,
                    name: line.name
                },
                geometry: line.geometry
            }));
            
            // Add to map
            this.brtLinesLayer = L.geoJSON({
                type: 'FeatureCollection',
                features: geojsonFeatures
            }, {
                style: (feature) => {
                    const route = feature.properties.route;
                    // Extract just the letter (e.g., "A-Line" -> "A")
                    const routeLetter = route ? route.charAt(0) : null;
                    const color = '#666666';
                    return {
                        color: color,
                        weight: 5,
                        opacity: 0.8
                    };
                },
                onEachFeature: (feature, layer) => {
                    const routeName = feature.properties.name || feature.properties.route;
                    layer.bindTooltip(routeName, {
                        sticky: true
                    });
                }
            }).addTo(this.map);
            
            console.log('✓ BRT  lines loaded:', lines.length, 'segments');
            return lines.length;
        } catch (error) {
            console.log('BRT lines not loaded:', error);
            return 0;
        }
    }

    /**
     * Load and render Bus Stops
     */
    async loadStops() {
        try {
            //const stations = await window.api.getStations();
            
            // Store stops for later buffer updates
            this.stops = stops;
            
            // Remove existing layer if present
            this.hideStops();
            
            // Create station markers
            const markers = stops.map(station => {
                const marker = L.circleMarker([stop.lat, stop.lon], {
                    radius: 6,
                    fillColor: '#CE0E2D',  // RTD Red
                    color: '#002F87',       // RTD Blue
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 1,
                    pane: 'markerPane'  // Ensures stops are on top
                });
                
                marker.bindPopup(`<strong>${stop.name}</strong>`);
                marker.bindTooltip(stop.name, {
                    permanent: false,
                    direction: 'top'
                });
                
                return marker;
            });
            
            this.stopsLayer = L.layerGroup(markers).addTo(this.map);
            
            // Also load buffer rings around stops
            this.loadBufferRings(stops);
            
            console.log('✓ Bus stops loaded:', stops.length);
            return stops.length;
        } catch (error) {
            console.log('Bus Stops not loaded:', error);
            return 0;
        }
    }

    /**
     * Create merged buffer rings around bus stops
     * @param {Array} stops - Array of stop objects with lat/lon
     * @param {Number} distanceFeet - Buffer distance in feet (default 1500 for Ring 3)
     */
    loadBufferRings(stops, distanceFeet = 1500) {
        try {
            // Remove existing buffer layer
            this.clearBuffers();
            
            // Create buffers around each station
            const buffers = stops.map(station => {
                // Create point
                const point = turf.point([stop.lon, stop.lat]);
                // Buffer by distance (converted to miles for turf)
                return turf.buffer(point, distanceFeet / 5280, { units: 'miles' });
            });
            
            // Union (merge) all overlapping buffers
            let merged = buffers[0];
            for (let i = 1; i < buffers.length; i++) {
                merged = turf.union(merged, buffers[i]);
            }
            
            // Add merged buffer to map
            this.bufferRingsLayer = L.geoJSON(merged, {
                style: {
                    fillColor: '#667eea',
                    fillOpacity: 0.6,
                    color: '#667eea',
                    weight: 2,
                    opacity: 0.8
                },
                pane: 'tilePane'  // Behind everything else
            }).addTo(this.map);
            
            console.log(`✓ BOD Buffer rings created: ${distanceFeet}ft radius`);
        } catch (error) {
            console.log('BOD Buffer rings not created:', error);
        }
    }

    /**
     * Update buffer rings with new distance
     * @param {Number} distanceFeet - Buffer distance in feet
     */
    updateBufferRings(distanceFeet) {
        if (this.stops.length > 0) {
            this.loadBufferRings(this.stops, distanceFeet);
        }
    }

    /**
     * Load both BRT lines and bus stops
     */
    async loadAll() {
        const [linesCount, stopsCount] = await Promise.all([
            this.loadBRTLines(),
            this.loadStops()
        ]);
        
        return { linesCount, stopsCount };
    }

     /**
     * Clear bus buffer rings from the map
     */
    clearBuffers() {
        // Remove existing buffer layer
        if (this.bufferRingsLayer) {
            this.map.removeLayer(this.bufferRingsLayer);
            console.log('✓ BOD buffers cleared');
        } 
    }

    /**
     * Hide BRT lines from the map
     */
    hideLines() {
        // Remove existing buffer layer
        if (this.brtLinesLayer) {
            this.map.removeLayer(this.brtLinesLayer);
        }
    }
    /**
     * Hide Bus stops from the map
     */
    hideStops() {
        // Remove existing buffer layer
        if (this.stopsLayer) {
            this.map.removeLayer(this.stopsLayer);
        }
    }

    /**
     * Show lines circles on the map
     */
    showLines() {
        if (this.brtLinesLayer && !this.map.hasLayer(this.brtLinesLayer)) {
            this.map.addLayer(this.brtLinesLayer);
            console.log('✓ BRT Lines shown');
        }
    }

    /**
     * Show stops circles on the map
     */
    showStops() {
        if (this.stopsLayer && !this.map.hasLayer(this.stopsLayer)) {
            this.map.addLayer(this.stopsLayer);
            console.log('✓ Bus stops shown');
        }
    }

}

// Make globally available
window.BusRenderer = BusRenderer;

console.log('Bus Renderer initialized');
