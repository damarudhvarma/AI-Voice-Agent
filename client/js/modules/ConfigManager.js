/**
 * ConfigManager Module - Handles API configuration and settings
 * Manages user-provided API keys and configuration UI
 */
class ConfigManager {
    constructor() {
        this.apiKeyConfigs = {
            'ASSEMBLYAI_API_KEY': {
                name: 'AssemblyAI',
                description: 'Speech-to-Text transcription service',
                placeholder: 'Enter your AssemblyAI API key...',
                required: true,
                docs: 'https://www.assemblyai.com/docs/'
            },
            'GEMINI_API_KEY': {
                name: 'Google Gemini',
                description: 'AI language model for intelligent responses',
                placeholder: 'Enter your Google Gemini API key...',
                required: true,
                docs: 'https://ai.google.dev/docs'
            },
            'MURF_API_KEY': {
                name: 'Murf AI',
                description: 'Text-to-Speech voice synthesis',
                placeholder: 'Enter your Murf AI API key...',
                required: true,
                docs: 'https://murf.ai/resources/murf-api-documentation/'
            },
            'NEWS_API_KEY': {
                name: 'NewsAPI',
                description: 'Latest news headlines and articles',
                placeholder: 'Enter your NewsAPI key...',
                required: false,
                docs: 'https://newsapi.org/docs'
            },
            'SERP_API_KEY': {
                name: 'SerpAPI',
                description: 'Web search and information retrieval',
                placeholder: 'Enter your SerpAPI key...',
                required: false,
                docs: 'https://serpapi.com/search-api'
            },
            'OPENWEATHER_API_KEY': {
                name: 'OpenWeather',
                description: 'Weather information and forecasts',
                placeholder: 'Enter your OpenWeather API key...',
                required: false,
                docs: 'https://openweathermap.org/api'
            },
            'EXCHANGE_RATE_API_KEY': {
                name: 'Exchange Rate API',
                description: 'Currency conversion rates',
                placeholder: 'Enter your Exchange Rate API key...',
                required: false,
                docs: 'https://exchangerate-api.com/docs'
            }
        };

        this.currentStatus = null;
        this.modal = null;
        this.isLoading = false;

        this.init();
    }

    init() {
        this.createModal();
        this.setupEventListeners();
        this.loadConfiguration();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Settings button
        const settingsBtn = document.getElementById('openSettings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.openModal());
        }

        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && this.modal.classList.contains('active')) {
                this.closeModal();
            }
        });
    }

    /**
     * Create the configuration modal
     */
    createModal() {
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'config-modal-overlay';
        modalOverlay.id = 'configModal';

        modalOverlay.innerHTML = `
            <div class="config-modal">
                <div class="config-modal-header">
                    <h2 class="config-modal-title">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2L2 7L12 12L22 7L12 2Z"></path>
                            <path d="M2 17L12 22L22 17"></path>
                            <path d="M2 12L12 17L22 12"></path>
                        </svg>
                        API Configuration
                    </h2>
                    <button class="config-modal-close" id="closeConfigModal">✕ Close</button>
                </div>

                <div class="config-section">
                    <h3 class="config-section-title">
                        🔑 API Keys
                    </h3>
                    <p class="config-section-description">
                        Configure your API keys to enable all features. Your keys are stored locally in your browser and take priority over environment variables.
                    </p>
                    
                    <div class="api-key-grid" id="apiKeyGrid">
                        <!-- API key inputs will be populated here -->
                    </div>
                </div>

                <div class="config-actions">
                    <button class="config-btn config-btn-danger" id="clearAllKeys">Clear All</button>
                    <button class="config-btn config-btn-secondary" id="loadFromStorage">Load Saved</button>
                    <button class="config-btn config-btn-primary" id="saveConfiguration">
                        <span class="config-loading" id="saveLoading" style="display: none;">
                            <div class="config-spinner"></div>
                            Saving...
                        </span>
                        <span id="saveText">Save Configuration</span>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modalOverlay);
        this.modal = modalOverlay;

        // Setup modal event listeners
        const closeBtn = modalOverlay.querySelector('#closeConfigModal');
        closeBtn.addEventListener('click', () => this.closeModal());

        const saveBtn = modalOverlay.querySelector('#saveConfiguration');
        saveBtn.addEventListener('click', () => this.saveConfiguration());

        const clearBtn = modalOverlay.querySelector('#clearAllKeys');
        clearBtn.addEventListener('click', () => this.clearAllKeys());

        const loadBtn = modalOverlay.querySelector('#loadFromStorage');
        loadBtn.addEventListener('click', () => this.loadFromStorage());

        // Close on overlay click
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                this.closeModal();
            }
        });

        this.populateApiKeyInputs();
    }

    /**
     * Populate API key input fields
     */
    populateApiKeyInputs() {
        const grid = this.modal.querySelector('#apiKeyGrid');
        grid.innerHTML = '';

        Object.entries(this.apiKeyConfigs).forEach(([keyName, config]) => {
            const item = document.createElement('div');
            item.className = 'api-key-item';
            item.setAttribute('data-key', keyName);

            const statusClass = this.getKeyStatus(keyName) ? 'configured' : 'not-configured';
            const statusText = this.getKeyStatus(keyName) ? 'Configured' : 'Not Set';
            const sourceInfo = this.getKeySourceInfo(keyName);

            item.innerHTML = `
                <div class="api-key-header">
                    <span class="api-key-name">${config.name}</span>
                    <span class="api-key-status ${statusClass}">${statusText}</span>
                </div>
                
                <div class="api-key-input-group">
                    <input 
                        type="password" 
                        class="api-key-input" 
                        placeholder="${config.placeholder}"
                        data-key="${keyName}"
                        autocomplete="off"
                    >
                    <button class="api-key-test-btn" data-key="${keyName}">Test</button>
                </div>
                
                <div class="api-key-info">
                    ${sourceInfo}
                    ${config.required ? '<span style="color: #ff4757;">• Required</span>' : '<span style="color: #ffa726;">• Optional</span>'}
                    <a href="${config.docs}" target="_blank" style="color: #667eea;">• Docs</a>
                </div>
                
                <div class="api-key-description">${config.description}</div>
                
                <div class="api-key-test-result" style="display: none;"></div>
            `;

            // Add event listeners
            const input = item.querySelector('.api-key-input');
            const testBtn = item.querySelector('.api-key-test-btn');

            input.addEventListener('input', () => {
                this.updateKeyStatus(keyName, input.value.trim());
                // Hide previous test results when input changes
                const result = item.querySelector('.api-key-test-result');
                result.style.display = 'none';
            });

            testBtn.addEventListener('click', () => {
                this.testApiKey(keyName, input.value.trim(), item);
            });

            grid.appendChild(item);
        });
    }

    /**
     * Get key status from current configuration
     */
    getKeyStatus(keyName) {
        if (!this.currentStatus) return false;
        return this.currentStatus.api_keys[keyName]?.configured || false;
    }

    /**
     * Get key source information
     */
    getKeySourceInfo(keyName) {
        if (!this.currentStatus) return '';

        const keyInfo = this.currentStatus.api_keys[keyName];
        if (!keyInfo) return '';

        if (keyInfo.source === 'user') {
            return '<span style="color: #00ff88;">• User Provided</span>';
        } else if (keyInfo.source === 'environment') {
            return '<span style="color: #667eea;">• Environment Variable</span>';
        } else {
            return '<span style="color: #888;">• Not Set</span>';
        }
    }

    /**
     * Update key status in UI
     */
    updateKeyStatus(keyName, value) {
        const item = this.modal.querySelector(`[data-key="${keyName}"]`);
        if (!item) return;

        const statusElement = item.querySelector('.api-key-status');
        const hasValue = value && value.length > 10;

        if (hasValue) {
            statusElement.className = 'api-key-status configured';
            statusElement.textContent = 'Ready to Save';
        } else {
            statusElement.className = 'api-key-status not-configured';
            statusElement.textContent = 'Not Set';
        }
    }

    /**
     * Test an API key
     */
    async testApiKey(keyName, keyValue, itemElement) {
        if (!keyValue || keyValue.length < 10) {
            this.showTestResult(itemElement, false, 'Please enter a valid API key');
            return;
        }

        const testBtn = itemElement.querySelector('.api-key-test-btn');
        const originalText = testBtn.textContent;

        testBtn.disabled = true;
        testBtn.innerHTML = '<div class="config-spinner"></div>';

        try {
            const response = await fetch('/api/config/api-keys/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    key_name: keyName,
                    key_value: keyValue
                })
            });

            const result = await response.json();
            this.showTestResult(itemElement, result.success, result.message);

        } catch (error) {
            console.error('API key test error:', error);
            this.showTestResult(itemElement, false, 'Test failed: Network error');
        } finally {
            testBtn.disabled = false;
            testBtn.textContent = originalText;
        }
    }

    /**
     * Show test result in UI
     */
    showTestResult(itemElement, success, message) {
        const resultElement = itemElement.querySelector('.api-key-test-result');
        resultElement.className = `api-key-test-result ${success ? 'success' : 'error'}`;
        resultElement.textContent = message;
        resultElement.style.display = 'block';

        // Hide after 5 seconds
        setTimeout(() => {
            resultElement.style.display = 'none';
        }, 5000);
    }

    /**
     * Load current configuration from server
     */
    async loadConfiguration() {
        try {
            const response = await fetch('/api/config/api-keys');
            if (response.ok) {
                this.currentStatus = await response.json();

                // Update UI if modal is open
                if (this.modal && this.modal.classList.contains('active')) {
                    this.populateApiKeyInputs();
                }
            }
        } catch (error) {
            console.error('Failed to load configuration:', error);
        }
    }

    /**
     * Validate mandatory API keys with server
     */
    async validateMandatoryKeys() {
        try {
            const response = await fetch('/api/config/validate-mandatory');
            if (response.ok) {
                const result = await response.json();
                return result;
            }
            return { success: false, is_valid: false, missing_keys: ['ASSEMBLYAI_API_KEY', 'GEMINI_API_KEY', 'MURF_API_KEY'] };
        } catch (error) {
            console.error('Failed to validate mandatory keys:', error);
            return { success: false, is_valid: false, missing_keys: ['ASSEMBLYAI_API_KEY', 'GEMINI_API_KEY', 'MURF_API_KEY'] };
        }
    }

    /**
     * Save configuration to server
     */
    async saveConfiguration() {
        if (this.isLoading) return;

        this.isLoading = true;
        const saveBtn = this.modal.querySelector('#saveConfiguration');
        const saveLoading = this.modal.querySelector('#saveLoading');
        const saveText = this.modal.querySelector('#saveText');

        saveLoading.style.display = 'inline-flex';
        saveText.style.display = 'none';
        saveBtn.disabled = true;

        try {
            // Collect API keys from form
            const apiKeys = {};
            const inputs = this.modal.querySelectorAll('.api-key-input');

            inputs.forEach(input => {
                const keyName = input.getAttribute('data-key');
                const keyValue = input.value.trim();
                if (keyValue) {
                    apiKeys[keyName] = keyValue;
                }
            });



            const response = await fetch('/api/config/api-keys', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_keys: apiKeys })
            });

            const result = await response.json();

            if (result.success) {
                // Save to localStorage as backup
                this.saveToStorage(apiKeys);

                // Reload configuration
                await this.loadConfiguration();

                // Show success notification
                this.showNotification('Configuration saved successfully!', 'success');

                // Close modal after short delay
                setTimeout(() => {
                    this.closeModal();
                }, 1500);

            } else {
                throw new Error(result.message || 'Failed to save configuration');
            }

        } catch (error) {
            console.error('Failed to save configuration:', error);
            this.showNotification(`Failed to save: ${error.message}`, 'error');
        } finally {
            this.isLoading = false;
            saveLoading.style.display = 'none';
            saveText.style.display = 'inline';
            saveBtn.disabled = false;
        }
    }

    /**
     * Clear all API keys
     */
    async clearAllKeys() {
        if (!confirm('Are you sure you want to clear all API keys? This will remove all user-provided keys and fall back to environment variables.')) {
            return;
        }

        try {
            const response = await fetch('/api/config/api-keys/clear', {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {

                // Clear localStorage
                localStorage.removeItem('voiceai_api_keys');

                // Clear form inputs
                const inputs = this.modal.querySelectorAll('.api-key-input');
                inputs.forEach(input => input.value = '');

                // Reload configuration
                await this.loadConfiguration();

                this.showNotification('All API keys cleared', 'success');
            } else {
                throw new Error(result.message || 'Failed to clear API keys');
            }

        } catch (error) {
            console.error('Failed to clear API keys:', error);
            this.showNotification(`Failed to clear: ${error.message}`, 'error');
        }
    }

    /**
     * Save API keys to localStorage
     */
    saveToStorage(apiKeys) {
        try {
            // Simple encoding (not for security, just to avoid accidental exposure)
            const encoded = btoa(JSON.stringify(apiKeys));
            localStorage.setItem('voiceai_api_keys', encoded);
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
        }
    }

    /**
     * Load API keys from localStorage
     */
    loadFromStorage() {
        try {
            const encoded = localStorage.getItem('voiceai_api_keys');
            if (!encoded) {
                this.showNotification('No saved configuration found', 'info');
                return;
            }

            const apiKeys = JSON.parse(atob(encoded));

            // Populate form inputs
            Object.entries(apiKeys).forEach(([keyName, keyValue]) => {
                const input = this.modal.querySelector(`[data-key="${keyName}"]`);
                if (input) {
                    input.value = keyValue;
                    this.updateKeyStatus(keyName, keyValue);
                }
            });

            this.showNotification('Configuration loaded from storage', 'success');

        } catch (error) {
            console.error('Failed to load from localStorage:', error);
            this.showNotification('Failed to load saved configuration', 'error');
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Use the UIManager's notification system if available
        if (window.uiManager && typeof window.uiManager.showNotification === 'function') {
            window.uiManager.showNotification(message, type);
        } else {
            // Fallback to console
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    /**
     * Open configuration modal
     */
    openModal() {
        if (!this.modal) return;

        this.loadConfiguration(); // Refresh configuration
        this.modal.classList.add('active');

        // Focus first empty input
        const inputs = this.modal.querySelectorAll('.api-key-input');
        for (const input of inputs) {
            if (!input.value.trim()) {
                input.focus();
                break;
            }
        }
    }

    /**
     * Close configuration modal
     */
    closeModal() {
        if (!this.modal) return;

        this.modal.classList.remove('active');
    }

    /**
 * Check if required API keys are configured for recording
 * @returns {Object} Validation result with missing keys
 */
    async validateRecordingRequirements() {
        // Use server-side validation for mandatory keys
        const validation = await this.validateMandatoryKeys();

        return {
            isValid: validation.is_valid,
            missingKeys: validation.missing_keys || []
        };
    }

    /**
     * Check if NEWS_API_KEY is configured for news commands
     * @returns {boolean} True if news API is configured
     */
    validateNewsRequirement() {
        if (!this.currentStatus) {
            return false;
        }

        const newsKeyInfo = this.currentStatus.api_keys['NEWS_API_KEY'];
        return newsKeyInfo && newsKeyInfo.configured;
    }

    /**
     * Open modal with specific focus on missing keys
     * @param {Array} missingKeys - Array of missing API key names
     * @param {string} reason - Reason for opening the modal
     */
    openModalWithFocus(missingKeys = [], reason = '') {
        this.openModal();

        if (reason) {
            this.showNotification(reason, 'warning', 8000);
        }

        // Highlight missing keys
        if (missingKeys.length > 0) {
            setTimeout(() => {
                missingKeys.forEach(keyName => {
                    const item = this.modal.querySelector(`[data-key="${keyName}"]`);
                    if (item) {
                        item.style.animation = 'pulse 1s ease-in-out 3 alternate';
                        item.style.border = '2px solid #ff4757';
                    }
                });
            }, 500);
        }
    }

    /**
     * Get current configuration status
     */
    getStatus() {
        return {
            isLoading: this.isLoading,
            currentStatus: this.currentStatus,
            hasModal: !!this.modal,
            modalOpen: this.modal?.classList.contains('active') || false
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConfigManager;
} else {
    window.ConfigManager = ConfigManager;
}
