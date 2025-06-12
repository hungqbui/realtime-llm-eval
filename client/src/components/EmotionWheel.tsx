import { useEffect, useRef } from 'react'
import "./EmotionWheel.css"

const EmotionWheel = (props: any) => {

    const scrollContainerRef = useRef<any>(null);
    const animationFrameIdRef = useRef<any>(null); // For managing smooth scroll animation

    useEffect(() => {

        const container = scrollContainerRef.current;
        if (container) {
            // Scroll to the end of the container when emotions change
            container.scrollLeft = container.scrollWidth - container.clientWidth;
        }

    }, [props.emotions]);

    return (
        <div className="timeline-container">
            {props.emotions.map((item : any) => (
                <EmotionItem item={item} key={item.time} />
            ))}
        </div>
    );
};


const EmotionItem = ({item} : any) => {
    return (
        <div className="timeline-item">
            <div className="timeline-content">
            <div className="timestamp">
                {item.time}
            </div>
            <ul className="emotions-list">
                {item.emotions.map((emotion : any, index : any) => (
                <li key={index} className="emotion-item">
                    <span className="emotion-name">{emotion.name}</span>
                    <span className="emotion-score">{emotion.score.toFixed(2)}</span>
                </li>
                ))}
            </ul>
            </div>
        </div>
    )
}

export default EmotionWheel;