import { useState, useEffect } from 'react'
import './App.css'

function App() {

  const [stream, setStream] = useState<any>(null)
  const [source, setSource] = useState<any>(null)
  const [context, setContext] = useState<any>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [processorNode, setProcessorNode] = useState<any>(null)
  const [buffer, setBuffer] = useState<Float32Array[]>([])

  useEffect(() => {

    navigator.mediaDevices.getUserMedia({ video: true})
      .then((stream) => {
        const video = document.createElement('video')
        video.srcObject = stream
        video.play()
        document.body.appendChild(video)
      })

  }, [])

  function mergeAndClear(chunks : any) {
    const length = chunks.reduce((sum : any, c : any) => sum + c.length, 0);
    const out = new Float32Array(length);
    let offset = 0;
    for (let c of chunks) {
      out.set(c, offset);
      offset += c.length;
    }
    chunks.length = 0;
    return out;
  }

  function floatTo16BitPCM(input : Float32Array) {
    const out = new DataView(new ArrayBuffer(input.length * 2));
    input.forEach((sample, i) => {
      let s = Math.max(-1, Math.min(1, sample));
      out.setInt16(i*2, s < 0 ? s*0x8000 : s*0x7FFF, true);
    });
    return out;
  }

  function encodeWAV(samples : Float32Array) {
    const data = floatTo16BitPCM(samples);
    const header = new ArrayBuffer(44);
    const view = new DataView(header);
    /* write “RIFF”, file length, “WAVE”, fmt-chunk, etc… */
    // (do the usual WAV-header boilerplate)
    return new Blob([header, data], { type: "audio/wav" });
  }

  async function sendChunk(float32Chunk : Float32Array) {
    const wav = encodeWAV(float32Chunk);
    // either via fetch:
    const res = await fetch("api/transcribe", {
      method: "POST",
      headers: { "Content-Type": "audio/wav" },
      body: wav
    });
    const ans = await res.json();
    console.log(ans);
  }

  useEffect(() => {

    if (!stream || !context || !source) return

    const processor = context.createScriptProcessor(4096, 1, 1)
    source.connect(processor)
    processor.connect(context.destination)

    setBuffer([])

    processor.onaudioprocess = (e : any) => {
      setBuffer((prevBuffer) => {

        const next = [...prevBuffer, new Float32Array(e.inputBuffer.getChannelData(0))]
        const totalSamples = next.reduce((acc, curr) => acc + curr.length, 0)
        if (totalSamples >= context.sampleRate * 1) {
          const chunk = mergeAndClear(next);
          sendChunk(chunk);
        }
        return next;
      });
    }
    setProcessorNode(processor)

  }, [stream, context, source])

  async function startRecording() {

    const ctx = new AudioContext({ sampleRate: 16000 });

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    setStream(stream);
    setContext(ctx);
    setSource(ctx.createMediaStreamSource(stream));

  }
  function stopRecording() {
    if (!context || !processorNode || !source) return

    processorNode.disconnect();
    source.disconnect();
    context.close();

    setProcessorNode(null);
    setSource(null);
    setContext(null);
    
    // stop all mic tracks
    stream.getTracks().forEach((t: MediaStreamTrack) => t.stop());
  }

  return (
    <>
      <button onClick={async () => {
        if (!isRecording) await startRecording();
        else stopRecording();
        setIsRecording(!isRecording)
      }}>
        { isRecording ? "Stop" : "Start" }
      </button>
    </>
  )
}

export default App
