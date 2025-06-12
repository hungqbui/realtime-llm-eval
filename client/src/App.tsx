
import React, { useState, useEffect, useRef } from 'react'
import { socket } from './utils/socket'; 
import './App.css'
import ChatBox from './components/ChatBox';
import TranscriptionBox from './components/TranscriptionBox';
import EmotionWheel from './components/EmotionWheel';


function App() {

  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState<any[]>([]);
  const [title, setTitle] = useState<string>("");
  const [titleSet, setTitleSet] = useState<boolean>(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [message, setMessage] = useState<string>("");
  const [emotions, setEmotions] = useState<any[]>([]);
  const [waitingForResponse, setWaitingForResponse] = useState<boolean>(false);
  const [fullText, setFullText] = useState<string>("");
  const [leftWidth, setLeftWidth] = useState<number>(50);

  const audioCtx = useRef<AudioContext | null>(null);
  const processor = useRef<ScriptProcessorNode | null>(null);
  const input = useRef<MediaStreamAudioSourceNode | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const vidRecorder = useRef<MediaRecorder | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fullTextRef = useRef<string>("");
  const fullTextTimeRef = useRef<string>("");
  const vidRef = useRef<HTMLVideoElement | null>(null);
  const timeRef = useRef<string>("");
  const isResizing = useRef<boolean>(false);

  const useEventListener = (eventName : any, handler : any, element = window) => {
    
    const savedHandler = useRef<any>("");
    useEffect(() => {
      savedHandler.current = handler;
    }, [handler]);

    useEffect(() => {
      // Make sure element supports addEventListener
      const isSupported = element && element.addEventListener;
      if (!isSupported) return;

      // Create event listener that calls handler function stored in ref
      const eventListener = (event : any) => savedHandler.current(event);

      // Add event listener
      element.addEventListener(eventName, eventListener);

      // Remove event listener on cleanup
      return () => {
        element.removeEventListener(eventName, eventListener);
      };
    }, [eventName, element]); // Re-run if eventName or element changes
  };

  
  const handleMouseDown = (e : any) => {
    // Prevent text selection while dragging
    e.preventDefault();
    isResizing.current = true;
  };
  
  const handleMouseUp = () => {
    // Stop resizing
    isResizing.current = false;
  };
  
  const handleMouseMove = (e : any) => {
    if (!isResizing.current) return;
    
    const containerWidth = document.body.clientWidth;
    const newWidth = (e.clientX / containerWidth) * 100;
    
    // Clamp the width between 10% and 90%
    if (newWidth >= 5 && newWidth <= 95) {
      setLeftWidth(newWidth);
    }
  };
  
  useEventListener('mousemove', handleMouseMove);
  useEventListener('mouseup', handleMouseUp);
  
  const handleTouchStart = (e : any) => {
    e.preventDefault();
    isResizing.current = true;
  };

  const getCurrentTime = () => {
    const date = new Date();
    return `${date.getHours()}:${padDigit(date.getMinutes())}`;
  }

  const getCurrentTimeSeconds = () => {
    const date = new Date();
    return `${date.getHours()}:${padDigit(date.getMinutes())}:${padDigit(date.getSeconds())}`;
  }

  const padDigit = (num: number) => {
    if (num < 10) {
      return `0${num}`;
    }
    return num.toString();
  }

  useEffect(() => {

    socket.on("connect", () => {
      console.log("Connected to server");
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
    });

    socket.on("audio_ans", (data : any) => {
      const lastEmitted = timeRef.current;
      timeRef.current = getCurrentTime();

      if (timeRef.current != lastEmitted) {
        setTranscription(prev => [...prev, { text: data["text"], time: getCurrentTime() }]);
      }
      else {
        setTranscription(prev => {
          const newTranscription = [...prev];
          newTranscription[newTranscription.length - 1].text += ` ${data["text"]}`;
          return newTranscription;
        });
      }
    })

    socket.on("chat_response", (data : any) => {
      setFullText(prev => prev + data["message"]);
      fullTextRef.current += data["message"];
      if (!fullTextTimeRef.current) fullTextTimeRef.current = getCurrentTime();
    })

    socket.on("stream_end", (data : any) => {
      setWaitingForResponse(false);
      const temp = fullTextRef.current;
      const tempTime = fullTextTimeRef.current;

      if (data["message"] == "END") {
        setMessages(prev => [...prev, { type: "AI", content: temp, time: tempTime }]);
      } else {
        setMessages(prev => {
          return prev.slice(0, -1);
        })
      }


      setFullText("");
      fullTextRef.current = "";
      fullTextTimeRef.current = "";
    })

    socket.on("face_recognition_ans", (data : any) => {
      console.log(data["message"]);

      const newItem = {
        time: getCurrentTimeSeconds(),
        emotions: data["message"].map((em: any) => {
          return {
            name: em[1],
            score: em[0]
          }
        })
      }

      setEmotions(prev => [newItem, ...prev]);
    });

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("audio_ans");
      socket.off("chat_response");
      socket.off("stream_end");
      socket.off("face_recognition_ans");
    }

  }, []);

  useEffect(() => {
    if (!isRecording) return;

    const frameInterval = setInterval(async () => {
      
      if (!vidRef.current || !vidRef.current.srcObject) return;

      const canvas = canvasRef.current;
      if (!canvas) return;
      const context = canvas.getContext('2d');
      if (!context) return;

      canvas.width = vidRef.current.videoWidth;
      canvas.height = vidRef.current.videoHeight;

      context.drawImage(vidRef.current, 0, 0);
      canvas.toBlob(async (blob) => {
        const buf = await blob?.arrayBuffer();

        socket.emit("face_recognition", {
          "image_data": buf,
        });

      }, 'image/jpeg', 1);

    }, 15000);

    return () => {
      clearInterval(frameInterval);
    };
  }, [isRecording]);

  const startRecording = async () => {

    stream.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });

    audioCtx.current = new AudioContext({ sampleRate: 16000 });
    audioCtx.current.resume();

    vidRecorder.current = new MediaRecorder(stream.current);

    vidRef.current!.srcObject = stream.current;

    vidRecorder.current.ondataavailable = async (event) => {
      if (event.data && event.data.size > 0) {
        const buf = await event.data.arrayBuffer();
        socket.emit("video", {
          "video_data": buf,
        });
      }
    }
    vidRecorder.current.start(1000)

    input.current = audioCtx.current.createMediaStreamSource(stream.current);
    processor.current = audioCtx.current.createScriptProcessor(4096, 1, 1);
    
    processor.current.onaudioprocess = async (e) => {
      const data = e.inputBuffer.getChannelData(0);
      sendChunkToServer(data);
    };
    input.current?.connect(processor.current);
    processor.current?.connect(audioCtx.current.destination);
    setIsRecording(true);
    socket.emit("start")
  }

  const stopRecording = () => {
    processor.current?.disconnect();
    input.current?.disconnect();
    audioCtx.current?.close();
    stream.current?.getTracks().forEach(track => track.stop());

    socket.emit("stop")

    setIsRecording(false);
  }

  function sendChunkToServer(int16Chunk : any) {
    const blob = new Blob([int16Chunk], { type: 'application/octet-stream' });
    socket.emit("audio", {
      "audio_data": blob,
    });
  }

  function stopHandler(event: any) {
    if (!waitingForResponse) return;

    socket.emit("stop_chat");
  }

  function textMessageHandler(event: any) {
    if (waitingForResponse) return

    if (message.trim() === "") {
      return
    }

    setMessages([...messages, {type: "User", content: message, time: getCurrentTime()}]);
    socket.emit("chat_message", { message, title, transcription: transcription.map((obj) => {
      return `${obj.time} ${obj.text}`;
    }).join("\n"), history: messages.slice(-10), "emotions": emotions.slice(-30) });
    setMessage("");
    setWaitingForResponse(true);
  }

  if (titleSet)
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", width: "100vw" }}>
        <canvas ref={canvasRef} style={{display: "none"}}></canvas>
        <div >
          <button onClick={async () => {
            if (!isRecording) startRecording();
            else stopRecording();
          }} style={{ backgroundColor: isRecording ? "red" : "lime", color: "black" }}>
            { isRecording ? "Stop" : "Start" }
          </button>
        </div>
        <div style={{ position: "relative", display: "flex", justifyContent: "center", width: "100%", height: "30vh" }}>
          <video style={{ border: "1px solid black", maxWidth:"400px", height: "100%" }}
            ref={vidRef}
            muted
            autoPlay
            playsInline
          ></video>
          <div style={{ position: "absolute", right: "3%", maxHeight: "100%", minWidth: "250px", width: "30vw" }}>
            <EmotionWheel emotions={emotions} />
          </div>
        </div>
        <div style={{ marginTop: "16px", width: "100%", textAlign: "center", display: "flex", flexDirection: "row", justifyContent: "space-evenly" }}>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", width: `${leftWidth}%` }}>
            <h3>Chatbox</h3>
            <ChatBox messages={messages} temp={fullText} temptime={fullTextTimeRef.current} />
            <div style={{width: "100%", position: "relative", display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "space-between"}}>
              <textarea rows={1} placeholder='Ask MedGemma...' className='input-text' onKeyDown={(e) => {
                if (e.key === "Enter") {
                  textMessageHandler(e);
                }
              }} value={message} onChange={(e) => setMessage(e.target.value == "\n" ? "" : e.target.value)} />
              <button onClick={e => {
                if (waitingForResponse) {
                  stopHandler(e);
                }
                else {
                  textMessageHandler(e);
                }
              }} className='send-button' aria-label="Send message">
              { !waitingForResponse ? 
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#b2b2b2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> :
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#b2b2b2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>
              }
            </button>
            </div>
          </div>
          <div className="resizer" 
              onMouseDown={handleMouseDown}
              onTouchStart={handleTouchStart}
              role="separator"
          >
            <div className="resize-handle"></div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", textAlign: "left", width: `${100 - leftWidth}%`, margin: 0 }}>
            <h3 style={{width: "100%", textAlign: "center"}}>Transcription</h3>
            <TranscriptionBox messages={transcription} />
          </div>
        </div>
        
      </div>
    )
  else return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", width: "100vw" }}>
      <input style={{ marginBottom: "16px", padding: "8px", fontSize: "16px", width: "80%" }} type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
      <button onClick={() => setTitleSet(true)}>Set Title</button>
    </div>
  )
}

export default App
