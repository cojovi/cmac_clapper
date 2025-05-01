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
# Modified to handle raw text input better
def summarize_with_gpt(input_data):
    # Determine if input is structured (dict) or raw text (str)
    if isinstance(input_data, dict):
        content_to_process = str(input_data) # Convert dict to string if needed by prompt
        prompt = (
            "You are ShadowDesk, a dark, witty herald for the IT department. "
            "You have received structured data about an IT request. " # Prompt adjusted for structured data
            "Craft ONE short spoken announcement (under 35 words) addressed to 'Tech Master'. "
            "Mood: mysterious, slightly ominous; vary wording each time. "
            "Include—verbatim where possible—the submitter's Name, Department, and Location, "
            "and paraphrase the Issue Description from the provided data. "
            "Return ONLY that single sentence."
            "IMPORTANT: Do not use technical terms, variable names, or words like 'extracted' or 'regex' in your final output sentence."
        )
    elif isinstance(input_data, str):
        content_to_process = input_data # Use the raw string
        prompt = (
            "You are ShadowDesk, a dark, witty herald for the IT department. "
            "You have received the following block of text describing an IT request: " # Prompt adjusted for raw text
            "Craft ONE short spoken announcement (under 35 words) addressed to 'Tech Master'. "
            "Mood: mysterious, slightly ominous; vary wording each time. "
            "From the text block, extract and include the submitter's Name, Department, and Location if present. "
            "Also, paraphrase the core Issue Description found in the text. "
            "Return ONLY that single sentence."
            "IMPORTANT: Do not use technical terms, variable names, or words like 'extracted' or 'regex' in your final output sentence."
         )
    else:
        logging.error("Invalid data type passed to summarize_with_gpt")
        return "ShadowDesk is perplexed by the formless void of data."

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user",   "content": content_to_process} # Send either the stringified dict or the raw text
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"GPT error: {e}")
        return "ShadowDesk falters—unable to conjure the words."

# === TTS SPEAKER ===
# (No changes needed in TTS functions)
def speak_with_elevenlabs(text):
    if not ELEVENLABS_API_KEY:
        logging.error("ELEVENLABS_API_KEY not set.")
        return
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.7}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            for chunk in response.iter_content(chunk_size=4096):
                tmp.write(chunk)
            tmp_path = tmp.name
        # --- play the file (basic playback) ---
        try:
             # Try common players, add others if needed (e.g., 'aplay' on Linux, 'afplay' on macOS)
             os.system(f'ffplay -nodisp -autoexit "{tmp_path}"')
        except FileNotFoundError:
             logging.warning("ffplay not found. Cannot play audio.")
        # --- cleanup ---
        time.sleep(1) # Give player time to release file
        os.remove(tmp_path)
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
# Modified to handle text/plain and application/json
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    received_data = None
    content_type = request.content_type

    logging.info(f"Webhook received with Content-Type: {content_type}")

    if content_type == 'application/json':
        received_data = request.json
        logging.info(f"Received JSON data: {received_data}")
    elif content_type == 'text/plain':
        # Read raw data and decode as UTF-8 text
        received_data = request.data.decode('utf-8')
        logging.info(f"Received text data: {received_data}")
    else:
        logging.warning(f"Unsupported Content-Type: {content_type}. Attempting to read raw data.")
        # Fallback: try reading raw data anyway, might be text or binary
        try:
            received_data = request.data.decode('utf-8')
            logging.info(f"Received raw data (decoded as text): {received_data}")
        except UnicodeDecodeError:
             received_data = request.data
             logging.info(f"Received raw data (binary or unknown encoding)")
        except Exception as e:
             logging.error(f"Error reading request data: {e}")
             return 'Error processing request body', 400

    if received_data is None and content_type == 'application/json':
         logging.error("Content-Type is JSON, but request.json is None. Invalid JSON?")
         return 'Invalid JSON received', 400
    elif not received_data:
         logging.warning("Received empty request body.")
         # Decide if you want to process empty requests or return an error
         # return 'Empty request body', 400
         # Or perhaps generate a default message:
         summary = "ShadowDesk senses a void... an empty request arrived."
    else:
        # Pass either the JSON dict (converted to string later) or the raw text string
        summary = summarize_with_gpt(received_data)
        logging.info(f"GPT Summary: {summary}")

    speak_text(summary)
    return '', 204 # Return "204 No Content" on success

# === RUN SERVER ===
if __name__ == '__main__':
    logging.info(f"Starting server on port {LISTEN_PORT}...")
    # Use host='0.0.0.0' to make it accessible on your network
    app.run(host='0.0.0.0', port=LISTEN_PORT)