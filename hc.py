import html2text
from bs4 import BeautifulSoup

# Read HTML content
input_path = "website/templates/bacon.html"
with open(input_path, "r", encoding="utf-8") as f:
    html_content = f.read()

markdown_output = html2text.html2text(html_content)
with open("output_html2text.md", "w", encoding="utf-8") as f:
    f.write(markdown_output)

soup = BeautifulSoup(html_content, "html.parser")
text_output = soup.get_text(separator="\n")  # preserves line breaks
with open("output_beautifulsoup.md", "w", encoding="utf-8") as f:
    f.write(text_output)
