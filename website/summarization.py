import os

import markdown
import openai
from bs4 import BeautifulSoup

openai.api_key = os.getenv("OPENAI_API_KEY")


def ai_summary(text, topics=None):
    """Generate an AI-driven summary using OpenAI's GPT, including GitHub topics."""
    try:
        topics_str = ", ".join(topics) if topics else "No topics provided."
        prompt = f"Generate a brief summary of the following text, focusing on key aspects such as purpose, features, technologies used, and current status. Consider the following GitHub topics to enhance the context: {topics_str}\n\n{text}"
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0.5,
        )
        summary = response.choices[0].text.strip()
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"

