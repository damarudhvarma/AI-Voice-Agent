/**
 * AudioPlayer Module - Handles seamless audio playback from base64 chunks
 * Supports real-time streaming audio playback with minimal latency
 */
class AudioPlayer {
    constructor() {
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.currentSource = null;
        this.gainNode = null;
        this.volume = 0.7;
        this.chunkBuffer = [];
        this.bufferSize = 4096;
        this.sampleRate = 22050; // Default sample rate for Murf audio

        // Fallback audio element for MP3 playback
        this.fallbackAudio = null;
        this.useFallback = false;

        this.init();
    }

    init() {
        try {
            // Initialize Web Audio API
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.gainNode = this.audioContext.createGain();
            this.gainNode.gain.value = this.volume;
            this.gainNode.connect(this.audioContext.destination);

            console.log('🎵 AudioPlayer initialized successfully');
            console.log('🎵 Audio Context state:', this.audioContext.state);

            // Check if audio context is suspended (requires user interaction)
            if (this.audioContext.state === 'suspended') {
                console.log('⚠️ Audio Context is suspended - user interaction required to resume');
            }
        } catch (error) {
            console.error('❌ Failed to initialize AudioPlayer with Web Audio API:', error);
            this.initFallback();
        }
    }

    /**
     * Initialize fallback audio element
     */
    initFallback() {
        try {
            this.fallbackAudio = new Audio();
            this.fallbackAudio.volume = this.volume;
            this.useFallback = true;
            console.log('🎵 AudioPlayer initialized with fallback audio element');
        } catch (error) {
            console.error('❌ Failed to initialize fallback audio:', error);
        }
    }

    /**
     * Start playing audio from base64 chunks
     * @param {string} base64Chunk - Base64 encoded audio chunk
     * @param {boolean} isComplete - Whether this is the final chunk
     */
    async playChunk(base64Chunk, isComplete = false) {
        console.log('🎵 AudioPlayer.playChunk called with:', {
            hasAudioContext: !!this.audioContext,
            hasChunk: !!base64Chunk,
            chunkLength: base64Chunk ? base64Chunk.length : 0,
            isComplete,
            useFallback: this.useFallback
        });

        if (!base64Chunk || base64Chunk.trim() === '') {
            console.log('🎵 AudioPlayer.playChunk: Missing or empty base64Chunk, returning');
            return;
        }

        // Validate base64 format
        try {
            // Test if it's valid base64
            const testDecode = atob(base64Chunk.substring(0, Math.min(100, base64Chunk.length)));
            console.log('🎵 Base64 validation passed, first 20 bytes:', testDecode.substring(0, 20));
        } catch (error) {
            console.error('🎵 AudioPlayer.playChunk: Invalid base64 data:', error);
            console.log('🎵 First 100 chars of base64:', base64Chunk.substring(0, 100));
            return;
        }

        // Check if we should use fallback
        if (!this.audioContext && !this.useFallback) {
            console.log('🎵 AudioPlayer.playChunk: No audio context, initializing fallback');
            this.initFallback();
        }

        try {
            // Resume audio context if suspended (browser requirement)
            if (this.audioContext.state === 'suspended') {
                console.log('🎵 AudioPlayer.playChunk: Resuming suspended audio context');
                await this.audioContext.resume();
            }

            if (this.useFallback) {
                // Use fallback mode
                console.log('🎵 AudioPlayer.playChunk: Using fallback mode');
                this.audioQueue.push({
                    buffer: null,
                    base64Data: base64Chunk,
                    isComplete: isComplete
                });

                // Start playing if not already playing
                if (!this.isPlaying) {
                    console.log('🎵 AudioPlayer.playChunk: Starting fallback playback');
                    this.playNextChunk();
                } else {
                    console.log('🎵 AudioPlayer.playChunk: Added to fallback queue');
                }
                return;
            }

            console.log('🎵 AudioPlayer.playChunk: Decoding base64 to audio buffer');
            // Decode base64 to audio buffer
            const audioBuffer = await this.decodeBase64ToAudioBuffer(base64Chunk);
            if (!audioBuffer) {
                console.log('🎵 AudioPlayer.playChunk: Failed to decode audio buffer, trying fallback');
                // Try fallback if Web Audio API fails
                this.initFallback();
                if (this.useFallback) {
                    // Add to queue with base64 data only
                    this.audioQueue.push({
                        buffer: null,
                        base64Data: base64Chunk,
                        isComplete: isComplete
                    });

                    // Start playing if not already playing
                    if (!this.isPlaying) {
                        console.log('🎵 AudioPlayer.playChunk: Starting fallback playback');
                        this.playNextChunk();
                    } else {
                        console.log('🎵 AudioPlayer.playChunk: Added to fallback queue');
                    }
                    return;
                } else {
                    console.log('🎵 AudioPlayer.playChunk: No fallback available');
                    return;
                }
            }

            console.log('🎵 AudioPlayer.playChunk: Adding to queue, buffer duration:', audioBuffer.duration);
            // Add to queue for seamless playback
            this.audioQueue.push({
                buffer: audioBuffer,
                base64Data: base64Chunk, // Store base64 data for fallback
                isComplete: isComplete
            });

            // Start playing if not already playing
            if (!this.isPlaying) {
                console.log('🎵 AudioPlayer.playChunk: Starting playback');
                this.playNextChunk();
            } else {
                console.log('🎵 AudioPlayer.playChunk: Already playing, added to queue');
            }

        } catch (error) {
            console.error('❌ Error playing audio chunk:', error);
        }
    }

    /**
     * Decode base64 string to AudioBuffer
     * @param {string} base64Data - Base64 encoded audio data
     * @returns {Promise<AudioBuffer|null>}
     */
    async decodeBase64ToAudioBuffer(base64Data) {
        try {
            console.log('🎵 decodeBase64ToAudioBuffer: Starting decode, data length:', base64Data.length);

            // Convert base64 to array buffer
            const binaryString = atob(base64Data);
            console.log('🎵 decodeBase64ToAudioBuffer: Binary string length:', binaryString.length);

            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            console.log('🎵 decodeBase64ToAudioBuffer: Bytes array length:', bytes.length);

            // Check if this looks like MP3 data (MP3 files start with specific bytes)
            const isMP3 = bytes.length >= 3 &&
                ((bytes[0] === 0xFF && (bytes[1] & 0xE0) === 0xE0) || // MP3 sync word
                    (bytes[0] === 0x49 && bytes[1] === 0x44 && bytes[2] === 0x33)); // ID3 tag

            console.log('🎵 decodeBase64ToAudioBuffer: Audio format detection - MP3:', isMP3);
            console.log('🎵 decodeBase64ToAudioBuffer: First few bytes:', bytes.slice(0, 10));

            // Decode audio data
            console.log('🎵 decodeBase64ToAudioBuffer: Calling decodeAudioData');
            const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
            console.log('🎵 decodeBase64ToAudioBuffer: Successfully decoded, duration:', audioBuffer.duration);
            return audioBuffer;

        } catch (error) {
            console.error('❌ Error decoding base64 audio:', error);

            // Try alternative approach for MP3
            if (error.name === 'EncodingError' || error.message.includes('decode')) {
                console.log('🎵 decodeBase64ToAudioBuffer: Trying alternative MP3 decoding approach...');
                return await this.decodeMP3Alternative(base64Data);
            }

            return null;
        }
    }

    /**
     * Alternative MP3 decoding method
     * @param {string} base64Data - Base64 encoded MP3 data
     * @returns {Promise<AudioBuffer|null>}
     */
    async decodeMP3Alternative(base64Data) {
        try {
            console.log('🎵 decodeMP3Alternative: Trying alternative MP3 decode...');

            // Convert base64 to blob
            const binaryString = atob(base64Data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const blob = new Blob([bytes], { type: 'audio/mpeg' });
            const arrayBuffer = await blob.arrayBuffer();

            console.log('🎵 decodeMP3Alternative: Blob created, size:', blob.size);

            // Try decoding with explicit MP3 type
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            console.log('🎵 decodeMP3Alternative: Successfully decoded MP3, duration:', audioBuffer.duration);
            return audioBuffer;

        } catch (error) {
            console.error('❌ Alternative MP3 decoding failed:', error);
            return null;
        }
    }

    /**
     * Play the next chunk in the queue
     */
    async playNextChunk() {
        if (this.audioQueue.length === 0 || this.isPlaying) return;

        this.isPlaying = true;
        const chunk = this.audioQueue.shift();

        try {
            if (this.useFallback) {
                // Use fallback audio element
                await this.playFallbackChunk(chunk);
            } else {
                // Use Web Audio API
                this.currentSource = this.audioContext.createBufferSource();
                this.currentSource.buffer = chunk.buffer;
                this.currentSource.connect(this.gainNode);

                // Handle playback end
                this.currentSource.onended = () => {
                    this.isPlaying = false;

                    // Play next chunk if available
                    if (this.audioQueue.length > 0) {
                        this.playNextChunk();
                    } else if (chunk.isComplete) {
                        this.onPlaybackComplete();
                    }
                };

                // Start playback
                this.currentSource.start(0);
                console.log('🎵 Playing audio chunk with Web Audio API');
            }

        } catch (error) {
            console.error('❌ Error playing audio chunk:', error);
            this.isPlaying = false;
        }
    }

    /**
     * Play chunk using fallback audio element
     * @param {Object} chunk - Audio chunk data
     */
    async playFallbackChunk(chunk) {
        try {
            // Convert base64 to blob URL
            const binaryString = atob(chunk.base64Data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            console.log('🎵 Fallback: Creating blob with', bytes.length, 'bytes');

            // Try different MIME types for better compatibility
            let blob;
            const mimeTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg'];

            for (const mimeType of mimeTypes) {
                try {
                    blob = new Blob([bytes], { type: mimeType });
                    const url = URL.createObjectURL(blob);

                    this.fallbackAudio.src = url;
                    this.fallbackAudio.volume = this.volume;

                    // Handle playback end
                    this.fallbackAudio.onended = () => {
                        URL.revokeObjectURL(url); // Clean up
                        this.isPlaying = false;

                        // Play next chunk if available
                        if (this.audioQueue.length > 0) {
                            this.playNextChunk();
                        } else if (chunk.isComplete) {
                            this.onPlaybackComplete();
                        }
                    };

                    // Handle errors
                    this.fallbackAudio.onerror = (e) => {
                        console.error(`❌ Fallback audio error with ${mimeType}:`, e);
                        URL.revokeObjectURL(url);
                        this.isPlaying = false;
                    };

                    await this.fallbackAudio.play();
                    console.log(`🎵 Playing audio chunk with fallback audio element (${mimeType})`);
                    return; // Success, exit the loop

                } catch (playError) {
                    console.warn(`⚠️ Failed to play with ${mimeType}:`, playError);
                    continue; // Try next MIME type
                }
            }

            throw new Error('All MIME types failed');

        } catch (error) {
            console.error('❌ Error playing fallback audio chunk:', error);
            this.isPlaying = false;

            // Try to play next chunk if available
            if (this.audioQueue.length > 0) {
                setTimeout(() => this.playNextChunk(), 100);
            }
        }
    }

    /**
     * Handle playback completion
     */
    onPlaybackComplete() {
        console.log('🎵 Audio playback completed');
        this.isPlaying = false;
        this.currentSource = null;

        // Dispatch custom event
        const event = new CustomEvent('audioPlaybackComplete', {
            detail: { timestamp: Date.now() }
        });
        document.dispatchEvent(event);
    }

    /**
     * Set volume level (0.0 to 1.0)
     * @param {number} volume - Volume level
     */
    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        if (this.gainNode) {
            this.gainNode.gain.value = this.volume;
        }
    }

    /**
     * Stop current playback and clear queue
     */
    stop() {
        if (this.currentSource) {
            this.currentSource.stop();
            this.currentSource = null;
        }

        this.audioQueue = [];
        this.isPlaying = false;
        console.log('🛑 Audio playback stopped');
    }

    /**
     * Pause current playback
     */
    pause() {
        if (this.audioContext && this.audioContext.state === 'running') {
            this.audioContext.suspend();
        }
    }

    /**
     * Resume paused playback
     */
    resume() {
        if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
    }

    /**
     * Get current playback status
     * @returns {Object} Playback status
     */
    getStatus() {
        return {
            isPlaying: this.isPlaying,
            queueLength: this.audioQueue.length,
            volume: this.volume,
            contextState: this.audioContext ? this.audioContext.state : 'uninitialized',
            useFallback: this.useFallback,
            hasFallbackAudio: !!this.fallbackAudio
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioPlayer;
} else {
    window.AudioPlayer = AudioPlayer;
}
