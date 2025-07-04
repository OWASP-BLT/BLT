import ast

code = """
import math
import numpy as np
from typing import List, Dict, Optional

PI = 3.14

def square(x):
    return x * x

@staticmethod
def greet(name: str = "World") -> str:
    print(f"Hello, {name}!")
    return f"Greeting sent to {name}"

try:
    with open('file.txt', 'w', encoding='utf-8') as f:
        f.write('Hello, world!')
        print("Successfully wrote to file.")
except FileNotFoundError:
    print("Error: The directory for the file does not exist.")
except PermissionError:
    print("Error: You do not have permission to write to this file.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
else:
    print("File operation completed successfully.")
finally:
    print("This will always run, whether an exception occurred or not.")


class Circle:
    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return PI * square(self.radius)

if __name__ == "__main__":
    c = Circle(5)
    print(c.area())
    greet()
"""

tree = ast.parse(code)
output = ast.dump(tree, indent=4)

with open("ast_output.txt", "w", encoding="utf-8") as f:
    f.write(output)

print(output)
