import os

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))

def resolve_path(path: str) -> str:
    x=os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    if x.startswith(WORKSPACE_ROOT):
        return x
    else:
        return None


def read_file(path: str, start_line: int = 1, read_lines: int = 200) -> dict:
    real_path = resolve_path(path)
    if real_path is None:
        return {"error": "Path escapes workspace."}
    if not os.path.exists(real_path):
        return {"error": f"File not found: {path}"}
    with open(real_path, 'r', encoding="utf-8") as f:
        lines=f.readlines()
    start_idx=start_line-1
    sel=lines[start_idx: start_idx+read_lines]
    content="".join(sel)
    return {"content":content}


def write_file(path: str, content: str) -> dict:
    real_path=resolve_path(path)        
    if real_path is None:
        return {"error": "Path escapes workspace."}
    os.makedirs(os.path.dirname(real_path), exist_ok=True)
    with open(real_path, 'w', encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "path":path}
        


def edit_file(
    path: str,
    operation: str,
    start_line: int,
    end_line: int | None = None,
    content: str | None = None,
) -> dict:
    real_path = resolve_path(path)        
    if real_path is None:
        return {"error": "Path escapes workspace."}
    if not os.path.exists(real_path):
        return {"error": f"File not found: {path}"}
    start_idx=start_line-1
    end_idx=end_line if end_line else start_line
    with open(real_path, 'r', encoding="utf-8") as f:
        files=f.readlines()
    if operation=="replace":
        files[start_idx:end_idx]=[content+"\n"]
    elif operation=="delete":
        files[start_idx:end_idx]=[]
    elif operation=="append":
        files.append(content + "\n")
    with open(real_path, 'w', encoding="utf-8") as f:
        f.writelines(files)
        return {"success":True}
    


def list_files(path: str = ".", pattern: str = "*") -> dict:
    real_path=resolve_path(path)  
    if real_path is None:
        return {"error": "Path escapes workspace."}
    if not os.path.isdir(real_path):
        return {"error": f"Directory not found: {path}"}
    files=os.listdir(real_path)
    return {"files":files}


TOOLS=[
        {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read lines from a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "read_lines": {"type": "integer"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "pattern": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing, deleting, or appending content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "delete", "append"]
                    },
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string"}
                },
                "required": ["path", "operation", "start_line"]
            }
        }
    },
]