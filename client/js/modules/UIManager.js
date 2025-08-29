/**
 * UI Manager Module - Handles all UI updates and interactions
 * Manages status updates, notifications, and UI state
 */
class UIManager {
    constructor() {
        this.elements = {};
        this.notifications = [];
        this.animationQueue = [];

        this.init();
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.animateOnLoad();
    }

    /**
     * Cache frequently used DOM elements
     */
    cacheElements() {
        this.elements = {
            toggleRecord: document.getElementById('toggleRecord'),
            letsGetStarted: document.getElementById('letsGetStarted'),
            learnMore: document.getElementById('learnMore'),
            voiceIndicator: document.getElementById('voiceIndicator'),
            echoStatus: document.getElementById('echoStatus'),
            echoSpinner: document.getElementById('echoSpinner'),
            recordingTimer: document.getElementById('recordingTimer'),
            timerText: document.getElementById('timerText'),
            audioPlayback: document.getElementById('audioPlayback'),
            conversationDisplay: document.getElementById('conversationDisplay'),
            statusMessage: document.getElementById('statusMessage'),
            loadingSpinner: document.getElementById('loadingSpinner'),
            voiceStatus: document.getElementById('voiceStatus')
        };
    }

    /**
     * Setup event listeners for UI interactions
     */
    setupEventListeners() {
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.ctrlKey) {
                e.preventDefault();
                this.dispatchEvent('toggleRecording');
            }
        });
    }

    /**
     * Update echo status message
     * @param {string} message - Status message
     * @param {string} type - Message type ('default', 'success', 'error', 'info', 'transcription', 'recording')
     * @param {boolean} showSpinner - Whether to show loading spinner
     */
    updateEchoStatus(message, type = 'default', showSpinner = false) {
        const statusElement = this.elements.echoStatus;
        if (!statusElement) return;

        // Clear existing classes
        statusElement.className = 'echo-status';
        if (type !== 'default') {
            statusElement.classList.add(`status-${type}`);
        }

        statusElement.textContent = message;

        // Handle spinner
        const spinner = this.elements.echoSpinner;
        if (spinner) {
            spinner.style.display = showSpinner ? 'inline-block' : 'none';
        }
    }

    /**
     * Update voice status
     * @param {string} message - Status message
     * @param {string} type - Message type
     * @param {boolean} showSpinner - Whether to show loading spinner
     */
    updateVoiceStatus(message, type = 'default', showSpinner = false) {
        const statusMessage = this.elements.statusMessage;
        const loadingSpinner = this.elements.loadingSpinner;
        const voiceStatus = this.elements.voiceStatus;

        if (statusMessage) {
            statusMessage.textContent = message;
        }

        if (loadingSpinner) {
            loadingSpinner.style.display = showSpinner ? 'flex' : 'none';
        }

        if (voiceStatus) {
            voiceStatus.className = 'voice-status';
            if (type !== 'default') {
                voiceStatus.classList.add(`status-${type}`);
            }
        }
    }

    /**
     * Update recording button state
     * @param {boolean} isRecording - Whether currently recording
     */
    updateRecordingButtons(isRecording) {
        const buttons = [this.elements.toggleRecord, this.elements.letsGetStarted].filter(btn => btn !== null);

        buttons.forEach(btn => {
            if (btn) {
                btn.disabled = isRecording;
                if (isRecording) {
                    btn.classList.add('recording');
                } else {
                    btn.classList.remove('recording');
                }

                const recordText = btn.querySelector('.record-text');
                if (recordText) {
                    recordText.textContent = isRecording ? 'Stop Recording' : 'Start Recording';
                }
            }
        });
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type ('success', 'warning', 'error', 'info')
     * @param {number} duration - Duration in milliseconds
     */
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '16px 24px',
            borderRadius: '12px',
            color: 'white',
            fontWeight: '500',
            zIndex: '1000',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease',
            maxWidth: '300px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
        });

        // Set background based on type
        const backgrounds = {
            success: 'linear-gradient(45deg, #00ff88 0%, #00cc6a 100%)',
            warning: 'linear-gradient(45deg, #ffa726 0%, #ff9800 100%)',
            error: 'linear-gradient(45deg, #ff4757 0%, #ff3742 100%)',
            info: 'linear-gradient(45deg, #667eea 0%, #764ba2 100%)'
        };

        notification.style.background = backgrounds[type] || backgrounds.info;

        document.body.appendChild(notification);
        this.notifications.push(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove after duration
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
                this.notifications = this.notifications.filter(n => n !== notification);
            }, 300);
        }, duration);
    }

    /**
     * Display transcription in UI
     * @param {string} transcript - Transcription text
     * @param {string} type - Transcription type ('real-time', 'final', 'turn-live', 'turn-final')
     * @param {number} confidence - Confidence score
     */
    displayTranscription(transcript, type = 'real-time', confidence = null) {
        let transcriptionArea = document.getElementById('transcriptionArea');
        if (!transcriptionArea) {
            transcriptionArea = this.createTranscriptionArea();
        }

        const content = document.getElementById('transcriptionContent');
        const timestamp = new Date().toLocaleTimeString();

        // Determine transcription type display
        const typeConfig = this.getTranscriptionTypeConfig(type);

        // Create transcription entry
        const entry = document.createElement('div');
        entry.className = `transcription-entry ${type}`;
        entry.innerHTML = `
            <div class="transcription-header">
                <span class="transcription-type">${typeConfig.display}</span>
                <span class="transcription-time">${timestamp}</span>
                ${confidence ? `<span class="transcription-confidence">${Math.round(confidence * 100)}%</span>` : ''}
            </div>
            <div class="transcription-text">${transcript}</div>
        `;

        // Style the entry
        Object.assign(entry.style, {
            marginBottom: '10px',
            padding: '10px',
            backgroundColor: typeConfig.backgroundColor,
            borderRadius: '8px',
            border: `1px solid ${typeConfig.borderColor}`
        });

        content.appendChild(entry);

        // Scroll to bottom
        transcriptionArea.scrollTop = transcriptionArea.scrollHeight;

        // Remove old entries if too many
        const entries = content.querySelectorAll('.transcription-entry');
        if (entries.length > 10) {
            entries[0].remove();
        }
    }

    /**
     * Display LLM response in UI
     * @param {string} response - LLM response text
     * @param {string} type - Response type ('chunk', 'complete')
     */
    displayLLMResponse(response, type = 'chunk') {
        let llmArea = document.getElementById('llmResponseArea');
        if (!llmArea) {
            llmArea = this.createLLMResponseArea();
        }

        const content = document.getElementById('llmResponseContent');
        const timestamp = new Date().toLocaleTimeString();

        if (type === 'complete') {
            // Display complete response
            const entry = document.createElement('div');
            entry.className = 'llm-response-entry complete';
            entry.innerHTML = `
                <div class="llm-response-header">
                    <span class="llm-response-type">✅ Complete</span>
                    <span class="llm-response-time">${timestamp}</span>
                </div>
                <div class="llm-response-text">${response}</div>
            `;

            Object.assign(entry.style, {
                marginBottom: '10px',
                padding: '10px',
                backgroundColor: 'rgba(0, 255, 136, 0.2)',
                borderRadius: '8px',
                border: '1px solid #00ff88'
            });

            content.appendChild(entry);
        } else {
            // Display streaming chunk
            let currentEntry = content.querySelector('.llm-response-entry.streaming');
            if (!currentEntry) {
                currentEntry = this.createStreamingLLMEntry(timestamp);
                content.appendChild(currentEntry);
            }

            // Append chunk to current streaming response
            const textElement = currentEntry.querySelector('.llm-response-text');
            textElement.textContent += response;
        }

        // Scroll to bottom
        llmArea.scrollTop = llmArea.scrollHeight;

        // Remove old entries if too many
        const entries = content.querySelectorAll('.llm-response-entry');
        if (entries.length > 5) {
            entries[0].remove();
        }
    }



    /**
     * Create transcription area
     * @returns {HTMLElement} Transcription area element
     */
    createTranscriptionArea() {
        const transcriptionArea = document.createElement('div');
        transcriptionArea.id = 'transcriptionArea';
        transcriptionArea.className = 'transcription-area';
        transcriptionArea.innerHTML = `
            <h3>🎤 Live Transcription</h3>
            <div id="transcriptionContent"></div>
        `;

        Object.assign(transcriptionArea.style, {
            position: 'fixed',
            bottom: '20px',
            left: '20px',
            width: '400px',
            maxHeight: '300px',
            backgroundColor: 'rgba(0, 0, 0, 0.9)',
            color: 'white',
            padding: '20px',
            borderRadius: '12px',
            fontSize: '14px',
            zIndex: '1000',
            overflowY: 'auto',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
        });

        document.body.appendChild(transcriptionArea);
        return transcriptionArea;
    }

    /**
     * Create LLM response area
     * @returns {HTMLElement} LLM response area element
     */
    createLLMResponseArea() {
        const llmArea = document.createElement('div');
        llmArea.id = 'llmResponseArea';
        llmArea.className = 'llm-response-area';
        llmArea.innerHTML = `
            <h3>🤖 LLM Response</h3>
            <div id="llmResponseContent"></div>
        `;

        Object.assign(llmArea.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            width: '400px',
            maxHeight: '300px',
            backgroundColor: 'rgba(0, 0, 0, 0.9)',
            color: 'white',
            padding: '20px',
            borderRadius: '12px',
            fontSize: '14px',
            zIndex: '1000',
            overflowY: 'auto',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
        });

        document.body.appendChild(llmArea);
        return llmArea;
    }



    /**
     * Create streaming LLM entry
     * @param {string} timestamp - Timestamp
     * @returns {HTMLElement} Streaming LLM entry element
     */
    createStreamingLLMEntry(timestamp) {
        const currentEntry = document.createElement('div');
        currentEntry.className = 'llm-response-entry streaming';
        currentEntry.innerHTML = `
            <div class="llm-response-header">
                <span class="llm-response-type">🔄 Streaming</span>
                <span class="llm-response-time">${timestamp}</span>
            </div>
            <div class="llm-response-text"></div>
        `;

        Object.assign(currentEntry.style, {
            marginBottom: '10px',
            padding: '10px',
            backgroundColor: 'rgba(102, 126, 234, 0.2)',
            borderRadius: '8px',
            border: '1px solid #667eea'
        });

        return currentEntry;
    }

    /**
     * Get transcription type configuration
     * @param {string} type - Transcription type
     * @returns {Object} Type configuration
     */
    getTranscriptionTypeConfig(type) {
        const configs = {
            'real-time': {
                display: '🔄 Live',
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderColor: '#667eea'
            },
            'final': {
                display: '✅ Final',
                backgroundColor: 'rgba(0, 255, 136, 0.2)',
                borderColor: '#00ff88'
            },
            'turn-live': {
                display: '🎤 Turn Live',
                backgroundColor: 'rgba(255, 193, 7, 0.2)',
                borderColor: '#ffc107'
            },
            'turn-final': {
                display: '🎤 Turn Complete',
                backgroundColor: 'rgba(220, 53, 69, 0.2)',
                borderColor: '#dc3545'
            }
        };

        return configs[type] || configs['real-time'];
    }

    /**
     * Animate elements on page load
     */
    animateOnLoad() {
        // Animate feature cards
        const featureCards = document.querySelectorAll('.feature-card');
        featureCards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';

            setTimeout(() => {
                card.style.transition = 'all 0.6s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 500 + (index * 100));
        });

        // Animate hero content
        const heroContent = document.querySelector('.hero-content');
        if (heroContent) {
            heroContent.style.opacity = '0';
            heroContent.style.transform = 'translateY(30px)';

            setTimeout(() => {
                heroContent.style.transition = 'all 0.8s ease';
                heroContent.style.opacity = '1';
                heroContent.style.transform = 'translateY(0)';
            }, 200);
        }

        // Animate voice indicator
        const voiceIndicator = document.querySelector('.voice-indicator');
        if (voiceIndicator) {
            voiceIndicator.style.opacity = '0';
            voiceIndicator.style.transform = 'scale(0.8)';

            setTimeout(() => {
                voiceIndicator.style.transition = 'all 0.8s ease';
                voiceIndicator.style.opacity = '1';
                voiceIndicator.style.transform = 'scale(1)';
            }, 600);
        }
    }

    /**
     * Dispatch custom event
     * @param {string} eventName - Event name
     * @param {Object} detail - Event detail
     */
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }

    /**
     * Clear all notifications
     */
    clearNotifications() {
        this.notifications.forEach(notification => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        });
        this.notifications = [];
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIManager;
} else {
    window.UIManager = UIManager;
}
