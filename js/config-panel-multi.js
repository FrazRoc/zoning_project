/**
 * Multi-Policy Configuration Panel Controller
 * Handles TOD, POD, and BOD policies with accordion interface
 */

class ConfigPanel {
    constructor() {
        this.panel = document.getElementById('config-panel');
        this.backdrop = document.getElementById('config-backdrop');
        this.openBtn = document.getElementById('open-config-btn');
        this.closeBtn = document.getElementById('close-config-btn');
        this.applyBtn = document.getElementById('apply-btn');
        this.resetBtn = document.getElementById('reset-btn');
        
        // Policy accordions
        this.accordions = {
            tod: document.getElementById('tod-accordion'),
            pod: document.getElementById('pod-accordion'),
            bod: document.getElementById('bod-accordion')
        };
        
        // Policy enable checkboxes
        this.policyToggles = {
            tod: document.getElementById('tod-enabled'),
            pod: document.getElementById('pod-enabled'),
            bod: document.getElementById('bod-enabled')
        };
        
        // TOD sliders
        this.todSliders = {
            ring1Distance: document.getElementById('tod-ring1-distance'),
            ring1Height: document.getElementById('tod-ring1-height'),
            ring2Distance: document.getElementById('tod-ring2-distance'),
            ring2Height: document.getElementById('tod-ring2-height'),
            ring3Distance: document.getElementById('tod-ring3-distance'),
            ring3Height: document.getElementById('tod-ring3-height'),
        };
        
        this.todDisplays = {
            ring1Distance: document.getElementById('tod-ring1-distance-value'),
            ring1Height: document.getElementById('tod-ring1-height-value'),
            ring2Distance: document.getElementById('tod-ring2-distance-value'),
            ring2Height: document.getElementById('tod-ring2-height-value'),
            ring3Distance: document.getElementById('tod-ring3-distance-value'),
            ring3Height: document.getElementById('tod-ring3-height-value'),
        };
        
        // POD sliders
        this.podSliders = {
            regionalInnerDistance: document.getElementById('pod-regional-inner-distance'),
            regionalInnerHeight: document.getElementById('pod-regional-inner-height'),
            regionalOuterDistance: document.getElementById('pod-regional-outer-distance'),
            regionalOuterHeight: document.getElementById('pod-regional-outer-height'),
            communityDistance: document.getElementById('pod-community-distance'),
            communityHeight: document.getElementById('pod-community-height'),
        };
        
        this.podDisplays = {
            regionalInnerDistance: document.getElementById('pod-regional-inner-distance-value'),
            regionalInnerHeight: document.getElementById('pod-regional-inner-height-value'),
            regionalOuterDistance: document.getElementById('pod-regional-outer-distance-value'),
            regionalOuterHeight: document.getElementById('pod-regional-outer-height-value'),
            communityDistance: document.getElementById('pod-community-distance-value'),
            communityHeight: document.getElementById('pod-community-height-value'),
        };
        
        // Result displays
        this.resultDisplays = {
            totalParcels: document.getElementById('result-total-parcels'),
            totalUnits: document.getElementById('result-total-units'),
            todParcels: document.getElementById('result-tod-parcels'),
            todUnits: document.getElementById('result-tod-units'),
            podParcels: document.getElementById('result-pod-parcels'),
            podUnits: document.getElementById('result-pod-units'),
        };
        
        this.isOpen = false;
        
        this.init();
    }

    init() {
        // Panel open/close
        this.openBtn.addEventListener('click', () => this.open());
        this.closeBtn.addEventListener('click', () => this.close());
        this.backdrop.addEventListener('click', () => this.close());
        
        // Accordion headers
        document.querySelectorAll('.accordion-header').forEach(header => {
            header.addEventListener('click', (e) => {
                const section = e.currentTarget.closest('.policy-section');
                section.classList.toggle('collapsed');
            });
        });
        
        // Policy toggle checkboxes
        Object.keys(this.policyToggles).forEach(policy => {
            this.policyToggles[policy].addEventListener('change', (e) => {
                this.updatePolicyState(policy, e.target.checked);
            });
        });
        
        // TOD sliders
        Object.keys(this.todSliders).forEach(key => {
            const slider = this.todSliders[key];
            const display = this.todDisplays[key];
            
            slider.addEventListener('input', (e) => {
                display.textContent = e.target.value;
            });
        });
        
        // POD sliders
        Object.keys(this.podSliders).forEach(key => {
            const slider = this.podSliders[key];
            const display = this.podDisplays[key];
            
            slider.addEventListener('input', (e) => {
                display.textContent = e.target.value;
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
        
        // Initialize with ballot measure defaults
        this.reset();
        
        console.log('Multi-Policy Config Panel initialized');
    }

    open() {
        this.panel.classList.add('open');
        this.backdrop.classList.add('visible');
        this.isOpen = true;
    }

    close() {
        this.panel.classList.remove('open');
        this.backdrop.classList.remove('visible');
        this.isOpen = false;
    }

    updatePolicyState(policy, enabled) {
        const section = this.accordions[policy].closest('.policy-section');
        if (enabled) {
            section.classList.remove('disabled');
        } else {
            section.classList.add('disabled');
        }
        
        // Update active policy bubbles
        this.updateActivePolicies();
    }

    updateActivePolicies() {
        const activePolicies = [];
        
        if (this.policyToggles.tod.checked) activePolicies.push('TOD');
        if (this.policyToggles.pod.checked) activePolicies.push('POD');
        if (this.policyToggles.bod.checked) activePolicies.push('BOD');
        
        // Update title card bubbles
        const bubblesContainer = document.getElementById('active-policies');
        if (bubblesContainer) {
            bubblesContainer.innerHTML = activePolicies.map(policy => 
                `<span class="policy-bubble" data-policy="${policy.toLowerCase()}">
                    ${policy}
                    <button class="remove-policy" data-policy="${policy.toLowerCase()}">×</button>
                </span>`
            ).join('');
            
            // Add click handlers to remove buttons
            bubblesContainer.querySelectorAll('.remove-policy').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const policy = e.target.dataset.policy;
                    this.policyToggles[policy].checked = false;
                    this.updatePolicyState(policy, false);
                });
            });
        }
    }

    getConfig() {
        const config = {
            exclude_unlikely: document.getElementById('exclude-unlikely')?.checked ?? true
        };
        
        // TOD config
        if (this.policyToggles.tod.checked) {
            config.tod = {
                enabled: true,
                rings: [
                    {
                        distance: parseInt(this.todSliders.ring1Distance.value),
                        height: parseInt(this.todSliders.ring1Height.value),
                        zone: `MX-${this.todSliders.ring1Height.value}`,
                        density: 'high'
                    },
                    {
                        distance: parseInt(this.todSliders.ring2Distance.value),
                        height: parseInt(this.todSliders.ring2Height.value),
                        zone: `RX-${this.todSliders.ring2Height.value}x`,
                        density: 'med'
                    },
                    {
                        distance: parseInt(this.todSliders.ring3Distance.value),
                        height: parseInt(this.todSliders.ring3Height.value),
                        zone: `MU-${this.todSliders.ring3Height.value}x`,
                        density: 'low'
                    }
                ],
            };
        }
        
        // POD config
        if (this.policyToggles.pod.checked) {
            config.pod = {
                enabled: true,
                regional_parks: [
                    {
                        distance: parseInt(this.podSliders.regionalInnerDistance.value),
                        height: parseInt(this.podSliders.regionalInnerHeight.value),
                        zone: `RX-${this.podSliders.regionalInnerHeight.value}x`,
                        density: 'med'
                    },
                    {
                        distance: parseInt(this.podSliders.regionalOuterDistance.value),
                        height: parseInt(this.podSliders.regionalOuterHeight.value),
                        zone: `MU-${this.podSliders.regionalOuterHeight.value}x`,
                        density: 'low'
                    }
                ],
                community_parks: [
                    {
                        distance: parseInt(this.podSliders.communityDistance.value),
                        height: parseInt(this.podSliders.communityHeight.value),
                        zone: `MU-${this.podSliders.communityHeight.value}x`,
                        density: 'low'
                    }
                ]
            };
        }
        
        // BOD config (placeholder for future)
        if (this.policyToggles.bod.checked) {
            config.bod = {
                enabled: true,
                brt_lines: [],
                medium_freq_bus: []
            };
        }
        
        return config;
    }

    updateResults(results) {
        console.log("trying to update results ", results)
        const formatNumber = (num) => num.toLocaleString();
        
        // Total results
        this.resultDisplays.totalParcels.textContent = formatNumber(results.total_parcels);
        this.resultDisplays.totalUnits.textContent = formatNumber(results.total_units);
        
        // Per-policy results
        if (results.by_policy) {
            if (results.by_policy.TOD) {
                this.resultDisplays.todParcels.textContent = formatNumber(results.by_policy.TOD.parcels);
                this.resultDisplays.todUnits.textContent = formatNumber(results.by_policy.TOD.units);
            } else {
                this.resultDisplays.todParcels.textContent = '--';
                this.resultDisplays.todUnits.textContent = '--';
            }
            
            if (results.by_policy.POD) {
                this.resultDisplays.podParcels.textContent = formatNumber(results.by_policy.POD.parcels);
                this.resultDisplays.podUnits.textContent = formatNumber(results.by_policy.POD.units);
            } else {
                this.resultDisplays.podParcels.textContent = '--';
                this.resultDisplays.podUnits.textContent = '--';
            }
        }
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
            console.log('Applying config:', config);
            
            // Call multi-policy API
            const results = await window.api.evaluatePolicies(config);
            
            // Update results display
            this.updateResults(results);
            
            // Update map (if map updater exists)
            if (window.mapUpdater) {
                console.log("map updater exists, calling updateParcels")
                window.mapUpdater.updateParcels(results.geojson);
            }
            
        } catch (error) {
            console.error('Failed to apply configuration:', error);
            alert('Failed to apply configuration. Make sure the API server is running.');
        } finally {
            this.hideLoading();
        }
    }

    reset() {
        // Enable all policies by default (ballot measure)
        this.policyToggles.tod.checked = true;
        this.policyToggles.pod.checked = true;
        this.policyToggles.bod.checked = false;
        
        // Set TOD defaults (V2 Ballot Measure)
        this.todSliders.ring1Distance.value = 500;
        this.todSliders.ring1Height.value = 8;
        this.todSliders.ring2Distance.value = 1000;
        this.todSliders.ring2Height.value = 5;
        this.todSliders.ring3Distance.value = 1500;
        this.todSliders.ring3Height.value = 3;
        
        // Update TOD displays
        Object.keys(this.todSliders).forEach(key => {
            this.todDisplays[key].textContent = this.todSliders[key].value;
        });
        
        // Set POD defaults (Ballot Measure)
        this.podSliders.regionalInnerDistance.value = 250;
        this.podSliders.regionalInnerHeight.value = 5;
        this.podSliders.regionalOuterDistance.value = 750;
        this.podSliders.regionalOuterHeight.value = 3;
        this.podSliders.communityDistance.value = 250;
        this.podSliders.communityHeight.value = 3;
        
        // Update POD displays
        Object.keys(this.podSliders).forEach(key => {
            this.podDisplays[key].textContent = this.podSliders[key].value;
        });
        
        // Update UI states
        this.updatePolicyState('tod', true);
        this.updatePolicyState('pod', true);
        this.updatePolicyState('bod', false);
        
        // Apply the reset configuration
        this.apply();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.configPanel = new ConfigPanel();
});
