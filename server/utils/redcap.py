import requests
import dotenv
import os

dotenv.load_dotenv("/data/qbui2/proj/dev/realtime-llm-eval/.env")

URL = "https://redcap.times.uh.edu/api/"


def list_folders(folder_id=''):
    data = {
        'token': os.getenv("REDCAP"),
        'content': 'fileRepository',
        'action': 'list',
        'format': 'json',
        'folder_id': folder_id,
        'returnFormat': 'json'
    }
    r = requests.post(URL, data=data)

    return r.json()


def create_folder(folder_name):
    data = {
        'token': os.getenv("REDCAP"),
        'content': 'fileRepository',
        'action': 'createFolder',
        'format': 'json',
        'name': folder_name,
        'folder_id': '',
        'returnFormat': 'json'
    }
    r = requests.post(URL, data=data)
    print(f"Created new folder: {folder_name}\n")
    return r.json()[0]['folder_id']

def upload_file(file_path, patient_name):
    """Upload a file to REDCAP under a specific patient's folder."""
    print(f"Uploading file {file_path} for patient {patient_name}")
    folders = list_folders()

    if patient_name not in set([folder['name'] for folder in folders if "folder_id" in folder]):
        folder_id = create_folder(patient_name)
    else:
        folder_id = get_id_from_name(patient_name)

    params = {
        "token": os.getenv("REDCAP"),
        "content": "fileRepository",
        "action": "import",
        "folder_id": folder_id,
        "returnFormat": "json"
    }
    with open(file_path, "rb") as f:

        files = {
            'file': (file_path, f)
        }
        response = requests.post(URL, data=params, files=files)
        print(response.text)

def get_file(doc_id):
    """Fetch a base64 encoded file from REDCAP given a document ID."""

    data = {
        'token': os.getenv("REDCAP"),
        'content': 'fileRepository',
        'action': 'export',
        'format': 'json',
        'doc_id': doc_id,
        'returnFormat': 'json'
    }
    r = requests.post(URL, data=data)
    return r.content

def delete_document(doc_id):
    """Delete a document from REDCAP given a document ID."""
    data = {
        'token': os.getenv("REDCAP"),
        'content': 'fileRepository',
        'action': 'delete',
        'doc_id': doc_id,
        'returnFormat': 'json'
    }
    r = requests.post(URL, data=data)
    print(r)
    

def delete_data(folder_id):
    """Delete all documents in a folder."""
    files = list_folders(folder_id)
    
    for file in files:
        if 'doc_id' in file:
            delete_document(file['doc_id'])

def get_id_from_name(name):
    """Get the document ID from the file name."""
    folders = list_folders()
    for folder in folders:
        if folder['name'] == name:
            return folder['folder_id']
    return None