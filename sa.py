import os
import subprocess
from typing import List


def _run_command(command: List[str]) -> str:
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        return result.stdout
    except Exception as e:
        return f"Error running {command}: {str(e)}"


def _run_ruff_on_files(files: List[str]) -> str:
    if not files:
        return ""
    command = ["ruff", "check", "--select=ALL", "--output-format", "json"] + files
    return _run_command(command)


if __name__ == "__main__":
    sample_filename = "sample_test_file.py"
    sample_code = "def foo():\n    return 42\n"
    with open(sample_filename, "w") as f:
        f.write(sample_code)

    print(f"Running ruff on {sample_filename}...")
    output = _run_ruff_on_files([sample_filename])
    print("Ruff output:")
    print(output)

    try:
        os.remove(sample_filename)
    except Exception:
        print(f"Could not remove {sample_filename}. Please delete it manually.")
