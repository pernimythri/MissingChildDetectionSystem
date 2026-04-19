from flask import Flask, render_template, request, redirect, session
import os
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
import cv2
import numpy as np
import uuid

app = Flask(__name__)
app.secret_key = "my_secret_key"

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        gmail TEXT UNIQUE,
        password TEXT,
        phone TEXT,
        address TEXT
    )
    """)

    # missing people table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS missing_people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age TEXT,
        last_seen TEXT,
        description TEXT,
        photo TEXT,
        uploaded_by INTEGER
    )
    """)

    conn.commit()
    conn.close()


# create tables automatically
init_db()
# ---------- CONFIG ----------
UPLOAD_FOLDER = "static/uploads"
DATASET_FOLDER = "missing_people_dataset"
DATASET_FILE = os.path.join(DATASET_FOLDER, "dataset.csv")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATASET_FOLDER, exist_ok=True)

# Load dataset
if os.path.exists(DATASET_FILE) and os.path.getsize(DATASET_FILE) > 0:
    try:
        df_dataset = pd.read_csv(DATASET_FILE)
    except:
        df_dataset = pd.DataFrame(columns=["name","address","image_path","encoding"])
else:
    df_dataset = pd.DataFrame(columns=["name","address","image_path","encoding"])

# Load face detector
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# ---------- FACE FUNCTIONS ----------
def encode_face(image_path):
    if not os.path.exists(image_path):
        return None

    img = cv2.imread(image_path)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return None

    x, y, w, h = faces[0]
    face_crop = cv2.resize(img[y:y+h, x:x+w], (128, 128))
    encoding = face_crop.flatten() / 255.0

    return encoding


def find_existing_person(new_encoding, new_name, threshold=0.6):
    global df_dataset

    for _, row in df_dataset.iterrows():
        try:
            existing_encoding = np.array(eval(row["encoding"]))
            distance = np.linalg.norm(existing_encoding - new_encoding)

            if distance < threshold and \
               new_name.lower() == row["name"].lower():
                return row
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


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        gmail = request.form.get("gmail")
        password = request.form.get("password")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, username FROM users
        WHERE gmail = ? AND password = ?
        """, (gmail, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/dashboard")
        else:
            return "Invalid email or password"

    return render_template("login.html")


# ---------- REGISTER ----------
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

        # check if gmail already exists
        cursor.execute("SELECT * FROM users WHERE gmail = ?", (gmail,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return "User already exists. Please login."

        cursor.execute("""
        INSERT INTO users (username, gmail, password, phone, address)
        VALUES (?, ?, ?, ?, ?)
        """, (username, gmail, password, phone, address))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html")


# ---------- SHOW MISSING ----------
@app.route("/missing")
def missing():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, age, last_seen, description, photo
    FROM missing_people
    """)

    people = cursor.fetchall()
    conn.close()

    return render_template("missing.html", people=people)


# ---------- ADD MISSING ----------
@app.route("/add-missing", methods=["GET", "POST"])
def add_missing():
    global df_dataset

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

        filename = str(uuid.uuid4()) + "_" + secure_filename(photo.filename)
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        photo.save(upload_path)

        # encode face
        new_encoding = encode_face(upload_path)
        if new_encoding is None:
            return "No face detected!"

        # check duplicate
        existing = find_existing_person(new_encoding, name)
        if existing is not None:
            return f"Person already exists: {existing['name']}"

        # save dataset
        new_row = {
            "name": name,
            "address": "N/A",
            "image_path": upload_path,
            "encoding": str(new_encoding.tolist())
        }

        df_dataset = pd.concat(
            [df_dataset, pd.DataFrame([new_row])],
            ignore_index=True
        )

        df_dataset.to_csv(DATASET_FILE, index=False)

        # save DB
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO missing_people
        (name, age, last_seen, description, photo, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            age,
            last_seen,
            description,
            filename,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect("/missing")

    return render_template("add_missing.html")


# ---------- DELETE ----------
@app.route("/delete/<int:person_id>", methods=["POST"])
def delete_person(person_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT photo FROM missing_people WHERE id=?",
        (person_id,)
    )

    result = cursor.fetchone()

    if result:
        photo_name = result[0]
        photo_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            photo_name
        )

        if os.path.exists(photo_path):
            os.remove(photo_path)

        cursor.execute(
            "DELETE FROM missing_people WHERE id=?",
            (person_id,)
        )

        conn.commit()

    conn.close()
    return redirect("/missing")


# ---------- PROFILE ----------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username, gmail, phone, address
    FROM users WHERE id=?
    """, (session["user_id"],))

    user = cursor.fetchone()
    conn.close()

    return render_template("profile.html", user=user)


# ---------- PERSON DETAILS ----------
@app.route("/person/<int:person_id>")
def person_details(person_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, age, last_seen, description, photo, uploaded_by
    FROM missing_people WHERE id=?
    """, (person_id,))

    person = cursor.fetchone()

    if not person:
        conn.close()
        return "Person not found"

    cursor.execute("""
    SELECT username, gmail, phone
    FROM users WHERE id=?
    """, (person[5],))

    uploader = cursor.fetchone()
    conn.close()

    return render_template(
        "person_details.html",
        person=person,
        uploader=uploader
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/helpline")
def helpline():
    return render_template("helpline.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
