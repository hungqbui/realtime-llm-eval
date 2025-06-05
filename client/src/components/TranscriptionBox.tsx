import { useEffect, useRef } from 'react'
import "./TranscriptionBox.css"

const TranscriptionBox = (props: any) => {

    const end = useRef<HTMLDivElement>(null);

    return (

        <div>
            <div className="timeline-messages-container"> 
                {props.messages.map((msg : any, index : number) => (
                    <TimeBlock key={index} message={msg} isLast={index === props.messages.length -1}/>
                ))}
                <div ref={end} className="timeline-messages-end"></div>
            </div>
            <button onClick={() => {
                if (end.current) {
                    end.current.scrollIntoView({ behavior: "smooth" });
                }
            }}>Scroll to Bottom</button>
        </div>
    )

}

const TimeBlock = ({ message, isLast } : any) => {
    return (
        <div className="message-item">
            <div className="message-item__timestamp"> 
                {message.time}
            </div>
            
            <div className="message-item__decorator">
                <div className="message-item__bullet"></div>
                {!isLast && <div className="message-item__line"></div>} 
            </div>

            <div className="message-item__content-box">
                <p className="message-item__text">{message.text}</p>
            </div>
        </div>
    )
}

export default TranscriptionBox;