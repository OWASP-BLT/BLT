import requests

from website.views.aibot import _process_diff

URL = "https://patch-diff.githubusercontent.com/raw/OWASP-BLT/BLT/pull/4396.diff"
response = requests.get(URL, timeout=5)
diff = response.text

output_filename = "processed_diff_output.txt"
processed_content = _process_diff(diff, "")

try:
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(processed_content)
    print(f"Successfully saved processed diff to {output_filename}")
except IOError as e:
    print(f"Error saving file {output_filename}: {e}")
