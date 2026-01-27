import cv2
import pandas as pd
import numpy as np
import os

# -------------------------
# Paths
# -------------------------
DATASET_FOLDER = "missing_people_dataset"
DATASET_FILE = os.path.join(DATASET_FOLDER, "dataset.csv")
UPLOADS_FOLDER = "static/uploads"

# Ensure folders exist
os.makedirs(DATASET_FOLDER, exist_ok=True)
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# -------------------------
# Load dataset safely
# -------------------------
if os.path.exists(DATASET_FILE) and os.path.getsize(DATASET_FILE) > 0:
    try:
        df = pd.read_csv(DATASET_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=["name", "address", "image_path", "encoding"])
else:
    df = pd.DataFrame(columns=["name", "address", "image_path", "encoding"])

# -------------------------
# Load Haar cascade
# -------------------------
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# -------------------------
# Encode face
# -------------------------
def encode_face(image_path):
    if not os.path.exists(image_path):
        print("Image not found:", image_path)
        return None

    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load:", image_path)
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        print("No face detected:", image_path)
        return None

    x, y, w, h = faces[0]  # take the first detected face
    face_crop = cv2.resize(img[y:y+h, x:x+w], (128, 128))
    encoding = face_crop.flatten() / 255.0  # normalize
    return encoding

# -------------------------
# Compare two faces
# -------------------------
def is_same_face(enc1, enc2, threshold=0.5):
    if enc1 is None or enc2 is None:
        return False
    dist = np.linalg.norm(np.array(enc1) - np.array(enc2))
    return dist < threshold

# -------------------------
# Check if face exists in dataset
# -------------------------
def find_existing_person(image_path):
    new_encoding = encode_face(image_path)
    if new_encoding is None:
        return None

    for idx, row in df.iterrows():
        try:
            existing_encoding = np.array(eval(row["encoding"]))
        except:
            continue
        if is_same_face(new_encoding, existing_encoding):
            return idx, row
    return None, None

# -------------------------
# Add or update person
# -------------------------
def add_or_update_person(name, address, image_path):
    global df
    idx, existing = find_existing_person(image_path)
    new_encoding = encode_face(image_path)
    if new_encoding is None:
        print("Face not detected, cannot add/update person.")
        return None

    if existing is not None:
        # Update existing person
        df.at[idx, "name"] = name
        df.at[idx, "address"] = address
        df.at[idx, "image_path"] = image_path
        df.at[idx, "encoding"] = str(new_encoding.tolist())
        print(f"Updated existing person: {name}")
    else:
        # Add new person
        new_row = {
            "name": name,
            "address": address,
            "image_path": image_path,
            "encoding": str(new_encoding.tolist())
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        print(f"Added new person: {name}")

    df.to_csv(DATASET_FILE, index=False)
    return df.loc[idx].to_dict() if existing is not None else new_row

# -------------------------
# Example usage
# -------------------------
people_to_add = [
    ("Deepthi", "123 Street, City", "missing_people_dataset/images/deepthi.jpeg"),
    ("Sireesha", "Guntur City", "missing_people_dataset/images/sireesha.jpeg")
]

for name, addr, path in people_to_add:
    info = add_or_update_person(name, addr, path)
    print(info)
