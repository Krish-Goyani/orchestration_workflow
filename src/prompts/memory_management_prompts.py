"""
Memory Management Prompts

This module contains prompts used for memory management operations:
- Intent classification to determine what context is needed
- Summarization of conversation history
"""

# System prompt for intent classification
INTENT_CLASSIFICATION_SYSTEM_PROMPT = """You are an intelligent context manager for an AI orchestration system.
Your task is to analyze the current task and determine what type of context is needed.

You need to classify the intent into one of these categories:
1. SUMMARY + RECENT: The task requires both summary and recent conversation history
2. RAG + RECENT: The task requires semantic retrieval of past conversations plus recent history
3. RECENT ONLY: The task only requires the most recent conversation history (default)

Respond in JSON format with the following fields:
- requires_summary: boolean (true if summary of past conversations is needed)
- requires_rag: boolean (true if semantic retrieval of relevant past conversations is needed)
- requires_recent_only: boolean (true if only recent conversations are needed)
- rag_query: string (optional, specific query for semantic search if different from the task)
- filter_by_agent: string (optional, filter RAG results by specific agent)
- filter_by_task_id: integer (optional, filter RAG results by task ID)
- filter_by_time_range: string (optional, "last_hour", "last_day", "last_week")
- confidence: float (confidence in your classification, 0.0-1.0)
- reasoning: string (brief explanation of your reasoning)
"""

# User prompt template for intent classification
INTENT_CLASSIFICATION_USER_PROMPT = """
USER QUERY: {user_query}

CURRENT TASK: {task}
AGENT: {agent_name}

SUMMARY OF PAST CONVERSATIONS:
{summary}

RECENT CONVERSATION HISTORY:
{recent_iterations}

Based on the current task and available context, what type of context is needed? Your response should be in JSON format.
"""
SUMMARIZATION_SYSTEM_PROMPT = """
You are tasked with creating a concise summary of a conversation between different AI agents.
The summary should capture key points, decisions, and important information discovered during the conversation.
"""
# Summarization prompt
SUMMARIZATION_USER_PROMPT = """


Here are the conversation iterations to summarize:

{iterations}
{summary}
Create a clear, concise summary of this conversation that captures the essential information.
Respond in JSON format with a single field named "summary" containing your summary text.
"""
