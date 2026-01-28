/**
 * Transit Renderer for Mile High Potential
 * Handles rendering of RTD stations and rail lines
 */

// Official RTD Rail Line Colors (from rtd-denver.com/brand-elements)
const RTD_RAIL_COLORS = {
    'A': '#54C0E8',  // A-Line (light blue)
    'B': '#4C9C2E',  // B-Line (green)
    'D': '#047835',  // D-Line (dark green)
    'E': '#691F74',  // E-Line (purple)
    'G': '#F4B223',  // G-Line (gold)
    'H': '#0055B8',  // H-Line (blue)
    'L': '#FFCD00',  // L-Line (yellow)
    'N': '#904199',  // N-Line (purple)
    'R': '#C1D32F',  // R-Line (lime)
    'W': '#0091B3'   // W-Line (teal)
};

class TransitRenderer {
    constructor(map) {
        this.map = map;
        this.railLinesLayer = null;
        this.stationsLayer = null;
    }

    /**
     * Load and render RTD rail lines
     */
    async loadRailLines() {
        try {
            const lines = await window.api.getRailLines();
            
            // Remove existing layer if present
            if (this.railLinesLayer) {
                this.map.removeLayer(this.railLinesLayer);
            }
            
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
            this.railLinesLayer = L.geoJSON({
                type: 'FeatureCollection',
                features: geojsonFeatures
            }, {
                style: (feature) => {
                    const route = feature.properties.route;
                    // Extract just the letter (e.g., "A-Line" -> "A")
                    const routeLetter = route ? route.charAt(0) : null;
                    const color = RTD_RAIL_COLORS[routeLetter] || '#666666';
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
            
            console.log('✓ RTD rail lines loaded:', lines.length, 'segments');
            return lines.length;
        } catch (error) {
            console.log('Rail lines not loaded:', error);
            return 0;
        }
    }

    /**
     * Load and render RTD stations
     */
    async loadStations() {
        try {
            const stations = await window.api.getStations();
            
            // Remove existing layer if present
            if (this.stationsLayer) {
                this.map.removeLayer(this.stationsLayer);
            }
            
            // Create station markers
            const markers = stations.map(station => {
                const marker = L.circleMarker([station.lat, station.lon], {
                    radius: 6,
                    fillColor: '#CE0E2D',  // RTD Red
                    color: '#002F87',       // RTD Blue
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 1,
                    pane: 'markerPane'  // Ensures stations are on top
                });
                
                marker.bindPopup(`<strong>${station.name}</strong>`);
                marker.bindTooltip(station.name, {
                    permanent: false,
                    direction: 'top'
                });
                
                return marker;
            });
            
            this.stationsLayer = L.layerGroup(markers).addTo(this.map);
            
            console.log('✓ RTD stations loaded:', stations.length);
            return stations.length;
        } catch (error) {
            console.log('Stations not loaded:', error);
            return 0;
        }
    }

    /**
     * Load both rail lines and stations
     */
    async loadAll() {
        const [linesCount, stationsCount] = await Promise.all([
            this.loadRailLines(),
            this.loadStations()
        ]);
        
        return { linesCount, stationsCount };
    }
}

// Make globally available
window.TransitRenderer = TransitRenderer;

console.log('Transit Renderer initialized');
