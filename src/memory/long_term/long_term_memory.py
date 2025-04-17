import time
import uuid
from datetime import datetime
from typing import Any, List, Optional

import motor.motor_asyncio
from pinecone import PineconeAsyncio

from src.config.settings import settings
from src.models.domain.history_iteration import HistoryDomain
from src.models.domain.summary_domain import Summary
from src.models.schema.histrory_schema import History, SingleIteration
from src.utils.session_context import session_state


class LongTermMemory:
    """
    Long-term memory system using MongoDB and vector database.
    Handles persistent storage of conversations, summaries, and vector search.
    """

    def __init__(self):
        """Initialize MongoDB connection."""
        self.client = None
        self.db = None
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure MongoDB connection is established."""
        if self.client is None:
            # Use direct connection to avoid dependency on SON
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.MONGODB_URL, maxpoolsize=30, minpoolsize=5
            )
            self.collection = self.client[settings.MONGODB_DB_NAME][
                settings.MONGODB_COLLECTION_NAME
            ]
            self.summary_collection = self.client[settings.MONGODB_DB_NAME][
                settings.MONGODB_SUMMARY_COLLECTION_NAME
            ]

    async def close(self):
        """Close the MongoDB client connection."""
        if self.client:
            print("Closing MongoDB connection...")
            try:
                self.client.close()
                self.client = None
                print("MongoDB connection closed")
            except Exception as e:
                print(f"Error closing MongoDB connection: {e}")

    async def initialize_session(self, user_query: str) -> None:
        """
        Initialize a new session in MongoDB.

        Args:
            session_id: The session identifier
            user_query: Initial user query
        """
        self._ensure_connection()

        # Create session document
        await self.collection.insert_one(
            {
                "session_id": session_state.get(),
                "user_query": user_query,
                "status": "in_progress",
                "start_time": datetime.now(),
                "last_updated": datetime.now(),
                "total_iterations": 0,
            }
        )

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
    ):
        """
        Add an iteration to MongoDB storage.

        Args:

            agent_name: Name of the agent
            thought: Agent's thought process
            action: Action taken by the agent
            observation: Result observed after the action
            tool_call_requires: Whether a tool call is required
            action_input: Input provided for the action
            status: Current status of the iteration
            task_id: Optional ID of the task this iteration belongs to

        Returns:
            The ID of the inserted iteration
        """
        self._ensure_connection()

        # Convert observation to string if needed
        if not isinstance(observation, str):
            observation = str(observation)

        # Create iteration document
        iteration = HistoryDomain(
            session_id=session_state.get(),
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            tool_call_requires=tool_call_requires,
            action_input=action_input,
            status=status,
            task_id=task_id,
        )

        # Insert into MongoDB
        iteration_dict = iteration.to_dict()
        result = await self.collection.insert_one(iteration_dict)

        # Update session metadata
        result = await self.collection.update_one(
            {"session_id": session_state.get()},
            {
                "$inc": {"total_iterations": 1},
                "$set": {"last_updated": datetime.now()},
            },
        )

        return True

    async def add_iteration_to_vector_db(
        self,
        session_id: str,
        agent_name: str,
        thought: str,
        action: str,
        observation: Any,
        task_id: Optional[int] = None,
    ) -> None:
        """
        Add an iteration to the vector database for RAG retrieval.

        Args:
            session_id: The session identifier
            agent_name: Name of the agent
            thought: Agent's thought process
            action: Action taken by the agent
            observation: Result observed after the action
            task_id: Optional ID of the task this iteration belongs to
        """
        # Convert observation to string if needed
        if not isinstance(observation, str):
            observation = str(observation)

        # Create a single chunk of text by combining thought, action, and observation
        chunk_text = (
            f"Thought: {thought}\nAction: {action}\nObservation: {observation}"
        )

        # Generate a unique ID for the vector
        vector_id = str(uuid.uuid4())

        # Create metadata dictionary
        metadata = {
            "session_id": session_id,
            "agent_name": agent_name,
            "timestamp": datetime.now().isoformat(),
        }

        # Add task_id to metadata if provided
        if task_id is not None:
            metadata["task_id"] = task_id

        async with PineconeAsyncio(api_key=settings.PINECONE_API_KEY) as pc:
            if not await pc.has_index(settings.INDEX_NAME):
                desc = await pc.create_index_for_model(
                    name=settings.INDEX_NAME,
                    cloud="aws",
                    region="us-east-1",
                    embed={
                        "model": "llama-text-embed-v2",
                        "field_map": {"text": "chunk_text"},
                    },
                )
                time.sleep(10)

            async with pc.IndexAsyncio(host=settings.INDEX_HOST) as index:
                await index.upsert_records(
                    namespace="",
                    records=[
                        {"_id": vector_id, "chunk_text": chunk_text, **metadata}
                    ],
                )

    async def add_summary(
        self,
        agent_name: str,
        content: str,
        start_idx: int,
        end_idx: int,
        task_id: Optional[int] = None,
    ) -> str:
        """
        Add a summary to MongoDB storage.

        Args:
            session_id: The session identifier
            agent_name: Name of the agent
            content: Summary content
            start_idx: Start index for the summary
            end_idx: End index for the summary
            task_id: Optional task ID

        Returns:
            ID of the inserted summary
        """
        self._ensure_connection()

        # Create summary document
        summary = Summary(
            summary_id=str(uuid.uuid4()),
            session_id=session_state.get(),
            agent_name=agent_name,
            content=content,
            start_idx=start_idx,
            end_idx=end_idx,
            task_id=task_id,
            timestamp=datetime.now(),
        )

        result = await self.summary_collection.insert_one(summary.to_dict())

        return summary.summary_id

    async def get_history(self, session_id: str) -> History:
        """
        Get complete conversation history.

        Args:
            session_id: The session identifier

        Returns:
            Complete conversation history
        """
        self._ensure_connection()

        # Get session metadata
        session = await self.collection.find_one({"session_id": session_id})
        if not session:
            return History(
                user_query="",
                iterations=[],
                total_iterations=0,
                final_status="in_progress",
            )

        # Get all iterations for the session
        cursor = self.collection.find({"session_id": session_id})
        iterations = await cursor.to_list(length=None)

        # Convert to SingleIteration objects
        single_iterations = []
        for iteration in iterations:
            single_iterations.append(
                SingleIteration(
                    agent_name=iteration.get("agent_name", "Unknown Agent"),
                    thought=iteration.get("thought", "No thought recorded"),
                    action=iteration.get("action", "No action taken"),
                    observation=iteration.get(
                        "observation", "No observation recorded"
                    ),
                    tool_call_requires=iteration.get(
                        "tool_call_requires", False
                    ),
                    action_input=iteration.get(
                        "action_input", "Not applicable"
                    ),
                    status=iteration.get("status", "in_progress"),
                    task_id=iteration.get("task_id", None),
                )
            )

        # Determine final status
        final_status = session.get("status", "in_progress")
        if final_status not in ["in_progress", "completed"]:
            final_status = "in_progress"

        # Get user query from session
        user_query = session.get("user_query", "")

        return History(
            user_query=user_query,
            iterations=single_iterations,
            total_iterations=session.get("total_iterations", 0),
            final_status=final_status,
        )

    async def get_task_history(
        self, session_id: str, task_ids: List[int]
    ) -> History:
        """
        Get history specific to tasks.

        Args:
            session_id: The session identifier
            task_ids: List of task IDs

        Returns:
            Task-specific conversation history
        """
        self._ensure_connection()

        # Get session for user_query
        session = await self.collection.find_one({"session_id": session_id})
        user_query = session.get("user_query", "") if session else ""

        # Get iterations for specific tasks
        cursor = self.collection.find(
            {"session_id": session_id, "task_id": {"$in": task_ids}}
        )
        iterations = await cursor.to_list(length=None)

        # Convert to SingleIteration objects
        single_iterations = []
        for iteration in iterations:
            single_iterations.append(
                SingleIteration(
                    agent_name=iteration.get("agent_name", "Unknown Agent"),
                    thought=iteration.get("thought", "No thought recorded"),
                    action=iteration.get("action", "No action taken"),
                    observation=iteration.get(
                        "observation", "No observation recorded"
                    ),
                    tool_call_requires=iteration.get(
                        "tool_call_requires", False
                    ),
                    action_input=iteration.get(
                        "action_input", "Not applicable"
                    ),
                    status=iteration.get("status", "in_progress"),
                    task_id=iteration.get("task_id", None),
                )
            )

        # Determine final status - If any iteration has status "in_progress", then the whole history is in_progress
        final_status = "completed"
        for iteration in single_iterations:
            if iteration.status == "in_progress":
                final_status = "in_progress"
                break

        return History(
            user_query=user_query,
            iterations=single_iterations,
            total_iterations=len(single_iterations),
            final_status=final_status,
        )

    async def get_latest_summary(
        self, session_id: str, agent_name: str
    ) -> Optional[Summary]:
        """
        Get the latest summary for an agent.

        Args:
            session_id: The session identifier
            agent_name: The agent name

        Returns:
            Latest summary if available
        """
        self._ensure_connection()

        # Find the latest summary for the agent
        summary = await self.summary_collection.find_one(
            {
                "session_id": session_id,
                "agent_name": agent_name,
                "task_id": None,  # General summary, not task-specific
            },
            sort=[("timestamp", -1)],  # Sort by timestamp descending
        )

        if summary:
            return Summary(**summary)

        return None

    async def get_latest_task_summary(
        self, session_id: str, task_id: int
    ) -> Optional[Summary]:
        """
        Get the latest summary for a task.

        Args:
            session_id: The session identifier
            task_id: The task ID

        Returns:
            Latest task summary if available
        """
        self._ensure_connection()

        # Find the latest summary for the task
        summary = await self.summary_collection.find_one(
            {"session_id": session_id, "task_id": task_id},
            sort=[("timestamp", -1)],  # Sort by timestamp descending
        )

        if summary:
            return Summary(**summary)

        return None

    async def complete_session(self, session_id: str) -> None:
        """
        Mark a session as completed.

        Args:
            session_id: The session identifier
        """
        self._ensure_connection()

        # Update session status
        await self.collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": "completed", "end_time": datetime.now()}},
        )


global_long_term_memory = LongTermMemory()
