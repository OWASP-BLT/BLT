import ast
import csv
import difflib
import io
import os
import re

import torch
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModel, AutoTokenizer

# Initialize CodeBERT model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
model = AutoModel.from_pretrained("microsoft/codebert-base")


def process_similarity_analysis(repo1_path, repo2_path):
    """
    Process the similarity analysis between two repositories.
    :param repo1_path: Path to the first repository
    :param repo2_path: Path to the second repository
    :return: Similarity score and matching details
    """
    # Dummy data for now, will be replaced by actual parsing logic
    matching_details = {
        "functions": [],
        "models": [],
    }

    # Step 1: Extract function signatures and content
    functions1 = extract_function_signatures_and_content(repo1_path)
    functions2 = extract_function_signatures_and_content(repo2_path)

    # Compare functions
    for func1 in functions1:
        for func2 in functions2:
            print(func1["signature"]["name"], func2["signature"]["name"])
            # Name similarity
            name_similarity_difflib = (
                difflib.SequenceMatcher(
                    None, func1["signature"]["name"], func2["signature"]["name"]
                ).ratio()
                * 100
            )
            name_similarity_codebert = analyze_code_similarity_with_codebert(
                func1["signature"]["name"], func2["signature"]["name"]
            )
            name_similarity = (name_similarity_difflib + name_similarity_codebert) / 2

            # Signature similarity
            signature1 = f"{func1['signature']['name']}({', '.join(func1['signature']['args'])})"
            signature2 = f"{func2['signature']['name']}({', '.join(func2['signature']['args'])})"
            signature_similarity_difflib = (
                difflib.SequenceMatcher(None, signature1, signature2).ratio() * 100
            )
            signature_similarity_codebert = analyze_code_similarity_with_codebert(
                signature1, signature2
            )
            signature_similarity = (
                signature_similarity_difflib + signature_similarity_codebert
            ) / 2

            # Content similarity
            content_similarity = analyze_code_similarity_with_codebert(
                func1["full_text"], func2["full_text"]
            )

            # Aggregate similarity
            overall_similarity = (name_similarity + signature_similarity + content_similarity) / 3
            if overall_similarity > 50:  # You can set the threshold here
                matching_details["functions"].append(
                    {
                        "name1": func1["signature"]["name"],
                        "name2": func2["signature"]["name"],
                        "name_similarity": round(name_similarity, 2),
                        "signature_similarity": round(signature_similarity, 2),
                        "content_similarity": round(content_similarity, 2),
                        "similarity": round(overall_similarity, 2),
                    }
                )

    # Step 2: Compare Django models
    models1 = extract_django_models(repo1_path)
    models2 = extract_django_models(repo2_path)

    # Compare models and fields
    for model1 in models1:
        for model2 in models2:
            model_similarity = (
                difflib.SequenceMatcher(None, model1["name"], model2["name"]).ratio() * 100
            )

            model_fields_similarity = compare_model_fields(model1, model2)
            matching_details["models"].append(
                {
                    "name1": model1["name"],
                    "name2": model2["name"],
                    "similarity": round(model_similarity, 2),
                    "field_comparison": model_fields_similarity,
                }
            )

    # Convert matching_details to CSV
    csv_file = convert_matching_details_to_csv(matching_details)

    return matching_details, csv_file


def convert_matching_details_to_csv(matching_details):
    """
    Convert matching details dictionary to a CSV file.
    :param matching_details: Dictionary containing matching details
    :return: CSV file as a string
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write function similarities
    writer.writerow(["Function Similarities"])
    writer.writerow(
        [
            "Name1",
            "Name2",
            "Name Similarity",
            "Signature Similarity",
            "Content Similarity",
            "Overall Similarity",
        ]
    )
    for func in matching_details["functions"]:
        writer.writerow(
            [
                func["name1"],
                func["name2"],
                func["name_similarity"],
                func["signature_similarity"],
                func["content_similarity"],
                func["similarity"],
            ]
        )

    # Write model similarities
    writer.writerow([])
    writer.writerow(["Model Similarities"])
    writer.writerow(["Name1", "Name2", "Model Name Similarity", "Overall Field Similarity"])
    for model in matching_details["models"]:
        writer.writerow(
            [
                model["name1"],
                model["name2"],
                model["similarity"],
                model["field_comparison"]["overall_field_similarity"],
            ]
        )

        # Write field comparison details
        writer.writerow(
            [
                "Field1 Name",
                "Field1 Type",
                "Field2 Name",
                "Field2 Type",
                "Field Name Similarity",
                "Field Type Similarity",
                "Overall Similarity",
            ]
        )
        for field in model["field_comparison"]["field_comparison_details"]:
            writer.writerow(
                [
                    field["field1_name"],
                    field["field1_type"],
                    field["field2_name"],
                    field["field2_type"],
                    field["field_name_similarity"],
                    field["field_type_similarity"],
                    field["overall_similarity"],
                ]
            )

    return output.getvalue()


def analyze_code_similarity_with_codebert(code1, code2):
    """
    Analyze the semantic similarity between two code snippets using CodeBERT embeddings.
    :param code1: First code snippet
    :param code2: Second code snippet
    :return: Similarity score (0-100)
    """

    # Tokenize and encode inputs
    inputs_code1 = tokenizer(
        code1, return_tensors="pt", truncation=True, max_length=512, padding="max_length"
    )
    inputs_code2 = tokenizer(
        code2, return_tensors="pt", truncation=True, max_length=512, padding="max_length"
    )

    # Generate embeddings
    with torch.no_grad():
        outputs_code1 = model(**inputs_code1)
        outputs_code2 = model(**inputs_code2)

        # Use mean pooling over the last hidden state to get sentence-level embeddings
        embedding_code1 = outputs_code1.last_hidden_state.mean(dim=1)
        embedding_code2 = outputs_code2.last_hidden_state.mean(dim=1)

    # Compute cosine similarity
    similarity = cosine_similarity(embedding_code1.numpy(), embedding_code2.numpy())
    similarity_score = similarity[0][0] * 100  # Scale similarity to 0-100

    return round(similarity_score, 2)


def extract_function_signatures_and_content(repo_path):
    """
    Extract function signatures (name, parameters) and full text from Python files.
    :param repo_path: Path to the repository
    :return: List of function metadata (signature + full text)
    """
    functions = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    try:
                        file_content = f.read()
                        tree = ast.parse(file_content, filename=file)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                signature = {
                                    "name": node.name,
                                    "args": [arg.arg for arg in node.args.args],
                                    "defaults": [
                                        ast.dump(default) for default in node.args.defaults
                                    ],
                                }
                                # Extract function body as full text
                                function_text = ast.get_source_segment(file_content, node)
                                function_data = {
                                    "signature": signature,
                                    "full_text": function_text,  # Full text of the function
                                }
                                functions.append(function_data)
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")
    return functions


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

                    for line in lines:
                        line = line.strip()
                        # Look for class definition that inherits from models.Model
                        if line.startswith("class ") and "models.Model" in line:
                            if model_name:  # Save the previous model if exists
                                models.append({"name": model_name, "fields": fields})
                            model_name = line.split("(")[0].replace("class ", "").strip()
                            fields = []  # Reset fields when a new model starts

                        else:
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

                    # Add the last model if the file ends without another class
                    if model_name:
                        models.append({"name": model_name, "fields": fields})

    return models


def compare_model_fields(model1, model2):
    """
    Compare the names and fields of two Django models using difflib.
    Compares model names, field names, and field types to calculate similarity scores.

    :param model1: First model's details (e.g., {'name': 'User', 'fields': [...]})
    :param model2: Second model's details (e.g., {'name': 'Account', 'fields': [...]})
    :return: Dictionary containing name and field similarity details
    """
    # Compare model names
    model_name_similarity = (
        difflib.SequenceMatcher(None, model1["name"], model2["name"]).ratio() * 100
    )

    # Initialize field comparison details
    field_comparison_details = []

    # Get fields from both models
    fields1 = model1.get("fields", [])
    fields2 = model2.get("fields", [])

    for field1 in fields1:
        for field2 in fields2:
            print(field1, field2)
            # Compare field names
            field_name_similarity = (
                difflib.SequenceMatcher(None, field1["field_name"], field2["field_name"]).ratio()
                * 100
            )

            # Compare field types
            field_type_similarity = (
                difflib.SequenceMatcher(None, field1["field_type"], field2["field_type"]).ratio()
                * 100
            )

            # Average similarity between the field name and type
            overall_similarity = (field_name_similarity + field_type_similarity) / 2

            # Append details for each field comparison
            if overall_similarity > 50:
                field_comparison_details.append(
                    {
                        "field1_name": field1["field_name"],
                        "field1_type": field1["field_type"],
                        "field2_name": field2["field_name"],
                        "field2_type": field2["field_type"],
                        "field_name_similarity": round(field_name_similarity, 2),
                        "field_type_similarity": round(field_type_similarity, 2),
                        "overall_similarity": round(overall_similarity, 2),
                    }
                )

    # Calculate overall similarity across all fields
    if field_comparison_details:
        total_similarity = sum([entry["overall_similarity"] for entry in field_comparison_details])
        overall_field_similarity = total_similarity / len(field_comparison_details)
    else:
        overall_field_similarity = 0.0

    return {
        "model_name_similarity": round(model_name_similarity, 2),
        "field_comparison_details": field_comparison_details,
        "overall_field_similarity": round(overall_field_similarity, 2),
    }
