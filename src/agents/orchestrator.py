import asyncio
from typing import Any, Dict, List, Set

from google.genai import types

from src.agents.agent_registry import global_agent_registry
from src.agents.research_expert import ResearchExpert
from src.agents.weather_expert import WeatherExpert
from src.config.settings import settings
from src.human_loop.human_feedback import global_feedback_registry
from src.llms.gemini_llm import GeminiLLM
from src.memory.long_term.memory_store import global_memory_store
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
        while len(self.completed_tasks) <= len(execution_plan):
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
        global_memory_store.create_history(
            session_id=self.session_id, user_query=user_query
        )

        final_result = None
        agent_result = None

        # Create a while loop to keep the orchestrator agent running
        while True:
            history = global_memory_store.get_history(
                session_id=self.session_id
            )
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
                global_memory_store.add_iteration(
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
                feedback = global_feedback_registry.get_human_feedback(
                    response=EXECUTION_PLAN_FEEDBACK_PROMPT.format(
                        execution_plan=execution_plan
                    ),
                    agent_name="OrchestratorAgent",
                )
                if feedback["status"] == "feedback":
                    global_memory_store.add_iteration(
                        session_id=self.session_id,
                        agent_name="OrchestratorAgent",
                        thought=f"I received feedback from human user which i must use and according to it i should rebuild the execution plan",
                        action="",
                        observation=f"feedback from the human user: {feedback['feedback']}",
                        action_input=execution_plan,
                        tool_call_requires=False,
                        status="in_progress",
                    )
                    continue

                else:
                    result = await self.execute_execution_plan(execution_plan)

                # Store the result for potential review
                final_result = result

                global_memory_store.add_iteration(
                    session_id=self.session_id,
                    agent_name="OrchestratorAgent",
                    thought="I have built the execution plan and I have the result from the execution",
                    action="Not applicable",
                    observation=result,
                    action_input=execution_plan,
                    tool_call_requires=False,
                    status="in_progress",  # Keep as in_progress to allow for review
                )

                # Add a quality check step
                quality_check = await self._evaluate_response_quality(
                    user_query, result
                )

                if str(quality_check["is_response_adequate"]).lower() == "true":
                    # If the response is satisfactory, mark as completed and return
                    global_memory_store.add_iteration(
                        session_id=self.session_id,
                        agent_name="OrchestratorAgent",
                        thought="I have reviewed the final response and it adequately addresses the user query now i need to get feedback from the human user",
                        action="not applicable",
                        observation="Response quality check passed",
                        action_input="",
                        tool_call_requires=False,
                        status="in_progress",
                    )

                    feedback = global_feedback_registry.get_human_feedback(
                        response=FINAL_RESPONSE_FEEDBACK_PROMPT.format(
                            final_response=final_result
                        ),
                        agent_name="OrchestratorAgent",
                    )
                    if feedback["status"] == "feedback":
                        global_memory_store.add_iteration(
                            session_id=self.session_id,
                            agent_name="OrchestratorAgent",
                            thought=f"I received feedback from human user which i must use and according to it i should rebuild the execution plan(not fully built as previous one but only such that it incoporate the feedback) and the final response",
                            action="",
                            observation=f"feedback from the human user: {feedback['feedback']}",
                            action_input=final_result,
                            tool_call_requires=False,
                            status="in_progress",
                        )
                        continue
                    else:
                        return final_result

                else:
                    # If not satisfactory, add feedback and continue the loop
                    global_memory_store.add_iteration(
                        session_id=self.session_id,
                        agent_name="OrchestratorAgent",
                        thought=f"The response needs improvement i should rebuild the execution plan (not fully built as previous one) which incoporate the feedback: {quality_check['feedback']}",
                        action="Continue",
                        observation="Response quality check failed",
                        action_input="",
                        tool_call_requires=False,
                        status="in_progress",
                    )
                    # Continue the loop to generate a new execution plan or take other actions

            # Otherwise, follow the original flow
            elif str(response_data.get("tool_call_requires")).lower() == "true":
                agent_result = await global_agent_registry.execute_agent(
                    agent_name=response_data["action"],
                    task=response_data["action_input"],
                )

                if response_data.get("action") == "ResponseSynthesizerExpert":
                    # Store the result for potential review
                    final_result = agent_result

                    # Add a quality check step
                    quality_check = await self._evaluate_response_quality(
                        user_query, final_result
                    )

                    if (
                        str(quality_check["is_response_adequate"]).lower()
                        == "true"
                    ):
                        global_memory_store.add_iteration(
                            session_id=self.session_id,
                            agent_name="OrchestratorAgent",
                            thought="I have reviewed the final response and it adequately addresses the user query now i need to get feedback from the human user",
                            action="not applicable",
                            observation="Response quality check passed",
                            action_input="",
                            tool_call_requires=False,
                            status="in_progress",
                        )
                        feedback = global_feedback_registry.get_human_feedback(
                            response=FINAL_RESPONSE_FEEDBACK_PROMPT.format(
                                final_response=final_result
                            ),
                            agent_name="OrchestratorAgent",
                        )
                        if feedback["status"] == "feedback":
                            global_memory_store.add_iteration(
                                session_id=self.session_id,
                                agent_name="OrchestratorAgent",
                                thought=f"I received feedback from human user which i must use and according to it i should rebuild the execution plan(not fully built as previous one but only such that it incoporate the feedback) and the final response",
                                action="",
                                observation=f"feedback from the human user: {feedback['feedback']}",
                                action_input=final_result,
                                tool_call_requires=False,
                                status="in_progress",
                            )
                            continue
                        else:
                            return final_result
                    else:
                        # If not satisfactory, add feedback and continue the loop
                        global_memory_store.add_iteration(
                            session_id=self.session_id,
                            agent_name="OrchestratorAgent",
                            thought=f"The response needs improvement i should rebuild the execution plan (not fully built as previous one) which incoporate the feedback: {quality_check['feedback']}",
                            action="Continue",
                            observation="Response quality check failed",
                            action_input="",
                            tool_call_requires=False,
                            status="in_progress",
                        )
                        # Continue the loop to generate a new execution plan or take other actions

            if (
                str(response_data.get("status")).lower() == "completed"
                or history.total_iterations >= settings.MAX_ITERATIONS
            ):
                break

        # If we've reached the maximum iterations or the orchestrator decided to complete
        # but we have a final result, return it
        if final_result:
            return final_result

        # Otherwise, return the last agent result
        return agent_result

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

        response = parse_response(evaluation_response)

        return response
