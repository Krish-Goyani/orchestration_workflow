import json
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from src.utils.session_context import session_state


class ShortTermMemory:
    """
    Short-term memory system using Redis.
    Handles fast access to recent conversations and session state.
    """

    def __init__(self):
        """Initialize Redis connection."""
        self.redis = None

    async def _ensure_connection(self):
        """Ensure Redis connection is established."""
        if self.redis is None:
            self.pool = redis.ConnectionPool.from_url(
                "redis://localhost:6379?decode_responses=True"
            )
            self.redis = redis.Redis.from_pool(self.pool)
            result = await self.redis.ping()
            print(f"Redis connection {result}")

    async def initialize_session(self, user_query: str) -> None:
        """
        Initialize a new session in Redis.

        Args:
            user_query: Initial user query
        """
        await self._ensure_connection()

        # Store session metadata
        await self.redis.hset(
            f"session:{session_state.get()}:metadata",
            mapping={
                "user_query": user_query,
                "status": "in_progress",
                "start_time": str(int(time.time())),
                "total_iterations": 0,
            },
        )

        # Create a list for iterations
        await self.redis.delete(f"session:{session_state.get()}:iterations")

    async def add_iteration(
        self,
        agent_name: str,
        thought: str,
        action: str,
        observation: Any,
        tool_call_requires: bool,
        action_input: Any,
        status: str = "in_progress",
        task_id: Optional[int] = None,
    ) -> None:
        """
        Add an iteration to Redis short-term memory.

        Args:
            agent_name: Name of the agent
            thought: Agent's thought process
            action: Action taken by the agent
            observation: Result observed after the action
            tool_call_requires: Whether a tool call is required
            action_input: Input provided for the action
            status: Current status of the iteration
            task_id: Optional ID of the task this iteration belongs to
        """
        await self._ensure_connection()

        # Convert non-string observation to string
        observation_str = (
            str(observation)
            if not isinstance(observation, str)
            else observation
        )

        # Serialize action input
        if not isinstance(action_input, str):
            action_input = json.dumps(action_input)

        # Create iteration data
        iteration_data = {
            "agent_name": agent_name,
            "thought": thought,
            "action": action,
            "observation": observation_str,
            "tool_call_requires": str(tool_call_requires).lower(),
            "action_input": action_input,
            "status": status,
            "task_id": str(task_id) if task_id is not None else "",
        }

        # Convert to JSON for storage
        iteration_json = json.dumps(iteration_data)

        # Add to the session iterations list
        await self.redis.lpush(
            f"session:{session_state.get()}:iterations", iteration_json
        )

        # Update total iterations counter
        await self.redis.hincrby(
            f"session:{session_state.get()}:metadata", "total_iterations", 1
        )

        # Add task-specific index if task_id is provided
        if task_id is not None:
            # Get iteration index (0-based)
            idx = await self.redis.hget(
                f"session:{session_state.get()}:metadata", "total_iterations"
            )
            idx = int(idx) - 1  # Convert to 0-based

            # Store task index mapping
            await self.redis.lpush(
                f"session:{session_state.get()}:task:{task_id}:iterations",
                str(idx),
            )

    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get context metadata for a session.

        Args:
            session_id: The session identifier

        Returns:
            Dictionary of session metadata
        """
        await self._ensure_connection()

        # Get session metadata
        metadata = await self.redis.hgetall(f"session:{session_id}:metadata")

        # Convert types for certain fields
        if "total_iterations" in metadata:
            metadata["total_iterations"] = int(metadata["total_iterations"])

        if "start_time" in metadata:
            metadata["start_time"] = int(metadata["start_time"])

        return metadata

    async def get_recent_iterations(
        self, session_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get most recent iterations.

        Args:
            session_id: The session identifier
            limit: Maximum number of iterations to retrieve

        Returns:
            List of recent iterations
        """
        await self._ensure_connection()

        # Get the most recent iterations (LPUSH adds to the front)
        iterations_json = await self.redis.lrange(
            f"session:{session_id}:iterations", 0, limit - 1
        )

        # Parse JSON data
        iterations = []
        for iteration_json in iterations_json:
            iteration = json.loads(iteration_json)
            iterations.append(iteration)

        return iterations

    async def get_task_iterations(
        self, session_id: str, task_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get iterations related to a specific task.

        Args:
            session_id: The session identifier
            task_id: The task ID

        Returns:
            List of task-specific iterations
        """
        await self._ensure_connection()

        # Get task-specific iteration indexes
        idx_list = await self.redis.lrange(
            f"session:{session_id}:task:{task_id}:iterations", 0, -1
        )

        if not idx_list:
            return []

        # Convert to integers
        indexes = [int(idx) for idx in idx_list]

        # Get all iterations
        all_iterations_json = await self.redis.lrange(
            f"session:{session_id}:iterations", 0, -1
        )
        all_iterations = [
            json.loads(iter_json) for iter_json in all_iterations_json
        ]

        # Filter by indexes
        task_iterations = [
            all_iterations[idx] for idx in indexes if idx < len(all_iterations)
        ]

        return task_iterations

    async def get_user_query(self) -> str:
        """

        Returns:
            Original user query string
        """
        await self._ensure_connection()

        return (
            await self.redis.hget(
                f"session:{session_state.get()}:metadata", "user_query"
            )
            or ""
        )

    async def complete_session(self, session_id: str) -> None:
        """
        Mark a session as completed and clean up short-term memory.

        Args:
            session_id: The session identifier
        """
        await self._ensure_connection()

        # Mark session as completed
        await self.redis.hset(
            f"session:{session_id}:metadata", "status", "completed"
        )

        # Set expiration for Redis keys (e.g., 24 hours)
        expiration = 86400  # 24 hours in seconds

        # Set expiration for all session keys
        keys = await self.redis.keys(f"session:{session_id}:*")
        for key in keys:
            await self.redis.expire(key, expiration)


# Create a global instance of ShortTermMemory
global_short_term_memory = ShortTermMemory()
