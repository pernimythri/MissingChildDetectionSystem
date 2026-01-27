from flask import Flask, render_template, request, redirect
import os
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
import cv2
import numpy as np
from flask import session



app = Flask(__name__)
app.secret_key = "my_secret_key"

# ---------- CONFIG ----------
UPLOAD_FOLDER = "static/uploads"
DATASET_FILE = "missing_people_dataset/dataset.csv"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load or create dataset.csv
if os.path.exists(DATASET_FILE) and os.path.getsize(DATASET_FILE) > 0:
    try:
        df_dataset = pd.read_csv(DATASET_FILE)
    except pd.errors.EmptyDataError:
        df_dataset = pd.DataFrame(columns=["name","address","image_path","encoding"])
else:
    df_dataset = pd.DataFrame(columns=["name","address","image_path","encoding"])

# Load OpenCV Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# ---------- HELPER FUNCTIONS ----------
def encode_face(image_path):
    """Detect face, crop, resize and return flattened encoding"""
    if not os.path.exists(image_path):
        return None

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return None

    x, y, w, h = faces[0]  # take first face
    face_crop = cv2.resize(img[y:y+h, x:x+w], (128, 128))
    encoding = face_crop.flatten() / 255.0
    return encoding

def find_existing_person(new_encoding, new_name, threshold=0.6):
    """Check if the face already exists in dataset.csv"""
    for _, row in df_dataset.iterrows():
        try:
            existing_encoding = np.array(eval(row['encoding']))
            distance = np.linalg.norm(existing_encoding - new_encoding)
            if distance < threshold and new_name.lower() == row['name'].lower():
                return row  # person exists
        except:
            continue
    return None

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/start")
def start():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("gmail")
        password = request.form.get("password")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, username FROM users
        WHERE gmail = ? AND password = ?
        """, (username, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/dashboard")
        else:
            return "Invalid username or password"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        gmail = request.form["gmail"]
        password = request.form["password"]
        phone = request.form["phone"]
        address = request.form["address"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO users (username, gmail, password, phone, address)
            VALUES (?, ?, ?, ?, ?)
            """, (username, gmail, password, phone, address))
            conn.commit()
        except:
            conn.close()
            return "Username already exists!"

        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/missing")
def missing():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, age, last_seen, description, photo FROM missing_people")
    people = cursor.fetchall()
    conn.close()
    return render_template("missing.html", people=people)

@app.route("/add-missing", methods=["GET", "POST"])
def add_missing():
    global df_dataset

    # Make sure user is logged in
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        last_seen = request.form["last_seen"]
        description = request.form["description"]
        photo = request.files["photo"]

        if photo.filename == "":
            return "No file selected"

        # Make filename unique
        import uuid
        filename = str(uuid.uuid4()) + "_" + secure_filename(photo.filename)

        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        photo.save(upload_path)

        # Encode face
        new_encoding = encode_face(upload_path)
        if new_encoding is None:
            return "No face detected in uploaded image!"

        # Check if person already exists
        existing_person = find_existing_person(new_encoding, name)
        if existing_person is not None:
            return f"Person already exists: {existing_person['name']}, Address: {existing_person['address']}"

        # Add to dataset.csv
        new_row = {
            "name": name,
            "address": "N/A",
            "image_path": upload_path,
            "encoding": str(new_encoding.tolist())
        }

        df_dataset = pd.concat([df_dataset, pd.DataFrame([new_row])], ignore_index=True)
        df_dataset.to_csv(DATASET_FILE, index=False)

        # Add to database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO missing_people 
            (name, age, last_seen, description, photo, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, age, last_seen, description, filename, session["user_id"]))

        conn.commit()
        conn.close()

        return redirect("/missing")

    return render_template("add_missing.html")


@app.route("/delete/<int:person_id>", methods=["POST"])
def delete_person(person_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT photo FROM missing_people WHERE id = ?", (person_id,))
    result = cursor.fetchone()
    if result:
        photo_name = result[0]
        photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo_name)
        if os.path.exists(photo_path):
            os.remove(photo_path)
        cursor.execute("DELETE FROM missing_people WHERE id = ?", (person_id,))
        conn.commit()
    conn.close()
    return redirect("/missing")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/helpline")
def helpline():
    return render_template("helpline.html")

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username, gmail, phone, address
    FROM users WHERE id = ?
    """, (session["user_id"],))

    user = cursor.fetchone()
    conn.close()

    return render_template("profile.html", user=user)

@app.route("/logout")
def logout():
    session.clear()   # removes user_id and username
    return redirect("/login")




@app.route("/person/<int:person_id>")
def person_details(person_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get missing person details
    cursor.execute("""
    SELECT name, age, last_seen, description, photo, uploaded_by
    FROM missing_people WHERE id = ?
    """, (person_id,))
    person = cursor.fetchone()

    # Get uploader details
    cursor.execute("""
    SELECT username, gmail, phone
    FROM users WHERE id = ?
    """, (person[5],))
    uploader = cursor.fetchone()

    conn.close()

    return render_template(
        "person_details.html",
        person=person,
        uploader=uploader
    )


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
