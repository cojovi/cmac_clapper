import openai
from flask import Flask, request, jsonify # Added jsonify for returning errors
import os
import logging
import requests
import tempfile
import time
import pyttsx3
from dotenv import load_dotenv
import traceback # Import traceback module

# Load environment variables from .env file
load_dotenv()

# === CONFIGURATION ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Removed default key for clarity
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4") # Allow overriding model via env
LISTEN_PORT = int(os.getenv("LISTEN_PORT", 5000)) # Allow overriding port via env
SPEECH_RATE = int(os.getenv("SPEECH_RATE", 180)) # Allow overriding rate via env
USE_ELEVENLABS = bool(ELEVENLABS_API_KEY) # True if API key is present

# === INITIALIZE ===
# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logging.info("--- Initializing Application ---")

# Validate essential configuration
if not OPENAI_API_KEY:
    logging.critical("FATAL: OPENAI_API_KEY environment variable not set.")
    # Consider exiting here if OpenAI is absolutely required
    # exit(1)
else:
    logging.info(f"OpenAI Client configured with model: {MODEL}")
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# Initialize TTS Engines (only if needed)
engine = None
if not USE_ELEVENLABS:
    try:
        engine = pyttsx3.init()
        if engine: # Check if init succeeded
             engine.setProperty('rate', SPEECH_RATE)
             logging.info(f"pyttsx3 engine initialized with rate {SPEECH_RATE}.")
        else:
             logging.error("pyttsx3 engine initialization failed.")
    except Exception:
        logging.exception("Failed to initialize pyttsx3 engine.")
        engine = None # Ensure engine is None if init fails

logging.info(f"ElevenLabs TTS {'ENABLED' if USE_ELEVENLABS else 'DISABLED'}.")
logging.info(f"pyttsx3 TTS {'ENABLED and initialized' if engine else ('DISABLED' if USE_ELEVENLABS else 'FAILED TO INITIALIZE')}.")
logging.info("--- Initialization Complete ---")


# === GPT SUMMARIZER ===
def summarize_with_gpt(input_data):
    logging.info("Entering summarize_with_gpt function.")
    prompt = None # Initialize prompt
    content_to_process = None # Initialize content_to_process

    try:
        if isinstance(input_data, dict):
            logging.info("Input data is dictionary (JSON assumed).")
            content_to_process = str(input_data)
            prompt = (
                 "You are ShadowDesk, a dark, witty herald for the IT department. "
                 "You have received structured data about an IT request. "
                 "Craft ONE short spoken announcement (under 35 words) addressed to 'Sir Cody of Technology'. "
                 "Mood: mysterious, slightly ominous; vary wording each time. "
                 "Include—verbatim where possible—the submitter's Name, Department, and Location fields, "
                 "and paraphrase the Issue Description field from the provided data structure. "
                 "Return ONLY that single sentence."
                 "IMPORTANT: Do not use technical terms, JSON keys, or words like 'extracted' or 'field' in your final output sentence."
             )
        elif isinstance(input_data, str):
            logging.info("Input data is string (plain text assumed).")
            content_to_process = input_data
            prompt = (
                "You are ShadowDesk, a dark, witty herald for the IT department, addressing 'Sir Cody of Technology'. "
                "You have intercepted the raw text body of an incoming email concerning an IT service request. "
                "Read the following email text carefully. "
                "Distill its essential information into ONE single, concise spoken announcement (under 35 words). "
                "Maintain a mysterious and slightly ominous tone, varying your phrasing each time for dramatic effect. "
                "From the provided email text, identify and try to include the submitter's Name and their Department or Location *if these details are clearly mentioned within the text*. "
                "Focus on capturing and briefly paraphrasing the core Issue or request described in the email. "
                "Return ONLY the announcement sentence itself. No extra text or explanation."
                "IMPORTANT: Avoid technical jargon, variable names like 'name' or 'issue', or meta-commentary like 'The email states...' or 'Request details:'. Just the announcement."
            )
        else:
            logging.error(f"Invalid data type passed to summarize_with_gpt: {type(input_data)}")
            return "ShadowDesk is perplexed by the formless void of data." # Return error message

        if not client: # Check if client was initialized
             logging.error("OpenAI client is not initialized (check API key). Cannot call GPT.")
             return "ShadowDesk is silent - the connection to the ether is broken."

        logging.info(f"Attempting GPT call with model {MODEL}.")
        # Log first 100 chars of content being sent (avoid logging huge emails)
        logging.debug(f"Content sent to GPT (first 100 chars): {content_to_process[:100]}")

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user",   "content": content_to_process}
        ]

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7
        )
        summary = response.choices[0].message.content.strip()
        logging.info(f"Successfully received GPT summary: '{summary}'")
        logging.info("Exiting summarize_with_gpt function successfully.")
        return summary

    # Catch OpenAI specific errors if desired (requires importing openai errors)
    # except openai.error.AuthenticationError as e:
    #     logging.exception(f"OpenAI Authentication Error: {e}")
    #     return "ShadowDesk whispers of invalid credentials."
    except Exception as e:
        # Use logging.exception to include traceback
        logging.exception("An unexpected error occurred during GPT processing.")
        logging.info("Exiting summarize_with_gpt function with error.")
        # Consider returning a more specific error message based on e if possible
        return "ShadowDesk falters—a disturbance in the connection prevents the message."

# === TTS SPEAKER ===
def speak_with_elevenlabs(text):
    logging.info("Entering speak_with_elevenlabs function.")
    if not text:
        logging.warning("speak_with_elevenlabs called with empty text. Skipping.")
        return False # Indicate failure

    if not ELEVENLABS_API_KEY:
        logging.error("ELEVENLABS_API_KEY not set. Cannot use ElevenLabs.")
        return False # Indicate failure

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg", # Explicitly accept mpeg
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.7}
    }
    tmp_path = None # Initialize tmp_path

    try:
        logging.info(f"Sending request to ElevenLabs API for voice {ELEVENLABS_VOICE_ID}.")
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60) # Added timeout

        logging.info(f"ElevenLabs API response status code: {response.status_code}")
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        # Create temp file BEFORE writing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name # Store path immediately
            logging.info(f"Saving ElevenLabs audio to temporary file: {tmp_path}")
            bytes_written = 0
            for chunk in response.iter_content(chunk_size=4096):
                tmp.write(chunk)
                bytes_written += len(chunk)
            logging.info(f"Finished writing {bytes_written} bytes to temporary file.")

        if bytes_written == 0:
             logging.warning("ElevenLabs returned an empty audio stream.")
             # Cleanup potentially empty file
             if tmp_path and os.path.exists(tmp_path):
                  os.remove(tmp_path)
             return False # Indicate failure

        # --- Play the file ---
        logging.info(f"Attempting to play audio file: {tmp_path}")
        # Use a more robust way to find ffplay or default player if possible
        # For simplicity, keeping os.system for now
        play_command = f'ffplay -nodisp -autoexit "{tmp_path}"'
        logging.info(f"Executing playback command: {play_command}")
        exit_code = os.system(play_command)
        if exit_code != 0:
            logging.error(f"Audio playback command failed with exit code {exit_code}. Is ffplay installed and in PATH?")
            # Fallback or alternative playback method could be added here
            return False # Indicate failure

        logging.info("Audio playback finished.")
        logging.info("Exiting speak_with_elevenlabs function successfully.")
        return True # Indicate success

    except requests.exceptions.RequestException as e:
        # Catch specific requests errors (network, timeout, etc.)
        logging.exception(f"ElevenLabs API request failed: {e}")
        return False # Indicate failure
    except Exception as e:
        # Catch other potential errors (file writing, playback command)
        logging.exception("An unexpected error occurred during ElevenLabs processing or playback.")
        return False # Indicate failure
    finally:
        # --- Cleanup ---
        if tmp_path and os.path.exists(tmp_path):
            try:
                logging.info(f"Attempting to remove temporary file: {tmp_path}")
                # Add a small delay before removing, might help on some systems
                time.sleep(0.5)
                os.remove(tmp_path)
                logging.info("Temporary file removed successfully.")
            except Exception as e:
                # Log exception during cleanup but don't override primary return status
                logging.exception(f"Error removing temporary file {tmp_path}: {e}")


def speak_with_pyttsx3(text):
    logging.info("Entering speak_with_pyttsx3 function.")
    if not text:
        logging.warning("speak_with_pyttsx3 called with empty text. Skipping.")
        return False # Indicate failure

    if not engine:
        logging.error("pyttsx3 engine is not initialized. Cannot speak.")
        return False # Indicate failure

    try:
        logging.info(f"Speaking with pyttsx3 (rate {SPEECH_RATE}): '{text}'")
        engine.say(text)
        engine.runAndWait()
        logging.info("pyttsx3 runAndWait finished.")
        logging.info("Exiting speak_with_pyttsx3 function successfully.")
        return True # Indicate success
    except Exception as e:
        logging.exception("An unexpected error occurred during pyttsx3 processing.")
        logging.info("Exiting speak_with_pyttsx3 function with error.")
        return False # Indicate failure

def speak_text(text):
    logging.info("Entering speak_text function.")
    if not text:
        logging.warning("speak_text called with empty text.")
        return # Or return an error status if preferred

    success = False
    if USE_ELEVENLABS:
        logging.info("Attempting TTS using ElevenLabs.")
        success = speak_with_elevenlabs(text)
        if not success:
            logging.error("ElevenLabs TTS failed.")
            # Optionally, add fallback to pyttsx3 here if desired
            # logging.info("Falling back to pyttsx3.")
            # success = speak_with_pyttsx3(text)
    else:
        logging.info("Attempting TTS using pyttsx3.")
        success = speak_with_pyttsx3(text)
        if not success:
             logging.error("pyttsx3 TTS failed.")

    if success:
         logging.info("Exiting speak_text function successfully.")
    else:
         logging.info("Exiting speak_text function with errors.")


# === WEBHOOK ENDPOINT ===
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    logging.info("--- Webhook request received ---")
    received_data = None
    content_type = request.content_type
    summary = None # Initialize summary

    logging.info(f"Request Content-Type: {content_type}")
    logging.debug(f"Request Headers: {request.headers}") # Log all headers at DEBUG level

    try:
        if content_type and 'application/json' in content_type: # More robust check
            try:
                received_data = request.get_json() # Use get_json for better error handling
                if received_data is None:
                     logging.warning("Content-Type is JSON, but parsing returned None. Check JSON validity.")
                     # Log raw body if possible (might be large)
                     logging.debug(f"Raw request body (first 500 chars): {request.get_data(as_text=True)[:500]}")
                else:
                     logging.info("Successfully parsed JSON data.")
                     logging.debug(f"Received JSON data structure: {received_data}")

            except Exception as json_error: # Catch potential JSON parsing errors
                 logging.exception("Error parsing JSON request body.")
                 # Log raw body if possible (might be large)
                 logging.debug(f"Raw request body (first 500 chars): {request.get_data(as_text=True)[:500]}")
                 return jsonify({"error": "Invalid JSON format"}), 400 # Return specific error

        elif content_type and 'text/plain' in content_type:
            try:
                received_data = request.data.decode('utf-8')
                logging.info("Successfully decoded text/plain data.")
                logging.debug(f"Received text data (first 500 chars): {received_data[:500]}")
            except UnicodeDecodeError:
                 logging.exception("Error decoding request body as UTF-8 text.")
                 return jsonify({"error": "Invalid UTF-8 encoding in text body"}), 400
            except Exception:
                 logging.exception("Error reading text request body.")
                 return jsonify({"error": "Could not read text request body"}), 400
        else:
            # Handle unsupported or missing Content-Type
            logging.warning(f"Unsupported or missing Content-Type: {content_type}. Attempting to read raw data as text.")
            try:
                # Try decoding as text, but don't assume it will work
                received_data = request.data.decode('utf-8')
                logging.info("Read raw data (decoded as text fallback).")
                logging.debug(f"Received raw fallback data (first 500 chars): {received_data[:500]}")
            except Exception:
                # If decoding fails, maybe it's binary or empty
                 received_data = request.data
                 logging.warning(f"Could not decode raw data as text (length: {len(received_data)} bytes). Passing raw bytes might fail later.")
                 # You might want to reject binary data here if you don't expect it
                 # return jsonify({"error": "Unsupported content type and failed to read as text"}), 415

        # --- Process the received data ---
        if not received_data:
            logging.warning("Received empty or unparseable request body.")
            # Decide if you want to process empty requests or return an error
            # return jsonify({"error": "Empty request body"}), 400
            summary = "ShadowDesk senses a void... an empty request arrived."
            logging.info(f"Using default summary for empty request: '{summary}'")
        else:
            # Call GPT
            summary = summarize_with_gpt(received_data) # This function now returns error messages too

        # --- Speak the summary (or error message from GPT) ---
        if summary: # Check if summary is not None or empty
            speak_text(summary)
        else:
             logging.error("Summary generation failed, nothing to speak.")
             # Potentially speak a generic error message here?
             # speak_text("ShadowDesk apologizes, an internal error occurred.")

        logging.info("--- Webhook request processing complete ---")
        # Return "204 No Content" only if everything seemed okay, otherwise Flask default is 200 OK
        # Or consider returning the summary or an error status in the response body.
        return '', 204

    except Exception as e:
        # Catch-all for any unexpected errors during request handling
        logging.exception("An unexpected error occurred in the main webhook handler.")
        # Return a generic server error response
        return jsonify({"error": "Internal Server Error"}), 500


# === RUN SERVER ===
if __name__ == '__main__':
    logging.info(f"--- Starting Flask server on host 0.0.0.0 port {LISTEN_PORT} ---")
    # Turn off Flask's default debugging in production if desired,
    # but keep it on for development debugging (provides interactive debugger in browser).
    # Set debug=True for development, debug=False for production.
    # Use debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true' to control via env var
    app.run(host='0.0.0.0', port=LISTEN_PORT, debug=False)