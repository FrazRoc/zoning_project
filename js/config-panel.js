/**
 * Configuration Panel Controller
 * Handles panel open/close, slider interactions, and user input
 */

class ConfigPanel {
    constructor() {
        this.panel = document.getElementById('config-panel');
        this.backdrop = document.getElementById('config-backdrop');
        this.openBtn = document.getElementById('open-config-btn');
        this.closeBtn = document.getElementById('close-config-btn');
        this.applyBtn = document.getElementById('apply-btn');
        this.resetBtn = document.getElementById('reset-btn');
        
        // Preset buttons
        this.presetButtons = document.querySelectorAll('.preset-btn');
        
        // Sliders
        this.sliders = {
            ring1Distance: document.getElementById('ring1-distance'),
            ring1Height: document.getElementById('ring1-height'),
            ring2Distance: document.getElementById('ring2-distance'),
            ring2Height: document.getElementById('ring2-height'),
            ring3Distance: document.getElementById('ring3-distance'),
            ring3Height: document.getElementById('ring3-height'),
        };
        
        // Value displays
        this.valueDisplays = {
            ring1Distance: document.getElementById('ring1-distance-value'),
            ring1Height: document.getElementById('ring1-height-value'),
            ring2Distance: document.getElementById('ring2-distance-value'),
            ring2Height: document.getElementById('ring2-height-value'),
            ring3Distance: document.getElementById('ring3-distance-value'),
            ring3Height: document.getElementById('ring3-height-value'),
        };
        
        // Result displays
        this.resultDisplays = {
            parcels: document.getElementById('result-parcels'),
            units: document.getElementById('result-units'),
            ring1: document.getElementById('result-ring1'),
            ring2: document.getElementById('result-ring2'),
            ring3: document.getElementById('result-ring3'),
        };
        
        this.isOpen = false;
        this.currentPreset = 'ballot';
        
        this.init();
    }

    init() {
        // Panel open/close
        this.openBtn.addEventListener('click', () => this.open());
        this.closeBtn.addEventListener('click', () => this.close());
        this.backdrop.addEventListener('click', () => this.close());
        
        // Preset buttons
        this.presetButtons.forEach(btn => {
            btn.addEventListener('click', (e) => this.selectPreset(e.target.dataset.preset));
        });
        
        // Sliders - update displays in real-time
        Object.keys(this.sliders).forEach(key => {
            const slider = this.sliders[key];
            const display = this.valueDisplays[key];
            
            slider.addEventListener('input', (e) => {
                display.textContent = e.target.value;
                // Switch to custom preset when user adjusts sliders
                if (this.currentPreset === 'ballot') {
                    this.selectPreset('custom');
                }
            });
        });
        
        // Action buttons
        this.applyBtn.addEventListener('click', () => this.apply());
        this.resetBtn.addEventListener('click', () => this.reset());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
        
        console.log('Config Panel initialized');
    }

    open() {
        console.log('Config Panel opened');
        this.panel.classList.add('open');
        this.backdrop.classList.add('visible');
        this.isOpen = true;
    }

    close() {
        this.panel.classList.remove('open');
        this.backdrop.classList.remove('visible');
        this.isOpen = false;
    }

    selectPreset(preset) {
        this.currentPreset = preset;
        
        // Update button states
        this.presetButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.preset === preset);
        });
        
        if (preset === 'ballot') {
            // V2 Ballot Measure preset
            this.setSliderValues({
                ring1Distance: 500,
                ring1Height: 8,
                ring2Distance: 1000,
                ring2Height: 5,
                ring3Distance: 1500,
                ring3Height: 3,
            });
        }
        // Custom preset doesn't change values, just unlocks editing
    }

    setSliderValues(values) {
        Object.keys(values).forEach(key => {
            if (this.sliders[key]) {
                this.sliders[key].value = values[key];
                this.valueDisplays[key].textContent = values[key];
            }
        });
    }

    getConfig() {
        return {
            rings: [
                {
                    distance: parseInt(this.sliders.ring1Distance.value),
                    height: parseInt(this.sliders.ring1Height.value),
                    zone: `C-MX-${this.sliders.ring1Height.value}x`
                },
                {
                    distance: parseInt(this.sliders.ring2Distance.value),
                    height: parseInt(this.sliders.ring2Height.value),
                    zone: `G-RX-${this.sliders.ring2Height.value}x`
                },
                {
                    distance: parseInt(this.sliders.ring3Distance.value),
                    height: parseInt(this.sliders.ring3Height.value),
                    zone: `G-MU-${this.sliders.ring3Height.value}x`
                }
            ],
            include_light_rail: true,
            include_brt: false,
            include_frequent_bus: false,
            exclude_unlikely: document.getElementById('exclude-unlikely').checked
        };
    }

    updateResults(results) {
        // Format numbers with commas
        const formatNumber = (num) => num.toLocaleString();
        
        this.resultDisplays.parcels.textContent = formatNumber(results.total_parcels);
        this.resultDisplays.units.textContent = formatNumber(results.total_units);
        
        // Ring breakdowns
        this.resultDisplays.ring1.textContent = formatNumber(results.parcels_by_ring['Ring 1'] || 0);
        this.resultDisplays.ring2.textContent = formatNumber(results.parcels_by_ring['Ring 2'] || 0);
        this.resultDisplays.ring3.textContent = formatNumber(results.parcels_by_ring['Ring 3'] || 0);
    }

    showLoading() {
        this.applyBtn.classList.add('loading');
        this.applyBtn.textContent = 'Loading...';
        this.applyBtn.disabled = true;
    }

    hideLoading() {
        this.applyBtn.classList.remove('loading');
        this.applyBtn.textContent = 'Apply Changes';
        this.applyBtn.disabled = false;
    }

    async apply() {
        this.showLoading();
        
        try {
            const config = this.getConfig();
            
            // Trigger evaluation through TOD controller
            if (window.todController) {
                await window.todController.evaluate(config);
            }
        } catch (error) {
            console.error('Failed to apply configuration:', error);
            alert('Failed to apply configuration. Make sure the API server is running.');
        } finally {
            this.hideLoading();
        }
    }

    reset() {
        this.selectPreset('ballot');
        this.apply();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.configPanel = new ConfigPanel();
});
