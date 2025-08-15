# AI Voice Agent

A modern web-based conversational agent that allows users to interact with an AI using both voice and text. The project features a sleek, animated UI and real-time audio playback, providing a seamless and engaging chat experience.

---

## Technologies Used

- **Frontend:** HTML5, CSS3 (modern, responsive, dark theme), JavaScript (ES6)
- **Backend:** Python (Flask)
- **Audio:** Web Audio API, MediaRecorder API
- **AI/Conversational Logic:** Integrates with an AI backend (customizable)

---

## Architecture

```
+-------------------+        HTTP/WebSocket         +-------------------+
|    Web Client     |  <------------------------>  |     Flask API     |
| (HTML/CSS/JS)     |                              |   (Python)        |
+-------------------+                              +-------------------+
				|                                                    |
				|<--- Audio/Text Input/Output, Chat UI --->|   AI/Voice Logic  |
```

- **Client:**
  - Single-page web app with a modern chat interface
  - Animated record button for voice input
  - Auto-playing audio responses
  - Responsive design for desktop and mobile
- **Server:**
  - Flask app handling API requests
  - Receives audio/text, processes with AI, returns responses

---

## Features

- 🎤 **Single Animated Record Button:** Start/stop voice recording with a visually engaging button.
- 💬 **Conversational Chat UI:** Modern, dark-themed chat bubbles for user and agent messages.
- 🔊 **Auto-Playing Audio:** Agent responses play automatically, no manual audio controls needed.
- 🕒 **Session Management:** Maintains chat history for each session.
- 📱 **Responsive Design:** Works beautifully on both desktop and mobile devices.

---

## Screenshots

![Chat UI Screenshot](client/screenshot1.png)
![Record Button Animation](client/screenshot2.gif)

> _Add your own screenshots in the `client/` folder as `screenshot1.png`, `screenshot2.gif`, etc._

---

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js (optional, for advanced frontend tooling)

### Installation

1. **Clone the repository:**

   ```powershell
   git clone https://github.com/damarudhvarma/AI-Voice-Agent.git
   cd AI-Voice-Agent
   ```

2. **Set up the backend:**

   ```powershell
   cd server
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**

   - Create a `.env` file in the `server/` directory with the following (example):
     ```env
     OPENAI_API_KEY=your_openai_api_key
     # Add any other required environment variables here
     ```

4. **Run the backend server:**

   ```powershell
   python app.py
   ```

5. **Open the frontend:**
   - Open `client/index.html` in your browser, or serve the `client/` folder using a simple HTTP server:
     ```powershell
     cd ..\client
     python -m http.server 8000
     # Then visit http://localhost:8000 in your browser
     ```

---

## API Server Details

- **Base URL:** `http://localhost:5000/`
- **Endpoints:**
  - `/api/message` (POST): Accepts text or audio, returns AI response (text + audio)
  - _See `server/app.py` for more details_
- **Environment Variables:**
  - `OPENAI_API_KEY` (required): Your OpenAI API key for AI responses
  - _Add any additional variables as needed for your backend_

---

## Customization

- **Change AI Model:** Update the backend logic in `server/app.py` to use your preferred AI model or service.
- **UI Tweaks:** Modify `client/style.css` and `client/index.html` for further UI customization.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Credits

- UI/UX inspired by modern chat and voice assistant apps.
- Built by [Your Name] and contributors.
