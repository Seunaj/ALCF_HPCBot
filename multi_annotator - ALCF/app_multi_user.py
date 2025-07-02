from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os, uuid
app = Flask(__name__)
app.secret_key = "super-secret-key"  # CHANGE this in production

required_directory = os.path.dirname(os.path.abspath(__file__))
questions_file_path = os.path.join(required_directory, "all_data.json")
annotations_file_path = os.path.join(required_directory, "annotations.json")

if not os.path.exists(annotations_file_path):
    with open(annotations_file_path, 'w') as f:
        json.dump({}, f)

with open(questions_file_path) as f:
    QUESTIONS = json.load(f)

# Helper: get user ID
def get_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return session["user_id"]

@app.route('/')
def home():
    get_user_id()  # Ensure session exists
    return redirect(url_for('question', qid=1))

@app.route('/question/<int:qid>')
def question(qid):
    if qid < 1 or qid > len(QUESTIONS):
        return redirect(url_for('home'))

    user_id = get_user_id()
    with open(annotations_file_path) as f:
        all_data = json.load(f)
    user_data = all_data.get(user_id, {})

    current = QUESTIONS[qid - 1]
    saved_answer = user_data.get(str(current["id"]), None)
    answered_count = len(user_data)

    return render_template("question.html",
                           question=current,
                           total=len(QUESTIONS),
                           current_index=qid,
                           selected=saved_answer,
                           progress=answered_count)

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    qid = str(data["id"])
    answer = data["answer"]
    user_id = get_user_id()

    with open(annotations_file_path, 'r+') as f:
        all_data = json.load(f)
        if user_id not in all_data:
            all_data[user_id] = {}
        all_data[user_id][qid] = answer
        f.seek(0)
        json.dump(all_data, f, indent=2)
        f.truncate()

    return jsonify({"status": "saved"})

@app.route('/thank-you')
def thank_you():
    return render_template("thank_you.html")

if __name__ == '__main__':
    app.run(debug=True)