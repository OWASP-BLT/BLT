import ast
import difflib
import os
import re

from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Initialize CodeBERT model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
model = AutoModelForSequenceClassification.from_pretrained("microsoft/codebert-base")


def process_similarity_analysis(repo1_path, repo2_path, use_codebert=False):
    """
    Process the similarity analysis between two repositories.
    :param repo1_path: Path to the first repository
    :param repo2_path: Path to the second repository
    :return: Similarity score and matching details
    """
    # Dummy data for now, will be replaced by actual parsing logic
    similarity_score = 0
    matching_details = {
        "functions": [],
        "models": [],
    }

    # Step 1: Compare function and model names using difflib or Levenshtein
    functions1 = extract_function_names(repo1_path)
    functions2 = extract_function_names(repo2_path)

    # Compare function names
    for f1 in functions1:
        for f2 in functions2:
            if use_codebert:
                similarity = analyze_code_similarity_with_codebert(f1, f2)
            else:
                similarity = difflib.SequenceMatcher(None, f1, f2).ratio() * 100

            if similarity > 80:  # You can set the threshold here
                matching_details["functions"].append(
                    {
                        "name1": f1,
                        "name2": f2,
                        "similarity": round(similarity, 2),
                    }
                )

    # Step 2: Compare method signatures
    method_signatures1 = extract_method_signatures(repo1_path)
    method_signatures2 = extract_method_signatures(repo2_path)

    # Compare method signatures
    for m1 in method_signatures1:
        for m2 in method_signatures2:
            if use_codebert:
                signature1 = f"{m1['name']}({', '.join(m1['args'])})"
                signature2 = f"{m2['name']}({', '.join(m2['args'])})"
                similarity = analyze_code_similarity_with_codebert(signature1, signature2)
            else:
                similarity = difflib.SequenceMatcher(None, str(m1), str(m2)).ratio() * 100

            if similarity > 80:  # You can set the threshold here
                matching_details["functions"].append(
                    {
                        "method1": str(m1),
                        "method2": str(m2),
                        "similarity": round(similarity, 2),
                    }
                )

    # Step 3: Compare Django models
    models1 = extract_django_models(repo1_path)
    models2 = extract_django_models(repo2_path)

    print(models1)
    print(models2)
    # Compare models and fields
    for model1 in models1:
        for model2 in models2:
            if use_codebert:
                model_similarity = analyze_code_similarity_with_codebert(
                    model1["name"], model2["name"]
                )
            else:
                model_similarity = (
                    difflib.SequenceMatcher(None, model1["name"], model2["name"]).ratio() * 100
                )

            if model_similarity > 80:  # You can set the threshold here
                model_fields_similarity = compare_model_fields(model1, model2)
                matching_details["models"].append(
                    {
                        "name1": model1["name"],
                        "name2": model2["name"],
                        "similarity": round(model_similarity, 2),
                        "field_comparison": model_fields_similarity,
                    }
                )

    return similarity_score, matching_details


def analyze_code_similarity_with_codebert(code1, code2):
    """
    Analyze the semantic similarity between two code snippets using CodeBERT.
    :param code1: First code snippet
    :param code2: Second code snippet
    :return: Similarity score (0-100)
    """
    inputs = tokenizer(
        f"{code1} [SEP] {code2}", return_tensors="pt", truncation=True, max_length=512
    )
    outputs = model(**inputs)
    logits = outputs.logits
    similarity_score = logits.softmax(dim=1)[0][1].item() * 100
    return round(similarity_score, 2)


def extract_function_names(repo_path):
    """
    Extract function names from Python files in the given repo.
    :param repo_path: Path to the repository
    :return: List of function names
    """
    function_names = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    tree = ast.parse(f.read(), filename=file)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            function_names.append(node.name)
    return function_names


def extract_method_signatures(repo_path):
    """
    Extract method signatures (name, parameters) from Python files.
    :param repo_path: Path to the repository
    :return: List of method signatures
    """
    method_signatures = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    tree = ast.parse(f.read(), filename=file)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            signature = {
                                "name": node.name,
                                "args": [arg.arg for arg in node.args.args],
                                "defaults": [ast.dump(default) for default in node.args.defaults],
                            }
                            method_signatures.append(signature)
    return method_signatures


def extract_django_models(repo_path):
    """
    Extract Django model names and fields from the given repository.
    :param repo_path: Path to the repository
    :return: List of models with their fields
    """
    models = []

    # Walk through the repository directory
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):  # Only process Python files
                file_path = os.path.join(root, file)

                # Open the file and read its contents
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    model_name = None
                    fields = []
                    inside_model = False  # To check if we are inside a model definition

                    for line in lines:
                        line = line.strip()

                        # Look for class definition that inherits from models.Model
                        if line.startswith("class ") and "models.Model" in line:
                            model_name = line.split("(")[0].replace("class ", "").strip()
                            inside_model = True
                            fields = []  # Reset fields when a new model starts

                        # Look for field definitions inside a model
                        if inside_model:
                            # Match field definitions like: name = models.CharField(max_length=...)
                            match = re.match(r"^\s*(\w+)\s*=\s*models\.(\w+)", line)
                            if match:
                                field_name = match.group(1)
                                field_type = match.group(2)
                                fields.append({"field_name": field_name, "field_type": field_type})

                            # Match other field types like ForeignKey, ManyToManyField, etc.
                            match_complex = re.match(
                                r"^\s*(\w+)\s*=\s*models\.(ForeignKey|ManyToManyField|OneToOneField)\((.*)\)",
                                line,
                            )
                            if match_complex:
                                field_name = match_complex.group(1)
                                field_type = match_complex.group(2)
                                field_params = match_complex.group(3).strip()
                                fields.append(
                                    {
                                        "field_name": field_name,
                                        "field_type": field_type,
                                        "parameters": field_params,
                                    }
                                )

                            # Check for the end of the class definition
                            if line.startswith("class ") and model_name:
                                models.append({"name": model_name, "fields": fields})
                                inside_model = False  # Reset for next class

                    # Add the last model if the file ends without another class
                    if model_name:
                        models.append({"name": model_name, "fields": fields})

    return models


def compare_model_fields(model1, model2):
    """
    Compare fields of two Django models.
    :param model1: First model's field details
    :param model2: Second model's field details
    :return: Field comparison details
    """
    fields1 = set(model1["fields"])
    fields2 = set(model2["fields"])
    common_fields = fields1.intersection(fields2)
    total_fields = len(fields1) + len(fields2) - len(common_fields)
    if total_fields == 0:
        field_similarity = 0.0
    else:
        field_similarity = len(common_fields) / float(total_fields) * 100
    return {"common_fields": list(common_fields), "field_similarity": round(field_similarity, 2)}
