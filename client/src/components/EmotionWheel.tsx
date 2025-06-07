import { useEffect, useRef } from 'react'
import "./EmotionWheel.css"

const EmotionWheel = (props: any) => {

    const scrollContainerRef = useRef<any>(null);
    const animationFrameIdRef = useRef<any>(null); // For managing smooth scroll animation

    useEffect(() => {
        const container = scrollContainerRef.current;
        if (container) {
            const handleWheelScroll = (event : any) => {
                // Only act on vertical wheel events for horizontal scrolling
                if (Math.abs(event.deltaY) > Math.abs(event.deltaX) || event.deltaX === 0) {
                    event.preventDefault(); // Prevent page from scrolling vertically

                    // Cancel any ongoing animation
                    if (animationFrameIdRef.current) {
                        cancelAnimationFrame(animationFrameIdRef.current);
                    }

                    const scrollAmount = event.deltaY * 0.7; // Adjust sensitivity/speed factor
                    let targetScrollLeft = container.scrollLeft + scrollAmount;

                    // Clamp targetScrollLeft to bounds
                    const maxScrollLeft = container.scrollWidth - container.clientWidth;
                    targetScrollLeft = Math.max(0, Math.min(targetScrollLeft, maxScrollLeft));

                    // Smooth scroll animation
                    const animateScroll = () => {
                        const currentScrollLeft = container.scrollLeft;
                        const step = (targetScrollLeft - currentScrollLeft) * 0.15; // Easing factor

                        if (Math.abs(targetScrollLeft - currentScrollLeft) < 1) {
                            container.scrollLeft = targetScrollLeft; // Snap to final position
                            animationFrameIdRef.current = null;
                        } else {
                            container.scrollLeft += step;
                            animationFrameIdRef.current = requestAnimationFrame(animateScroll);
                        }
                    };
                    animationFrameIdRef.current = requestAnimationFrame(animateScroll);
                }
            };

            container.addEventListener('wheel', handleWheelScroll, { passive: false });

            return () => {
                container.removeEventListener('wheel', handleWheelScroll);
                if (animationFrameIdRef.current) {
                    cancelAnimationFrame(animationFrameIdRef.current);
                }
            };
        }
    }, []); // Empty dependency array: effect runs once on mount, cleans up on unmount

    return (
        <div
            ref={scrollContainerRef}
            className="timeline-scroll-container hidden-scrollbar"
        >
            <div className="timeline-track">
                <div className="timeline-line"></div>
                {props.emotions.map((item : any, index: any) => (
                    <EmotionItem
                        key={index}
                        time={item.time}
                        emotion={item.emotion}
                    />
                ))}
            </div>
        </div>
    );
};


const EmotionItem = ({emotion, time, conf} : any) => {
    return (
        <div
            className="timeline-item "
        >
            <div className="timeline-item-time">{time}</div>
            <div className="timeline-item-label">{emotion}</div>
            <div className="timeline-item-conf">{conf}</div>
        </div>
    )
}

export default EmotionWheel;