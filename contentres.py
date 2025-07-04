import requests


def _fetch_file_content(head_ref: str, file_path: str):
    content_url = "https://raw.githubusercontent.com/SahilDhillon21/BLT"
    url = f"{content_url}/{head_ref}/{file_path}"
    response = requests.get(url, timeout=5)
    print(response.text)
    return ""


_fetch_file_content("aibot", "website/views/aibot.py")
