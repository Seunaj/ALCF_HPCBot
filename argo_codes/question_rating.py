import requests
import json
from langchain_community.document_loaders import TextLoader

# API endpoint to POST
url = "https://apps-dev.inside.anl.gov/argoapi/api/v1/resource/chat/"

# Add a header stating that the content type is JSON
headers = {"Content-Type": "application/json"}

# Set the parent folder path
parent_folder = "../user-guides-main/"

total_batches = 258  # number of files in the ./offline_dataset/ folder

model_lists = ['gpto3mini', 'gpt4turbo']

for llm in model_lists:
    for j in range(183,total_batches+1):
        # Open the file and load its content
        with open('../QAR_dataset/QA_batch'+str(j)+'.json', 'r', encoding='utf-8') as f:
            qa_batch = json.load(f)

        for i in range(len(qa_batch)):
            question = qa_batch[i]['question']
            source = qa_batch[i]['source']

            local_source = source.removeprefix('https://github.com/argonne-lcf/user-guides/tree/main/')
            local_source = parent_folder + local_source

            try:
                loader = TextLoader(local_source)
                data = loader.load()
                for doc in data:
                    doc.page_content = " ".join(doc.page_content.split())  # remove white space

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
                        "model": "gpt4turbo",
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
                        qa_batch[i][llm] = "L1"
                    elif "L2" in result:
                        qa_batch[i][llm] = "L2"
                    elif "L3" in result:
                        qa_batch[i][llm] = "L3"
                    elif "L4" in result:
                        qa_batch[i][llm] = "L4"
                    else:
                        qa_batch[i][llm] = "Unknown"
            except Exception as e:
                print(f"[✗] Failed to load {local_source}: {e}")

        # Save the updated file
        with open('../QAR_dataset/QA_batch'+str(j)+'.json', 'w', encoding='utf-8') as f:
            json.dump(qa_batch, f, ensure_ascii=False, indent=4)

        print("--- Batch", j, "Completed for", llm, "---")