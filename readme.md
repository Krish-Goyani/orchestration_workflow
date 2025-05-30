# Multi-Agent System

A flexible, extensible multi-agent system built from scratch without relying on any specific agent framework. This system enables dynamic agent and tool management with a central orchestrator controlling the workflow.

## Overview

This system implements a multi-agent architecture where specialized agents collaborate to solve complex tasks. The orchestrator agent coordinates the process, delegating subtasks to specialized agents based on their capabilities.

Key features:
- Modular agent architecture
- Dynamic tool registration and execution
- Structured memory system for conversation tracking
- LLM-powered reasoning and decision making
- No dependency on specific agent frameworks

## Architecture

### Core Components

#### Agents
- **Orchestrator Agent**: Coordinates the entire process and delegates tasks
- **Research Expert**: Handles information retrieval and research tasks
- **Weather Expert**: Provides weather information for specific locations
- **Response Synthesizer Expert**: Compiles final responses from all agent interactions

#### Registries
- **Agent Registry**: Central registry for all agents and their tools
- **Tool Registry**: Manages available tools that agents can use

#### Memory
- **Memory Store**: Maintains conversation history and agent interactions
- **Session Context**: Manages user session state

#### LLM Integration
- **GeminiLLM**: Interface to Google's Gemini model for agent reasoning

### Tools
- **Web Search**: Search the web for information
- **URL Scraper**: Extract content from web pages
- **Weather Forecast**: Get weather information for locations

## Workflow

1. User submits a query
2. Orchestrator analyzes the query and determines which specialized agents to invoke
3. Specialized agents use their tools to gather information
4. Agents record their thoughts, actions, and observations in memory
5. Orchestrator continues to coordinate until the task is complete
6. Response Synthesizer compiles the final answer

## Getting Started

### Prerequisites
- Python 3.9+
- Google Gemini API key
- Serper API key (for web search)
- OpenWeatherMap API key



in my mind i have one approach :

<APPROACH>

orchestrator agent first call the query decomposer. the query decomposer give the output in below format:

{"task_id" : 1, "task", etc}

now based on that the orchestrator agent will design the implementation plan.

the implementation plan will be looks like :

{

  "execution_plan": [

    {

      "task_id": "1",

      "task": "Explain RAG in AI",

      "agent": "ResearchAgent",

      "dependencies": []

    },

    {

      "task_id": "2",

      "task": "Research recent findings in AI",

      "agent": "ResearchAgent",

      "dependencies": []

    },

    {

      "task_id": "3",

      "task": "synteise the final response",

      "agent": "ResponseSyntesizer",

      "dependencies": [1,2]

    }

  ]

}

once we get the execution plan we will start the all agents in parallel who dont have dependacies on others. than the agent who have the dependancies are executed.

the specialized agent only get the history iterations of that task id only and if they have the dependencies than their + their parent's history iterations.

the orchestrator and the ResponseSyntesizer get the whole history.

for that i have a thought to do the memory management in below way.

maintain the window for each task_id and once the threshold is meet do the summary of the past conversations. for every llm calls inside the Agent do the intent identification call in which give the recent 5 interactions and summary and ask the llm do the additional context required 

</APPROACH>