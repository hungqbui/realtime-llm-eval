from quart import Quart, session
import socketio
from quart_cors import cors
import numpy as np
from faster_whisper import WhisperModel
import wave
import asyncio
import uvicorn

app = Quart(__name__)
app = cors(app, allow_origin="*")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

model = WhisperModel("tiny", device="auto", compute_type="int8")

audio_queue = asyncio.Queue()
overall_buffer = asyncio.Queue()


@sio.event
def connect(sid, environ):
    print("Client connected")

@sio.event
def disconnect(sid):
    print("Client disconnected")


@sio.on("audio")
async def handle_audio(sid, data):
    try:
        pcm = np.frombuffer(data["audio_data"], dtype=np.float32)
        await audio_queue.put(pcm)
    except Exception as e:
        print(f"Error processing audio: {e}")
        await sio.emit("error", {"message": "Error processing audio"})


SAMPLE_RATE       = 16_000
MIN_CHUNK_SIZE    = 2                # seconds
CHUNK_SIZE        = int(SAMPLE_RATE * MIN_CHUNK_SIZE)
USE_VAD           = True              # disable VAD for fluent speech
PROMPT_WORD_COUNT = 200                # how many words to keep as context


async def transcribe():
    buffer           = np.zeros((0,), dtype=np.int16)
    prev_words       = None
    last_emitted_cnt = 0
    prompt           = ""

    while True:
        while buffer.shape[0] < CHUNK_SIZE or audio_queue.empty():
            if audio_queue.empty():
                await asyncio.sleep(0.01)
                continue

            pcm    = await audio_queue.get()
            buffer = np.concatenate((buffer, pcm))

        # 2) Run Whisper on the entire current buffer
        segments, _ = model.transcribe(
            buffer,
            language="en",
            initial_prompt=prompt,
            beam_size=5,
            word_timestamps=True,
            condition_on_previous_text=True,
            vad_filter=USE_VAD,
        )
        # 3) Flatten into a list of word-timestamp objects
        words = []
        for seg in segments:
            for w in seg.words:
                words.append(w)
                print(w.word)   # w.word, w.start, w.end


        # 4) LocalAgreement-2: compare this run vs the previous run
        if prev_words is not None:
            # find longest common prefix (by words)
            stable_len = 0
            for pw, cw in zip(prev_words, words):
                if pw.word == cw.word:
                    stable_len += 1
                else:
                    break

            # 5) Emit any newly stable words
            if stable_len > last_emitted_cnt:
                new_segment = " ".join(w.word for w in words[last_emitted_cnt:stable_len])
                await sio.emit("audio_ans", {"text": new_segment})
                # update counters & prompt context
                last_emitted_cnt = stable_len
                confirmed_words  = [w.word for w in words[:stable_len]]
                prompt = " ".join(confirmed_words[-PROMPT_WORD_COUNT:])

                print(prompt)

                # 6) Trim the audio buffer up to the last confirmed timestamp
                last_ts       = words[stable_len-1].end
                trim_samples  = int(last_ts * SAMPLE_RATE)
                buffer        = buffer[trim_samples:]

        # 7) Prep for next iteration
        prev_words = words
        await asyncio.sleep(0.01)

async def save_audio():
    local = []
    for pcm in overall_buffer._queue:
        local.append(pcm)

    with wave.open("audio.wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"".join(local))
        

async def start_up():
    loop = asyncio.get_event_loop()
    loop.create_task(transcribe())

app = socketio.ASGIApp(sio, app, on_startup=start_up)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)