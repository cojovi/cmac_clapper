from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    print("Webhook received!")
    subprocess.Popen(['powershell', '-Command', 'Start-Process', 'wmplayer.exe', '"C:\\path\\to\\your\\sound.mp3"'])
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

