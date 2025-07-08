from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os
import bcrypt # for encrypting (hashing) passwords

app = Flask(__name__)
app.secret_key = "super-secret-key"  # CHANGE this in production

required_directory = os.path.dirname(os.path.abspath(__file__))
questions_file_path = os.path.join(required_directory, "all_aurora_tickets.json")
annotations_file_path = os.path.join(required_directory, "aurora_annotations.json")

# define the rating scale for mapping between the numerical and text values
annotations = [
            "Excellent: Both Q and A are suitable for training data",
            "Good: Q is great, but A is not correct",
            "Fair: Minor issues in Q or A or both; needs to be fixed",
            "Poor: Likely unusable; requires checking the ticket to modify",
            "Invalid: QA should be discarded"
        ]

if not os.path.exists(annotations_file_path):
    with open(annotations_file_path, 'w') as f:
        json.dump({}, f)

with open(questions_file_path, encoding='utf-8') as f:
    QUESTIONS = json.load(f)

# Mock user database for simplicity (replace with a persistent store in production)
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


# Helper: get current logged-in user
def get_user_id():
    return session.get("username", None)


@app.route('/')
def home():
    if not get_user_id():
        return redirect(url_for('login'))
    return redirect(url_for('question', qid=1))


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if the username exists in the USERS database
        if username in USERS:
            # Verify the hashed password
            hashed_password = USERS[username].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                session["username"] = username
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
        session["username"] = username  # Log in the user immediately after signup
        return redirect(url_for('home'))

    return render_template("signup.html")


@app.route('/logout')
def logout():
    session.pop("username", None)  # Remove the user from the session
    return redirect(url_for('login'))


@app.route('/question/<int:qid>')
def question(qid):
    if not get_user_id():
        return redirect(url_for('login'))

    if qid < 1 or qid > len(QUESTIONS):
        return redirect(url_for('home'))

    user_id = get_user_id()
    with open(annotations_file_path) as f:
        all_data = json.load(f)
    user_data = all_data.get(user_id, {})

    current = QUESTIONS[qid - 1]
    saved_answer = user_data.get(str(current["id"]), None)

    # mapping from numerical to text values
    if saved_answer == 4:
        saved_answer = annotations[0]
    elif saved_answer == 3:
        saved_answer = annotations[1]
    elif saved_answer == 2:
        saved_answer = annotations[2]
    elif saved_answer == 1:
        saved_answer = annotations[3]
    elif saved_answer == 0:
        saved_answer = annotations[4]

    answered_count = len(user_data)

    return render_template(
        "aurora_question.html",
        question=current,
        total=len(QUESTIONS),
        current_index=qid,
        selected=saved_answer,
        progress=answered_count)


@app.route('/submit', methods=['POST'])
def submit():
    if not get_user_id():
        return jsonify({"status": "error", "message": "User not logged in"}), 401

    data = request.json
    qid = str(data["id"])
    answer = data["answer"]
    user_id = get_user_id()

    with open(annotations_file_path, 'r+') as f:
        all_data = json.load(f)
        if user_id not in all_data:
            all_data[user_id] = {}

        # mapping from text to numerical values
        if answer == annotations[0]:
            all_data[user_id][qid] = 4
        elif answer == annotations[1]:
            all_data[user_id][qid] = 3
        elif answer == annotations[2]:
            all_data[user_id][qid] = 2
        elif answer == annotations[3]:
            all_data[user_id][qid] = 1
        else:
            all_data[user_id][qid] = 0

        f.seek(0)
        json.dump(all_data, f, indent=2)
        f.truncate()

    return jsonify({"status": "saved"})


@app.route('/thank-you')
def thank_you():
    if not get_user_id():
        return redirect(url_for('login'))
    return render_template("thank_you.html")


if __name__ == '__main__':
    app.run(debug=True)