import json

from website.aibot.chunk_utils import chunk_file, postprocess_chunks

fpath = ".lgtm.yml"
with open(fpath, "r", encoding="utf-8") as f:
    content = f.read()


chunks = chunk_file(content, fpath)

chunks = postprocess_chunks(chunks)

with open("ind-chunks.txt", "w", encoding="utf-8") as f:
    for chunk in chunks:
        f.write(json.dumps(chunk, ensure_ascii=False, indent=2))
        f.write("\n")
