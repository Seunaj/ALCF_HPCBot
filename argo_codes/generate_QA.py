import requests
import json
import os
import glob
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, SystemMessage

# API endpoint to POST
url = "https://apps-dev.inside.anl.gov/argoapi/api/v1/resource/chat/"

# 3. Set the parent folder path
parent_folder = "../user-guides-main"

# Recursively find all .md files in subdirectories
md_file_paths = glob.glob(os.path.join(parent_folder, "**", "*.md"), recursive=True)
print(f"Total ALCF document files found: {len(md_file_paths)}")

# Load all markdown files
all_docs = []

for path in md_file_paths:
    normalized_path = path.replace("\\", "/")
    url_path = normalized_path.removeprefix('user-guides-main/')
    full_url = 'https://github.com/argonne-lcf/user-guides/tree/main/' + url_path

    try:
        loader = TextLoader(normalized_path)
        data = loader.load()
        for doc in data:
            # Add metadata to each document indicating its source
            doc.metadata = {"source": full_url}
            all_docs.append(doc)
            # all_docs += data
        print(f"[✓] Loaded {normalized_path}")
    except Exception as e:
        print(f"[✗] Failed to load {normalized_path}: {e}")

for doc in all_docs:
    doc.page_content = " ".join(doc.page_content.split())  # remove white space

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = text_splitter.split_documents(all_docs)

query = (
        "Here are some relevant documents to generate a dataset for a question answering task: "
        + "\n\nRelevant Documents:\n"
        + "\n\n".join(docs[0].page_content)
        + "\n\nHere are the requirements:"
        + "\n\n1. Try not to repeat the verb for each question to maximize diversity."
        + "\n\n2. Try not to repeat the verb for each answer to maximize diversity."
        + "\n\n3. The questions can be asked under many conditions."
        + "\n\n4. Do not generate the same or similar questions as generated before."
        + "\n\n Now, please generate 20 unique question and answer pairs following the above requirements."
        + "\n\n Dataset should be in a dictionary format containing only 'question' and 'answer'. Do NOT add anything else."
    )

# Define the messages for the model
messages = [
    SystemMessage(content="You are a helpful assistant that generates human-like questions and answers."),
    HumanMessage(content=query),
]

# Data to be sent as a POST in JSON format
data = {
    "user": "seuntol",
    "model": "gpt4o",
    "system": "You are a large language model with the name Argo.",
    "prompt": [query],
    "stop": [],
    "temperature": 0.1,
    "top_p": 0.9,
    # "max_tokens": 1000,
    # "max_completion_tokens": 1000
}

# Convert the dict to JSON
payload = json.dumps(data)

# Add a header stating that the content type is JSON
headers = {"Content-Type": "application/json"}

# Send POST request
response = requests.post(url, data=payload, headers=headers)

# Receive the response data
print("Status Code:", response.status_code)
print("JSON Response ", response.json()['response'])