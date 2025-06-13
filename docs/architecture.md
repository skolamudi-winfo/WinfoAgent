# Architecture Overview

## Introduction
This document provides an overview of the architecture of the ChatBot application. It outlines the key components, their responsibilities, and how they interact with each other.

## Architecture Diagram
[Insert architecture diagram here]

## Components

### 1. Main Application (`src/main.py`)
The entry point of the application that initializes and starts the chatbot services.

### 2. Chatbot Module (`src/chatbot`)
This module contains the core logic for different types of chatbots:
- **Sales ChatBot**: Handles sales-related queries and interactions.
- **Support ChatBot**: Manages support-related inquiries and provides assistance.
- **Oracle Support Process**: Specific functionalities related to Oracle support processes.

### 3. Services Module (`src/services`)
This module encapsulates various services used by the chatbot:
- **Database Service**: Manages database interactions, including data retrieval and storage.
- **Embedding Service**: Handles the generation and storage of content embeddings for improved search and response capabilities.
- **Content Preparation Service**: Responsible for processing and preparing content for the chatbot.

### 4. Utilities Module (`src/utils`)
Contains utility functions and classes that support the main application, including:
- **Logger**: Centralized logging functionality for tracking application behavior and errors.
- **Query Executor**: Facilitates the execution of database queries.
- **String Utilities**: Provides helper functions for string manipulation.

### 5. Configuration Module (`src/config`)
Holds configuration settings and external resources, such as API keys and application settings.

## Data Flow
1. User interacts with the chatbot through a user interface.
2. The main application processes the input and routes it to the appropriate chatbot module.
3. The chatbot module may call upon services to retrieve data or perform actions.
4. Responses are generated and sent back to the user.

## Conclusion
The architecture of the ChatBot application is designed to be modular and scalable, allowing for easy maintenance and future enhancements. Each component has a clear responsibility, promoting separation of concerns and improving code readability.