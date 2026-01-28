/**
 * API Client for Mile High Potential
 * Handles all communication with the FastAPI backend
 */

class MileHighAPI {
    constructor(baseURL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://mile-high-potential-api.onrender.com') {
        this.baseURL = baseURL;
    }

    /**
     * Health check - verify API is running
     */
    async healthCheck() {
        try {
            const response = await fetch(`${this.baseURL}/`);
            return await response.json();
        } catch (error) {
            console.error('API health check failed:', error);
            throw new Error('Cannot connect to API server');
        }
    }

    /**
     * Get database statistics
     */
    async getStats() {
        try {
            const response = await fetch(`${this.baseURL}/api/stats`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to get stats:', error);
            throw error;
        }
    }

    /**
     * Evaluate TOD policy with custom configuration
     * @param {Object} config - Policy configuration
     * @param {Array} config.rings - Array of {distance, height, zone} objects
     * @param {boolean} config.include_light_rail
     * @param {boolean} config.include_brt
     * @param {boolean} config.include_frequent_bus
     */
    async evaluateTOD(config) {
        try {
            const response = await fetch(`${this.baseURL}/api/evaluate-tod`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to evaluate TOD policy:', error);
            throw error;
        }
    }

    /**
     * Get details for a specific parcel
     * @param {string} parcelId - Parcel ID
     */
    async getParcel(parcelId) {
        try {
            const response = await fetch(`${this.baseURL}/api/parcel/${parcelId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to get parcel:', error);
            throw error;
        }
    }

    /**
     * Get all RTD light rail stations
     */
    async getStations() {
        try {
            const response = await fetch(`${this.baseURL}/api/stations`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to get stations:', error);
            throw error;
        }
    }

    /**
     * Get all RTD light rail lines
     */
    async getRailLines() {
        try {
            const response = await fetch(`${this.baseURL}/api/rail-lines`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to get rail lines:', error);
            throw error;
        }
    }
}

// Create global API instance
window.api = new MileHighAPI();

console.log('API Client initialized');
