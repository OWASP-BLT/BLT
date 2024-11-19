import markdown
from bs4 import BeautifulSoup
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")


def ai_summary(text):
    """Generate an AI-driven summary using OpenAI's GPT."""
    try:
        # Generate summary using OpenAI's GPT-3 model
        response = openai.Completion.create(
            model="text-davinci-003",  # Or any available GPT model
            prompt=f"Generate a brief summary of the following text, focusing on key aspects such as purpose, features, technologies used, and current status:\n\n{text}",
            max_tokens=150,
            temperature=0.5,
        )

        summary = response.choices[0].text.strip()
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"


def markdown_to_text_and_summary(markdown_content):
    """Convert Markdown to plain text and generate an AI-driven summary."""
    # Convert Markdown content to HTML
    html_content = markdown.markdown(markdown_content)

    # Extract text from HTML
    text_content = BeautifulSoup(html_content, "html.parser").get_text()

    # Generate AI summary of the text
    summary = ai_summary(text_content)

    return summary
