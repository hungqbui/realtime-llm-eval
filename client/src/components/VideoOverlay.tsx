import React, { useEffect } from 'react';
import './VideoOverlay.css'; // Assuming you have a CSS file for styling the overlay

function VideoOverlay({ video, onClose } : any) {
  // If no video is selected, render nothing.
  if (!video) {
    return null;
  }

  // This effect handles the 'Escape' key press to close the overlay
  useEffect(() => {
    const handleEsc = (event : any) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEsc);

    // Cleanup function to remove the event listener
    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, [onClose]);


  return (
    // The main overlay container. Clicking the background will also close it.
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-content" onClick={(e) => e.stopPropagation()}>
        {/* Stop propagation prevents the overlay from closing if you click inside the content area */}
        <div className="overlay-header">
          <h3>{video["name"]}</h3>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="overlay-body">
          <video key={video["doc_id"]} width="100%" height="auto" controls autoPlay>
            <source src={`/api/get_file/${video["doc_id"]}`} type="video/webm" />
            Your browser does not support the video tag.
          </video>
        </div>
      </div>
    </div>
  );
}

export default VideoOverlay;