from typing import Any, Dict, List, Optional

from google.genai import types
from pinecone import PineconeAsyncio

from src.config.settings import settings
from src.llms.gemini_llm import GeminiLLM
from src.memory.long_term.long_term_memory import LongTermMemory
from src.memory.short_term.short_term_memory import ShortTermMemory
from src.models.schema.histrory_schema import History, SingleIteration
from src.models.schema.memory_schema import ContextIntent
from src.prompts.memory_management_prompts import (
    INTENT_CLASSIFICATION_SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_USER_PROMPT,
    SUMMARIZATION_SYSTEM_PROMPT,
    SUMMARIZATION_USER_PROMPT,
)
from src.utils.response_parser import parse_response
from src.utils.session_context import session_state


class MemoryManager:
    """
    Centralized memory management system that coordinates short-term and long-term memory operations.

    This class handles context retrieval, intent determination, and summary generation
    based on the orchestrator's execution plan and individual agent needs.
    """

    def __init__(self):
        """Initialize the memory manager."""
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.llm = GeminiLLM()
        self.conversation_length_threshold = (
            10  # Threshold to trigger summarization
        )

    async def close(self):
        """Close all database connections properly."""
        print("Closing all memory connections...")
        try:
            # Close Redis connection
            await self.short_term.close()

            # If your LongTermMemory has MongoDB connections that need closing, add that here
            print("Memory connections closed")
        except Exception as e:
            print(f"Error closing memory connections: {e}")

    async def initialize_session(self, session_id: str, user_query: str) -> str:
        """
        Initialize a new session in both short-term and long-term memory.

        Args:
            session_id: The session identifier
            user_query: Initial user query

        Returns:
            Session ID for the new session
        """
        # Initialize in both memory systems
        await self.short_term.initialize_session(user_query)
        await self.long_term.initialize_session(user_query)

        return session_id

    async def add_iteration(
        self,
        session_id: str,
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
        Add an iteration to both short-term and long-term memory.

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
        # Add to short-term memory first
        await self.short_term.add_iteration(
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            tool_call_requires=tool_call_requires,
            action_input=action_input,
            status=status,
            task_id=task_id,
        )

        # Add to long-term memory
        iteration_id = await self.long_term.add_iteration(
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            tool_call_requires=tool_call_requires,
            action_input=action_input,
            status=status,
            task_id=task_id,
        )

        # Get updated history with the new iteration count
        history = await self.long_term.get_history(session_id)

        # Log the current iteration details
        print(
            "=========================================================================================="
        )
        print(
            "=========================================================================================="
        )
        print(f"Total Iterations: {history.total_iterations}")
        print(f"Current status: {status}")
        print(f"Agent: {agent_name}")
        print(f"Task ID: {task_id if task_id else 'None'}")
        print(f"Action: {action}")
        print(f"Observation: {observation}")
        print(
            "=========================================================================================="
        )
        print(
            "=========================================================================================="
        )

        # Store in vector DB for RAG
        await self.long_term.add_iteration_to_vector_db(
            session_id=session_id,
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            task_id=task_id,
        )

        # Check if we need to create a summary
        await self._check_and_generate_summary(session_id, agent_name, task_id)

    async def _check_and_generate_summary(
        self, session_id: str, agent_name: str, task_id: Optional[int] = None
    ) -> None:
        """
        Check if we need to generate a summary and generate if needed.

        Args:
            session_id: The session identifier
            agent_name: Name of the agent
            task_id: Optional task ID
        """
        # Get session metadata
        if task_id is None:
            # For orchestrator/general summaries
            metadata = await self.short_term.get_context(session_id)
            total_iterations = metadata.get("total_iterations", 0)

            # Check if we've reached the threshold
            if (
                total_iterations > 0
                and total_iterations % self.conversation_length_threshold == 0
            ):
                # Get history from long-term memory for summarizing
                history = await self.long_term.get_history(session_id)

                # Get latest summary if available
                latest_summary = await self.long_term.get_latest_summary(
                    session_id, agent_name
                )

                # Determine range to summarize
                start_idx = 0
                if latest_summary:
                    start_idx = latest_summary.end_idx + 1
                end_idx = total_iterations - 1

                # Only summarize if we have new iterations
                if end_idx >= start_idx:
                    # Generate summary
                    summary_content = await self._generate_summary(
                        history.iterations[start_idx : end_idx + 1]
                    )

                    # Store summary
                    await self.long_term.add_summary(
                        agent_name=agent_name,
                        content=summary_content,
                        start_idx=start_idx,
                        end_idx=end_idx,
                        task_id=None,
                    )
        else:
            # For task-specific summaries
            # Get task-specific iterations
            task_history = await self.long_term.get_task_history(
                session_id, [task_id]
            )
            total_iterations = (
                task_history.total_iterations if task_history else 0
            )

            # Check if we've reached the threshold
            if (
                total_iterations > 0
                and total_iterations % self.conversation_length_threshold == 0
            ):
                # Get latest task-specific summary if available
                latest_summary = await self.long_term.get_latest_task_summary(
                    session_id, task_id
                )

                # Determine range to summarize
                start_idx = 0
                if latest_summary:
                    start_idx = latest_summary.end_idx + 1
                end_idx = total_iterations - 1

                # Only summarize if we have new iterations
                if end_idx >= start_idx:
                    # Generate summary
                    summary_content = await self._generate_summary(
                        task_history.iterations[start_idx : end_idx + 1]
                    )

                    # Store summary
                    await self.long_term.add_summary(
                        agent_name=agent_name,
                        content=summary_content,
                        start_idx=start_idx,
                        end_idx=end_idx,
                        task_id=task_id,
                    )

    async def _generate_summary(self, iterations: List[SingleIteration]) -> str:
        """
        Generate a summary of iterations using the LLM.

        Args:
            iterations: List of iterations to summarize

        Returns:
            Generated summary content
        """

        # Get the session and agent information from the first iteration
        if iterations:
            session_id = session_state.get()
            agent_name = iterations[0].agent_name
            task_id = iterations[0].task_id

            # Get the previous summary if available
            previous_summary = None
            if task_id:
                previous_summary = await self.long_term.get_latest_task_summary(
                    session_id, task_id
                )
            else:
                previous_summary = await self.long_term.get_latest_summary(
                    session_id, agent_name
                )

            previous_summary_text = (
                previous_summary.content
                if previous_summary
                else "No previous summary available."
            )
        else:
            previous_summary_text = "No previous summary available."

        # Fill the prompt template with both previous summary and new iterations
        config = types.GenerateContentConfig(
            system_instruction=SUMMARIZATION_SYSTEM_PROMPT
        )
        prompt = SUMMARIZATION_USER_PROMPT.format(
            summary=previous_summary_text, iterations=iterations
        )

        # Call the LLM to generate a summary
        response = await self.llm.generate_response(
            config=config, contents=prompt
        )
        response = parse_response(response)
        return response.get("summary", "No summary generated.")

    async def get_task_context(
        self,
        session_id: str,
        agent_name: str,
        task: str,
        task_id: int,
        dependencies: List[int],
    ) -> Dict[str, Any]:
        """
        Get the appropriate context for a task based on intent classification.

        Args:
            session_id: The session identifier
            agent_name: Name of the agent
            task: The task description
            task_id: The task ID
            dependencies: List of task IDs this task depends on

        Returns:
            Context dictionary with relevant information for the task
        """
        # Get the original user query
        user_query = await self.short_term.get_user_query()

        # Get recent iterations (always included)
        recent_iterations = await self.short_term.get_recent_iterations(
            session_id
        )

        # For tasks with no dependencies, we skip intent classification
        if not dependencies:
            return {
                "user_query": user_query,
                "task": task,
                "recent_history": recent_iterations,
                "summary": None,
                "rag_results": None,
            }

        # # Get dependent task histories
        # dependent_history = await self.long_term.get_task_history(session_id, dependencies)

        # Get any existing summaries
        summaries = []
        for dep_task_id in dependencies:
            summary = await self.long_term.get_latest_task_summary(
                session_id, dep_task_id
            )
            if summary:
                summaries.append(summary.content)

        # Format summaries for intent classification
        summary_text = ""
        for i, summary in enumerate(summaries):
            summary_text += (
                f"Summary {i+1} (Task ID: {dependencies[i]}):\n{summary}\n\n"
            )

        # Call intent classification
        intent = await self._classify_intent(
            user_query=user_query,
            task=task,
            agent_name=agent_name,
            summary=summary_text,
            recent_iterations=recent_iterations,
        )

        # Build context based on intent
        context = {
            "user_query": user_query,
            "task": task,
            "recent_history": recent_iterations,
            "summary": None,
            "rag_results": None,
        }

        # Add summary if needed
        if intent.requires_summary and summaries:
            context["summary"] = summaries

        # Add RAG results if needed
        if intent.requires_rag:
            # RAG query is either the specified one or the task itself
            query = intent.rag_query or task

            # Build filters
            filters = intent.rag_filters or {}

            rag_results = await self.retrieve_from_vectordb(
                query, task, agent_name, session_id
            )
            context["rag_results"] = rag_results

        return context

    async def _classify_intent(
        self,
        user_query: str,
        task: str,
        agent_name: str,
        summary: str,
        recent_iterations,
    ) -> ContextIntent:
        """
        Classify the intent to determine what context is needed.

        Args:
            user_query: The original user query
            task: The current task
            agent_name: Name of the agent
            summary: Summary of past conversations
            recent_iterations: Recent conversation history

        Returns:
            ContextIntent classification
        """
        # Fill the prompt template
        content = INTENT_CLASSIFICATION_USER_PROMPT.format(
            user_query=user_query,
            task=task,
            agent_name=agent_name,
            summary=summary or "No summary available.",
            recent_iterations=recent_iterations
            or "No recent history available.",
        )
        config = types.GenerateContentConfig(
            system_instruction=INTENT_CLASSIFICATION_SYSTEM_PROMPT
        )

        # Call the LLM with system and user prompts
        response = await self.llm.generate_response(
            config=config, contents=content
        )

        intent_data = parse_response(response)
        print(intent_data)
        # Parse the JSON response
        try:
            return ContextIntent(
                requires_summary=intent_data.get("requires_summary", False),
                requires_rag=intent_data.get("requires_rag", False),
                requires_recent_only=intent_data.get(
                    "requires_recent_only", True
                ),
                rag_query=intent_data.get("rag_query"),
                rag_filters=(
                    {
                        "agent_name": intent_data.get("filter_by_agent"),
                        "task_id": intent_data.get("filter_by_task_id"),
                        "time_range": intent_data.get("filter_by_time_range"),
                    }
                    if any(
                        key in intent_data
                        for key in [
                            "filter_by_agent",
                            "filter_by_task_id",
                            "filter_by_time_range",
                        ]
                    )
                    else None
                ),
                confidence=intent_data.get("confidence", 1.0),
                reasoning=intent_data.get("reasoning", ""),
            )
        except Exception as e:
            # Default to recent only if parsing fails
            return ContextIntent(
                requires_summary=False,
                requires_rag=False,
                requires_recent_only=True,
                confidence=0.5,
                reasoning="Intent classification failed, defaulting to recent only.",
            )

    async def complete_session(self, session_id: str) -> None:
        """
        Mark a session as completed in both short-term and long-term memory.

        Args:
            session_id: The session identifier
        """
        await self.short_term.complete_session(session_id)
        await self.long_term.complete_session(session_id)

    async def get_complete_history(self, session_id: str) -> History:
        """
        Get the complete conversation history for a session.

        Args:
            session_id: The session identifier

        Returns:
            Complete conversation history
        """
        try:
            return await self.long_term.get_history(session_id)
        except Exception as e:
            print(f"Error retrieving complete history: {e}")
            # Return a properly formatted empty History object
            return History(
                user_query="",
                iterations=[],
                total_iterations=0,
                final_status="in_progress",
            )

    async def get_task_history(
        self, session_id: str, task_ids: List[int]
    ) -> History:
        """
        Get history specific to the given task IDs.

        Args:
            session_id: The session identifier
            task_ids: List of task IDs to retrieve history for

        Returns:
            Task-specific conversation history
        """
        try:
            return await self.long_term.get_task_history(session_id, task_ids)
        except Exception as e:
            print(f"Error retrieving task history: {e}")
            # Return a properly formatted empty History object
            return History(
                user_query="",
                iterations=[],
                total_iterations=0,
                final_status="in_progress",
            )

    async def retrieve_from_vectordb(
        self, query: str, task: str, agent_name: str, session_id: str
    ) -> List[str]:
        """
        Retrieve relevant context from the vector database.

        Args:
            user_query: The original user query
            task: The current task
            agent_name: Name of the agent
            session_id: The session identifier

        Returns:
            List of relevant context items retrieved from the vector database
        """
        try:
            async with PineconeAsyncio(api_key=settings.PINECONE_API_KEY) as pc:
                async with pc.IndexAsyncio(settings.INDEX_HOST) as index:

                    # Combine query and task for better context
                    query_text = f"{query} {task}"

                    # Perform the query
                    response = await index.search_records(
                        namespace="",
                        query={
                            "query": query_text,
                            "top_k": settings.RAG_TOP_K,
                        },
                    )

                # Parse the response (handling different Pinecone formats)
                results = []
                if hasattr(response, "matches"):
                    # Standard Pinecone response format
                    for match in response.matches:
                        if match.metadata and "chunk_text" in match.metadata:
                            results.append(match.metadata["chunk_text"])
                elif isinstance(response, dict) and "result" in response:
                    # Serverless response format
                    hits = response.get("result", {}).get("hits", [])
                    for hit in hits:
                        chunk_text = hit.get("fields", {}).get("chunk_text")
                        if chunk_text:
                            results.append(chunk_text)

                return results
        except Exception as e:
            print(f"Error retrieving from vector DB: {e}")
            return []


# Create a global instance of MemoryManager
global_memory_manager = MemoryManager()
