import ast
import os
import re

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_GREP_RESULTS = 50
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def resolve_path(path: str) -> str | None:
    x=os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    if x.startswith(WORKSPACE_ROOT):
        return x
    else:
        return None


def grep(
    pattern: str,
    path: str = ".",
    case_sensitive: bool = False,
    max_results: int = MAX_GREP_RESULTS,
) -> dict:
    real_path=resolve_path(path)
    if real_path is None:
        return {"error": "Path escapes directory"}      
    matches=[]
    total_matches=0
    for root, dirs, files in os.walk(real_path):
  
        dirs[:]=[
            d for d in dirs
            if d not in EXCLUDE_DIRS
        ]
        for file in files:
            file_path=os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, start=1):
                        if case_sensitive:
                            found=re.search(pattern, line)
                        else:
                            found=re.search(pattern, line, re.IGNORECASE)
                        if found:
                            if len(matches)<max_results:
                                matches.append({
                                    "file": os.path.relpath(file_path, WORKSPACE_ROOT),
                                    "line": line_no,
                                    "text":line.strip(),
                                })
                            total_matches+=1
            except (UnicodeDecodeError, OSError):
                continue
    truncated=total_matches>max_results
    return {
        "matches":matches,
        "truncated":truncated,
        "total_matches":total_matches
    }   
         




def list_definitions(path: str) -> dict:
    real_path=resolve_path(path)
    if real_path is None:
        return {"error": "Path escapes workspace."}
    try:

        with open(real_path, "r", encoding="utf-8") as f:
            source=f.read()
        tree=ast.parse(source)
        definitions=[]
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                definitions.append({
                    "kind":"function",
                    "name":node.name,
                    "line":node.lineno,
                    "end_line":node.end_lineno,
                })
            elif isinstance(node, ast.AsyncFunctionDef):
                definitions.append({
                    "kind":"async function",
                    "name":node.name,
                    "line":node.lineno,
                    "end_line":node.end_lineno,
                })
            elif isinstance(node, ast.ClassDef):
                definitions.append({
                    "kind":"class",
                    "name":node.name,
                    "line":node.lineno,
                    "end_line":node.end_lineno,                    
                })
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        definitions.append(
                            {
                                "kind": "method",
                                "name": item.name,
                                "line": item.lineno,
                                "end_line": item.end_lineno,
                            }
                        )
        return {"definitions":definitions}
    except SyntaxError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error":str(e)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Search file contents for a pattern across the workspace. "
                "Use this before read_file when you don't already know which "
                "file you need."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Text or regex to search for."},
                    "path": {"type": "string", "description": "Subdirectory to search, default workspace root."},
                    "case_sensitive": {"type": "boolean", "description": "Default false."},
                    "max_results": {
                        "type": "integer",
                        "description": f"Cap on matches returned. Default {MAX_GREP_RESULTS}.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_definitions",
            "description": (
                "List the functions and classes declared in a Python file, "
                "with line numbers, without reading the whole file. Use this "
                "right after grep to decide which match is worth reading in "
                "full with read_file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to a Python file."},
                },
                "required": ["path"],
            },
        },
    },
]