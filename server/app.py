from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os

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

if __name__ == '__main__':
    print("🎤 AI Voice Agent Server Starting...")
    print("🌐 Server running at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
