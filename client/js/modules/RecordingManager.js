/**
 * Recording Manager Module - Handles audio recording functionality
 * Manages MediaRecorder, audio stream, and recording state
 */
class RecordingManager {
    constructor(webSocketManager) {
        this.webSocketManager = webSocketManager;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.isRecording = false;
        this.recordingStartTime = null;
        this.timerInterval = null;
        this.chunkInterval = 100; // Send audio chunks every 100ms
        this.audioChunks = [];

        this.init();
    }

    init() {
        console.log('🎤 RecordingManager initialized');
    }

    /**
     * Start audio recording
     * @returns {Promise<boolean>} Success status
     */
    async startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error('❌ Browser does not support audio recording');
            return false;
        }

        try {
            // Check microphone permissions
            const permission = await navigator.permissions.query({ name: 'microphone' });
            if (permission.state === 'denied') {
                console.error('❌ Microphone access denied');
                return false;
            }

            // Connect to WebSockets
            try {
                await Promise.all([
                    this.webSocketManager.connectMainWebSocket(),
                    this.webSocketManager.connectTurnDetectionWebSocket()
                ]);
            } catch (error) {
                console.error('❌ WebSocket connection failed:', error);
                return false;
            }

            // Get audio stream
            this.audioStream = await this.getAudioStream();
            if (!this.audioStream) return false;

            // Configure MediaRecorder
            const options = this.getMediaRecorderOptions();
            console.log('🎤 Using audio format:', options.mimeType || 'default');

            this.mediaRecorder = new MediaRecorder(this.audioStream, options);
            this.setupMediaRecorderEvents();

            // Start recording
            this.mediaRecorder.start(this.chunkInterval);
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            this.startTimer();

            // Send start signal
            this.webSocketManager.sendStartSignal({
                timestamp: Date.now(),
                audioFormat: options.mimeType || 'default'
            });

            console.log('🎤 Recording started successfully');
            return true;

        } catch (error) {
            console.error('❌ Error starting recording:', error);
            return false;
        }
    }

    /**
     * Stop audio recording
     */
    stopRecording() {
        console.log('🛑 Stopping recording...');

        if (this.mediaRecorder) {
            try {
                if (this.mediaRecorder.state === 'recording') {
                    this.mediaRecorder.stop();
                }
            } catch (error) {
                console.error('❌ Error stopping MediaRecorder:', error);
            }
        }

        // Stop audio stream
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => {
                track.stop();
                console.log('🛑 Stopped track:', track.kind);
            });
            this.audioStream = null;
        }

        // Stop timer
        this.stopTimer();

        // Reset state
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];

        // Send stop signal
        this.webSocketManager.sendStopSignal({
            timestamp: Date.now()
        });

        console.log('🛑 Recording stopped');
    }

    /**
     * Get audio stream with optimal settings
     * @returns {Promise<MediaStream|null>}
     */
    async getAudioStream() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    sampleRate: 16000,
                    channelCount: 1
                }
            });

            return stream;

        } catch (error) {
            console.error('❌ Microphone access error:', error);

            if (error.name === 'NotAllowedError') {
                throw new Error('Microphone access denied. Please allow microphone access and try again.');
            } else if (error.name === 'NotFoundError') {
                throw new Error('No microphone found. Please connect a microphone and try again.');
            } else if (error.name === 'NotReadableError') {
                throw new Error('Microphone is already in use by another application.');
            } else {
                throw new Error(`Microphone error: ${error.message}`);
            }
        }
    }

    /**
     * Get MediaRecorder options with fallbacks
     * @returns {Object} MediaRecorder options
     */
    getMediaRecorderOptions() {
        const options = {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 16000
        };

        // Fallback to other formats if WebM is not supported
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'audio/mp4';
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'audio/wav';
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                    delete options.mimeType;
                }
            }
        }

        return options;
    }

    /**
     * Setup MediaRecorder event handlers
     */
    setupMediaRecorderEvents() {
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.handleAudioChunk(event.data);
            }
        };

        this.mediaRecorder.onstop = () => {
            console.log('🛑 MediaRecorder stopped');
        };

        this.mediaRecorder.onerror = (error) => {
            console.error('❌ MediaRecorder error:', error);
        };
    }

    /**
     * Handle audio chunk from MediaRecorder
     * @param {Blob} audioBlob - Audio chunk blob
     */
    handleAudioChunk(audioBlob) {
        try {
            const reader = new FileReader();
            reader.onload = () => {
                const base64Data = reader.result.split(',')[1]; // Remove data URL prefix
                this.webSocketManager.sendAudioChunk(base64Data);
            };
            reader.readAsDataURL(audioBlob);
        } catch (error) {
            console.error('❌ Error processing audio chunk:', error);
        }
    }

    /**
     * Start recording timer
     */
    startTimer() {
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

    /**
     * Stop recording timer
     */
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }

        const timerDisplay = document.getElementById('recordingTimer');
        if (timerDisplay) {
            timerDisplay.style.display = 'none';
        }
    }

    /**
     * Get recording status
     * @returns {Object} Recording status
     */
    getStatus() {
        return {
            isRecording: this.isRecording,
            recordingTime: this.recordingStartTime ? Date.now() - this.recordingStartTime : 0,
            mediaRecorderState: this.mediaRecorder ? this.mediaRecorder.state : 'inactive',
            hasAudioStream: !!this.audioStream
        };
    }

    /**
     * Check if recording is supported
     * @returns {boolean} Support status
     */
    isSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RecordingManager;
} else {
    window.RecordingManager = RecordingManager;
}
