/**
 * TOD Controller
 * Main orchestrator for Transit-Oriented Development policy evaluation
 * Coordinates between API, UI, and Map
 */

class TODController {
    constructor(map, transitRenderer = null) {
        this.map = map;
        this.mapUpdater = new MapUpdater(map);
        this.transitRenderer = transitRenderer;
        this.currentResults = null;
        
        // Default configuration (V2 Ballot Measure)
        this.config = {
            rings: [
                { distance: 500, height: 8, zone: 'C-MX-8x', density: "high" },
                { distance: 1000, height: 5, zone: 'G-RX-5x', density: "med" },
                { distance: 1500, height: 3, zone: 'G-MU-3x', density: "low" }
            ],
            include_light_rail: true,
            include_brt: false,
            include_frequent_bus: false,
            exclude_unlikely: true
        };
        
        console.log('TOD Controller initialized');
        
        // Evaluate default configuration on load
        this.init();
    }

    async init() {
        console.log('Initializing TOD Controller...');
        
        try {
            // Check if API is available
            await window.api.healthCheck();
            console.log('✓ API connection successful');
            
            // Load initial data
            //Evan commented this out
            //await this.evaluate(this.config);
            
        } catch (error) {
            console.error('Failed to initialize:', error);
            this.showError('Cannot connect to API server. Make sure it is running on http://localhost:8000');
        }
    }

    /**
     * Evaluate TOD policy with given configuration
     * @param {Object} config - Policy configuration
     */
    async evaluate(config) {
        console.log('Evaluating TOD policy with config:', config);
        
        try {
            // Update current config
            this.config = config;

            // Update buffer rings to match Ring 3 distance
            if (this.transitRenderer && config.rings && config.rings.length >= 3) {
                const ring3Distance = config.rings[2].distance; // Ring 3 is index 2
                this.transitRenderer.updateBufferRings(ring3Distance);
            }
            
            // Call API
            const results = await window.api.evaluateTOD(config);
            
            // Store results
            this.currentResults = results;
            
            // Update UI components
            this.updateUI(results);
            
            return results;
            
        } catch (error) {
            console.error('Evaluation failed:', error);
            throw error;
        }
    }

    /**
     * Update all UI components with results
     */
    updateUI(results) {
        // Update map with GeoJSON
        this.mapUpdater.updateWithResults(results);
        
        // Update config panel results (if it exists)
        // Extract metadata for config panel
        if (window.configPanel && results.metadata) {
            window.configPanel.updateResults(results.metadata);
        }
    }

    /**
     * Show error message to user
     */
    showError(message) {
        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f56565;
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            max-width: 400px;
            font-size: 14px;
            line-height: 1.5;
        `;
        errorDiv.innerHTML = `
            <div style="display: flex; align-items: start; gap: 12px;">
                <span style="font-size: 20px;">⚠️</span>
                <div>
                    <div style="font-weight: 700; margin-bottom: 4px;">Connection Error</div>
                    <div>${message}</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 8 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 8000);
    }

    /**
     * Get current results
     */
    getResults() {
        return this.currentResults;
    }

    /**
     * Get current configuration
     */
    getConfig() {
        return this.config;
    }
}

// Initialize when map is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for map and transitRenderer to be fully initialized
    setTimeout(() => {
        // The map is defined globally in the HTML, stored as window.map
        if (typeof map !== 'undefined') {
            window.todController = new TODController(map, window.transitRenderer);
        } else {
            console.error('Map not found! TOD Controller cannot initialize.');
        }
    }, 500);
});
