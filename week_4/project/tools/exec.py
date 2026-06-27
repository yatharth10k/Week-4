import os
import shlex
import subprocess

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
TIMEOUT_DEFAULT = 10
MAX_OUTPUT_CHARS = 8_000

# Known-safe: run immediately once the path check passes.
READ_ONLY_PREFIXES = (
    "grep", "find", "ls", "cat", "head", "tail", "wc",
    "git log", "git diff", "git status", "git blame", "git show",
    "pytest", "python -m pytest", "ruff", "flake8", "mypy", "dir", "type", "more", "powershell Get-Content"
)

# Known-destructive: always ask, even if they'd otherwise look harmless.
DESTRUCTIVE_PATTERNS = (
    "rm ", "mv ", ">", ">>", "git commit", "git push", "git checkout --",
    "pip install", "npm install", "curl ", "sudo ", "chmod ", "notepad", "start", "del"
)


def paths_within_sandbox(command: str, workspace_root: str) -> bool:
    _ = (command, workspace_root)
    tokens=shlex.split(command)
    for _ in tokens:
        if "/" in _ or "\\" in _ or _.startswith("."):
            abs_path=os.path.abspath(os.path.join(workspace_root, _))
            if not abs_path.startswith(workspace_root):
                return False
    return True
            




def classify_command(command: str) -> str:
    _ = command
    cmd = command.lower()
    for pattern in READ_ONLY_PREFIXES:
        if pattern.lower() in cmd:
            return "read_only"
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern.lower() in cmd:
            return "ask"
    return "ask"

def run_command(command: str, cwd: str = WORKSPACE_ROOT, timeout: int = TIMEOUT_DEFAULT) -> dict:
    _ = (command, cwd, timeout)
    if not paths_within_sandbox(command, cwd):
        return {"error": "Command escapes workspace sandbox.", "exit_code":-1}
    if classify_command(command)!="read_only":
        x=input(f"This command ({command}) is a destructive command, it could modify your system, do you wish to proceed? [y/n]: ").strip().lower()
        if x=="n":
            return {"error": "cancelled by user!", "cancelled":True, "exit_code":-1}
        elif x!="y":
            return {"error": "Invalid input.", "exit_code":-1}
    try:
        result=subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        return {
            "stdout": result.stdout[:MAX_OUTPUT_CHARS],
            "stderr": result.stderr[:MAX_OUTPUT_CHARS],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timeout", "exit_code":-1}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command in the workspace and return its output. "
                "Use this to search (grep/find), inspect history (git log/diff), "
                "run tests, or make a change. Read-only commands run immediately. "
                "Anything that writes, deletes, or installs will pause and ask the "
                "human operator for approval — expect that pause, it's not a failure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Seconds before the command is killed. Default {TIMEOUT_DEFAULT}.",
                    },
                },
                "required": ["command"],
            },
        },
    }
]