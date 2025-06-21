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

def list_records(records=[]):
    """List all records in REDCAP."""
    data = {
        'token': os.getenv("REDCAP"),
        'content': 'record',
        'format': 'json',
        'returnFormat': 'json',
        "records": records
    }
    r = requests.post(URL, data=data)
    return r.json()

GENDER = {
    "1": "Man",
    "2": "Woman",
    "3": "Transgender",
    "4": "Not Listed",
    "5": "Prefer not to answer"
}


AGE = {
    "1": "18-24 years old",
    "2": "25-34 years old",
    "3": "35-49 years old",
    "4": "50-64 years old",
    "5": "65 years old and older"
}

RACE = ["r_r___1", "r_r___2", "r_r___3", "r_r___4", "r_r___5", "r_r___6", "r_r___7"]
RACE_LABELS = {
    "r_r___1": "American Indian or Alaskan Native",
    "r_r___2": "Asian",
    "r_r___3": "Native Hawaiian or Other Pacific Islander",
    "r_r___4": "Black or African American",
    "r_r___5": "White",
    "r_r___6": "Other",
    "r_r___7": "Prefer not to answer"
}

TECHNOLOGICAL_SKILL = {
    "1": "Not at all proficient",
    "2": "Slightly proficient",
    "3": "Moderately proficient",
    "4": "Very proficient",
    "5": "Extremely proficient"
}

MEDICAL_PROBLEMS = ["r_mp___1", "r_mp___2", "r_mp___3", "r_mp___4", "r_mp___5", "r_mp___6"]
MEDICAL_PROBLEMS_LABELS = {
    "r_mp___1": "Type 2 diabetes mellitus",
    "r_mp___2": "Type 1 diabetes mellitus",
    "r_mp___3": "Hypertension",
    "r_mp___4": "Heart disease",
    "r_mp___5": "Obesity",
    "r_mp___6": "None of the above"
}

def get_screening_prettify(record):
    """Get a record in a pretty format."""
    data = {
        'token': os.getenv("REDCAP"),
        'content': 'record',
        'format': 'json',
        'returnFormat': 'json',
        "records": [record]
    }
    r = requests.post(URL, data=data)
    parsed = r.json()[0]

    races = []

    for r in RACE:
        if parsed.get(r, "0") == "1":
            races.append(RACE_LABELS[r])

    filtered = {
        "record_id": parsed.get("record_id", ""),
        "gender": GENDER[parsed.get("r_gi", "5")],
        "age": AGE[parsed.get("r_age")],
        "race": races,
        "ethnicity": "Hispanic" if parsed.get("r_e", "") == "1" else "Non-Hispanic",
        "technological_skill": TECHNOLOGICAL_SKILL.get(parsed.get("r_t", "1"), "Not specified"),
        "patient_or_clinician": "Patient" if parsed.get("r_pc", "1") == "1" else "Clinician" if parsed.get("r_pc") == 2 else "Neither",
        "screening_complete": parsed.get("screening_complete", "0")
    }

    if (parsed.get("r_pc") and parsed.get("r_pc") == "1"):
        medical_problems = []
        for mp in MEDICAL_PROBLEMS:
            if parsed.get(mp, "0") == "1":
                medical_problems.append(MEDICAL_PROBLEMS_LABELS[mp])
        filtered["medical_problems"] = medical_problems
        filtered["nicotine"] = "Every Day" if parsed.get("r_n", "1") == "1" else "Some Days" if parsed.get("r_n") == "2" else "Not at all"
        filtered["alcohol"] = "Never" if parsed.get("r_a", "1") == "1" else "Monthly or less" if parsed.get("r_a") == "2" else "2-4 times a month" if parsed.get("r_a") == "3" else "2-3 times a week" if parsed.get("r_a") == "4" else "4 or more times a week"
        filtered["days_per_week_exercise"] = parsed.get("r_de")
        filtered["average_minutes_exercise"] = parsed.get("r_eal")
        filtered["pieces_of_fruit_per_day"] = parsed.get("r_f")
        filtered["pieces_of_vegetables_per_day"] = parsed.get("r_v")

        if (parsed.get("r_a") == "2"):
            filtered["standard_drinks"] = "1 or 2" if parsed.get("r_sd", "1") == "1" else "3 or 4" if parsed.get("r_sd") == "2" else "5 or 6" if parsed.get("r_sd") == "3" else "7 to 9" if parsed.get("r_sd") == "4" else "10 or more"
            filtered["frequency_of_6_plus_drinks"] = "Never" if parsed.get("r_6", "1") == "1" else "Less than monthly" if parsed.get("r_6") == "2" else "Monthly" if parsed.get("r_6") == "3" else "Weekly" if parsed.get("r_6") == "4" else "Daily or almost daily"
    elif (parsed.get("r_pc") and parsed.get("r_pc") == "2"):
        filtered["role"] = {
            "1": "Physician",
            "2": "Nurse practitioner",
            "3": "Physician assistant",
            "4": "Behavioral specialist (including psychologists, clinical social workers, and therapists)",
            "5": "Physical therapist",
            "6": "Pharmacist",
            "7": "None of the above"
        }.get(parsed.get("r_pr", "7"), "Not specified")
        filtered["years_of_graduation"] = parsed.get("r_gr", "0")
        filtered["specialty"] = {
            "1": "Family medicine",
            "2": "Internal medicine",
            "3": "Endocrinology",
            "4": "Pediatrics",
            "5": "Medicine -- Pediatrics",
            "6": "Psychiatry",
            "7": "Obstetrics / Gynecology",
            "8": "Other"
        }.get(parsed.get("r_s", "8"), "Not specified")

    return filtered

BEHAVIORS = ["prv_hb___1", "prv_hb___2", "prv_hb___3", "prv_hb___4", "prv_hb___5"] 
BEHAVIORS_LABELS = {
    "prv_hb___1": "Exercise",
    "prv_hb___2": "Diet",
    "prv_hb___3": "Nicotine use",
    "prv_hb___4": "Alcohol use",
    "prv_hb___5": "Other"
}
BEHAVIORS_LABELSID = {
    "1": "Exercise",
    "2": "Diet",
    "3": "Nicotine use",
    "4": "Alcohol use",
    "5": "Other"
}


def get_patient_previsit(record):
    """Get a record in a pretty format."""
    data = {
        'token': os.getenv("REDCAP"),
        'content': 'record',
        'format': 'json',
        'returnFormat': 'json',
        "records": [record]
    }
    r = requests.post(URL, data=data)
    parsed = r.json()[0]

    behaviors = []
    for b in BEHAVIORS:
        if parsed.get(b, "0") == "1":
            behaviors.append(BEHAVIORS_LABELS[b])

    filtered = {
        "record_id": parsed.get("record_id", ""),
        "health_behaviors_to_discuss": behaviors,
        "behavior_most_want_to_change": BEHAVIORS_LABELSID.get(parsed.get("prv_mwc", ""), "Not specified"),
        "level_of_wanting_to_take_responsibility": parsed.get("prv_r", "1"),
        "level_of_shame_of_health_behavior": parsed.get("prv_g", "1"),
        "level_of_belief_changing_is_better": parsed.get("prv_btfh", "1"),
        "level_of_belief_others_will_be_upset_if_not_changed": parsed.get("prv_cwtb", "1"),
        "level_of_not_thinking_about_it": parsed.get("prv_dtai", "1"),
        "level_of_belief_change_is_important": parsed.get("prv_cimaol", "1"),
        "level_of_feeling_bad_if_not_changed": parsed.get("prv_fbas", "1"),
        "level_of_wanting_to_change": parsed.get("prv_rwtm", "1"),
        "level_of_pressure_from_others": parsed.get("prv_pfo", "1"),
        "level_of_belief_in_easier_to_what_is_told": parsed.get("prv_dwit", "1"),
        "level_of_align_with_life_goals": parsed.get("prv_cwlg", "1"),
        "level_of_wanting_approval_from_others": parsed.get("prv_aom", "1"),
        "level_of_belief_in_being_as_healthy_as_possible": parsed.get("prv_hap", "1"),
        "level_of_wanting_to_show_others_can_change": parsed.get("prv_icdi", "1"),
        "level_of_dont_know_why": parsed.get("prv_dkw", "1"),
        "level_of_confidence_in_ability_to_change": parsed.get("prv_acb", "1"),
        "level_of_belief_in_ability_to_change_after_above": parsed.get("prv_nfchb", "1"),
        "level_of_belief_in_change_in_the_long_term": parsed.get("prv_hbolt", "1"),
        "level_of_belief_in_overcoming_challenges": parsed.get("prv_mcchb", "1"),
        "level_of_options_from_healthcare_provider": parsed.get("prv_oachb", "1"),
        "level_of_belief_in_healthcare_provider_understanding_about_changing": parsed.get("prv_uhist", "1"),
        "level_of_belief_in_healthcare_provider_confidence_in_ability_to_change": parsed.get("prv_cc", "1"),
        "level_of_belief_in_healthcare_provider_listening_to_concerns": parsed.get("prv_ltdtrhb", "1"),
        "level_of_healthcare_provider_encouragement": parsed.get("prv_aqhb", "1"),
        "level_of_healthcare_provider_understanding_before_suggesting": parsed.get("prv_ttuhismhb", "1"),
        "patient_previsit_complete": parsed.get("patient_previsit_complete", "0")
    }

    return filtered

print(get_screening_prettify(1))