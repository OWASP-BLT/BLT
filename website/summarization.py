import markdown
from bs4 import BeautifulSoup


def markdown_to_text(markdown_content):
    """Convert the Markdown content to plain text"""
    html_content = markdown.markdown(markdown_content)
    text_content = BeautifulSoup(html_content, "html.parser").get_text()

    return text_content

def summarize_readme(readme_content):
    """Generate a summary using the Hugging Face BART model"""
    from transformers import pipeline

    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    plain_text = markdown_to_text(readme_content)
    summary = summarizer(plain_text, max_length=130, min_length=30, do_sample=False)

    return summary[0]['summary_text']
