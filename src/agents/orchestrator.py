import asyncio
from typing import Any, Dict, List, Set

from google.genai import types

from src.agents.agent_registry import global_agent_registry
from src.agents.research_expert import ResearchExpert
from src.agents.weather_expert import WeatherExpert
from src.config.settings import settings
from src.human_loop.human_feedback import global_feedback_registry
from src.llms.gemini_llm import GeminiLLM
from src.memory.memory_manager import global_memory_manager
from src.models.schema.agent_schema import Agent
from src.prompts.human_feedback_prompts import (
    EXECUTION_PLAN_FEEDBACK_PROMPT,
    FINAL_RESPONSE_FEEDBACK_PROMPT,
)
from src.prompts.orchestator_prompt import (
    EVALUATION_PROMPT,
    ORCHESTARTOR_SYSTEM_PROMPT,
    ORCHESTARTOR_USER_PROMPT,
)
from src.utils.memory_store import store_iteration
from src.utils.response_parser import parse_response
from src.utils.session_context import session_state


class OrchestratorAgent:
    """
    Orchestrator Agent Module

    This agent controls and coordinates all other agents in the system.
    It handles task distribution, communication between agents, and overall workflow management.
    """

    def __init__(self):
        """
        Initialize the orchestrator agent.

        Args:
            config: Configuration for the orchestrator
        """
        self.llm = GeminiLLM()
        self.session_id = session_state.get()
        self.research_expert = ResearchExpert()
        self.weather_expert = WeatherExpert()
        self.completed_tasks: Set[int] = set()
        self.task_results: Dict[int, Any] = {}

    def get_available_agents(self) -> List[Agent]:
        """
        Get the list of registered agents.

        Returns:
            list: The list of registered agents.
        """
        return global_agent_registry.get_all_agents()

    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Execute a single task using the appropriate agent.

        Args:
            task: The task to execute

        Returns:
            The result of the task execution
        """
        task_id = task["task_id"]
        agent_name = task["agent"]
        task_description = task["task"]

        # Add parent_ids if there are dependencies
        dependencies = task.get("dependencies", [])

        # Execute the agent with the task
        result = await global_agent_registry.execute_agent(
            task_id=task_id,
            agent_name=agent_name,
            task=task_description,
            parent_ids=dependencies,
        )

        # Store the result
        self.task_results[task_id] = result
        self.completed_tasks.add(task_id)

        return result

    async def execute_execution_plan(
        self, execution_plan: List[Dict[str, Any]]
    ) -> str:
        """
        Execute the tasks in the execution plan respecting dependencies.

        Args:
            execution_plan: The execution plan with tasks and dependencies

        Returns:
            The final result after all tasks are completed
        """
        # Reset state for new execution plan
        self.completed_tasks = set()
        self.task_results = {}

        # Continue until all tasks are completed
        while len(self.completed_tasks) < len(execution_plan):
            # Find tasks that can be executed (all dependencies are satisfied)
            executable_tasks = []
            for task in execution_plan:
                task_id = task["task_id"]

                # Skip already completed tasks
                if task_id in self.completed_tasks:
                    continue

                # Check if all dependencies are completed
                dependencies = task.get("dependencies", [])
                if all(
                    dep_id in self.completed_tasks for dep_id in dependencies
                ):
                    executable_tasks.append(task)

            if not executable_tasks:
                # If no tasks can be executed but we haven't completed all tasks,
                # there might be a circular dependency
                raise ValueError(
                    "Circular dependency detected in execution plan"
                )

            # Execute all executable tasks in parallel
            tasks = [self.execute_task(task) for task in executable_tasks]
            await asyncio.gather(*tasks)

            # If we've completed the ResponseSynthesizerExpert task, return its result
            for task in executable_tasks:
                if (
                    task["agent"] == "ResponseSynthesizerExpert"
                    and task["task_id"] in self.completed_tasks
                ):
                    return self.task_results[task["task_id"]]

        # If we've completed all tasks but there's no ResponseSynthesizerExpert,
        # return the result of the last task
        last_task_id = max(task["task_id"] for task in execution_plan)
        return self.task_results[last_task_id]

    async def start(self, user_query: str) -> str:
        """
        Start the orchestrator agent.

        This method initializes the agent and starts the main loop for task management.
        """
        # Initialize the memory manager with the user query
        try:
            await global_memory_manager.initialize_session(
                session_id=self.session_id, user_query=user_query
            )
        except Exception as e:
            print(f"Error initializing memory system: {e}")
            # Proceed anyway as the agent should be resilient to memory errors

        final_result = None
        agent_result = None

        # Create a while loop to keep the orchestrator agent running
        while True:
            # Get context using the context-aware memory retrieval system
            try:
                history = await global_memory_manager.get_complete_history(
                    session_id=self.session_id
                )
            except Exception as e:
                print(f"Error retrieving memory context: {e}")
                history = "Error retrieving conversation history"

            # Generate next action using the orchestrator prompt
            content = ORCHESTARTOR_USER_PROMPT.format(history=history)
            config = types.GenerateContentConfig(
                system_instruction=ORCHESTARTOR_SYSTEM_PROMPT.format(
                    available_agents=self.get_available_agents()
                )
            )

            response = await self.llm.generate_response(
                config=config, contents=content
            )

            response_data = parse_response(response)

            # Check if the response contains an execution plan
            execution_plan = response_data.get("execution_plan", None)

            if not execution_plan:
                # Store iteration in memory
                await store_iteration(
                    session_id=self.session_id,
                    agent_name="OrchestratorAgent",
                    thought=response_data.get("thought"),
                    action=response_data.get("action"),
                    observation="not applicable",
                    action_input=response_data.get("action_input"),
                    tool_call_requires=response_data.get("tool_call_requires"),
                    status=response_data.get("status"),
                )

            # If we have an execution plan, execute it
            if execution_plan:
                # Get human feedback on the execution plan if enabled
                feedback = global_feedback_registry.get_human_feedback(
                    response=EXECUTION_PLAN_FEEDBACK_PROMPT.format(
                        execution_plan=execution_plan
                    ),
                    agent_name="OrchestratorAgent",
                )

                if feedback["status"] == "feedback":
                    # Store the feedback in memory
                    await store_iteration(
                        session_id=self.session_id,
                        agent_name="OrchestratorAgent",
                        thought=f"I received feedback from human user which I must use to rebuild the execution plan",
                        action="Process Feedback",
                        observation=f"User feedback: {feedback['feedback']}",
                        action_input=execution_plan,
                        tool_call_requires=False,
                        status="in_progress",
                    )
                    continue
                else:
                    # Execute the plan
                    result = await self.execute_execution_plan(execution_plan)
                    final_result = result

                    # Record the execution result
                    await store_iteration(
                        session_id=self.session_id,
                        agent_name="OrchestratorAgent",
                        thought="I have executed the plan and received results",
                        action="Execute Plan",
                        observation=result,
                        action_input=execution_plan,
                        tool_call_requires=False,
                        status="in_progress",
                    )

                    # Evaluate response quality
                    quality_check = await self._evaluate_response_quality(
                        user_query, result
                    )

                    if (
                        str(quality_check["is_response_adequate"]).lower()
                        == "true"
                    ):
                        # If response is adequate, get final user feedback
                        await store_iteration(
                            session_id=self.session_id,
                            agent_name="OrchestratorAgent",
                            thought="The response adequately addresses the user query",
                            action="Quality Check",
                            observation="Response quality check passed",
                            action_input="",
                            tool_call_requires=False,
                            status="in_progress",
                        )

                        # Get final user feedback
                        feedback = global_feedback_registry.get_human_feedback(
                            response=FINAL_RESPONSE_FEEDBACK_PROMPT.format(
                                final_response=final_result
                            ),
                            agent_name="OrchestratorAgent",
                        )

                        if feedback["status"] == "feedback":
                            # If user has feedback, continue the loop
                            await store_iteration(
                                session_id=self.session_id,
                                agent_name="OrchestratorAgent",
                                thought=f"User provided feedback on the final response",
                                action="Process Feedback",
                                observation=f"User feedback: {feedback['feedback']}",
                                action_input=final_result,
                                tool_call_requires=False,
                                status="in_progress",
                            )
                            continue
                        else:
                            # Mark session as complete and return
                            await store_iteration(
                                session_id=self.session_id,
                                agent_name="OrchestratorAgent",
                                thought="User is satisfied with the response",
                                action="Complete Session",
                                observation="Task completed successfully",
                                action_input="",
                                tool_call_requires=False,
                                status="completed",
                            )

                            # Complete the memory session
                            try:
                                await global_memory_manager.complete_session(
                                    self.session_id
                                )
                            except Exception as e:
                                print(f"Error completing memory session: {e}")

                            return final_result
                    else:
                        # If quality check fails, continue to improve
                        await store_iteration(
                            session_id=self.session_id,
                            agent_name="OrchestratorAgent",
                            thought=f"The response needs improvement based on quality check",
                            action="Revise Plan",
                            observation=f"Quality feedback: {quality_check['feedback']}",
                            action_input="",
                            tool_call_requires=False,
                            status="in_progress",
                        )

            # Process direct agent calls
            elif str(response_data.get("tool_call_requires")).lower() == "true":
                # Execute agent directly
                agent_result = await global_agent_registry.execute_agent(
                    agent_name=response_data["action"],
                    task=response_data["action_input"],
                )

                # Special handling for ResponseSynthesizerExpert
                if response_data.get("action") == "ResponseSynthesizerExpert":
                    final_result = agent_result
                    quality_check = await self._evaluate_response_quality(
                        user_query, final_result
                    )

                    if (
                        str(quality_check["is_response_adequate"]).lower()
                        == "true"
                    ):
                        # If response is adequate, get final user feedback
                        feedback = global_feedback_registry.get_human_feedback(
                            response=FINAL_RESPONSE_FEEDBACK_PROMPT.format(
                                final_response=final_result
                            ),
                            agent_name="OrchestratorAgent",
                        )

                        if feedback["status"] == "feedback":
                            # Process feedback and continue
                            await store_iteration(
                                session_id=self.session_id,
                                agent_name="OrchestratorAgent",
                                thought=f"Received feedback on final response",
                                action="Process Feedback",
                                observation=f"User feedback: {feedback['feedback']}",
                                action_input=final_result,
                                tool_call_requires=False,
                                status="in_progress",
                            )
                            continue
                        else:
                            # Mark as complete and return
                            await store_iteration(
                                session_id=self.session_id,
                                agent_name="OrchestratorAgent",
                                thought="User is satisfied with the response",
                                action="Complete Session",
                                observation="Task completed successfully",
                                action_input="",
                                tool_call_requires=False,
                                status="completed",
                            )

                            # Complete memory session
                            try:
                                await global_memory_manager.complete_session(
                                    self.session_id
                                )
                            except Exception as e:
                                print(f"Error completing memory session: {e}")

                            return final_result
                    else:
                        # If quality check fails, continue to improve
                        await store_iteration(
                            session_id=self.session_id,
                            agent_name="OrchestratorAgent",
                            thought=f"The synthesized response needs improvement",
                            action="Request Revision",
                            observation=f"Quality feedback: {quality_check['feedback']}",
                            action_input="",
                            tool_call_requires=False,
                            status="in_progress",
                        )

            # Check for exit conditions
            try:
                # Get updated history to check iteration count
                history_obj = await global_memory_manager.get_complete_history(
                    self.session_id
                )
                iterations_count = (
                    history_obj.total_iterations if history_obj else 0
                )

                # Exit if completed or max iterations reached
                status = response_data.get("status", "").lower()
                if (
                    status == "completed"
                    or iterations_count >= settings.MAX_ITERATIONS
                ):
                    break
            except Exception as e:
                print(f"Error checking exit conditions: {e}")
                # Simple fallback exit check
                if str(response_data.get("status")).lower() == "completed":
                    break

        # Complete memory session before exiting
        try:
            await global_memory_manager.complete_session(self.session_id)
        except Exception as e:
            print(f"Error completing memory session: {e}")

        # Return the final result or agent result
        return final_result if final_result else agent_result

    async def _evaluate_response_quality(
        self, user_query: str, response: str
    ) -> Dict:
        """
        Evaluate the quality of the response in relation to the user query.

        Args:
            user_query: The original user query
            response: The generated response to evaluate

        Returns:
            A dictionary with evaluation results
        """
        evaluation_prompt = EVALUATION_PROMPT.format(
            user_query=user_query, response=response
        )

        # Call the LLM for evaluation
        config = types.GenerateContentConfig(
            system_instruction="You are a quality control expert for AI-generated responses."
        )

        evaluation_response = await self.llm.generate_response(
            config=config, contents=evaluation_prompt
        )

        # Parse and return the evaluation results
        return parse_response(evaluation_response)
