// AI Voice Agent - Day 1 JavaScript
class VoiceAgent {
    constructor() {
        this.isListening = false;
        this.isConnected = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingStartTime = null;
        this.timerInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkServerConnection();
        this.animateOnLoad();
    }

    setupEventListeners() {
        const startVoiceBtn = document.getElementById('startVoice');
        const learnMoreBtn = document.getElementById('learnMore');
        const voiceIndicator = document.getElementById('voiceIndicator');

        startVoiceBtn.addEventListener('click', () => this.toggleVoiceChat());
        learnMoreBtn.addEventListener('click', () => this.showInfo());
        voiceIndicator.addEventListener('click', () => this.toggleVoiceChat());

        // TTS Test functionality
        this.setupAIAgentEventListeners();

        // Echo Bot functionality
        this.setupEchoBotEventListeners();

        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.ctrlKey) {
                e.preventDefault();
                this.toggleVoiceChat();
            }
        });
    }

    setupAIAgentEventListeners() {
        const ttsInput = document.getElementById('ttsInput');
        const generateBtn = document.getElementById('generateTts');
        const clearBtn = document.getElementById('clearText');
        const charCount = document.getElementById('charCount');

        // Character counter
        ttsInput.addEventListener('input', () => {
            const count = ttsInput.value.length;
            charCount.textContent = count;

            if (count > 450) {
                charCount.style.color = '#ff4757';
            } else if (count > 350) {
                charCount.style.color = '#ffa726';
            } else {
                charCount.style.color = '#888';
            }
        });

        // Generate AI Response
        generateBtn.addEventListener('click', () => this.handleAIAgentMessage());

        // Clear text
        clearBtn.addEventListener('click', () => {
            ttsInput.value = '';
            charCount.textContent = '0';
            charCount.style.color = '#888';
            this.updateTtsStatus('Ready to chat with AI agent', 'default');
        });

        // Enter key to send message (Ctrl+Enter)
        ttsInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                this.handleAIAgentMessage();
            }
        });
    }

    async handleAIAgentMessage() {
        const ttsInput = document.getElementById('ttsInput');
        const generateBtn = document.getElementById('generateTts');
        const text = ttsInput.value.trim();

        if (!text) {
            this.updateTtsStatus('Please enter a message for the AI agent', 'error');
            return;
        }

        if (text.length > 500) {
            this.updateTtsStatus('Message is too long. Maximum 500 characters allowed.', 'error');
            return;
        }

        // Disable button and show loading
        generateBtn.disabled = true;
        this.updateTtsStatus('AI agent is processing your message...', 'loading', true);

        try {
            // For now, just simulate the AI response
            console.log('🤖 AI Agent processing message:', text);

            // Simulate AI processing delay
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Simulate success
            this.updateTtsStatus(`AI agent responded successfully! (${text.length} characters processed)`, 'success');

            // Show notification
            this.showNotification('AI agent response ready! (Simulated)', 'success');

        } catch (error) {
            console.error('AI Agent Error:', error);
            this.updateTtsStatus('AI agent failed to respond. Please try again.', 'error');
            this.showNotification('AI agent response failed', 'error');
        } finally {
            // Re-enable button and hide loading
            generateBtn.disabled = false;
            this.updateTtsStatus('Ready to chat with AI agent', 'default', false);
        }
    }

    setupEchoBotEventListeners() {
        const startRecordBtn = document.getElementById('startRecord');
        const stopRecordBtn = document.getElementById('stopRecord');

        startRecordBtn.addEventListener('click', () => this.startRecording());
        stopRecordBtn.addEventListener('click', () => this.stopRecording());

        // Check for MediaRecorder support
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.updateEchoStatus('Your browser does not support audio recording', 'error');
            startRecordBtn.disabled = true;
        }
    }

    async startRecording() {
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
            document.getElementById('startRecord').disabled = true;
            document.getElementById('startRecord').classList.add('recording');
            document.getElementById('stopRecord').disabled = false;
            document.getElementById('audioPlayback').style.display = 'none';

            this.updateEchoStatus('Recording... Speak into your microphone', 'recording');

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
            document.getElementById('startRecord').disabled = false;
            document.getElementById('startRecord').classList.remove('recording');
            document.getElementById('stopRecord').disabled = true;

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

        // Send to LLM Query endpoint for transcription + LLM + Murf TTS
        await this.processLLMQuery(audioBlob);

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

    updateEchoStatus(message, type = 'default') {
        const statusMessage = document.getElementById('echoStatusMessage');
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;
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
