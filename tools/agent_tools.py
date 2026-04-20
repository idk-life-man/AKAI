import os
import subprocess
import json
from playwright.sync_api import sync_playwright

AKAI_ROOT = "C:/AKAI"

# Browser instance held globally so multiple tool calls can reuse it
_browser = None
_page = None
_playwright = None

def _get_browser():
    global _browser, _page, _playwright
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=False)
        _page = _browser.new_page()
    return _page

def browser_goto(url: str) -> str:
    page = _get_browser()
    page.goto(url, timeout=30000)
    return f"Navigated to {url}. Title: {page.title()}"

def browser_read(selector: str = "body") -> str:
    page = _get_browser()
    try:
        text = page.locator(selector).inner_text(timeout=5000)
        return text[:5000]  # Cap at 5k chars
    except Exception as e:
        return f"Error reading {selector}: {str(e)}"

def browser_click(selector: str) -> str:
    page = _get_browser()
    try:
        page.locator(selector).click(timeout=5000)
        return f"Clicked {selector}"
    except Exception as e:
        return f"Error clicking {selector}: {str(e)}"

def browser_fill(selector: str, text: str) -> str:
    page = _get_browser()
    try:
        page.locator(selector).fill(text, timeout=5000)
        return f"Filled {selector} with text"
    except Exception as e:
        return f"Error filling {selector}: {str(e)}"

def browser_close() -> str:
    global _browser, _page, _playwright
    if _browser:
        _browser.close()
        _playwright.stop()
        _browser = None
        _page = None
        _playwright = None
    return "Browser closed"

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
    },
    {
        "type": "function",
        "function": {
            "name": "browser_goto",
            "description": "Open a URL in the browser. Returns the page title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to navigate to e.g. 'https://google.com'"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read",
            "description": "Read text content from the current page. Defaults to whole body.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector e.g. 'h1', '.article-body', '#main'. Default is 'body'."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element on the current page",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the element to click"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fill",
            "description": "Type text into an input field",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the input"},
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_close",
            "description": "Close the browser when done",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "run_python": run_python,
    "browser_goto": browser_goto,
    "browser_read": browser_read,
    "browser_click": browser_click,
    "browser_fill": browser_fill,
    "browser_close": browser_close
}