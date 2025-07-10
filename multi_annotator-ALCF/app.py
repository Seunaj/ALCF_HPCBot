from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os
import bcrypt  # for encrypting (hashing) passwords

app = Flask(__name__)
app.secret_key = "super-secret-key"  # CHANGE this in production

required_directory = os.path.dirname(os.path.abspath(__file__))

# define the rating scale for mapping between the numerical and text values
annotations = [
            "Invalid: QA should be discarded",
            "Poor: Likely unusable; requires checking the ticket to modify",
            "Fair: Minor issues in Q or A or both; needs to be fixed",
            "Good: Q is great, but A is not correct",
            "Excellent: Both Q and A are suitable for training data"
        ]

# Define a mapping for qa_type to file paths
QA_TYPE_CONFIG = {
    "alcf_user_guide": {
        "questions_file": os.path.join(required_directory, "all_alcf_user_guide.json"),
        "annotations_file": os.path.join(required_directory, "alcf_user_guide_annotations.json"),
    },
    "aurora_support_ticket": {
        "questions_file": os.path.join(required_directory, "all_aurora_tickets.json"),
        "annotations_file": os.path.join(required_directory, "aurora_annotations.json"),
    },
    "polaris_support_ticket": {
        "questions_file": os.path.join(required_directory, "all_polaris_tickets.json"),
        "annotations_file": os.path.join(required_directory, "polaris_annotations.json"),
    },
}

# Initialize files if they do not exist
for config in QA_TYPE_CONFIG.values():
    if not os.path.exists(config["annotations_file"]):
        with open(config["annotations_file"], 'w') as f:
            json.dump({}, f)

USERS_FILE_PATH = os.path.join(required_directory, "users.json")

# Load or create USERS database
if not os.path.exists(USERS_FILE_PATH):
    with open(USERS_FILE_PATH, 'w') as f:
        json.dump({}, f)

with open(USERS_FILE_PATH) as f:
    USERS = json.load(f)


# Save users to the file
def save_users():
    with open(USERS_FILE_PATH, 'w') as f:
        json.dump(USERS, f)


# Helper: get current logged-in user's username
def get_user_id():
    return session.get("username", None)


# Helper: get qa_type for the logged-in user
def get_qa_type():
    return session.get("qa_type", None)


# Load questions for a specific qa_type
def load_questions(qa_type):
    questions_file = QA_TYPE_CONFIG[qa_type]["questions_file"]
    with open(questions_file, encoding="utf-8") as f:
        return json.load(f)


@app.route('/')
def home():
    if not get_user_id():
        return redirect(url_for('login'))

    qa_type = get_qa_type()
    if not qa_type or qa_type not in QA_TYPE_CONFIG:
        return "Invalid qa_type. Please log in again.", 400

    # Redirect to the questions display page with the starting ID
    return redirect(url_for('question', qid=1))


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        qa_type = request.form["qa_type"]

        if qa_type not in QA_TYPE_CONFIG:  # Validate qa_type
            return render_template("login.html", error="Invalid qa_type selected.")

        # Check if the username exists in the USERS database
        if username in USERS:
            # Verify the hashed password
            hashed_password = USERS[username].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                session["username"] = username
                session["qa_type"] = qa_type
                return redirect(url_for('home'))

        # If login fails
        return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")


@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check if the username already exists
        if username in USERS:
            return render_template("signup.html", error="Username already exists. Please choose another.")

        # Check if passwords match
        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match. Please try again.")

        # Hash the user's password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Add the new user to the USERS database
        USERS[username] = hashed_password.decode('utf-8')  # Save the hashed password
        save_users()  # Save the updated users database
        return redirect(url_for('login'))

    return render_template("signup.html")


@app.route('/logout')
def logout():
    session.pop("username", None)  # Remove the user from the session
    session.pop("qa_type", None)   # Remove the qa_type from the session
    return redirect(url_for('login'))


@app.route('/question/<int:qid>')
def question(qid):
    if not get_user_id():
        return redirect(url_for('login'))

    qa_type = get_qa_type()
    if not qa_type or qa_type not in QA_TYPE_CONFIG:
        return "Invalid qa_type. Please log in again.", 400

    questions = load_questions(qa_type)
    if qid < 1 or qid > len(questions):
        return redirect(url_for('home'))

    annotations_file = QA_TYPE_CONFIG[qa_type]["annotations_file"]
    user_id = get_user_id()
    with open(annotations_file) as f:
        all_data = json.load(f)
    user_data = all_data.get(user_id, {})

    current = questions[qid - 1]
    saved_answer = user_data.get(str(current["id"]), None)
    answered_count = len(user_data)

    return render_template(
        f"{qa_type}.html",
        question=current,
        total=len(questions),
        current_index=qid,
        selected=saved_answer,
        progress=answered_count
    )


@app.route('/submit', methods=['POST'])
def submit():
    if not get_user_id():
        return jsonify({"status": "error", "message": "User not logged in"}), 401

    qa_type = get_qa_type()
    if not qa_type or qa_type not in QA_TYPE_CONFIG:
        return jsonify({"status": "error", "message": "Invalid qa_type. Please log in again."}), 400

    data = request.json  # Parse incoming data
    print("Received payload:", data)
    qid = str(data.get("id"))
    selected_option = data.get("answer")
    feedback = data.get("feedback", "").strip()  # Extract feedback or default to an empty string
    user_id = get_user_id()

    annotations_file = QA_TYPE_CONFIG[qa_type]["annotations_file"]
    with open(annotations_file, 'r+') as f:
        all_data = json.load(f)
        if user_id not in all_data:
            all_data[user_id] = {}

        # Map selected option to numerical value
        try:
            numerical_value = annotations.index(selected_option)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid option selected"}), 400

        # Save user feedback, numerical value, and selected option
        all_data[user_id][qid] = {
            "numerical_value": numerical_value,
            "selected_option": selected_option,
            "feedback": feedback
        }

        f.seek(0)
        json.dump(all_data, f, indent=2)
        f.truncate()

    return jsonify({"status": "success", "message": "Submission saved successfully"})


@app.route('/thank-you')
def thank_you():
    if not get_user_id():
        return redirect(url_for('login'))
    return render_template("thank_you.html")


# if __name__ == '__main__':
#     app.run(debug=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
