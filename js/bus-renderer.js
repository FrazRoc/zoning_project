/**
 * Bus Renderer for Mile High Potential
 * Handles rendering of bus stops (from static GeoJSON) and BRT lines
 * 
 * Buffer Strategy: Uses a custom Canvas overlay instead of turf.union().
 * Drawing 1,390 filled circles on a single <canvas> is near-instant,
 * vs. sequential polygon union which chokes the browser.
 * Overlapping circles with the same fill color visually merge automatically.
 */

class BusRenderer {
    constructor(map) {
        this.map = map;
        this.brtLinesLayer = null;
        this.stopsLayer = null;
        this.bufferCanvasLayer = null;
        this.stops = []; // Store stops for buffer updates
        this.busStopsData = null; // Cache loaded GeoJSON
        this._currentBufferFeet = 250; // Track current buffer distance
    }

    /**
     * Load and render BRT lines (optional - gracefully handles if file doesn't exist)
     */
    async loadBRTLines() {
        try {
            const response = await fetch('data/brt_lines.geojson');
            
            if (!response.ok) {
                console.log('ℹ️  BRT lines data not available yet');
                return 0;
            }
            
            const brtData = await response.json();
            
            this.hideLines();
            
            this.brtLinesLayer = L.geoJSON(brtData, {
                style: (feature) => {
                    return {
                        color: '#FF6A00',
                        weight: 4,
                        opacity: 0.8,
                        dashArray: '10, 5'
                    };
                },
                onEachFeature: (feature, layer) => {
                    const name = feature.properties.name || feature.properties.route || 'BRT Line';
                    layer.bindTooltip(name, {
                        sticky: true,
                        className: 'brt-tooltip'
                    });
                    layer.bindPopup(`<strong>${name}</strong><br><small>Bus Rapid Transit</small>`);
                }
            }).addTo(this.map);
            
            console.log(`✔ BRT lines loaded: ${brtData.features.length} segments`);
            return brtData.features.length;
        } catch (error) {
            console.log('ℹ️  BRT lines not loaded (expected if no data yet):', error.message);
            return 0;
        }
    }

    /**
     * Load and render bus stops from static GeoJSON file
     */
    async loadStops() {
        try {
            const response = await fetch('data/bus_stops.geojson'); //1,923 stops
            //const response = await fetch('data/bus_stops_merged.geojson'); // 1300 stops by merging stops with the same name
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.busStopsData = await response.json();
            
            this.stops = this.busStopsData.features.map(feature => ({
                stop_id: feature.properties.stop_id,
                name: feature.properties.stop_name,
                lat: feature.geometry.coordinates[1],
                lon: feature.geometry.coordinates[0],
                frequency: feature.properties.peak_frequency,
                am_frequency: feature.properties.am_frequency,
                pm_frequency: feature.properties.pm_frequency
            }));
            
            this.hideStops();
            
            const markers = this.stops.map(stop => {
                const marker = L.circleMarker([stop.lat, stop.lon], {
                    radius: 2,
                    fillColor: '#FF6A00',
                    color: '#ffffff',
                    weight: 0.5,
                    opacity: 1,
                    fillOpacity: 1,
                    pane: 'markerPane'
                });
                
                marker.bindPopup(`
                    <strong>${stop.name}</strong><br>
                    <small>Stop ID: ${stop.stop_id}</small><br>
                    Peak: <strong>${stop.frequency.toFixed(1)} trips/hr</strong><br>
                    <small>AM: ${stop.am_frequency.toFixed(1)}/hr | PM: ${stop.pm_frequency.toFixed(1)}/hr</small>
                `);
                
                marker.bindTooltip(stop.name, {
                    permanent: false,
                    direction: 'top',
                    opacity: 0.9
                });
                
                return marker;
            });
            
            this.stopsLayer = L.layerGroup(markers).addTo(this.map);
            
            // Draw buffer rings using canvas approach
            this.loadBufferRings(this.stops);
            
            console.log(`✔ Bus stops loaded: ${this.stops.length}`);
            return this.stops.length;
        } catch (error) {
            console.error('❌ Bus stops failed to load:', error);
            console.error('Make sure data/bus_stops_merged.geojson exists');
            return 0;
        }
    }

    /**
     * Create merged buffer rings using a Canvas overlay.
     * 
     * Instead of computing turf.union() on 1,390 polygons (very slow),
     * we draw filled circles on a single <canvas>. Overlapping circles
     * with the same fill color visually merge — same end result, near-instant.
     * 
     * @param {Array} stops - Array of stop objects with lat/lon
     * @param {Number} distanceFeet - Buffer distance in feet (default 250)
     */
    loadBufferRings(stops, distanceFeet = 250) {
        this.clearBuffers();
        
        if (!stops || stops.length === 0) {
            console.log('No stops available for buffer rings');
            return;
        }

        this._currentBufferFeet = distanceFeet;

        // Custom Leaflet layer that draws on a <canvas>
        const CanvasBufferLayer = L.Layer.extend({
            initialize: function(stops, distanceFeet, options) {
                this._stops = stops;
                this._distanceFeet = distanceFeet;
                L.setOptions(this, options);
            },

            onAdd: function(map) {
                this._map = map;
                
                // Create canvas element
                this._canvas = L.DomUtil.create('canvas', 'bod-buffer-canvas');
                const pane = map.getPane('tilePane');
                pane.appendChild(this._canvas);
                
                // Style the canvas
                this._canvas.style.position = 'absolute';
                this._canvas.style.pointerEvents = 'none';
                
                // Bind events
                map.on('moveend zoomend resize', this._redraw, this);
                this._redraw();
            },

            onRemove: function(map) {
                map.off('moveend zoomend resize', this._redraw, this);
                if (this._canvas && this._canvas.parentNode) {
                    this._canvas.parentNode.removeChild(this._canvas);
                }
            },

            _redraw: function() {
                const map = this._map;
                if (!map) return;

                const size = map.getSize();
                const canvas = this._canvas;
                canvas.width = size.x;
                canvas.height = size.y;

                // Position canvas at top-left of the map container
                const topLeft = map.containerPointToLayerPoint([0, 0]);
                L.DomUtil.setPosition(canvas, topLeft);

                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, size.x, size.y);

                // Convert buffer distance from feet to meters for projection
                const bufferMeters = this._distanceFeet * 0.3048;

                // Draw all circles in one pass — no stroke for clean overlaps
                ctx.fillStyle = 'rgba(255, 106, 0, 0.6)';  // BOD orange, matches TOD/POD opacity

                ctx.beginPath();
                for (const stop of this._stops) {
                    const latlng = L.latLng(stop.lat, stop.lon);
                    const centerPx = map.latLngToContainerPoint(latlng);

                    // Calculate pixel radius: project a point bufferMeters east
                    // to get accurate screen-space radius at this zoom level
                    const earthRadius = 6378137; // meters
                    const dLng = (bufferMeters / (earthRadius * Math.cos(stop.lat * Math.PI / 180))) * (180 / Math.PI);
                    const edgePoint = L.latLng(stop.lat, stop.lon + dLng);
                    const edgePx = map.latLngToContainerPoint(edgePoint);
                    const radiusPx = Math.abs(edgePx.x - centerPx.x);

                    // Skip stops outside the visible viewport (with buffer padding)
                    if (centerPx.x + radiusPx < 0 || centerPx.x - radiusPx > size.x ||
                        centerPx.y + radiusPx < 0 || centerPx.y - radiusPx > size.y) {
                        continue;
                    }

                    ctx.moveTo(centerPx.x + radiusPx, centerPx.y);
                    ctx.arc(centerPx.x, centerPx.y, radiusPx, 0, Math.PI * 2);
                }
                ctx.fill();

                console.log(`✔ BOD canvas buffers drawn: ${this._stops.length} stops, ${this._distanceFeet}ft`);
            },

            // Allow updating distance without recreating the layer
            setDistance: function(distanceFeet) {
                this._distanceFeet = distanceFeet;
                this._redraw();
            }
        });

        this.bufferCanvasLayer = new CanvasBufferLayer(stops, distanceFeet);
        this.bufferCanvasLayer.addTo(this.map);

        console.log(`✔ BOD buffer rings created: ${distanceFeet}ft radius (canvas mode)`);
    }

    /**
     * Update buffer rings with new distance — instant with canvas approach
     * @param {Number} distanceFeet - Buffer distance in feet
     */
    updateBufferRings(distanceFeet) {
        this._currentBufferFeet = distanceFeet;
        if (this.bufferCanvasLayer && this.bufferCanvasLayer.setDistance) {
            // Just update distance and redraw — no geometry computation
            this.bufferCanvasLayer.setDistance(distanceFeet);
        } else if (this.stops.length > 0) {
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
        if (this.bufferCanvasLayer) {
            this.map.removeLayer(this.bufferCanvasLayer);
            this.bufferCanvasLayer = null;
            console.log('✔ BOD buffers cleared');
        }
    }

    hideLines() {
        if (this.brtLinesLayer) {
            this.map.removeLayer(this.brtLinesLayer);
        }
    }

    hideStops() {
        if (this.stopsLayer) {
            this.map.removeLayer(this.stopsLayer);
        }
    }

    showLines() {
        if (this.brtLinesLayer && !this.map.hasLayer(this.brtLinesLayer)) {
            this.map.addLayer(this.brtLinesLayer);
            console.log('✔ BRT lines shown');
        }
    }

    showStops() {
        if (this.stopsLayer && !this.map.hasLayer(this.stopsLayer)) {
            this.map.addLayer(this.stopsLayer);
            console.log('✔ Bus stops shown');
        }
    }
}

window.BusRenderer = BusRenderer;

console.log('Bus Renderer initialized');
