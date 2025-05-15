from flask import Flask, request, jsonify
import io
from flask_cors import CORS
import whisper
import soundfile as sf

app = Flask(__name__)
CORS(app)

model = whisper.load_model("small")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    audio_data = request.data

    print("Started transcribing audio...", flush=True)

    audio, sr = sf.read(io.BytesIO(audio_data).seek(0), dtype="float32")

    res = model.transcribe(
        audio,
        language="en",
        fp16=True
    )

    print("Finished transcribing audio..." + res["text"], flush=True)


    return jsonify({"message": "Audio received successfully!", "text": res["text"]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)