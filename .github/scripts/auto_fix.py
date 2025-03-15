import os

import openai

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Read Issue Body from GitHub
issue_body = os.getenv("ISSUE_BODY", "No issue details provided.")

# AI Prompt to Generate Code Fix
prompt = f"""
Sentry reported an issue:
{issue_body}

Provide a concise fix in Python.
"""

# Get AI-Generated Fix using the new API format
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": "You are an experienced software engineer. Provide a concise and effective bug fix.",
        },
        {"role": "user", "content": prompt},
    ],
)

# Extract the AI-generated fix
fix_code = response.choices[0].message.content

# Write Fix to a File (Example: Modify `app.py`)
with open("app.py", "a") as f:
    f.write("\n# Auto-Fix by AI\n")
    f.write(fix_code + "\n")

print("Fix generated and written to app.py")

