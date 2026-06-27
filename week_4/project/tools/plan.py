TODOS=[]
VALID_STATUS=[
    "completed", "in_progress", "pending",
]
NEXT_ID=1
def add_todos(todos:list[dict])->dict:
    global NEXT_ID
    if TODOS:
        return {"success":True, "message": "Todo list already exists.", "todos": TODOS}
    num=0

    for todo in todos:
        todo["todo_id"]=NEXT_ID
        NEXT_ID+=1
        todo["status"]="pending"
        TODOS.append(todo)
        num+=1
    return {
        "success":True,
        "added":num,
        "todos":TODOS
    }



def get_todos()->dict:
    return {"todos":TODOS}




def mark_todo(todo_id:int, status:str, command_result:None) ->dict:
    if status not in VALID_STATUS:
        return {"error": "Invalid status."}
    for todo in TODOS:
        if todo["todo_id"]==todo_id:
            if status=="completed":
                if command_result is None:
                    return {"error": "No verification command has been run."}
                if command_result.get("exit_code")!=0:
                    return {"error": "Verification failed."}
                else:
                    todo["status"]="completed"
            else:
                todo["status"]=status
            return {"success":True, "todo":todo}
    return {"error":"Todo not found."}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_todos",
            "description": (
                "Create one or more todos before starting a non-trivial task. "
                "Each todo must include a short title, a description, and a "
                "verification method."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "List of todos to add.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Short title of the todo."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What needs to be done."
                                },
                                "verification": {
                                    "type": "string",
                                    "description": "How completion should be verified."
                                },
                            },
                            "required": [
                                "title",
                                "description",
                                "verification",
                            ],
                        },
                    }
                },
                "required": ["todos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_todos",
            "description": (
                "Return the current todo list. Use this whenever you need to "
                "review the current plan or check progress."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_todo",
            "description": (
                "Update the status of a todo. Only mark a todo as completed "
                "after a successful verification using run_command."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "integer",
                        "description": "ID of the todo to update.",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "in_progress",
                            "completed",
                        ],
                        "description": "New status of the todo.",
                    },
                },
                "required": [
                    "todo_id",
                    "status",
                ],
            },
        },
    },
]