import React, { useEffect, useState } from 'react';
import fetchTool from "./utils/fetchData"; 
import { useParams } from 'react-router';
import VideoOverlay from './components/VideoOverlay';
import './DataViewPage.css'; // Assuming you have a CSS file for styling

export default () => {
    const { patient } = useParams<{ patient: string }>();
    const [data, setData] = useState<any>(null);
    const [selectedVideo, setSelectedVideo] = useState<any | null>(null);

    const handleCloseOverlay = () => {
        setSelectedVideo(null);
    };

    useEffect(() => {
        // This effect runs when the component mounts
        console.log('Patient ID:', patient);
        
        fetchTool.fetchPatientData(patient as string)
            .then(fetchedData => {
                console.log('Fetched data:', fetchedData);
                setData(fetchedData);
            })

        
    }, []);
    
    return (
        <>
            <VideoOverlay video={selectedVideo} onClose={handleCloseOverlay} />
            <div>
                <h1>Data View Page</h1>
                <p>This is the data view page where you can see data for {patient}.</p>
                {data ? (
                    <div>
                        <h2>Recordings</h2>
                        <ul>
                            {data.map((vid: any) => (
                                <li className='video-title-list' key={vid["doc_id"]}>
                                    <strong onClick={() => {
                                        setSelectedVideo(vid);
                                    }}>{vid.name}</strong>
                                    <button onClick={() => {
                                        fetchTool.deleteDocument(vid["doc_id"])
                                        // Remove this listing from the UI
                                        .then(() => {
                                            setData((prevData : any) => prevData.filter((item: any) => item.doc_id !== vid.doc_id));
                                        }
                                        ).catch(error => {
                                            console.error('Error deleting document:', error);
                                        });
                                    }}
                                    >Delete</button>
                                </li>
                            ))}
                        </ul>
                    </div>
                ) : (
                    <p>Loading data...</p>
                )}
            </div>
        </>
    );
}