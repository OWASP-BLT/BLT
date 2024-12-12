import os
import re

# Root directory of your project
root_directory = 'E:\\OWASP\\blt'

# Pattern to match the og_image block
pattern = re.compile(r'{%\s*block\s*og_image\s*%}.*?{%\s*endblock\s*og_image\s*%}', re.DOTALL)

# Function to remove the og_image block from a file
def remove_og_image_block(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Remove the og_image block
    new_content = re.sub(pattern, '', content)
    
    # Write the updated content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)

# Iterate through all files in the root directory
for root, _, files in os.walk(root_directory):
    for file in files:
        if file.endswith('.html'):
            file_path = os.path.join(root, file)
            remove_og_image_block(file_path)

print("og_image blocks removed successfully.")
