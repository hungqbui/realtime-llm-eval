import { useEffect, useRef } from 'react'
import "./ChatBox.css"

function ChatBox(props : any) {

    const end = useRef<HTMLDivElement>(null);
    useEffect(() => {
        end.current?.scrollIntoView({ behavior: "smooth" });
    }, [props]);

    return (
        <div className="chat-container">
            {props.messages.map((msg : any, index : any) => (
              <div style={{ width: "80%" }} key={index}><div style={{ fontWeight: "bold", width: "80%", display: "flex" }}>{msg.type}</div><span style={{ textAlign: "left", display: "flex", justifyContent: "left" }}>{msg.content}</span></div>
            ))}
            { props.temp && <div style={{ width: "80%" }}><div style={{ fontWeight: "bold", width: "80%", display: "flex" }}>AI</div><span style={{ textAlign: "left", display: "flex", justifyContent: "left" }}>{props.temp}</span></div>}
            <div ref={end}></div>
        </div>
    )
}

export default ChatBox;