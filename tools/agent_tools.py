import os
import subprocess
import json

AKAI_ROOT = "C:/AKAI"

def read_file(path: str) -> str:
    full_path = os.path.join(AKAI_ROOT, path)
    if not os.path.exists(full_path):
        return f"Error: {path} does not exist."
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path: str, content: str) -> str:
    full_path = os.path.join(AKAI_ROOT, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written to {path}"

def list_files(subpath: str = "") -> str:
    full_path = os.path.join(AKAI_ROOT, subpath)
    if not os.path.exists(full_path):
        return f"Error: {subpath} does not exist."
    result = []
    for root, dirs, files in os.walk(full_path):
        dirs[:] = [d for d in dirs if d not in ["venv", "chromadb"]]
        level = root.replace(full_path, "").count(os.sep)
        indent = "  " * level
        result.append(f"{indent}{os.path.basename(root)}/")
        for file in files:
            result.append(f"{indent}  {file}")
    return "\n".join(result)

def run_python(code: str) -> str:
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=AKAI_ROOT
        )
        output = result.stdout or result.stderr
        return output if output else "Code ran with no output."
    except subprocess.TimeoutExpired:
        return "Error: Code timed out after 10 seconds."
    except Exception as e:
        return f"Error: {str(e)}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file inside C:/AKAI. Use relative paths e.g. 'projects/app.py'",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file inside C:/AKAI"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file inside C:/AKAI. Creates the file if it doesn't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file inside C:/AKAI"},
                    "content": {"type": "string", "description": "Content to write to the file"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and folders inside C:/AKAI",
            "parameters": {
                "type": "object",
                "properties": {
                    "subpath": {"type": "string", "description": "Optional subfolder to list e.g. 'projects'"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute a Python code snippet. Use for calculations, data processing, testing logic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"]
            }
        }
    }
]

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "run_python": run_python
}