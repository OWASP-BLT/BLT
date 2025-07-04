import os

import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat(history=[])

response = chat.send_message(
    """Im conversing with you using model = genai.GenerativeModel("gemini-2.0-flash")
    chat = model.start_chat(history=[])
    Now, if in my backend, How can I ensure to make this conversation continue? How should i use the same chat object? 
    If after this request, you get the next request 2 days later but using the same chat object, will you remember it?
    """
)
print(response.text)
