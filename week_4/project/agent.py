from sessions import *
from tool_schema import TOOLS
from tools.plan import TODOS

from tools.files import (
    read_file,
    write_file,
    edit_file,
    list_files,
)
from tools.exec import run_command
from tools.search import (
    grep,
    list_definitions,
)
from tools.plan import (
    add_todos,
    get_todos,
    mark_todo,
)
import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_ITERATIONS = 25


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = "openai/gpt-4o-mini"



class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None):
        self.last_command_result=None
        self.workspace = os.path.abspath(workspace)
        if session_id:
            session = load_session(session_id)
            self.session_id = session_id
            self.messages = session["messages"]
        else:
            self.session_id = create_session()
            self.messages = [
                {
                    "role": "system",
                    "content": build_system_prompt(),
                }
            ]

    def chat(self, user_message: str) -> str:
        self.messages.append(
            {"role":"user",
            "content":user_message}
        )
        answer = self._run_loop()
        save_session(
            self.session_id,
            self.messages,
            title="Code Scout Session"
        )
        return answer

    def run_once(self, prompt: str) -> str:
        return self.chat(prompt)


    def _run_loop(self) -> str:
        completed=False
        for _ in range(MAX_ITERATIONS):
            response=client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=TOOLS
            )
            message=response.choices[0].message
            self.messages.append(message.model_dump())
            if not message.tool_calls:
                if completed:
                    TODOS.clear()
                    return message.content or ""
                my_todos=get_todos()["todos"]
                if not my_todos:
                    return message.content or ""
                if all(todo["status"]=="completed" for todo in my_todos):
                    completed=True
                    self.messages.append(
                        {
                            "role":"system",
                            "content": "All todos are completed and verified. Now provide the final summary for the user.",
                        }
                    )
                    continue
                else:
                    self.messages.append(
                        {
                            "role": "system",
                            "content": "There are still incomplete todos. Continue working until every todo is completed and verified.",
                        }
                    )
            else:
                for tool_call in message.tool_calls:
                    self._emit("tool_call", name=tool_call.function.name)
                    result=self.dispatch(tool_call)
                    self.messages.append(
                        {
                            "role":"tool",
                            "tool_call_id":tool_call.id,
                            "content": json.dumps(result)
                        }
                    )
                    if result.get("cancelled"):
                        self.messages.append(
                            {
                                "role": "system",
                                "content":
                                "The user denied permission for this destructive command. "
                                "Do NOT retry it or attempt equivalent destructive commands. "
                                "Explain to the user that the action cannot proceed without approval.",
                            }
                        )
        return "Hit iteration limit!"




    def dispatch(self, tool_call) -> str:
        tool_name=tool_call.function.name
        args=json.loads(tool_call.function.arguments)
        if tool_name == "read_file":
            result = read_file(**args)
        elif tool_name == "write_file":
            result = write_file(**args)
        elif tool_name == "list_files":
            result = list_files(**args)
        elif tool_name == "edit_file":
            result = edit_file(**args)
        elif tool_name == "grep":
            result = grep(**args)
        elif tool_name == "list_definitions":
            result = list_definitions(**args)
        elif tool_name == "add_todos":
            result = add_todos(**args)
        elif tool_name == "get_todos":
            result = get_todos(**args)
        elif tool_name == "mark_todo":
            args["command_result"]=self.last_command_result
            result = mark_todo(**args)
            if result.get("success"):
                self.last_command_result = None
        elif tool_name== "run_command":
            result=run_command(**args)
            self.last_command_result=result
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        return result



    def _emit(self, event: str, **data) -> None:
        pass



class REPLAgent(Agent):
    def run(self) -> None:
        print(f"Code Scout Session [{self.session_id}] — /quit to exit")
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user_input or user_input in ("/quit", "/exit"):
                break
            print(self.chat(user_input))
            print()

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            print(f"  [tool] {data.get('name')}", file=sys.stderr)




def build_system_prompt() -> str:
    prompt = """You are Code Scout, an autonomous coding agent.
Your job is to solve coding tasks on an unfamiliar codebase by exploring it, planning the work, making changes, verifying those changes, and only then reporting success.
You have access to the following tools.

File tools:
    - list_files
    - read_file
    - write_file
    - edit_file
Search tools:
    - grep
    - list_definitions
Execution:
    - run_command
Planning:
    - add_todos
    - get_todos
    - mark_todo
General workflow:
1. IMPORTANT:
        Before using any file-editing tool (write_file or edit_file), you MUST first create at least one todo using add_todos().
        Do not call write_file or edit_file until add_todos has been called.
        This workflow is mandatory.
2. Before reading files, search the repository.
   - Prefer grep to locate relevant code.
   - Use list_definitions to understand the structure of Python files.
   - Do not read files until you know they are relevant.
3. Read only the files necessary to complete the task.
   Never read the repository from top to bottom.
4. Make changes using write_file or edit_file.
   Do not modify files unless you understand why the change is needed.
5. If a command writes, deletes, installs, commits, or otherwise changes the repository through run_command, it will require human approval. Wait for that approval before continuing.
6. Verification must always use run_command.

When verifying file creation:
    - Use a simple read-only shell command such as "type", "cat", "dir", or "ls".
    - Do not create temporary test files unless the user explicitly requests tests.
    - Do not perform multiple verification commands if one successful verification is sufficient.

Do NOT create new test files unless the user explicitly asks for tests.
   Use run_command to execute the appropriate verification command, such as:
   - pytest
   - python -m pytest
   - unit tests
   - linting
   - any command requested by the user
7. Never mark a todo as completed until the verification command succeeds.
8. Never claim a fix worked unless you have verification evidence from run_command.
9. If verification fails, continue investigating and fixing the problem until either:
   - the verification succeeds, or
   - you have enough evidence to explain why the task cannot currently be completed.
10. Use get_todos whenever you need to review the current plan.
11. When every todo is completed, provide a concise final summary describing:
   - what was changed
   - which files were modified
   - how the fix was verified
Verification workflow:
    1. Execute the verification command with run_command().
    2. Immediately call mark_todo(status="completed") if the command succeeded.
    3. If verification fails, do not mark the todo completed.
    4. Continue with the next todo only after the current todo has been updated.
Guidelines:
    - Prefer searching before reading.
    - Prefer reading before editing.
    - Never invent file contents.
    - Never invent command output.
    - Never assume tests passed unless run_command proves it.
    - Use tools whenever information is missing.
    - Work step-by-step.
    - Keep your responses concise.
"""


    agents_path=AGENTS_PATH
    if os.path.exists(agents_path):
        with open(agents_path, 'r', encoding="utf-8") as f:
            prompt+= '\n' + f.read()
    return prompt



if __name__ == "__main__":
    REPLAgent().run()