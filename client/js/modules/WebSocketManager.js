/**
 * WebSocket Manager Module - Handles all WebSocket connections
 * Manages main audio WebSocket and turn detection WebSocket
 */
class WebSocketManager {
    constructor() {
        this.mainWebSocket = null;
        this.turnDetectionWebSocket = null;
        this.isMainConnected = false;
        this.isTurnDetectionConnected = false;
        this.messageHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;

        this.init();
    }

    init() {
        // Register default message handlers
        this.registerMessageHandlers();
    }

    /**
     * Register message handlers for different message types
     */
    registerMessageHandlers() {
        this.messageHandlers.set('status', this.handleStatus.bind(this));
        this.messageHandlers.set('error', this.handleError.bind(this));
        this.messageHandlers.set('transcription', this.handleTranscription.bind(this));
        this.messageHandlers.set('final_transcription', this.handleFinalTranscription.bind(this));
        this.messageHandlers.set('llm_stream_chunk', this.handleLLMStreamChunk.bind(this));
        this.messageHandlers.set('llm_error', this.handleLLMError.bind(this));
        this.messageHandlers.set('murf_base64_audio_chunk', this.handleMurfBase64AudioChunk.bind(this));
        this.messageHandlers.set('murf_error', this.handleMurfError.bind(this));
        this.messageHandlers.set('transcription_update', this.handleTranscriptionUpdate.bind(this));
        this.messageHandlers.set('turn_end', this.handleTurnEnd.bind(this));
        this.messageHandlers.set('chunk_received', this.handleChunkReceived.bind(this));
    }

    /**
     * Connect to main audio WebSocket
     * @returns {Promise}
     */
    async connectMainWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/audio`;

                console.log('🔌 Connecting to Main WebSocket:', wsUrl);

                this.mainWebSocket = new WebSocket(wsUrl);

                this.mainWebSocket.onopen = () => {
                    console.log('✅ Main WebSocket connected');
                    this.isMainConnected = true;
                    this.reconnectAttempts = 0;
                    resolve();
                };

                this.mainWebSocket.onmessage = (event) => {
                    this.handleMessage(event, 'main');
                };

                this.mainWebSocket.onerror = (error) => {
                    console.error('❌ Main WebSocket error:', error);
                    this.isMainConnected = false;
                    reject(error);
                };

                this.mainWebSocket.onclose = () => {
                    console.log('🔌 Main WebSocket disconnected');
                    this.isMainConnected = false;
                    this.attemptReconnect('main');
                };

            } catch (error) {
                console.error('❌ Main WebSocket connection error:', error);
                reject(error);
            }
        });
    }

    /**
     * Connect to turn detection WebSocket
     * @returns {Promise}
     */
    async connectTurnDetectionWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/turn-detection`;

                console.log('🔌 Connecting to Turn Detection WebSocket:', wsUrl);

                this.turnDetectionWebSocket = new WebSocket(wsUrl);

                this.turnDetectionWebSocket.onopen = () => {
                    console.log('✅ Turn Detection WebSocket connected');
                    this.isTurnDetectionConnected = true;
                    this.reconnectAttempts = 0;
                    resolve();
                };

                this.turnDetectionWebSocket.onmessage = (event) => {
                    this.handleMessage(event, 'turn-detection');
                };

                this.turnDetectionWebSocket.onerror = (error) => {
                    console.error('❌ Turn Detection WebSocket error:', error);
                    this.isTurnDetectionConnected = false;
                    reject(error);
                };

                this.turnDetectionWebSocket.onclose = () => {
                    console.log('🔌 Turn Detection WebSocket disconnected');
                    this.isTurnDetectionConnected = false;
                    this.attemptReconnect('turn-detection');
                };

            } catch (error) {
                console.error('❌ Turn Detection WebSocket connection error:', error);
                reject(error);
            }
        });
    }

    /**
     * Handle incoming WebSocket messages
     * @param {MessageEvent} event - WebSocket message event
     * @param {string} source - Source WebSocket ('main' or 'turn-detection')
     */
    handleMessage(event, source) {
        try {
            const data = JSON.parse(event.data);
            console.log(`📨 ${source} WebSocket message:`, data);

            // Special logging for audio-related messages
            if (data.type && data.type.includes('audio') || data.type === 'murf_base64_audio_chunk') {
                console.log(`🎵 AUDIO MESSAGE RECEIVED: ${data.type} from ${source}`);
                console.log(`🎵 Audio data:`, {
                    type: data.type,
                    hasChunk: !!data.chunk,
                    chunkLength: data.chunk ? data.chunk.length : 0,
                    chunkIndex: data.chunk_index,
                    totalChunks: data.total_chunks,
                    isComplete: data.is_complete
                });
            }

            // First try to get handler from the Map
            let handler = this.messageHandlers.get(data.type);

            // If not found in Map, try to get from instance properties (for overridden handlers)
            if (!handler) {
                const handlerName = `handle${data.type.charAt(0).toUpperCase() + data.type.slice(1).replace(/_([a-z])/g, (g) => g[1].toUpperCase())}`;
                handler = this[handlerName];
            }

            if (handler && typeof handler === 'function') {
                console.log(`📨 Calling handler for message type: ${data.type}`);
                try {
                    handler.call(this, data, source);
                } catch (error) {
                    console.error(`📨 Handler error for ${data.type}:`, error);
                }
            } else {
                console.log(`📨 Unhandled message type: ${data.type}`);
                // Log all available handlers for debugging
                if (data.type && data.type.includes('audio')) {
                    console.log(`🔍 Available handlers:`, Array.from(this.messageHandlers.keys()));
                }
            }
        } catch (e) {
            console.log(`📨 ${source} WebSocket raw message:`, event.data);
        }
    }

    /**
     * Send message to main WebSocket
     * @param {Object|string} message - Message to send
     */
    sendToMain(message) {
        if (this.isMainConnected && this.mainWebSocket) {
            try {
                const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
                this.mainWebSocket.send(messageStr);
            } catch (error) {
                console.error('❌ Error sending to main WebSocket:', error);
            }
        }
    }

    /**
     * Send message to turn detection WebSocket
     * @param {Object|string} message - Message to send
     */
    sendToTurnDetection(message) {
        if (this.isTurnDetectionConnected && this.turnDetectionWebSocket) {
            try {
                const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
                this.turnDetectionWebSocket.send(messageStr);
            } catch (error) {
                console.error('❌ Error sending to turn detection WebSocket:', error);
            }
        }
    }

    /**
     * Send audio chunk to both WebSockets
     * @param {string} base64Audio - Base64 encoded audio data
     */
    sendAudioChunk(base64Audio) {
        this.sendToMain(base64Audio);
        this.sendToTurnDetection(base64Audio);
    }

    /**
     * Send start signal to both WebSockets
     * @param {Object} startData - Start signal data
     */
    sendStartSignal(startData) {
        this.sendToMain({ type: 'start', ...startData });
        this.sendToTurnDetection({ type: 'start', ...startData });
    }

    /**
     * Send stop signal to both WebSockets
     * @param {Object} stopData - Stop signal data
     */
    sendStopSignal(stopData) {
        this.sendToMain({ type: 'stop', ...stopData });
        this.sendToTurnDetection({ type: 'stop', ...stopData });
    }

    /**
     * Disconnect all WebSockets
     */
    disconnect() {
        if (this.mainWebSocket) {
            this.mainWebSocket.close();
            this.mainWebSocket = null;
            this.isMainConnected = false;
        }

        if (this.turnDetectionWebSocket) {
            this.turnDetectionWebSocket.close();
            this.turnDetectionWebSocket = null;
            this.isTurnDetectionConnected = false;
        }
    }

    /**
     * Attempt to reconnect to WebSocket
     * @param {string} type - WebSocket type ('main' or 'turn-detection')
     */
    async attemptReconnect(type) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`❌ Max reconnect attempts reached for ${type} WebSocket`);
            return;
        }

        this.reconnectAttempts++;
        console.log(`🔄 Attempting to reconnect ${type} WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(async () => {
            try {
                if (type === 'main') {
                    await this.connectMainWebSocket();
                } else if (type === 'turn-detection') {
                    await this.connectTurnDetectionWebSocket();
                }
            } catch (error) {
                console.error(`❌ Reconnect failed for ${type} WebSocket:`, error);
            }
        }, this.reconnectDelay * this.reconnectAttempts);
    }

    // Message handlers - these will be overridden by the main VoiceAgent
    handleStatus(data, source) {
        // Override in main class
    }

    handleError(data, source) {
        // Override in main class
    }

    handleTranscription(data, source) {
        // Override in main class
    }

    handleFinalTranscription(data, source) {
        // Override in main class
    }

    handleLLMStreamChunk(data, source) {
        // Override in main class
    }

    handleLLMError(data, source) {
        // Override in main class
    }

    handleMurfBase64AudioChunk(data, source) {
        // Override in main class
    }

    handleMurfError(data, source) {
        // Override in main class
    }

    handleTranscriptionUpdate(data, source) {
        // Override in main class
    }

    handleTurnEnd(data, source) {
        // Override in main class
    }

    handleChunkReceived(data, source) {
        // Override in main class
    }

    /**
     * Get connection status
     * @returns {Object} Connection status
     */
    getStatus() {
        return {
            mainConnected: this.isMainConnected,
            turnDetectionConnected: this.isTurnDetectionConnected,
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketManager;
} else {
    window.WebSocketManager = WebSocketManager;
}
