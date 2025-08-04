from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import requests
import json

app = Flask(__name__, template_folder='../client', static_folder='../client', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files like CSS, JS, images"""
    if filename.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
        return send_from_directory('../client', filename)
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    return {'status': 'healthy', 'message': 'AI Voice Agent Backend is running!'}

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
  
    try:
        # Get the request data
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text field in request'}), 400
        
        text = data['text']
        
        if not text.strip():
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        # Murf API configuration
        murf_api_url = "https://api.murf.ai/v1/speech/generate"
        
        # You'll need to set these environment variables or replace with actual values
        api_key = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
        
        if api_key == 'your_murf_api_key_here':
            return jsonify({'error': 'Murf API key not configured. Please set MURF_API_KEY environment variable.'}), 500
        
        # Prepare the payload for Murf API
        murf_payload = {
            "voiceId": "en-US-ken",  # Default voice, can be made configurable
            "style": "Conversational",
            "text": text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False,
            "variation": 1,
            "audioDuration": 0
        }
        
        # Headers for Murf API
        headers = {
            'Content-Type': 'application/json',
            'api-key': api_key
        }
        
        # Make the request to Murf API
        response = requests.post(
            murf_api_url,
            headers=headers,
            json=murf_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            murf_response = response.json()
    
            audio_url = murf_response.get('audioFile', murf_response.get('url', ''))
            
            if audio_url:
                return jsonify({
                    'success': True,
                    'audio_url': audio_url,
                    'text': text
                })
            else:
                return jsonify({'error': 'No audio URL received from Murf API'}), 500
        else:
            error_msg = f"Murf API error: {response.status_code}"
            try:
                error_detail = response.json().get('message', 'Unknown error')
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            
            return jsonify({'error': error_msg}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to Murf API timed out'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("🎤 AI Voice Agent Server Starting...")
    print("🌐 Server running at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
