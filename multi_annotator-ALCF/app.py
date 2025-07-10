from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os

app = Flask(__name__)
required_directory = os.path.dirname(os.path.abspath(__file__))
questions_file_path = os.path.join(required_directory, "all_data.json")
annotations_file_path = os.path.join(required_directory, "annotations.json")

# Ensure annotations file exists
if not os.path.exists(annotations_file_path):
    with open(annotations_file_path, 'w') as f:
        json.dump({}, f)

with open(questions_file_path) as f:
    QUESTIONS = json.load(f)

@app.route('/')
def home():
    return redirect(url_for('question', qid=1))

@app.route('/question/<int:qid>')
def question(qid):
    if qid < 1 or qid > len(QUESTIONS):
        return redirect(url_for('home'))

    with open(annotations_file_path) as f:
        annotations = json.load(f)

    current = QUESTIONS[qid - 1]
    saved_answer = annotations.get(str(current["id"]), None)
    answered_count = len(annotations)

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

    with open(annotations_file_path, 'r+') as f:
        annotations = json.load(f)
        annotations[qid] = answer
        f.seek(0)
        json.dump(annotations, f, indent=2)
        f.truncate()

    return jsonify({"status": "saved"})

@app.route('/thank-you')
def thank_you():
    return render_template("thank_you.html")

if __name__ == '__main__':
    app.run(debug=True)