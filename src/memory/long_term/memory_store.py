from typing import Dict

from src.models.schema.histrory_schema import History, SingleIteration


class MemoryStore:
    """
    A class that stores and manages the history of agent interactions.
    This includes thoughts, actions, observations, etc.
    """

    def __init__(self):
        self.histories: Dict[str, History] = {}

    def create_history(self, session_id: str, user_query: str) -> None:
        """
        Initialize a new history for a session.

        Args:
            session_id: A unique identifier for the session
            user_query: The initial query from the user
        """
        self.histories[session_id] = History(
            user_query=user_query,
            iterations=[],
            total_iterations=0,
            final_status="in_progress",
        )

    def add_iteration(
        self,
        session_id: str,
        agent_name: str,
        thought: str,
        action: str,
        observation: str,
        tool_call_requires: str,
        status: str,
        action_input: str,
    ) -> None:
        """
        Add a new iteration to the history.

        Args:
            session_id: The session identifier
            agent_name: Name of the agent
            thought: Agent's thought process
            action: Action taken by the agent
            observation: Result observed after the action
            tool_call_requires: Whether a tool call is required
        """
        if session_id not in self.histories:
            raise ValueError(f"No history found for session ID: {session_id}")

        iteration = SingleIteration(
            agent_name=agent_name,
            thought=thought,
            action=action,
            tool_call_requires=str(tool_call_requires).lower(),
            action_input=action_input,
            observation=observation,
            status=status,
        )

        self.histories[session_id].iterations.append(iteration)
        self.histories[session_id].total_iterations += 1
        print(
            "=========================================================================================="
        )
        print(
            "=========================================================================================="
        )

        print(
            f"Total Iterations: {self.histories[session_id].total_iterations}"
        )
        print(f"current status: {self.histories[session_id].final_status}")
        print(f"Iteration : {iteration}")
        print(
            "=========================================================================================="
        )
        print(
            "=========================================================================================="
        )

    def complete_session(self, session_id: str) -> None:
        """
        Mark the entire session as completed.

        Args:
            session_id: The session identifier
        """
        if session_id not in self.histories:
            raise ValueError(f"No history found for session ID: {session_id}")

        self.histories[session_id].final_status = "completed"

        # Mark all iterations as completed
        for iteration in self.histories[session_id].iterations:
            iteration.status = "completed"

    def get_history(self, session_id: str) -> History:
        """
        Retrieve the history for a specific session.

        Args:
            session_id: The session identifier

        Returns:
            The complete history for the session
        """
        if session_id not in self.histories:
            raise ValueError(f"No history found for session ID: {session_id}")

        return self.histories[session_id]

    def get_formatted_history(self, session_id: str) -> str:
        """
        Get a formatted string representation of the history to pass to LLM.

        Args:
            session_id: The session identifier

        Returns:
            A formatted string containing the history
        """
        if session_id not in self.histories:
            raise ValueError(f"No history found for session ID: {session_id}")

        history = self.histories[session_id]
        result = [f"USER QUERY: {history.user_query}\n"]

        for i, iteration in enumerate(history.iterations):
            result.append(f"ITERATION {i+1}:")
            result.append(f"AGENT: {iteration.agent_name}")
            result.append(f"THOUGHT: {iteration.thought}")
            result.append(f"ACTION: {iteration.action}")
            result.append(f"OBSERVATION: {iteration.observation}")
            result.append("")

        return "\n".join(result)

    def clear_history(self, session_id: str) -> None:
        """
        Delete the history for a specific session.

        Args:
            session_id: The session identifier
        """
        if session_id in self.histories:
            del self.histories[session_id]


global_memory_store = MemoryStore()
