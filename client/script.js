// AI Voice Agent - WebSocket Audio Streaming Version
class VoiceAgent {
    constructor() {
        this.isListening = false;
        this.isConnected = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingStartTime = null;
        this.timerInterval = null;
        this.sessionId = this.getOrCreateSessionId();
        this.isConversationMode = false;
        this.audioPlayer = null;

        // WebSocket properties
        this.websocket = null;
        this.isWebSocketConnected = false;
        this.audioStreamInterval = null;
        this.chunkInterval = 100; // Send audio chunks every 100ms

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkServerConnection();
        this.animateOnLoad();
        this.updateSessionDisplay();
    }

    getOrCreateSessionId() {
        // Check URL params first
        const urlParams = new URLSearchParams(window.location.search);
        let sessionId = urlParams.get('session_id');

        if (!sessionId) {
            // Generate new session ID
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

            // Update URL without page reload
            const newUrl = new URL(window.location);
            newUrl.searchParams.set('session_id', sessionId);
            window.history.replaceState({}, '', newUrl);
        }

        console.log('💬 Session ID:', sessionId);
        return sessionId;
    }

    updateSessionDisplay() {
        // Add session info to the UI
        const echoSection = document.querySelector('.echo-bot');
        if (echoSection && !document.getElementById('sessionInfo')) {
            const sessionInfo = document.createElement('div');
            sessionInfo.id = 'sessionInfo';
            sessionInfo.className = 'session-info';
            sessionInfo.innerHTML = `
                <div class="session-details">
                    <span class="session-label">💬 Session:</span>
                    <span class="session-id">${this.sessionId}</span>
                    <button class="clear-chat-btn" onclick="voiceAgent.clearChatHistory()">🗑️ Clear Chat</button>
                </div>
            `;
            echoSection.insertBefore(sessionInfo, echoSection.firstChild);
        }
    }

    async clearChatHistory() {
        try {
            const response = await fetch(`/api/agent/chat/${this.sessionId}/clear`, {
                method: 'DELETE'
            });

            if (response.ok) {
                // Clear any displayed conversation
                const conversationDiv = document.getElementById('conversationDisplay');
                if (conversationDiv) {
                    conversationDiv.style.display = 'none';
                }

                // Reset conversation history
                this.conversationHistory = [];

                this.updateEchoStatus('Chat history cleared! Starting fresh conversation.', 'success');
                console.log('🗑️ Chat history cleared for session:', this.sessionId);
            }
        } catch (error) {
            console.error('Error clearing chat history:', error);
            this.updateEchoStatus('Failed to clear chat history', 'error');
        }
    }

    setupEventListeners() {
        const toggleRecordBtn = document.getElementById('toggleRecord');
        const learnMoreBtn = document.getElementById('learnMore');
        const voiceIndicator = document.getElementById('voiceIndicator');

        toggleRecordBtn.addEventListener('click', () => this.toggleRecording());
        learnMoreBtn.addEventListener('click', () => this.showInfo());
        voiceIndicator.addEventListener('click', () => this.toggleRecording());

        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.ctrlKey) {
                e.preventDefault();
                this.toggleRecording();
            }
        });
    }

    toggleRecording() {
        const toggleRecordBtn = document.getElementById('toggleRecord');
        const recordText = toggleRecordBtn.querySelector('.record-text');

        if (!this.isListening) {
            this.startRecording();
            toggleRecordBtn.classList.add('recording');
            recordText.textContent = 'Stop Recording';
        } else {
            this.stopRecording();
            toggleRecordBtn.classList.remove('recording');
            recordText.textContent = 'Start Recording';
        }
    }

    updateVoiceStatus(message, type = 'default', showSpinner = false) {
        const statusMessage = document.getElementById('statusMessage');
        const loadingSpinner = document.getElementById('loadingSpinner');
        const voiceStatus = document.getElementById('voiceStatus');

        statusMessage.textContent = message;
        loadingSpinner.style.display = showSpinner ? 'flex' : 'none';

        // Reset classes
        voiceStatus.className = 'voice-status';
        if (type !== 'default') {
            voiceStatus.classList.add(`status-${type}`);
        }
    }

    // WebSocket connection management
    connectWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                // Determine WebSocket URL
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/audio`;

                console.log('🔌 Connecting to WebSocket:', wsUrl);

                this.websocket = new WebSocket(wsUrl);

                this.websocket.onopen = () => {
                    console.log('✅ WebSocket connected');
                    this.isWebSocketConnected = true;
                    resolve();
                };

                this.websocket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        console.log('📨 WebSocket message:', data);

                        if (data.type === 'status') {
                            this.updateEchoStatus(`WebSocket: ${data.message}`, 'success');
                        } else if (data.type === 'error') {
                            this.updateEchoStatus(`WebSocket Error: ${data.message}`, 'error');
                        } else if (data.type === 'chunk_received') {
                            // Optional: Update status with chunk info
                            // this.updateEchoStatus(`Received chunk: ${data.chunk_size} bytes`, 'default');
                        } else if (data.type === 'transcription') {
                            // Handle real-time transcription
                            console.log('🎤 Real-time transcription:', data.transcript);
                            this.updateEchoStatus(`🎤 Real-time: ${data.transcript}`, 'transcription');

                            // Display transcription in UI
                            this.displayTranscription(data.transcript, 'real-time', data.confidence);
                        } else if (data.type === 'final_transcription') {
                            // Handle final transcription
                            console.log('🎤 Final transcription:', data.transcript);
                            this.updateEchoStatus(`🎤 Final: ${data.transcript}`, 'success');

                            // Display final transcription in UI
                            this.displayTranscription(data.transcript, 'final', data.confidence);
                        }
                    } catch (e) {
                        console.log('📨 WebSocket raw message:', event.data);
                    }
                };

                this.websocket.onerror = (error) => {
                    console.error('❌ WebSocket error:', error);
                    this.isWebSocketConnected = false;
                    reject(error);
                };

                this.websocket.onclose = () => {
                    console.log('🔌 WebSocket disconnected');
                    this.isWebSocketConnected = false;
                };

            } catch (error) {
                console.error('❌ WebSocket connection error:', error);
                reject(error);
            }
        });
    }

    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
            this.isWebSocketConnected = false;
        }
    }

    async startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.updateEchoStatus('Your browser does not support audio recording', 'error');
            return;
        }

        try {
            // Connect to WebSocket first
            await this.connectWebSocket();

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    sampleRate: 16000,  // Use 16kHz for better compatibility
                    channelCount: 1     // Mono audio
                }
            });

            this.audioChunks = [];

            // Configure MediaRecorder with compatible settings
            const options = {
                mimeType: 'audio/webm;codecs=opus',  // Use WebM with Opus codec
                audioBitsPerSecond: 16000
            };

            // Fallback to other formats if WebM is not supported
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'audio/mp4';
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                    options.mimeType = 'audio/wav';
                    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                        // Use default format
                        delete options.mimeType;
                    }
                }
            }

            console.log('🎤 Using audio format:', options.mimeType || 'default');

            this.mediaRecorder = new MediaRecorder(stream, options);
            this.isListening = true;

            // Send start signal to WebSocket
            if (this.isWebSocketConnected) {
                this.websocket.send(JSON.stringify({
                    type: 'start',
                    timestamp: Date.now(),
                    audioFormat: options.mimeType || 'default'
                }));
            }

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    // Send audio chunk immediately via WebSocket
                    this.sendAudioChunk(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.stopWebSocketStreaming();
                stream.getTracks().forEach(track => track.stop());
            };

            // Start recording with small timeslice for frequent chunks
            this.mediaRecorder.start(this.chunkInterval);
            this.recordingStartTime = Date.now();
            this.startTimer();

            // Update UI
            const toggleRecordBtn = document.getElementById('toggleRecord');
            if (toggleRecordBtn) {
                toggleRecordBtn.disabled = true;
                toggleRecordBtn.classList.add('recording');
            }

            const audioPlayback = document.getElementById('audioPlayback');
            if (audioPlayback) {
                audioPlayback.style.display = 'none';
            }

            this.updateEchoStatus('Recording... Sending audio via WebSocket', 'recording');

        } catch (error) {
            console.error('Error starting recording:', error);
            this.updateEchoStatus('Failed to access microphone. Please check permissions.', 'error');
        }
    }

    sendAudioChunk(audioBlob) {
        if (!this.isWebSocketConnected || !this.websocket) {
            console.warn('WebSocket not connected, cannot send audio chunk');
            return;
        }

        try {
            // Convert blob to base64 and send
            const reader = new FileReader();
            reader.onload = () => {
                const base64Data = reader.result.split(',')[1]; // Remove data URL prefix
                this.websocket.send(base64Data);
            };
            reader.readAsDataURL(audioBlob);
        } catch (error) {
            console.error('Error sending audio chunk:', error);
        }
    }

    stopWebSocketStreaming() {
        if (this.isWebSocketConnected && this.websocket) {
            // Send stop signal
            this.websocket.send(JSON.stringify({
                type: 'stop',
                timestamp: Date.now()
            }));
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            this.stopTimer();

            // Update UI
            const toggleRecordBtn = document.getElementById('toggleRecord');
            if (toggleRecordBtn) {
                toggleRecordBtn.disabled = false;
                toggleRecordBtn.classList.remove('recording');
            }

            this.updateEchoStatus('Recording stopped. Audio saved via WebSocket.', 'success');

            console.log('🛑 Recording stopped');
        }
    }

    // Add missing methods
    async processRecording(audioBlob) {
        this.updateVoiceStatus('Processing your message...', 'loading', true);

        try {
            // Create form data for upload
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            formData.append('session_id', this.sessionId);

            // Upload audio file
            const response = await fetch('/api/agent/chat', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Failed to process audio');

            const data = await response.json();

            // Auto-play the response
            if (data.audio_url) {
                const audio = new Audio(data.audio_url);
                audio.play();
            }

            // Display the conversation
            this.displayAgentConversation(data.user_message, data.assistant_response, data.message_count);
            this.updateVoiceStatus('Ready to record', 'default');

        } catch (error) {
            console.error('Error processing recording:', error);
            this.updateVoiceStatus('Error processing your message. Please try again.', 'error');
        }
    }

    updateTtsStatus(message, type = 'default', showSpinner = false) {
        const statusMessage = document.getElementById('statusMessage');
        const loadingSpinner = document.getElementById('loadingSpinner');

        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;

        if (showSpinner) {
            loadingSpinner.style.display = 'flex';
        } else {
            loadingSpinner.style.display = 'none';
        }
    }

    checkServerConnection() {
        // Check if server is available
        fetch('/api/health')
            .then(response => {
                if (response.ok) {
                    this.isConnected = true;
                    console.log('✅ Server connection established');
                }
            })
            .catch(error => {
                this.isConnected = false;
                console.error('❌ Server connection failed:', error);
            });
    }

    updateConnectionStatus(isConnected) {
        this.isConnected = isConnected;
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');

        if (isConnected) {
            statusIndicator.style.background = '#00ff88';
            statusText.textContent = 'Connected';
        } else {
            statusIndicator.style.background = '#ff4757';
            statusText.textContent = 'Disconnected';
        }
    }

    toggleVoiceChat() {
        if (!this.isConnected) {
            this.showNotification('Please wait for server connection...', 'warning');
            return;
        }

        const startVoiceBtn = document.getElementById('startVoice');
        const voiceIndicator = document.getElementById('voiceIndicator');

        this.isListening = !this.isListening;

        if (this.isListening) {
            this.startListening();
            startVoiceBtn.innerHTML = `
                <svg class="btn-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="6" y="6" width="12" height="12"/>
                </svg>
                Stop Listening
            `;
            startVoiceBtn.style.background = 'linear-gradient(45deg, #ff4757 0%, #ff3742 100%)';
            voiceIndicator.classList.add('listening');
        } else {
            this.stopListening();
            startVoiceBtn.innerHTML = `
                <svg class="btn-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 1C10.34 1 9 2.34 9 4V12C9 13.66 10.34 15 12 15S15 13.66 15 12V4C15 2.34 13.66 1 12 1Z"/>
                    <path d="M19 10V12C19 15.87 15.87 19 12 19S5 15.87 5 12V10"/>
                    <path d="M12 19V23"/>
                    <path d="M8 23H16"/>
                </svg>
                Start Voice Chat
            `;
            startVoiceBtn.style.background = 'linear-gradient(45deg, #667eea 0%, #764ba2 100%)';
            voiceIndicator.classList.remove('listening');
        }
    }

    startListening() {
        console.log('🎤 Voice chat started');
        this.showNotification('Voice chat activated! Speak now...', 'success');

        // Add listening animation
        const pulseRings = document.querySelectorAll('.pulse-ring');
        pulseRings.forEach(ring => {
            ring.style.animationDuration = '1s';
            ring.style.borderColor = 'rgba(0, 255, 136, 0.6)';
        });
    }

    stopListening() {
        console.log('🛑 Voice chat stopped');
        this.showNotification('Voice chat deactivated', 'info');

        // Reset animation
        const pulseRings = document.querySelectorAll('.pulse-ring');
        pulseRings.forEach(ring => {
            ring.style.animationDuration = '2s';
            ring.style.borderColor = 'rgba(102, 126, 234, 0.3)';
        });
    }

    // Add missing methods
    animateOnLoad() {
        // Simple animation for UI elements on load
        const voiceStatus = document.getElementById('voiceStatus');
        if (voiceStatus) {
            voiceStatus.classList.add('animate-in');
            setTimeout(() => {
                voiceStatus.classList.remove('animate-in');
            }, 1000);
        }
    }

    startTimer() {
        // Start recording timer
        const timerDisplay = document.getElementById('recordingTimer');
        if (!timerDisplay) return;

        timerDisplay.style.display = 'block';
        timerDisplay.textContent = '00:00';

        const startTime = Date.now();
        this.timerInterval = setInterval(() => {
            const elapsedTime = Date.now() - startTime;
            const seconds = Math.floor((elapsedTime / 1000) % 60);
            const minutes = Math.floor((elapsedTime / (1000 * 60)) % 60);
            timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    stopTimer() {
        // Stop recording timer
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        const timerDisplay = document.getElementById('recordingTimer');
        if (timerDisplay) {
            timerDisplay.style.display = 'none';
        }
    }

    updateEchoStatus(message, type = 'default', showSpinner = false) {
        // Update status message in the UI
        const statusElement = document.getElementById('echoStatus');
        if (!statusElement) return;

        // Clear existing classes
        statusElement.className = 'echo-status';
        if (type !== 'default') {
            statusElement.classList.add(`status-${type}`);
        }

        statusElement.textContent = message;

        // Handle spinner if needed
        const spinner = document.getElementById('echoSpinner');
        if (spinner) {
            spinner.style.display = showSpinner ? 'inline-block' : 'none';
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
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

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    displayTranscription(transcript, type = 'real-time', confidence = null) {
        // Create or get transcription display area
        let transcriptionArea = document.getElementById('transcriptionArea');
        if (!transcriptionArea) {
            transcriptionArea = document.createElement('div');
            transcriptionArea.id = 'transcriptionArea';
            transcriptionArea.className = 'transcription-area';
            transcriptionArea.innerHTML = `
                <h3>🎤 Live Transcription</h3>
                <div id="transcriptionContent"></div>
            `;

            // Style the transcription area
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
        }

        const content = document.getElementById('transcriptionContent');
        const timestamp = new Date().toLocaleTimeString();

        // Create transcription entry
        const entry = document.createElement('div');
        entry.className = `transcription-entry ${type}`;
        entry.innerHTML = `
            <div class="transcription-header">
                <span class="transcription-type">${type === 'real-time' ? '🔄 Live' : '✅ Final'}</span>
                <span class="transcription-time">${timestamp}</span>
                ${confidence ? `<span class="transcription-confidence">${Math.round(confidence * 100)}%</span>` : ''}
            </div>
            <div class="transcription-text">${transcript}</div>
        `;

        // Style the entry
        Object.assign(entry.style, {
            marginBottom: '10px',
            padding: '10px',
            backgroundColor: type === 'real-time' ? 'rgba(102, 126, 234, 0.2)' : 'rgba(0, 255, 136, 0.2)',
            borderRadius: '8px',
            border: `1px solid ${type === 'real-time' ? '#667eea' : '#00ff88'}`
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

    displayAgentConversation(userMessage, aiResponse, messageCount) {
        const conversationDiv = document.getElementById('conversationDisplay');
        if (!conversationDiv) return;

        // Show the conversation display
        conversationDiv.style.display = 'block';

        // Create conversation entry
        const conversationEntry = document.createElement('div');
        conversationEntry.className = 'conversation-entry';
        conversationEntry.innerHTML = `
            <div class="message user-message">
                <div class="message-header">
                    <span class="message-type">👤 You</span>
                    <span class="message-time">${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="message-content">${userMessage}</div>
            </div>
            <div class="message ai-message">
                <div class="message-header">
                    <span class="message-type">🤖 AI Assistant</span>
                    <span class="message-time">${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="message-content">${aiResponse}</div>
            </div>
        `;

        // Style the conversation entry
        Object.assign(conversationEntry.style, {
            marginBottom: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
        });

        // Style user message
        const userMsg = conversationEntry.querySelector('.user-message');
        Object.assign(userMsg.style, {
            background: 'rgba(102, 126, 234, 0.1)',
            border: '1px solid rgba(102, 126, 234, 0.3)',
            borderRadius: '12px',
            padding: '16px',
            alignSelf: 'flex-end',
            maxWidth: '80%'
        });

        // Style AI message
        const aiMsg = conversationEntry.querySelector('.ai-message');
        Object.assign(aiMsg.style, {
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '12px',
            padding: '16px',
            alignSelf: 'flex-start',
            maxWidth: '80%'
        });

        // Style message headers
        const headers = conversationEntry.querySelectorAll('.message-header');
        headers.forEach(header => {
            Object.assign(header.style, {
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px',
                fontSize: '0.9rem',
                opacity: '0.8'
            });
        });

        // Style message content
        const contents = conversationEntry.querySelectorAll('.message-content');
        contents.forEach(content => {
            Object.assign(content.style, {
                fontSize: '1rem',
                lineHeight: '1.5'
            });
        });

        conversationDiv.appendChild(conversationEntry);

        // Scroll to bottom
        conversationDiv.scrollTop = conversationDiv.scrollHeight;

        // Remove old entries if too many
        const entries = conversationDiv.querySelectorAll('.conversation-entry');
        if (entries.length > 5) {
            entries[0].remove();
        }
    }

    animateOnLoad() {
        // Add stagger animation to feature cards
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
        heroContent.style.opacity = '0';
        heroContent.style.transform = 'translateY(30px)';

        setTimeout(() => {
            heroContent.style.transition = 'all 0.8s ease';
            heroContent.style.opacity = '1';
            heroContent.style.transform = 'translateY(0)';
        }, 200);

        // Animate voice indicator
        const voiceIndicator = document.querySelector('.voice-indicator');
        voiceIndicator.style.opacity = '0';
        voiceIndicator.style.transform = 'scale(0.8)';

        setTimeout(() => {
            voiceIndicator.style.transition = 'all 0.8s ease';
            voiceIndicator.style.opacity = '1';
            voiceIndicator.style.transform = 'scale(1)';
        }, 600);
    }
}

// Add listening state styles
const style = document.createElement('style');
style.textContent = `
    .voice-indicator.listening .pulse-ring {
        border-color: rgba(0, 255, 136, 0.6) !important;
        animation-duration: 1s !important;
    }
    
    .voice-indicator.listening .microphone-icon {
        background: linear-gradient(45deg, #00ff88 0%, #00cc6a 100%) !important;
        animation: micPulse 1s ease-in-out infinite !important;
    }
    
    @keyframes micPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    
    .echo-status.status-transcription {
        color: #667eea !important;
        font-weight: bold;
    }
    
    .transcription-area h3 {
        margin: 0 0 15px 0;
        color: #00ff88;
        font-size: 16px;
    }
    
    .transcription-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
        font-size: 12px;
        opacity: 0.8;
    }
    
    .transcription-type {
        font-weight: bold;
    }
    
    .transcription-confidence {
        background: rgba(0, 255, 136, 0.3);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 10px;
    }
    
    .transcription-text {
        font-size: 13px;
        line-height: 1.4;
    }
`;
document.head.appendChild(style);

// Initialize the voice agent when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const voiceAgent = new VoiceAgent();

    // Make it globally accessible for debugging
    window.voiceAgent = voiceAgent;

    console.log('🚀 AI Voice Agent initialized!');
    console.log('📅 Day 1 of 30 Days Challenge');
    console.log('💡 Use Ctrl+Space to toggle voice chat');
});
