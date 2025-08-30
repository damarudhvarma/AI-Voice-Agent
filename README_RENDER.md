# 🎤 AI Voice Agent - Render Deployment

A real-time AI voice agent with speech-to-text, language model processing, and text-to-speech capabilities.

## 🚀 Quick Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## ⚡ One-Click Setup

1. Click the "Deploy to Render" button above
2. Connect your GitHub account
3. Set your API keys in environment variables:
   - `ASSEMBLYAI_API_KEY` - [Get here](https://www.assemblyai.com/)
   - `GEMINI_API_KEY` - [Get here](https://makersuite.google.com/app/apikey)
   - `MURF_API_KEY` - [Get here](https://murf.ai/)
4. Click "Create Web Service"

## 🔑 Required API Keys

| Service       | Purpose           | Free Tier          | Get Key                                                 |
| ------------- | ----------------- | ------------------ | ------------------------------------------------------- |
| AssemblyAI    | Speech-to-Text    | 3 hours/month      | [Sign up](https://www.assemblyai.com/)                  |
| Google Gemini | AI Language Model | 15 requests/minute | [Get API Key](https://makersuite.google.com/app/apikey) |
| Murf          | Text-to-Speech    | 10 minutes/month   | [Sign up](https://murf.ai/)                             |

## 🎯 Features

- ✅ Real-time voice recording
- ✅ Speech-to-text transcription
- ✅ AI-powered responses
- ✅ Text-to-speech playback
- ✅ WebSocket support for streaming
- ✅ Voice commands (weather, calculations, etc.)
- ✅ Chat history management

## 🔧 Manual Deployment

### Render Configuration:

- **Build Command**: `pip install -r server/requirements.txt`
- **Start Command**: `python run.py`
- **Environment**: Python 3

#### Alternative Start Commands (if render.yaml doesn't work):

**If Render ignores render.yaml, manually set in dashboard:**

- **Universal launcher**: `python run.py`
- **Direct with path fix**: `cd server && python app_refactored.py`
- **Gunicorn production**: `cd server && gunicorn -w 1 -b 0.0.0.0:$PORT app_refactored:app`
- **Alternative startup**: `python start_app.py`

### 🔧 Manual Override Instructions:

If Render is not using your render.yaml file:

1. **Go to your Render service dashboard**
2. **Settings → Environment**
3. **Scroll to "Build & Deploy"**
4. **Set Start Command manually**: `python run.py`
5. **Set Build Command**: `pip install -r server/requirements.txt`
6. **Add Environment Variable**: `PYTHONPATH=/opt/render/project/src/server`

## 📱 Usage

1. Open your deployed app URL
2. Allow microphone permissions
3. Click and hold to record your voice
4. Release to send and get AI response
5. Listen to the generated audio response

## 🔧 Troubleshooting Build Issues

If you encounter build errors related to Rust/Cargo or pydantic compilation:

1. **Use the stable requirements**: Replace `server/requirements.txt` content with `requirements-stable.txt`
2. **Update Python version**: Use Python 3.11 in your Render settings
3. **Clear build cache**: In Render dashboard, go to Settings > Clear build cache

### Common Build Error Fix

If you see Rust compilation errors, use these stable package versions in `server/requirements.txt`:

```
Flask==2.3.3
pydantic==1.10.12
google-generativeai==0.7.2
gunicorn==20.1.0
```

## 🆘 Need Help?

- Visit `/api/health` on your deployed app to check API configuration
- Review Render logs in your dashboard for troubleshooting
- Check that all required API keys are set in environment variables
- For build issues, try the stable requirements above

---

**Tech Stack**: Python, Flask, AssemblyAI, Google Gemini, Murf, WebSockets
