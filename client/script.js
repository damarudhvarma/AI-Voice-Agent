// AI Voice Agent - Day 1 JavaScript
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

    async startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.updateEchoStatus('Your browser does not support audio recording', 'error');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false
                }
            });

            this.audioChunks = [];
            this.mediaRecorder = new MediaRecorder(stream);
            this.isListening = true;

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.processRecording();
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start();
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

            this.updateEchoStatus('Recording... Speak into your microphone', 'recording');

        } catch (error) {
            console.error('Error starting recording:', error);
            this.updateEchoStatus('Failed to access microphone. Please check permissions.', 'error');
        }
    }

    // Add missing methods
    checkServerConnection() {
        // Check if server is available
        fetch('/api/status')
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

    showInfo() {
         // Show information about the application
         alert('AI Voice Agent\n\nThis application allows you to have voice conversations with an AI assistant.\n\nPress the record button or Ctrl+Space to start recording your voice.');
     }

            console.log('🎙️ Recording started');

        } catch (error) {
            console.error('Error starting recording:', error);
            this.updateEchoStatus('Failed to access microphone. Please check permissions.', 'error');
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

            this.updateEchoStatus('Processing recording...', 'default');

            console.log('🛑 Recording stopped');
        }
    }

    async processRecording() {
        if (this.audioChunks.length === 0) {
            this.updateEchoStatus('No audio data recorded', 'error');
            return;
        }

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });

        // Calculate recording duration
        const duration = this.recordingStartTime ?
            ((Date.now() - this.recordingStartTime) / 1000).toFixed(1) : 0;

        this.updateEchoStatus(`Recording complete! Duration: ${duration}s - Processing with AI...`, 'loading');

        // Send to Agent Chat endpoint for conversation with history
        await this.processAgentChat(audioBlob);

        console.log('✅ Audio processed with LLM Query');
    }

    async transcribeAudioFile(audioBlob) {
        this.updateEchoStatus('Transcribing audio...', 'loading');
        try {
            const formData = new FormData();
            // Use a timestamp for filename to avoid collisions
            const filename = `echo_recording_${Date.now()}.wav`;
            formData.append('audio', audioBlob, filename);

            const response = await fetch('/api/transcribe/file', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                this.updateEchoStatus('Transcription failed: ' + (err.error || response.statusText), 'error');
                return;
            }

            const result = await response.json();
            if (result.success && result.transcript) {
                // Display the transcription in the UI
                this.displayTranscription(result.transcript, result.confidence, result.audio_duration);
                this.updateEchoStatus('Transcription complete!', 'success');
            } else {
                this.updateEchoStatus('Transcription failed: No transcript received', 'error');
            }
        } catch (error) {
            console.error('Transcription error:', error);
            this.updateEchoStatus('Transcription failed: ' + error.message, 'error');
        }
    }

    displayTranscription(transcript, confidence, duration) {
        // Create or update transcription display area
        const echoSection = document.querySelector('.echo-bot');
        let transcriptionDiv = document.getElementById('transcriptionDisplay');

        if (!transcriptionDiv) {
            transcriptionDiv = document.createElement('div');
            transcriptionDiv.id = 'transcriptionDisplay';
            transcriptionDiv.className = 'transcription-display';
            transcriptionDiv.innerHTML = `
                <h4>🎯 Transcription Results</h4>
                <div class="transcription-content">
                    <div class="transcript-text" id="transcriptText"></div>
                    <div class="transcript-metadata" id="transcriptMetadata"></div>
                </div>
            `;

            // Insert after audio playback
            const audioPlayback = document.getElementById('audioPlayback');
            audioPlayback.parentNode.insertBefore(transcriptionDiv, audioPlayback.nextSibling);
        }

        // Update the content
        const transcriptText = document.getElementById('transcriptText');
        const transcriptMetadata = document.getElementById('transcriptMetadata');

        transcriptText.textContent = transcript || 'No speech detected';

        let metadataHtml = '';
        if (duration) {
            metadataHtml += `<span class="metadata-item">Duration: ${duration.toFixed(1)}s</span>`;
        }
        if (confidence) {
            metadataHtml += `<span class="metadata-item">Confidence: ${(confidence * 100).toFixed(1)}%</span>`;
        }
        transcriptMetadata.innerHTML = metadataHtml;

        // Show the transcription display
        transcriptionDiv.style.display = 'block';

        // Scroll into view
        transcriptionDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        console.log('📝 Transcription displayed:', transcript);
    }

    async processEchoBot(audioBlob) {
        this.updateEchoStatus('🎤 Transcribing audio and generating AI voice...', 'loading');

        try {
            const formData = new FormData();
            const filename = `echo_recording_${Date.now()}.wav`;
            formData.append('audio', audioBlob, filename);

            const response = await fetch('/api/tts/echo', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                this.updateEchoStatus('Echo Bot failed: ' + (err.error || response.statusText), 'error');
                return;
            }

            const result = await response.json();

            if (result.success && result.audio_url) {
                // Display the transcription
                this.displayTranscription(result.transcription, null, null);

                // Play the AI-generated audio
                const audioPlayer = document.getElementById('audioPlayer');
                audioPlayer.src = result.audio_url;
                document.getElementById('audioPlayback').style.display = 'block';

                this.updateEchoStatus(`✅ Echo Bot complete! Playing AI voice...`, 'success');

                // Auto-play the AI-generated audio
                setTimeout(() => {
                    audioPlayer.play().catch(e => {
                        console.log('Auto-play prevented by browser policy');
                        this.updateEchoStatus('Echo Bot complete! Click play button to hear AI voice.', 'success');
                    });
                }, 500);

                console.log('🎵 AI voice generated and playing:', result.audio_url);
                console.log('📝 Transcription:', result.transcription);

            } else {
                this.updateEchoStatus('Echo Bot failed: No audio generated', 'error');
            }

        } catch (error) {
            console.error('Echo Bot error:', error);
            this.updateEchoStatus('Echo Bot failed: ' + error.message, 'error');
        }
    }

    async processLLMQuery(audioBlob) {
        this.updateEchoStatus('🎤 Transcribing audio and generating AI response...', 'loading');

        try {
            const formData = new FormData();
            const filename = `llm_query_${Date.now()}.wav`;
            formData.append('audio', audioBlob, filename);

            const response = await fetch('/api/llm/query', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                this.updateEchoStatus('AI Query failed: ' + (err.error || response.statusText), 'error');
                return;
            }

            const result = await response.json();

            if (result.success && result.audio_url) {
                // Display the transcription and LLM response
                this.displayLLMConversation(result.transcription, result.llm_response);

                // Play the AI-generated audio
                const audioPlayer = document.getElementById('audioPlayer');
                audioPlayer.src = result.audio_url;
                document.getElementById('audioPlayback').style.display = 'block';

                this.updateEchoStatus(`✅ AI conversation complete! Playing response...`, 'success');

                // Auto-play the AI-generated audio
                setTimeout(() => {
                    audioPlayer.play().catch(e => {
                        console.log('Auto-play prevented by browser policy');
                        this.updateEchoStatus('AI response ready! Click play button to hear the response.', 'success');
                    });
                }, 500);

                console.log('🎵 AI response audio generated and playing:', result.audio_url);
                console.log('📝 Your message:', result.transcription);
                console.log('🤖 AI response:', result.llm_response);

            } else {
                this.updateEchoStatus('AI Query failed: No audio generated', 'error');
            }

        } catch (error) {
            console.error('LLM Query error:', error);
            this.updateEchoStatus('AI Query failed: ' + error.message, 'error');
        }
    }

    displayLLMConversation(userMessage, aiResponse) {
        // Create or update conversation display area
        const echoSection = document.querySelector('.echo-bot');
        let conversationDiv = document.getElementById('conversationDisplay');

        if (!conversationDiv) {
            conversationDiv = document.createElement('div');
            conversationDiv.id = 'conversationDisplay';
            conversationDiv.className = 'conversation-display';
            conversationDiv.innerHTML = `
                <h4>💬 AI Conversation</h4>
                <div class="conversation-content" id="conversationContent"></div>
            `;

            // Insert after audio playback
            const audioPlayback = document.getElementById('audioPlayback');
            audioPlayback.parentNode.insertBefore(conversationDiv, audioPlayback.nextSibling);
        }

        // Update the content
        const conversationContent = document.getElementById('conversationContent');

        conversationContent.innerHTML = `
            <div class="message user-message">
                <div class="message-label">🎤 Your message:</div>
                <div class="message-text">${userMessage || 'No speech detected'}</div>
            </div>
            <div class="message ai-message">
                <div class="message-label">🤖 AI response:</div>
                <div class="message-text">${aiResponse || 'No response generated'}</div>
            </div>
        `;

        // Show the conversation display
        conversationDiv.style.display = 'block';

        // Scroll into view
        conversationDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        console.log('💬 Conversation displayed');
    }

    async processAgentChat(audioBlob) {
        this.updateEchoStatus('🎤 Starting conversation with AI agent...', 'loading');

        try {
            const formData = new FormData();
            const filename = `agent_chat_${Date.now()}.wav`;
            formData.append('audio', audioBlob, filename);

            const response = await fetch(`/api/agent/chat/${this.sessionId}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                this.updateEchoStatus('Agent chat failed: ' + (err.error || response.statusText), 'error');
                return;
            }

            const result = await response.json();

            if (result.success) {
                // Display the conversation
                this.displayAgentConversation(result.user_message, result.assistant_response, result.message_count);

                // Handle audio playback (either real audio or fallback)
                this.audioPlayer = document.getElementById('audioPlayer');
                const audioPlayback = document.getElementById('audioPlayback');

                if (result.audio_url) {
                    // Normal audio response
                    this.audioPlayer.src = result.audio_url;
                    audioPlayback.style.display = 'block';

                    this.updateEchoStatus(`✅ AI response ready! Playing...`, 'success');

                    // Set up audio end listener for automatic next recording
                    this.audioPlayer.onended = () => {
                        console.log('🎵 Audio playback finished, starting next recording...');
                        setTimeout(() => {
                            this.startNextRecording();
                        }, 1000);
                    };

                    // Auto-play the AI-generated audio
                    setTimeout(() => {
                        this.audioPlayer.play().catch(e => {
                            console.log('Auto-play prevented by browser policy');
                            this.updateEchoStatus('AI response ready! Click play button to hear response.', 'success');
                        });
                    }, 500);

                } else if (result.is_fallback && result.fallback_text) {
                    // Fallback text response (no audio available)
                    audioPlayback.style.display = 'none';

                    let statusMessage = `⚠️ ${result.fallback_text}`;
                    if (result.error_type === 'stt_error') {
                        statusMessage = '� ' + result.fallback_text;
                    } else if (result.error_type === 'tts_error') {
                        statusMessage = '🔊 ' + result.fallback_text;
                    } else if (result.error_type === 'llm_error') {
                        statusMessage = '🧠 ' + result.fallback_text;
                    }

                    this.updateEchoStatus(statusMessage, 'warning');

                    // Show fallback message to user
                    this.showFallbackNotification(result.fallback_text, result.error_type);

                    // Auto-start next recording after fallback
                    setTimeout(() => {
                        this.startNextRecording();
                    }, 3000); // Wait 3 seconds before next recording
                } else {
                    this.updateEchoStatus('❌ No audio or fallback response received', 'error');
                }

                console.log('📝 Your message:', result.user_message);
                console.log('🤖 AI response:', result.assistant_response);
                console.log('💬 Total messages in session:', result.message_count);
                if (result.is_fallback) {
                    console.log('⚠️ Fallback response due to:', result.error_type);
                }

            } else {
                this.updateEchoStatus('Agent chat failed: Invalid response format', 'error');
            }
        } catch (error) {
            console.error('Agent Chat error:', error);

            // Show user-friendly error message
            this.updateEchoStatus('❌ Connection trouble. Please check your internet and try again.', 'error');

            // Show fallback notification
            this.showFallbackNotification(
                "I'm having trouble connecting right now. Please check your internet connection and try again.",
                'general_error'
            );

            // Allow user to try again
            setTimeout(() => {
                this.updateEchoStatus('Ready to try again...', 'default');
            }, 5000);
        }
    }

    showFallbackNotification(message, errorType) {
        // Create or update fallback notification
        let notification = document.getElementById('fallbackNotification');

        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'fallbackNotification';
            notification.className = 'fallback-notification';

            const echoSection = document.querySelector('.echo-bot');
            echoSection.appendChild(notification);
        }

        // Set appropriate icon based on error type
        let icon = '⚠️';
        let className = 'warning';

        switch (errorType) {
            case 'stt_error':
                icon = '🎤';
                className = 'stt-error';
                break;
            case 'llm_error':
                icon = '🧠';
                className = 'llm-error';
                break;
            case 'tts_error':
                icon = '🔊';
                className = 'tts-error';
                break;
            case 'api_key_missing':
                icon = '🔑';
                className = 'config-error';
                break;
            case 'timeout_error':
                icon = '⏱️';
                className = 'timeout-error';
                break;
            default:
                icon = '⚠️';
                className = 'general-error';
        }

        notification.className = `fallback-notification ${className}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${icon}</span>
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
        `;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (notification && notification.parentElement) {
                notification.remove();
            }
        }, 5000);

        console.log(`📢 Fallback notification: ${message}`);
    }

    async startNextRecording() {
        // Check if we can start recording automatically
        const toggleRecordBtn = document.getElementById('toggleRecord');

        if (toggleRecordBtn && !toggleRecordBtn.disabled && this.mediaRecorder?.state !== 'recording') {
            this.updateEchoStatus('🎤 Ready for your next message...', 'default');

            // Auto-start recording after a short delay
            setTimeout(() => {
                this.startRecording();
            }, 500);
        }
    }

    displayAgentConversation(userMessage, aiResponse, messageCount) {
        // Create or update conversation display area
        const echoSection = document.querySelector('.echo-bot');
        let conversationDiv = document.getElementById('conversationDisplay');

        if (!conversationDiv) {
            conversationDiv = document.createElement('div');
            conversationDiv.id = 'conversationDisplay';
            conversationDiv.className = 'conversation-display';
            conversationDiv.innerHTML = `
                <h4>💬 AI Agent Chat (${messageCount} messages)</h4>
                <div class="conversation-content" id="conversationContent"></div>
            `;

            // Insert after audio playback
            const audioPlayback = document.getElementById('audioPlayback');
            audioPlayback.parentNode.insertBefore(conversationDiv, audioPlayback.nextSibling);

            // Initialize conversation history storage
            this.conversationHistory = [];
        } else {
            // Update message count
            conversationDiv.querySelector('h4').textContent = `💬 AI Agent Chat (${messageCount} messages)`;
        }

        // Add new messages to history
        this.conversationHistory.push(
            { role: 'user', content: userMessage },
            { role: 'assistant', content: aiResponse }
        );

        // Update the content with full conversation
        const conversationContent = document.getElementById('conversationContent');

        let conversationHTML = '';
        this.conversationHistory.forEach((msg, index) => {
            const isUser = msg.role === 'user';
            const messageClass = isUser ? 'user-message' : 'ai-message';
            const label = isUser ? '🎤 You' : '🤖 AI Agent';
            const content = msg.content || (isUser ? 'No speech detected' : 'No response generated');

            conversationHTML += `
                <div class="message ${messageClass}">
                    <div class="message-label">${label}</div>
                    <div class="message-bubble">${content}</div>
                </div>
            `;
        });

        conversationContent.innerHTML = conversationHTML;

        // Show the conversation display
        conversationDiv.style.display = 'block';

        // Scroll to bottom of conversation
        setTimeout(() => {
            conversationContent.scrollTop = conversationContent.scrollHeight;
        }, 100);

        console.log('💬 Agent conversation displayed with full history');
    }

    startTimer() {
        const timerElement = document.getElementById('recordingTimer');
        const timerText = document.getElementById('timerText');

        timerElement.style.display = 'block';

        this.timerInterval = setInterval(() => {
            if (this.recordingStartTime) {
                const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
                const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
                const seconds = (elapsed % 60).toString().padStart(2, '0');
                timerText.textContent = `${minutes}:${seconds}`;
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        document.getElementById('recordingTimer').style.display = 'none';
    }

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
            this.displayAgentConversation(data.user_message, data.ai_response, data.message_count);
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

    async checkServerConnection() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();

            if (data.status === 'healthy') {
                this.updateConnectionStatus(true);
                console.log('✅ Server connection established');
            }
        } catch (error) {
            this.updateConnectionStatus(false);
            console.log('❌ Server connection failed:', error);
        }
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

    showInfo() {
        const info = `
🎤 AI Voice Agent - Day 1 of 30 Days Challenge

Features planned for this project:
• Real-time voice recognition
• AI-powered responses
• Natural conversation flow
• Voice synthesis with Murf AI
• Multi-language support
• Custom voice training

Current Features:
• AI Voice Agent Chat - Send messages to your AI assistant
• Modern UI with responsive design
• Server health monitoring
• Real-time character counting

Day 1: Basic setup with Flask backend and modern frontend
Day 2-30: Adding AI capabilities, voice recognition, and more!

Keyboard Shortcuts:
• Ctrl+Space: Toggle voice chat
• Ctrl+Enter (in message area): Send message to AI agent

Try the AI agent section below to chat with your intelligent assistant!
        `;

        alert(info);
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
