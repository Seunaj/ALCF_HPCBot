import json

# Define the query categories
categories = [
    'Job Submission', 'Job Scheduling and Queuing',
    'File Transfer and Storage', 'Job Scripting', 'Job Optimization', 'Software Installation',
    'Software Usage', 'Compilation and Linking', 'Resource Allocation and Management',
    'Troubleshooting Common Issues', 'Code Optimization and Performance Tuning',
    'Specialized Hardware Utilization', 'Parallel Programming and Debugging',
    'Software Environment Configuration', 'Data Analysis and Visualization',
    'System Architecture and Configuration', 'Data Management and Archiving',
    'System Monitoring and Logging'
]

# Load the JSON dataset
with open('all_aurora_tickets_LLM_GRADED.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Filter data to include only items where the category is in the categories list
filtered_data = [item for item in data if item['category'] in categories]

# Sort the filtered dataset based on the "grade" in descending order
sorted_data = sorted(filtered_data, key=lambda x: int(x['grade']), reverse=True)

# Assign new ranks to the "id" field
for rank, item in enumerate(sorted_data, start=1):
    item['id'] = rank

# Extract the top 100 samples
top_samples = sorted_data[:100]

# Save the top samples to a new JSON file
with open('top100_aurora_tickets_LLM_GRADED.json', 'w', encoding='utf-8') as f:
    json.dump(top_samples, f, ensure_ascii=False, indent=4)

print("Top 100 filtered and ranked samples have been saved to 'top100_aurora_tickets_LLM_GRADED.json'")