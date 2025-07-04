import requests

url = "https://api.github.com/repos/SahilDhillon21/BLT/contents/website/views/aibot.py?ref=aibot"

response = requests.get(url)
print(response.json())
