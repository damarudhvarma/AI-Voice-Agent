// AI Voice Agent - Day 1 JavaScript
class VoiceAgent {
    constructor() {
        this.isListening = false;
        this.isConnected = false;
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

        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.ctrlKey) {
                e.preventDefault();
                this.toggleVoiceChat();
            }
        });
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
• Voice synthesis
• Multi-language support
• Custom voice training

Day 1: Basic setup with Flask backend and modern frontend
Day 2-30: Adding AI capabilities, voice recognition, and more!

Press Ctrl+Space to quickly start/stop voice chat.
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
