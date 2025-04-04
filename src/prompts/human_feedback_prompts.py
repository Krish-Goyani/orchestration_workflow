QUERY_DECOMPOSER_FEEDBACK_PROMPT = """
below is the task decomposition result, please review it.

## Task Decomposition Result
{task_decomposition_result}
"""


EXECUTION_PLAN_FEEDBACK_PROMPT = """
below is the execution plan, please review it.

## Execution Plan
{execution_plan}
"""


FINAL_RESPONSE_FEEDBACK_PROMPT = """
below is the final response, please review it.

## Final Response
{final_response}
"""
