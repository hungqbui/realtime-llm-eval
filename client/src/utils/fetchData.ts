const fetchPatients = async () => {
    try {
        const response = await fetch('/api/get_folders');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching patients:', error);
        throw error;
    }
}

const fetchPatientData = async (patientId: string) => {
    try {
        const response = await fetch(`/api/get_data/${patientId}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error fetching data for patient ${patientId}:`, error);
        throw error;
    }
}

const deletePatientData = async (patientId: string) => {
    try {
        const response = await fetch(`/api/delete_data/${patientId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error deleting data for patient ${patientId}:`, error);
        throw error;
    }
}

const deleteDocument = async (docId: string) => {
    try {
        const response = await fetch(`/api/delete_document/${docId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error deleting document with ID ${docId}:`, error);
        throw error;
    }
}

const createPatient = async (patientName: string) => {
    try {
        const response = await fetch('/api/create_patient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ patientName: patientName }),
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error creating patient ${patientName}:`, error);
        throw error;
    }
}

export default { fetchPatients, fetchPatientData, deletePatientData, deleteDocument, createPatient };