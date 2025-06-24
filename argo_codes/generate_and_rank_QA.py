import requests
import json
import os
import glob
from langchain_community.document_loaders import TextLoader

# API endpoint to POST
url = "https://apps-dev.inside.anl.gov/argoapi/api/v1/resource/chat/"

# Add a header stating that the content type is JSON
headers = {"Content-Type": "application/json"}

# Set the parent folder path
parent_folder = "../user-guides-main"

# Recursively find all .md files in subdirectories
md_file_paths = glob.glob(os.path.join(parent_folder, "**", "*.md"), recursive=True)
print(f"Total ALCF document files found: {len(md_file_paths)}")

# Open the query categories file in read mode
with open('../query_categories.txt', 'r') as file:
    # Read all lines from the file
    lines = file.readlines()
categories = [line.strip() for line in lines]

# Load all markdown files
count = 1
for path in md_file_paths:
    normalized_path = path.replace("\\", "/")
    url_path = normalized_path.removeprefix('../user-guides-main/')
    full_url = 'https://github.com/argonne-lcf/user-guides/tree/main/' + url_path

    try:
        loader = TextLoader(normalized_path)
        data = loader.load()
        for doc in data:
            # print(f"[✓] Loaded {normalized_path}")
            # Add metadata to each document indicating its source
            # doc.metadata = {"source": full_url}
            # print(len(doc.page_content))
            doc.page_content = " ".join(doc.page_content.split())  # remove white space
            # print(len(doc.page_content))
            # text_splitter = RecursiveCharacterTextSplitter(chunk_size=len(doc.page_content), chunk_overlap=0)
            # doc = text_splitter.split_documents(doc)

            # 4. Generate QA pairs
            print('Document ', count, '/', len(md_file_paths))
            # sample QA pairs from a single doc (i.e., chunk)
            query = (
                    "Here are some relevant documents to generate a dataset for a question answering task: "
                    + "\n\nRelevant Documents:\n"
                    + doc.page_content
                    + "\n\nHere are the requirements:"
                    + "\n\n1. Try not to repeat the verb for each question to maximize diversity."
                    + "\n\n2. Try not to repeat the verb for each answer to maximize diversity."
                    + "\n\n3. The questions can be asked under many conditions."
                    + "\n\n4. Do not generate the same or similar questions as generated before."
                    + "\n\nNow, please generate 10 unique question and answer pairs following the above requirements."
                    + "\n\nAlso, identify which category each question belongs to from the following list:"
                    + "\n\n" + "\n\n".join(categories)
                    + "\n\nRequirement: The dataset should be in a dictionary format containing only 'question', 'answer' and 'category'. Do NOT add anything else."
            )

            # Data to be sent as a POST in JSON format
            data_request = {
                "user": "seuntol",
                "model": "gpt4o",
                "system": "You are a helpful assistant that generates human-like questions and answers.",
                "prompt": [query],
                "stop": [],
                "temperature": 0.1,
                "top_p": 0.9,
                # "max_tokens": 1000,
                # "max_completion_tokens": 1000
            }

            # Convert the dict to JSON
            payload = json.dumps(data_request)

            # Send POST request
            response = requests.post(url, data=payload, headers=headers)

            # Receive the response data
            # print("Status Code:", response.status_code)
            # print("JSON Response ", response.json()['response'])
            qa_batch = response.json()['response']

            # Filter the output to get correct JSON content
            lines = qa_batch.splitlines()
            filtered_lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned_json_content = "\n".join(filtered_lines) # Join the filtered lines back into a single string
            json_data = json.loads(cleaned_json_content) # Convert string to JSON object

            # Evaluate the difficulty level of each question using GPT-4o
            for item in json_data:
                # Add the source url for each question
                item['source'] = full_url

                question = item['question']

                # Combine the query and the relevant document contents
                combined_input = (
                        "Here are some documents that might help you assess the query's difficulty: "
                        + question
                        + "\n\nRelated Documents:\n"
                        + "\n\n".join(doc.page_content)
                        + "\n\nPlease, assign a difficulty level to the query. The difficulty levels are defined as follows:"
                        + "\n\nL1: The query asks about explicit facts directly present in the Related Documents data without requiring any additional reasoning."
                        + "\n\nL2: The query asks about implicit facts, which are not immediately obvious in the Related Document and may require some level of common sense reasoning or basic logical deductions. The necessary information might be spread across multiple segments of the Related Document or require simple inferencing."
                        + "\n\nL3: This query demands not only a grasp of the factual content but also the capacity to comprehend and apply domain-specific rationales that are integral to the Related Document’s context."
                        + "\n\nL4: This query delves into the more challenging realm where the rationales are not explicitly in the Related Documents but must be inferred from patterns and outcomes observed in Related Document."
                )

                # Data to be sent as a POST in JSON format
                data_request = {
                    "user": "seuntol",
                    "model": "gpt4o",
                    "system": "You are a helpful assistant. Your task is to evaluate the difficulty level of a question.",
                    "prompt": [combined_input],
                    "stop": [],
                    "temperature": 0.1,
                    "top_p": 0.9,
                    # "max_tokens": 1000,
                    # "max_completion_tokens": 1000
                }

                # Convert the dict to JSON
                payload = json.dumps(data_request)

                # Send POST request
                response = requests.post(url, data=payload, headers=headers)

                # Receive the response data
                # print("Status Code:", response.status_code)
                # print("JSON Response ", response.json()['response'])
                result = response.json()['response']

                if "L1" in result:
                    item['gpt4o'] = "L1"
                elif "L2" in result:
                    item['gpt4o'] = "L2"
                elif "L3" in result:
                    item['gpt4o'] = "L3"
                elif "L4" in result:
                    item['gpt4o'] = "L4"
                else:
                    item['gpt4o'] = "Unknown"

            # Save data as a .json file
            # QAR stands for Question Answer Ranking
            with open('../QAR_dataset/QA_batch'+str(count)+'.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
        print(f"[✓] Loaded {normalized_path}")
        count += 1
    except Exception as e:
        print(f"[✗] Failed to load {normalized_path}: {e}")