import ast
import difflib
import os
import re

from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
import torch

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
    similarity_score = 0
    matching_details = {
        "functions": [],
        "models": [],
    }

    # Step 1: Extract function signatures and content
    functions1 = extract_function_signatures_and_content(repo1_path)
    functions2 = extract_function_signatures_and_content(repo2_path)
    print(functions1)   
    print(functions2)   
    # Compare functions
    for func1 in functions1:
        for func2 in functions2:
            # Name similarity
            name_similarity_difflib = difflib.SequenceMatcher(None, func1["signature"]["name"], func2["signature"]["name"]).ratio() * 100
            name_similarity_codebert = analyze_code_similarity_with_codebert(func1["signature"]["name"], func2["signature"]["name"])
            name_similarity = (name_similarity_difflib + name_similarity_codebert) / 2
            print(f"Name similarity: {name_similarity}")

            # Signature similarity
            signature1 = f"{func1['signature']['name']}({', '.join(func1['signature']['args'])})"
            signature2 = f"{func2['signature']['name']}({', '.join(func2['signature']['args'])})"
            signature_similarity_difflib = difflib.SequenceMatcher(None, signature1, signature2).ratio() * 100
            signature_similarity_codebert = analyze_code_similarity_with_codebert(signature1, signature2)
            signature_similarity = (signature_similarity_difflib + signature_similarity_codebert) / 2
            print(f"Signature similarity: {signature_similarity}")

            # Content similarity
            content_similarity = analyze_code_similarity_with_codebert(func1["full_text"], func2["full_text"])
            print(f"Content similarity: {content_similarity}")   
            
            # Aggregate similarity
            overall_similarity = (name_similarity + signature_similarity + content_similarity) / 3
            print(f"Overall similarity: {overall_similarity}")   
            # if overall_similarity > 80:  # You can set the threshold here
            matching_details["functions"].append({
                "name1": func1["signature"]["name"],
                "name2": func2["signature"]["name"],
                "similarity": round(overall_similarity, 2),
            })

    # Step 2: Compare Django models
    models1 = extract_django_models(repo1_path)
    models2 = extract_django_models(repo2_path)

    print(models1)
    print(models2)
    # Compare models and fields
    for model1 in models1:
        for model2 in models2:
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
    Analyze the semantic similarity between two code snippets using CodeBERT embeddings.
    :param code1: First code snippet
    :param code2: Second code snippet
    :return: Similarity score (0-100)
    """
    print(f"Analyzing similarity between:\nCode1: {code1}\nCode2: {code2}")
    
    # Tokenize and encode inputs
    inputs_code1 = tokenizer(code1, return_tensors="pt", truncation=True, max_length=512, padding="max_length")
    inputs_code2 = tokenizer(code2, return_tensors="pt", truncation=True, max_length=512, padding="max_length")
    
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

    print(f"Similarity score: {similarity_score}")
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
                                    "defaults": [ast.dump(default) for default in node.args.defaults],
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
                    inside_model = False  # To check if we are inside a model definition

                    for line in lines:
                        line = line.strip()

                        # Look for class definition that inherits from models.Model
                        if line.startswith("class ") and "models.Model" in line:
                            if model_name:  # Save the previous model if exists
                                models.append({"name": model_name, "fields": fields})
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
