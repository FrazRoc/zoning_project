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
     * Evaluate multiple policies (TOD, POD, BOD) with custom configuration
     * @param {Object} config - Multi-policy configuration
     * @param {Object} config.tod - TOD policy config (optional)
     * @param {Object} config.pod - POD policy config (optional)
     * @param {Object} config.bod - BOD policy config (optional)
     * @param {boolean} config.exclude_unlikely - Exclude unlikely development parcels
     */
    async evaluatePolicies(config) {
        try {
            const response = await fetch(`${this.baseURL}/api/evaluate-policies`, {
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
            console.error('Failed to evaluate policies:', error);
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

    /**
     * Get all Parks over 10 acres
     */
    async getParks() {
        try {
            const response = await fetch(`${this.baseURL}/api/parks`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to get parks:', error);
            throw error;
        }
    }
}

// Create global API instance
window.api = new MileHighAPI();

console.log('API Client initialized');
