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
        
        // BOD sliders
        this.bodSliders = {
            // BRT sliders
            brtInnerDistance: document.getElementById('brt-inner-distance'),
            brtInnerHeight: document.getElementById('brt-inner-height'),
            brtOuterDistance: document.getElementById('brt-outer-distance'),
            brtOuterHeight: document.getElementById('brt-outer-height'),
            // Bus sliders
            busDistance: document.getElementById('bus-distance'),
            busHeight: document.getElementById('bus-height'),
        };
        
        this.bodDisplays = {
            // BRT displays
            brtInnerDistance: document.getElementById('brt-inner-distance-value'),
            brtInnerHeight: document.getElementById('brt-inner-height-value'),
            brtOuterDistance: document.getElementById('brt-outer-distance-value'),
            brtOuterHeight: document.getElementById('brt-outer-height-value'),
            // Bus displays
            busDistance: document.getElementById('bus-distance-value'),
            busHeight: document.getElementById('bus-height-value'),
        };
        
        // BOD sub-toggles
        this.bodToggles = {
            brt: document.getElementById('brt-enabled'),
            bus: document.getElementById('bus-enabled')
        };
        
        // Result displays
        this.resultDisplays = {
            totalParcels: document.getElementById('result-total-parcels'),
            totalUnits: document.getElementById('result-total-units'),
            todParcels: document.getElementById('result-tod-parcels'),
            todUnits: document.getElementById('result-tod-units'),
            podParcels: document.getElementById('result-pod-parcels'),
            podUnits: document.getElementById('result-pod-units'),
            bodParcels: document.getElementById('result-bod-parcels'),
            bodUnits: document.getElementById('result-bod-units'),
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
        
        // BOD sliders
        Object.keys(this.bodSliders).forEach(key => {
            const slider = this.bodSliders[key];
            const display = this.bodDisplays[key];
            
            if (slider && display) {  // Check exists (BRT might be disabled)
                slider.addEventListener('input', (e) => {
                    display.textContent = e.target.value;
                });
            }
        });
        
        // BOD sub-toggles (BRT and Bus)
        if (this.bodToggles.brt) {
            this.bodToggles.brt.addEventListener('change', (e) => {
                this.updateBODSubPolicy('brt', e.target.checked);
            });
        }
        if (this.bodToggles.bus) {
            this.bodToggles.bus.addEventListener('change', (e) => {
                this.updateBODSubPolicy('bus', e.target.checked);
            });
        }
        
        // Action buttons
        this.applyBtn.addEventListener('click', () => this.apply());
        this.resetBtn.addEventListener('click', () => {this.reset(); this.apply();});
        
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
    
    updateBODSubPolicy(subPolicy, enabled) {
        // Enable/disable BRT or Bus controls
        const prefix = subPolicy === 'brt' ? 'brt' : 'bus';
        
        // Find all controls for this sub-policy
        const controls = document.querySelectorAll(`[id^="${prefix}-"]`);
        controls.forEach(control => {
            if (enabled) {
                control.removeAttribute('disabled');
            } else {
                control.setAttribute('disabled', 'disabled');
            }
        });
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
                    this.apply();
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
        else {
            config.tod = {
                enabled: false
            }
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
        else {
            config.pod = {
                enabled: false
            }
        }
        
        // BOD config
        if (this.policyToggles.bod.checked) {
            config.bod = {
                enabled: true,
                brt_enabled: this.bodToggles.brt ? this.bodToggles.brt.checked : false,
                brt_rings: [],
                bus_enabled: this.bodToggles.bus ? this.bodToggles.bus.checked : true,
                bus_rings: []
            };
            
            // Add BRT rings if enabled
            if (config.bod.brt_enabled && this.bodSliders.brtInnerDistance) {
                config.bod.brt_rings = [
                    {
                        distance: parseInt(this.bodSliders.brtInnerDistance.value),
                        height: parseInt(this.bodSliders.brtInnerHeight.value),
                        zone: `RX-${this.bodSliders.brtInnerHeight.value}`,
                        density: 'med'
                    },
                    {
                        distance: parseInt(this.bodSliders.brtOuterDistance.value),
                        height: parseInt(this.bodSliders.brtOuterHeight.value),
                        zone: `MX-${this.bodSliders.brtOuterHeight.value}`,
                        density: 'low'
                    }
                ];
            }
            
            // Add Bus rings if enabled
            if (config.bod.bus_enabled && this.bodSliders.busDistance) {
                config.bod.bus_rings = [
                    {
                        distance: parseInt(this.bodSliders.busDistance.value),
                        height: parseInt(this.bodSliders.busHeight.value),
                        zone: `MX-${this.bodSliders.busHeight.value}`,
                        density: 'low'
                    }
                ];
            }
        }
        else {
            config.bod = {
                enabled: false
            };
        }
        
        return config;
    }

    updatePanelStats(results) {
        const formatNumber = (num) => num.toLocaleString();
        
        // Total results
        this.resultDisplays.totalParcels.textContent = formatNumber(results.summary.total_parcels);
        this.resultDisplays.totalUnits.textContent = formatNumber(results.summary.total_units);
        
        // Per-policy results
        if (results.summary.by_policy) {
            if (results.summary.by_policy.TOD) {
                this.resultDisplays.todParcels.textContent = formatNumber(results.summary.by_policy.TOD.parcels);
                this.resultDisplays.todUnits.textContent = formatNumber(results.summary.by_policy.TOD.units);
            } else {
                this.resultDisplays.todParcels.textContent = '--';
                this.resultDisplays.todUnits.textContent = '--';
            }
            
            if (results.summary.by_policy.POD) {
                this.resultDisplays.podParcels.textContent = formatNumber(results.summary.by_policy.POD.parcels);
                this.resultDisplays.podUnits.textContent = formatNumber(results.summary.by_policy.POD.units);
            } else {
                this.resultDisplays.podParcels.textContent = '--';
                this.resultDisplays.podUnits.textContent = '--';
            }
            
            if (results.summary.by_policy.BOD) {
                this.resultDisplays.bodParcels.textContent = formatNumber(results.summary.by_policy.BOD.parcels);
                this.resultDisplays.bodUnits.textContent = formatNumber(results.summary.by_policy.BOD.units);
            } else {
                this.resultDisplays.bodParcels.textContent = '--';
                this.resultDisplays.bodUnits.textContent = '--';
            }
        }
    }

    showLoading() {
        this.applyBtn.classList.add('loading');
        this.applyBtn.textContent = 'Loading...';
        this.applyBtn.disabled = true;
        
        // Show loading overlay
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('active');
            console.log('Loading overlay shown');
        } else {
            console.warn('Loading overlay element not found');
        }
    }

    hideLoading() {
        this.applyBtn.classList.remove('loading');
        this.applyBtn.textContent = 'Apply Changes';
        this.applyBtn.disabled = false;
        
        // Hide loading overlay
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            console.log('Loading overlay hidden');
        }
    }

    async apply() {
        this.showLoading();

        // Update rail features and buffers based on TOD toggle
        if (window.transitRenderer) {
            if (this.policyToggles.tod.checked) {
                console.log("TOD enabled, showing rails and updating buffers");
                window.transitRenderer.showLines();
                window.transitRenderer.showStations();
                //Evan: we might want to change this to take the largest distance of the 3 rings
                window.transitRenderer.updateBufferRings(this.todSliders.ring3Distance.value);
            } else {
                console.log("TOD disabled, hiding rails and clearing buffers");
                window.transitRenderer.hideLines();
                window.transitRenderer.hideStations();
                window.transitRenderer.clearBuffers();
            }
        }

        // Update park features and buffers based on POD toggle
        if (window.parkRenderer) {
            if (this.policyToggles.pod.checked) {
                console.log("POD enabled, showing parks and updating buffers");
                window.parkRenderer.showParks();
                window.parkRenderer.updateBuffers(
                    this.podSliders.regionalOuterDistance.value, 
                    this.podSliders.communityDistance.value
                );
            } else {
                console.log("POD disabled, hiding parks and clearing buffers");
                window.parkRenderer.hideParks();
                window.parkRenderer.clearBuffers();
            }
        }

        // Update bus features and buffers based on BOD toggle
        if (window.busRenderer) {
            if (this.policyToggles.bod.checked) {
                console.log("BOD enabled, showing stops and updating buffers");
                window.busRenderer.showStops();
                window.busRenderer.updateBufferRings(parseInt(this.bodSliders.busDistance.value));
            } else {
                console.log("BOD disabled, hiding stops and clearing buffers");
                window.busRenderer.hideStops();
                window.busRenderer.clearBuffers();
            }
        }
        
        try {
            const config = this.getConfig();
            
            // Call multi-policy API
            const results = await window.api.evaluatePolicies(config);
            
            // Update Config Panel results display
            this.updatePanelStats(results);

            // Update Title Stats using metadata summary
            if (window.mapUpdater && results.summary) {
                window.mapUpdater.updateTitleStats(results);
            }
            
            // Update map (if map updater exists)
            if (window.mapUpdater) {
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
        this.policyToggles.bod.checked = true;
        
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
        
        // Set BOD defaults (Ballot Measure)
        if (this.bodToggles.brt) {
            this.bodToggles.brt.checked = false; // BRT disabled (no data yet)
        }
        if (this.bodToggles.bus) {
            this.bodToggles.bus.checked = true;  // Bus enabled
        }
        
        if (this.bodSliders.brtInnerDistance) {
            this.bodSliders.brtInnerDistance.value = 250;
            this.bodSliders.brtInnerHeight.value = 5;
            this.bodSliders.brtOuterDistance.value = 750;
            this.bodSliders.brtOuterHeight.value = 3;
        }
        
        if (this.bodSliders.busDistance) {
            this.bodSliders.busDistance.value = 250;
            this.bodSliders.busHeight.value = 3;
        }
        
        // Update BOD displays
        Object.keys(this.bodSliders).forEach(key => {
            if (this.bodDisplays[key] && this.bodSliders[key]) {
                this.bodDisplays[key].textContent = this.bodSliders[key].value;
            }
        });
        
        // Reset "Exclude Unlikely" checkbox to checked (default enabled)
        const excludeUnlikelyCheckbox = document.getElementById('exclude-unlikely');
        if (excludeUnlikelyCheckbox) {
            excludeUnlikelyCheckbox.checked = true;
        }
        
        // Update UI states
        this.updatePolicyState('tod', true);
        this.updatePolicyState('pod', true);
        this.updatePolicyState('bod', true);
    }
}
