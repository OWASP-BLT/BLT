import os

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_labels(readme_content, github_topics):
    prompt = f"""
    You are an AI that assigns relevant labels to GitHub projects based on their readme content and github topics.

    ### Input:
    - **README Content:** {readme_content}
    - **GitHub Topics:** {github_topics}

    ### Task:
    Analyze the input and assign appropriate labels. 
    Labels should include:
    1. **Technology Stacks** (e.g., Python, JavaScript, Java).
    2. **Project Type** (e.g., Web Application, CLI Tool, Library).
    3. **OWASP Relevance** (e.g., Security Testing, Secure Coding).
    4. Any other relevant labels.

    ### Output:
    Provide the labels in JSON format like this:
    {{
      "Technology Stack": ["Python", "JavaScript"],
      "Project Type": ["Web Application"],
      "OWASP Relevance": ["Secure Coding"],
      "Other Labels": ["Machine Learning", "Data Processing"]
    }}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for labeling projects."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    return response["choices"][0]["message"]["content"]
