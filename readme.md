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

