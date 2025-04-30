import openai
from flask import Flask, request
import os
import logging
import requests
import tempfile
import time
import pyttsx3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# === CONFIGURATION ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", None)
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Default voice
MODEL = "gpt-4"
LISTEN_PORT = 5000
SPEECH_RATE = 180
USE_ELEVENLABS = bool(ELEVENLABS_API_KEY)

# === INITIALIZE ===
client = openai.OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)
engine = pyttsx3.init()
engine.setProperty('rate', SPEECH_RATE)
logging.basicConfig(level=logging.INFO)

# === GPT SUMMARIZER ===
def summarize_with_gpt(json_data):
    prompt = (
        "You are a helpful assistant. "
        "Summarize this JSON for verbal understanding and extract the sentiment. "
        "Keep it short, clear, and conversational."
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": str(json_data)}
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"GPT error: {e}")
        return "Sorry, I couldn't process that request."

# === TTS SPEAKER ===
def speak_with_elevenlabs(text):
    logging.info("Using ElevenLabs voice synthesis...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                for chunk in response.iter_content(chunk_size=1024):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            os.system(f'start wmplayer "{tmp_path}"')  # Windows only
            time.sleep(5)
            os.remove(tmp_path)
        else:
            logging.error(f"ElevenLabs API error: {response.text}")
    except Exception as e:
        logging.error(f"ElevenLabs playback error: {e}")

def speak_with_pyttsx3(text):
    logging.info(f"Speaking with pyttsx3: {text}")
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        logging.error(f"TTS error: {e}")

def speak_text(text):
    if USE_ELEVENLABS:
        speak_with_elevenlabs(text)
    else:
        speak_with_pyttsx3(text)

# === WEBHOOK ENDPOINT ===
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    json_data = request.json
    logging.info(f"Webhook received: {json_data}")

    summary = summarize_with_gpt(json_data)
    logging.info(f"GPT Summary: {summary}")

    speak_text(summary)
    return '', 204

# === RUN SERVER ===
if __name__ == '__main__':
    logging.info(f"Starting server on port {LISTEN_PORT}...")
    app.run(host='0.0.0.0', port=LISTEN_PORT)

