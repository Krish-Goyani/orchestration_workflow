from typing import Any, Optional

from src.memory.memory_manager import global_memory_manager


async def store_iteration(
    session_id: str,
    agent_name: str,
    thought: str,
    action: str,
    observation: Any,
    action_input: Any,
    tool_call_requires: bool,
    status: str = "in_progress",
    task_id: Optional[int] = None,
):
    """
    Store an iteration in both memory systems with fallback.

    Args:
        session_id: The session identifier
        agent_name: Name of the agent
        thought: Agent's thought process
        action: Action taken by the agent
        observation: Result observed after the action
        tool_call_requires: Whether a tool call is required
        action_input: Input provided for the action
        status: Current status of the iteration
        task_id: Optional ID of the task this iteration belongs to
    """
    # Store in enhanced memory manager (primary)
    try:
        await global_memory_manager.add_iteration(
            session_id=session_id,
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            tool_call_requires=tool_call_requires,
            action_input=action_input,
            status=status,
            task_id=task_id,
        )
    except Exception as e:
        print(f"Error storing in enhanced memory: {e}")


# async def get_task_context(
#         session_id: str,
#         agent_name: str,
#         task: str,
#         task_id: Optional[int] = None,
#         dependencies: Optional[List[int]] = None
#     ) -> Dict[str, Any]:
#     """
#     Get context for a specific task with intelligent context retrieval.

#     This function uses intent classification to determine what context is needed,
#     potentially including summaries and RAG results.

#     Args:
#         session_id: The session identifier
#         agent_name: Name of the agent requesting context
#         task: Description of the current task
#         task_id: ID of the current task
#         dependencies: List of task IDs this task depends on

#     Returns:
#         Dictionary with context information (recent_history, summary, rag_results)
#     """
#     try:
#         # Use the memory manager's context-aware retrieval
#         context = await global_memory_manager.get_task_context(
#             session_id=session_id,
#             agent_name=agent_name,
#             task=task,
#             task_id=task_id,
#             dependencies=dependencies or []
#         )
#         return context
#     except Exception as e:
#         print(f"Error retrieving task context: {e}")
#         # Return empty context as fallback
#         return {
#             "recent_history": [],
#             "summary": None,
#             "rag_results": None,
#             "user_query": ""
#         }

# async def get_complete_history(session_id: str):
#     """
#     Get complete conversation history.

#     Args:
#         session_id: The session identifier

#     Returns:
#         Complete conversation history
#     """
#     try:
#         return await global_memory_manager.get_complete_history(session_id)
#     except Exception as e:
#         print(f"Error retrieving complete history: {e}")
#         return None

# async def get_task_history(session_id: str, task_ids: List[int]):
#     """
#     Get history specific to a set of tasks.

#     Args:
#         session_id: The session identifier
#         task_ids: List of task IDs to retrieve history for

#     Returns:
#         Task-specific conversation history
#     """
#     try:
#         return await global_memory_manager.get_task_history(session_id, task_ids)
#     except Exception as e:
#         print(f"Error retrieving task history: {e}")
#         return None
