from flask import Flask, request, jsonify, session
import io
from flask_cors import CORS
import numpy as np
import wave
import subprocess
from flask_socketio import SocketIO, emit
from faster_whisper import WhisperModel


app = Flask(__name__)
CORS(app)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SECRET_KEY"] = "your_secret"

socketio = SocketIO(app, cors_allowed_origins="*")
model = WhisperModel("base", device="auto", compute_type="int8")

buffer = {}

@socketio.on("connect")
def handle_connect():
    print("Client connected")
    emit("response", {"message": "Connected to server"})

@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


@socketio.on("audio")
def handle_audio(data):
    session_id = data["session_id"]
    audio_data = data["audio_data"]

    if session_id not in buffer:
        buffer[session_id] = []

    buffer[session_id].append(audio_data)

    processed = np.frombuffer(b"".join(buffer[session_id]), dtype=np.float32)
    processed = processed.astype(np.float16)

    segments, _ = model.transcribe(processed, beam_size=5, language="en")

    for segment in segments:
        emit("audio_ans", { "res" : segment.text })



if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)