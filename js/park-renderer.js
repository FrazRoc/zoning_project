/**
 * Park Renderer for Mile High Potential
 * Handles rendering of Regional/Community parks and a single policy buffer
 */
class ParkRenderer {
    constructor(map) {
        this.map = map;
        this.parksLayer = null;
        this.bufferRingsLayer = null;
        this.parksFeatures = []; 
    }

    async loadParks() {
        try {
            const parkData = await window.api.getParks();
            // Store features for buffer recalculations
            this.parksFeatures = parkData.features; 

            if (this.parksLayer) this.map.removeLayer(this.parksLayer);

            this.parksLayer = L.geoJSON(parkData, {
                style: {
                    fillColor: '#2D5A27', 
                    fillOpacity: 0.5,
                    color: '#1E3C1A',
                    weight: 1.5
                },
                onEachFeature: (feature, layer) => {
                    layer.bindTooltip(`<strong>${feature.properties.name}</strong><br>${feature.properties.park_type} (${Math.round(feature.properties.land_area_acres)} ac)`);
                }
            }).addTo(this.map);

            console.log(`✓ ${this.parksFeatures.length} Parks loaded`);
        } catch (error) {
            console.error('Parks failed to load:', error);
        }
    }

    /**
     * Generates a single outer buffer for Regional and Community parks
     */
    updateBuffers(regionalDist, communityDist) {
        try {
           console.time('⚡ Park Buffer (Fast)');
            
            if (this.bufferRingsLayer) this.map.removeLayer(this.bufferRingsLayer);
            if (!this.parksFeatures.length) return;

            const bufferList = this.parksFeatures.map(park => {
                const isRegional = park.properties.park_type === 'regional';
                const distFeet = isRegional ? regionalDist : communityDist;
                return distFeet > 0 ? turf.buffer(park, distFeet / 5280, { units: 'miles' }) : null;
            }).filter(x => x);

            if (bufferList.length === 0) return;

            // Use combine instead of union for 10x speed boost
            const combined = turf.combine(turf.featureCollection(bufferList));

            this.bufferRingsLayer = L.geoJSON(combined, {
                style: {
                    fillColor: '#009483',
                    fillOpacity: 0.6,
                    color: '#009483',
                    weight: 2,
                    opacity: 0.8
                },
                pane: 'tilePane'
            }).addTo(this.map);

            console.timeEnd('⚡ Park Buffer (Fast)');

        } catch (error) {
            console.error('Error updating park buffers:', error);
        }
    }
}

window.ParkRenderer = ParkRenderer;