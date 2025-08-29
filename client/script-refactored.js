/**
 * AI Voice Agent - Refactored Modular Version
 * Main application class that orchestrates all modules
 * Features seamless audio playback from base64 chunks
 */

// Import modules (these will be loaded via script tags in HTML)
// AudioPlayer, WebSocketManager, RecordingManager, UIManager

class VoiceAgent {
    constructor() {
        // Core properties
        this.sessionId = this.getOrCreateSessionId();
        this.isConversationMode = true;

        // Turn detection properties
        this.currentTurnTranscript = "";
        this.isUserSpeaking = false;
        this.turnTimeout = null;
        this.turnEndCallback = null;

        // Base64 audio streaming properties
        this.base64AudioChunks = [];
        this.currentAudioStreamId = null;
        this.isReceivingAudio = false;

        // Initialize modules
        this.initModules();
        this.init();
    }

    /**
     * Initialize all modules
     */
    initModules() {
        // Initialize WebSocket Manager
        this.webSocketManager = new WebSocketManager();

        // Initialize Recording Manager with WebSocket Manager
        this.recordingManager = new RecordingManager(this.webSocketManager);

        // Initialize UI Manager
        this.uiManager = new UIManager();

        // Initialize Audio Player
        this.audioPlayer = new AudioPlayer();

        // Initialize Configuration Manager
        this.configManager = new ConfigManager();

        // Override WebSocket message handlers
        this.setupWebSocketHandlers();
    }

    /**
     * Setup WebSocket message handlers
     */
    setupWebSocketHandlers() {
        // Override message handlers to connect to UI and audio player
        // Register all custom handlers in the messageHandlers Map
        this.webSocketManager.messageHandlers.set('status', (data, source) => {
            this.uiManager.updateEchoStatus(`WebSocket: ${data.message}`, 'success');
        });

        this.webSocketManager.messageHandlers.set('error', (data, source) => {
            this.uiManager.updateEchoStatus(`WebSocket Error: ${data.message}`, 'error');
        });

        this.webSocketManager.messageHandlers.set('transcription', (data, source) => {
            console.log('🎤 Real-time transcription:', data.transcript);
            this.uiManager.updateEchoStatus(`🎤 Real-time: ${data.transcript}`, 'transcription');
            this.uiManager.displayTranscription(data.transcript, 'real-time', data.confidence);
        });

        this.webSocketManager.messageHandlers.set('final_transcription', (data, source) => {
            console.log('🎤 Final transcription:', data.transcript);
            this.uiManager.updateEchoStatus(`🎤 Final: ${data.transcript}`, 'success');
            this.uiManager.displayTranscription(data.transcript, 'final', data.confidence);
        });

        this.webSocketManager.messageHandlers.set('llm_stream_chunk', (data, source) => {
            if (data.is_complete) {
                console.log('🤖 LLM response complete:', data.full_response);
                this.uiManager.updateEchoStatus(`🤖 LLM Complete: ${data.full_response.substring(0, 50)}...`, 'success');
                this.uiManager.displayLLMResponse(data.full_response, 'complete');
            } else {
                console.log('🤖 LLM chunk:', data.chunk);
                this.uiManager.displayLLMResponse(data.chunk, 'chunk');
            }
        });

        this.webSocketManager.messageHandlers.set('llm_error', (data, source) => {
            console.error('❌ LLM error:', data.error);
            this.uiManager.updateEchoStatus(`❌ LLM Error: ${data.error}`, 'error');
        });

        // Register custom handlers in the messageHandlers Map (this is the correct way)
        this.webSocketManager.messageHandlers.set('murf_base64_audio_chunk', (data, source) => {
            console.log('🎵 handleMurfBase64AudioChunk called with:', { data, source });
            console.log('🎵 VoiceAgent instance:', this);
            console.log('🎵 AudioPlayer exists:', !!this.audioPlayer);
            console.log('🎵 About to call handleBase64AudioChunk...');
            this.handleBase64AudioChunk(data, source);
        });

        // Verify the handler was set correctly
        console.log('🔧 Handler verification:', {
            mapHasHandler: this.webSocketManager.messageHandlers.has('murf_base64_audio_chunk'),
            handlerType: typeof this.webSocketManager.messageHandlers.get('murf_base64_audio_chunk')
        });

        this.webSocketManager.messageHandlers.set('murf_error', (data, source) => {
            console.error('❌ Murf error:', data.error);
            this.uiManager.updateEchoStatus(`❌ Murf Error: ${data.error}`, 'error');
        });

        this.webSocketManager.messageHandlers.set('transcription_update', (data, source) => {
            console.log('🎤 Turn transcription update:', data.transcript);
            this.currentTurnTranscript = data.transcript;
            this.isUserSpeaking = data.is_speaking;
            this.uiManager.displayTranscription(data.transcript, 'turn-live', null);
            this.resetTurnTimeout();
        });

        this.webSocketManager.messageHandlers.set('turn_end', (data, source) => {
            console.log('🎤 Turn ended:', data.transcript);
            this.handleTurnEnd(data.transcript, data.timestamp);
        });

        this.webSocketManager.messageHandlers.set('chunk_received', (data, source) => {
            // Handle chunk_received messages - these are acknowledgments from server
            console.log('📨 Server acknowledgment:', data);
            this.uiManager.updateEchoStatus(`📨 Server received chunk: ${data.chunk_size} bytes`, 'info');
        });
    }

    /**
     * Initialize the application
     */
    init() {
        this.setupEventListeners();
        this.checkServerConnection();
        this.updateSessionDisplay();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Recording button events
        const toggleRecordBtn = document.getElementById('toggleRecord');
        const letsGetStartedBtn = document.getElementById('letsGetStarted');
        const learnMoreBtn = document.getElementById('learnMore');
        const voiceIndicator = document.getElementById('voiceIndicator');

        if (toggleRecordBtn) {
            toggleRecordBtn.addEventListener('click', () => this.toggleRecording());
        }
        if (letsGetStartedBtn) {
            letsGetStartedBtn.addEventListener('click', () => this.scrollToAISection());
        }
        if (learnMoreBtn) {
            learnMoreBtn.addEventListener('click', () => this.showInfo());
        }
        if (voiceIndicator) {
            voiceIndicator.addEventListener('click', () => this.toggleRecording());
        }

        // Quick question button events
        this.setupQuickQuestionListeners();

        // Show more commands button
        const showMoreBtn = document.getElementById('showMoreCommands');
        if (showMoreBtn) {
            showMoreBtn.addEventListener('click', () => this.showMoreCommands());
        }

        // Listen for custom events
        document.addEventListener('toggleRecording', () => this.toggleRecording());
        document.addEventListener('audioPlaybackComplete', (e) => this.onAudioPlaybackComplete(e));

        // Resume audio context on user interaction
        const resumeAudioContext = async () => {
            if (this.audioPlayer && this.audioPlayer.audioContext && this.audioPlayer.audioContext.state === 'suspended') {
                try {
                    await this.audioPlayer.audioContext.resume();
                    console.log('🎵 Audio Context resumed successfully');
                } catch (error) {
                    console.error('❌ Failed to resume audio context:', error);
                }
            }
        };

        // Add event listeners for user interaction
        document.addEventListener('click', resumeAudioContext, { once: true });
        document.addEventListener('keydown', resumeAudioContext, { once: true });
    }

    /**
     * Toggle recording state
     */
    async toggleRecording() {
        const isRecording = this.recordingManager.getStatus().isRecording;

        if (!isRecording) {
            await this.startRecording();
        } else {
            this.stopRecording();
        }
    }

    /**
     * Start recording
     */
    async startRecording() {
        // Validate API keys before starting recording
        const validation = await this.configManager.validateRecordingRequirements();
        if (!validation.isValid) {
            const missingKeyNames = validation.missingKeys.map(key => {
                const keyConfigs = {
                    'ASSEMBLYAI_API_KEY': 'AssemblyAI (Speech-to-Text)',
                    'GEMINI_API_KEY': 'Google Gemini (AI Language Model)',
                    'MURF_API_KEY': 'Murf AI (Text-to-Speech)'
                };
                return keyConfigs[key] || key;
            });

            const reason = `Recording requires the following API keys: ${missingKeyNames.join(', ')}. Please configure them to start recording.`;
            this.configManager.openModalWithFocus(validation.missingKeys, reason);
            return;
        }

        this.uiManager.updateEchoStatus('Starting recording...', 'info', true);

        const success = await this.recordingManager.startRecording();

        if (success) {
            this.uiManager.updateRecordingButtons(true);
            this.uiManager.updateEchoStatus('Recording... Turn detection active', 'recording');
            this.uiManager.showNotification('Recording started! Speak now...', 'success');
        } else {
            this.uiManager.updateEchoStatus('Failed to start recording', 'error');
            this.uiManager.showNotification('Failed to start recording. Please check microphone permissions.', 'error');
        }
    }

    /**
     * Stop recording
     */
    stopRecording() {
        this.recordingManager.stopRecording();
        this.uiManager.updateRecordingButtons(false);
        this.uiManager.updateEchoStatus('Recording stopped. Turn detection completed.', 'success');
        this.uiManager.showNotification('Recording stopped', 'info');
    }

    /**
 * Handle base64 audio chunks with seamless playback
 * @param {Object} data - Audio chunk data
 * @param {string} source - Source WebSocket
 */
    handleBase64AudioChunk(data, source = 'main') {

        const { chunk, chunk_index, total_chunks, is_complete, text } = data;

        if (is_complete) {
            // Audio streaming completed - now concatenate all chunks and play the complete audio
            if (this.base64AudioChunks.length > 0) {
                // Concatenate all base64 chunks into a single audio file
                const completeBase64Audio = this.base64AudioChunks.join('');

                // Play the complete audio file
                this.audioPlayer.playChunk(completeBase64Audio, true);
            }

            // Update UI
            this.uiManager.updateEchoStatus(`🎵 Audio playback started - ${this.base64AudioChunks.length} chunks concatenated`, 'success');

            // Reset for next audio stream
            this.base64AudioChunks = [];
            this.currentAudioStreamId = null;
            this.isReceivingAudio = false;

        } else {
            // Handle audio chunk - just collect chunks, don't play individually
            if (!this.isReceivingAudio) {
                // Start new audio stream
                this.isReceivingAudio = true;
                this.currentAudioStreamId = `audio_${Date.now()}`;
                this.base64AudioChunks = [];
                this.uiManager.updateEchoStatus(`🎵 Collecting audio chunks (${source})`, 'info');
            }

            // Add chunk to array for later concatenation
            if (chunk && chunk.trim()) {
                this.base64AudioChunks.push(chunk);
            }

            // Update status periodically
            if ((chunk_index + 1) % 10 === 0 || chunk_index + 1 === total_chunks) {
                this.uiManager.updateEchoStatus(`🎵 Collecting: ${chunk_index + 1}/${total_chunks} chunks`, 'info');
            }
        }
    }

    /**
     * Handle audio playback completion
     * @param {CustomEvent} event - Playback complete event
     */
    onAudioPlaybackComplete(event) {
        this.uiManager.showNotification('Audio playback completed', 'success');
    }

    /**
     * Handle turn end
     * @param {string} finalTranscript - Final transcript
     * @param {number} timestamp - Timestamp
     */
    handleTurnEnd(finalTranscript, timestamp) {
        console.log('🎤 Turn ended with transcript:', finalTranscript);

        // Clear turn timeout
        if (this.turnTimeout) {
            clearTimeout(this.turnTimeout);
            this.turnTimeout = null;
        }

        // Reset turn state
        this.isUserSpeaking = false;
        this.currentTurnTranscript = "";

        // Display final transcription
        this.uiManager.displayTranscription(finalTranscript, 'turn-final', null);

        // Update status
        this.uiManager.updateEchoStatus(`🎤 Turn completed: "${finalTranscript}"`, 'success');

        // Auto-process the completed turn if in conversation mode
        if (this.isConversationMode && finalTranscript.trim()) {
            this.processCompletedTurn(finalTranscript);
        }
    }

    /**
     * Reset turn timeout
     */
    resetTurnTimeout() {
        if (this.turnTimeout) {
            clearTimeout(this.turnTimeout);
        }

        this.turnTimeout = setTimeout(() => {
            if (this.isUserSpeaking && this.currentTurnTranscript.trim()) {
                console.log('⏰ Turn timeout reached, ending turn');
                this.handleTurnEnd(this.currentTurnTranscript, Date.now());
            }
        }, 2000);
    }

    /**
     * Process completed turn
     * @param {string} transcript - Turn transcript
     */
    processCompletedTurn(transcript) {
        console.log('🤖 Processing completed turn:', transcript);
        this.uiManager.updateEchoStatus('🤖 Processing turn...', 'info');
    }

    /**
     * Get or create session ID
     * @returns {string} Session ID
     */
    getOrCreateSessionId() {
        const urlParams = new URLSearchParams(window.location.search);
        let sessionId = urlParams.get('session_id');

        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            const newUrl = new URL(window.location);
            newUrl.searchParams.set('session_id', sessionId);
            window.history.replaceState({}, '', newUrl);
        }

        console.log('💬 Session ID:', sessionId);
        return sessionId;
    }

    /**
     * Update session display
     */
    updateSessionDisplay() {
        console.log('💬 Session display updated for:', this.sessionId);
    }

    /**
     * Check server connection
     */
    checkServerConnection() {
        fetch('/api/health')
            .then(response => {
                if (response.ok) {
                    console.log('✅ Server connection established');
                }
            })
            .catch(error => {
                console.error('❌ Server connection failed:', error);
            });
    }



    /**
     * Get base64 audio statistics
     * @returns {Object} Audio statistics
     */
    getBase64AudioStats() {
        if (this.base64AudioChunks.length === 0) {
            return {
                chunkCount: 0,
                totalLength: 0,
                isReceiving: false,
                streamId: null
            };
        }

        const totalLength = this.base64AudioChunks.reduce((total, chunk) => total + chunk.length, 0);
        return {
            chunkCount: this.base64AudioChunks.length,
            totalLength: totalLength,
            isReceiving: this.isReceivingAudio,
            streamId: this.currentAudioStreamId
        };
    }

    /**
     * Setup quick question button listeners
     */
    setupQuickQuestionListeners() {
        const quickQuestionBtns = document.querySelectorAll('.quick-question-btn');
        quickQuestionBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const command = btn.getAttribute('data-command');
                if (command) {
                    this.executeQuickQuestion(btn, command);
                }
            });
        });
    }

    /**
     * Execute a quick question command
     * @param {HTMLElement} button - The clicked button element
     * @param {string} command - The voice command to execute
     */
    async executeQuickQuestion(button, command) {
        console.log(`🎤 Executing quick question: "${command}"`);

        // Check if this is a news command and validate NEWS_API_KEY
        const isNewsCommand = command.toLowerCase().includes('news') ||
            command.toLowerCase().includes('latest') ||
            command.toLowerCase().includes('headlines');

        if (isNewsCommand) {
            const newsValidation = this.configManager.validateNewsRequirement();
            if (!newsValidation) {
                const reason = "News commands require the NewsAPI key. Please configure it to get the latest news.";
                this.configManager.openModalWithFocus(['NEWS_API_KEY'], reason);
                return;
            }
        }

        // Add executing visual state
        button.classList.add('executing');
        const originalText = button.querySelector('.quick-question-text').textContent;
        button.querySelector('.quick-question-text').textContent = 'Executing...';

        // Update UI status
        this.uiManager.updateEchoStatus(`🎤 Executing: ${command}`, 'info');

        try {
            // Call the voice commands API directly
            const response = await fetch('/api/voice-commands/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command: command })
            });

            const result = await response.json();

            if (result.success) {
                console.log(`✅ Quick question executed successfully:`, result);

                // Update UI with command result
                this.uiManager.updateEchoStatus(`✅ ${result.response}`, 'success');

                // Display as a conversation message
                this.displayQuickQuestionResult(command, result.response);

                // Show notification of successful execution
                this.uiManager.showNotification(`Command executed: ${result.command_type}`, 'success');

                // Generate TTS for the response
                await this.generateTTSForQuickQuestion(result.response);

            } else {
                console.log(`❌ Quick question failed:`, result);
                this.uiManager.updateEchoStatus(`❌ ${result.message || 'Command failed'}`, 'error');
                this.uiManager.showNotification(result.message || 'Command execution failed', 'error');
            }

        } catch (error) {
            console.error('❌ Quick question execution error:', error);
            this.uiManager.updateEchoStatus('❌ Failed to execute command', 'error');
            this.uiManager.showNotification('Failed to execute command. Please try again.', 'error');
        } finally {
            // Remove executing state
            button.classList.remove('executing');
            button.querySelector('.quick-question-text').textContent = originalText;
        }
    }

    /**
     * Display quick question result in conversation
     * @param {string} command - The executed command
     * @param {string} response - The response from the command
     */
    displayQuickQuestionResult(command, response) {
        // Show conversation display if hidden
        const conversationDisplay = document.getElementById('conversationDisplay');
        if (conversationDisplay) {
            conversationDisplay.style.display = 'block';

            // Create or get conversation content
            let conversationContent = conversationDisplay.querySelector('.conversation-content');
            if (!conversationContent) {
                conversationDisplay.innerHTML = `
                    <h4>💬 Voice Commands</h4>
                    <div class="conversation-content"></div>
                `;
                conversationContent = conversationDisplay.querySelector('.conversation-content');
            }

            // Add user message
            const userMessage = document.createElement('div');
            userMessage.className = 'message user-message';
            userMessage.innerHTML = `
                <div class="message-label">You (Quick Command)</div>
                <div class="message-bubble">${command}</div>
            `;

            // Add AI response
            const aiMessage = document.createElement('div');
            aiMessage.className = 'message ai-message';
            aiMessage.innerHTML = `
                <div class="message-label">AI Agent</div>
                <div class="message-bubble">${response}</div>
            `;

            // Append messages
            conversationContent.appendChild(userMessage);
            conversationContent.appendChild(aiMessage);

            // Scroll to bottom
            conversationContent.scrollTop = conversationContent.scrollHeight;
        }
    }

    /**
     * Generate TTS for quick question response
     * @param {string} text - Text to convert to speech
     */
    async generateTTSForQuickQuestion(text) {
        try {
            console.log('🎵 Generating TTS for quick question response...');

            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            });

            const result = await response.json();

            if (result.success && result.audio_url) {
                console.log('🎵 TTS generated successfully, playing audio...');

                // Play the audio
                const audioPlayer = document.getElementById('audioPlayer');
                const audioPlayback = document.getElementById('audioPlayback');

                if (audioPlayer && audioPlayback) {
                    audioPlayer.src = result.audio_url;
                    audioPlayback.style.display = 'block';
                    audioPlayer.play();
                }

                this.uiManager.updateEchoStatus('🎵 Playing audio response', 'success');
            } else {
                console.log('⚠️ TTS generation failed or no audio URL');
            }

        } catch (error) {
            console.error('❌ TTS generation error:', error);
        }
    }

    /**
     * Show more voice commands in a modal or expanded view
     */
    async showMoreCommands() {
        try {
            console.log('📋 Fetching available voice commands...');
            this.uiManager.updateEchoStatus('📋 Loading voice commands...', 'info');

            const response = await fetch('/api/voice-commands');
            const commandsData = await response.json();

            if (commandsData && commandsData.commands) {
                this.displayCommandsModal(commandsData);
            } else {
                this.uiManager.showNotification('Failed to load voice commands', 'error');
            }

        } catch (error) {
            console.error('❌ Error fetching voice commands:', error);
            this.uiManager.showNotification('Failed to load voice commands', 'error');
        }
    }

    /**
     * Display voice commands in a modal-like interface
     * @param {Object} commandsData - Commands data from API
     */
    displayCommandsModal(commandsData) {
        // Create modal overlay
        const modalOverlay = document.createElement('div');
        modalOverlay.id = 'commandsModal';
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            backdrop-filter: blur(10px);
        `;

        // Create modal content
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: linear-gradient(135deg, rgba(15, 15, 35, 0.95) 0%, rgba(26, 26, 46, 0.95) 100%);
            border-radius: 20px;
            padding: 32px;
            max-width: 90vw;
            max-height: 90vh;
            overflow-y: auto;
            border: 1px solid rgba(102, 126, 234, 0.3);
            box-shadow: 0 25px 70px rgba(0, 0, 0, 0.4);
        `;

        // Build content HTML
        let contentHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                <h2 style="color: #ffffff; margin: 0; font-size: 1.5rem;">🎤 Voice Commands Reference</h2>
                <button id="closeModal" style="background: rgba(255, 71, 87, 0.2); border: 1px solid rgba(255, 71, 87, 0.3); border-radius: 8px; padding: 8px 12px; color: #ff4757; cursor: pointer;">✕ Close</button>
            </div>
        `;

        // Add command categories
        Object.entries(commandsData.commands).forEach(([category, info]) => {
            contentHTML += `
                <div style="margin-bottom: 24px; background: rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1);">
                    <h3 style="color: #667eea; margin: 0 0 12px 0; font-size: 1.2rem; text-transform: capitalize;">${category}</h3>
                    <p style="color: #b0b0b0; margin: 0 0 16px 0; font-size: 0.9rem;">${info.description}</p>
                    <div style="margin-bottom: 12px;">
                        <strong style="color: #ffffff; font-size: 0.9rem;">Examples:</strong>
                        <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px;">
                            ${info.examples.map(example => `
                                <button class="modal-command-btn" data-command="${example}" style="
                                    background: rgba(102, 126, 234, 0.1);
                                    border: 1px solid rgba(102, 126, 234, 0.2);
                                    border-radius: 8px;
                                    padding: 6px 12px;
                                    color: #ffffff;
                                    font-size: 0.8rem;
                                    cursor: pointer;
                                    transition: all 0.3s ease;
                                ">
                                    ${example}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                    <div style="margin-top: 12px;">
                        <strong style="color: #ffffff; font-size: 0.9rem;">Patterns:</strong>
                        <div style="margin-top: 4px; color: #a0a0a0; font-size: 0.8rem;">
                            ${info.patterns.join(', ')}
                        </div>
                    </div>
                </div>
            `;
        });

        // Add notes
        if (commandsData.notes) {
            contentHTML += `
                <div style="margin-top: 24px; padding: 16px; background: rgba(102, 126, 234, 0.1); border-radius: 12px; border: 1px solid rgba(102, 126, 234, 0.2);">
                    <h4 style="color: #667eea; margin: 0 0 12px 0;">📝 Notes:</h4>
                    <ul style="color: #b0b0b0; font-size: 0.9rem; margin: 0; padding-left: 20px;">
                        ${commandsData.notes.map(note => `<li style="margin-bottom: 4px;">${note}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        modalContent.innerHTML = contentHTML;
        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        // Add event listeners
        const closeBtn = modalContent.querySelector('#closeModal');
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(modalOverlay);
        });

        // Close on overlay click
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                document.body.removeChild(modalOverlay);
            }
        });

        // Add click handlers for example commands
        const modalCommandBtns = modalContent.querySelectorAll('.modal-command-btn');
        modalCommandBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const command = btn.getAttribute('data-command');
                document.body.removeChild(modalOverlay);
                // Create a temporary button element for the executeQuickQuestion method
                const tempBtn = document.createElement('button');
                tempBtn.innerHTML = '<span class="quick-question-text">Loading...</span>';
                this.executeQuickQuestion(tempBtn, command);
            });

            // Add hover effect
            btn.addEventListener('mouseenter', () => {
                btn.style.background = 'rgba(102, 126, 234, 0.2)';
                btn.style.borderColor = 'rgba(102, 126, 234, 0.4)';
                btn.style.transform = 'translateY(-1px)';
            });

            btn.addEventListener('mouseleave', () => {
                btn.style.background = 'rgba(102, 126, 234, 0.1)';
                btn.style.borderColor = 'rgba(102, 126, 234, 0.2)';
                btn.style.transform = 'translateY(0)';
            });
        });

        console.log('📋 Voice commands modal displayed');
        this.uiManager.updateEchoStatus('📋 Voice commands reference displayed', 'success');
    }

    /**
     * Show application info
     */
    showInfo() {
        this.uiManager.showNotification('AI Voice Agent - Real-time voice interaction with seamless audio playback and quick voice commands', 'info');
    }

    /**
     * Scroll to AI Voice Agent section
     */
    scrollToAISection() {
        const aiSection = document.querySelector('.ai-voice-agent-section');
        if (aiSection) {
            aiSection.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    /**
     * Get application status
     * @returns {Object} Application status
     */
    getStatus() {
        return {
            sessionId: this.sessionId,
            recording: this.recordingManager.getStatus(),
            webSocket: this.webSocketManager.getStatus(),
            audio: this.audioPlayer.getStatus(),
            base64Audio: this.getBase64AudioStats(),
            configuration: this.configManager.getStatus()
        };
    }

    /**
     * Stop all operations
     */
    stop() {
        this.recordingManager.stopRecording();
        this.webSocketManager.disconnect();
        this.audioPlayer.stop();
        this.uiManager.clearNotifications();
        console.log('🛑 Voice Agent stopped');
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

    // Make it globally accessible for debugging in development
    if (typeof window !== 'undefined') {
        window.voiceAgent = voiceAgent;
    }

    console.log('🚀 AI Voice Agent initialized successfully');
    console.log('💡 Use Ctrl+Space to toggle voice chat');
    console.log('⚙️ Click the settings icon to configure API keys');
});
