from website.aibot.utils import chunk_yaml_file, cvt_yml_to_json, generate_yml_string

file = "coderabbit.yaml"

with open(file, "r", encoding="utf-8") as f:
    content = f.read()

yml_json = cvt_yml_to_json(content, file)

yml_string = generate_yml_string(yml_json, file)

for line in yml_string:
    main_key, value = line.split(":", 1)
    keys = main_key.split(".")
    # print(main_key, value)

chunks = chunk_yaml_file(content, file)

for chunk in chunks:
    print(chunk)
    print("-" * 40)
    print()
