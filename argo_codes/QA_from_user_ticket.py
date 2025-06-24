import requests
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict

# API endpoint to POST
url = "https://apps-dev.inside.anl.gov/argoapi/api/v1/resource/chat/"

# Add a header stating that the content type is JSON
headers = {"Content-Type": "application/json"}

# Open the query categories file in read mode
with open('../query_categories.txt', 'r') as file:
    # Read all lines from the file
    lines = file.readlines()
categories = [line.strip() for line in lines]

machine_type = "polaris"

# Dictionary to store RITM numbers and their corresponding json_data
ritm_to_json_data = defaultdict(list)

# Open and parse the JSONL file
with open('../clean_alcf_support.jsonl', 'r', encoding='utf-8') as file:
    lines = file.readlines()

    for line_no, line in enumerate(lines):
        json_data = json.loads(line)  # Parse the JSON line

        date_time = json_data.get('date', '')
        # Parse the date string into a datetime object
        date_obj = datetime.strptime(date_time, '%Y-%m-%dT%H:%M:%S')  # Adjust format if needed

        # Check if the year is before 2023
        if date_obj.year < 2023:
            continue

        subject_content = json_data.get('subject', '')
        # Use regex to extract the RITM number
        match = re.search(r'RITM\d+', subject_content)
        if match:
            ritm_number = match.group()  # Extract the RITM number
            ritm_to_json_data[ritm_number].append(json_data)  # Map RITM to the json_data

# Now you have a dictionary where each RITM has all related json_data
completed_ritm = [] # just to keep track of the number of tickets processed so far if running STOPS.
for ritm_number, data_list in ritm_to_json_data.items():
    body_list = []
    for data in data_list:
        # Assuming the HTML is stored in a field named 'html_content'
        html_content = data.get('body', '')

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract only the body of the HTML and strip off tags
        body_content = soup.body.get_text(strip=True)
        body_list.append(body_content)

    if len(body_list) <= 1:
        joined_body_content = body_list[0]
    else:
        # Join the strings in body_list with a newline as the separator
        joined_body_content = "\n".join(body_list)

    if machine_type not in joined_body_content.lower():
        continue

    # sample QA pairs from an entire user-support ticket
    query = (
            "Read the following user-support ticket and check if there are question-answer pairs: "
            + "\n\nUser-support ticket:\n"
            + joined_body_content
            + "\n\nGenerate the user questions and support staff answers that are related to " + machine_type + ". Let it be clear what the question is about and don't include name(s) in the answer."
            + "\n\nAlso, identify which category each question belongs to from the following list:"
            + "\n\n" + "\n\n".join(categories)
            + "\n\nIt's okay if you can't find any meaningful question-answer pairs."
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

    try:
        # Filter the output to get correct JSON content
        lines = qa_batch.splitlines()
        filtered_lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned_json_content = "\n".join(filtered_lines)  # Join the filtered lines back into a single string
        json_data = json.loads(cleaned_json_content)  # Convert string to JSON object

        # Evaluate the difficulty level of each question using GPT-4o
        for item in json_data:
            item['ticket_ID'] = ritm_number # Add the RITM number to each question-answer pair

            question = item['question']
            # Combine the query and the relevant document contents
            combined_input = (
                    "Here are some documents that might help you assess the query's difficulty: "
                    + question
                    + "\n\nRelated Documents:\n"
                    + joined_body_content
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

        if not json_data:  # checks if the json_data is empty
            continue

        # Save data as a .json file
        # QAR stands for Question Answer Ranking
        with open('../support_ticket_dataset/polaris/ticket_' + str(ritm_number) + '.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

        completed_ritm.append(ritm_number)
        print("--- Done: Ticket", ritm_number, "*****", len(completed_ritm),'of', len(ritm_to_json_data) )

        # Save the list to a text file
        with open("completed_ritm.txt", "w") as file:
            for item in completed_ritm:
                file.write(f"{item}\n")  # Write each list item on a new line

    except Exception as e:
        print(f"[✗] Failed to load json data for Ticket {ritm_number}: {e}")