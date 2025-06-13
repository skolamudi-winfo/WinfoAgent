# API Documentation for ChatBot Application

## Overview

This document provides an overview of the API endpoints available in the ChatBot application. The ChatBot application is designed to assist users with queries related to various products and services through a conversational interface.

## Base URL

The base URL for accessing the API is:

```
http://<hostname>:<port>/api
```

## Endpoints

### 1. Sales ChatBot

#### POST /sales/chat

- **Description**: Initiates a conversation with the sales chatbot.
- **Request Body**:
  ```json
  {
    "user_query": "string",
    "previous_conversation": "string"
  }
  ```
- **Response**:
  - **200 OK**: Returns a response from the sales chatbot.
  - **400 Bad Request**: If the request body is invalid.

### 2. Support ChatBot

#### POST /support/chat

- **Description**: Initiates a conversation with the support chatbot.
- **Request Body**:
  ```json
  {
    "data": {
      "user_message": "string",
      "chat_id": "string",
      "issue_id": "string"
    }
  }
  ```
- **Response**:
  - **200 OK**: Returns a response from the support chatbot.
  - **400 Bad Request**: If the request body is invalid.

### 3. Content Preparation

#### POST /content/prepare

- **Description**: Prepares content for the chatbot from a given file.
- **Request Body**:
  ```json
  {
    "file_path": "string",
    "product": "string",
    "process_name": "string",
    "process_area": "string",
    "sub_process": "string"
  }
  ```
- **Response**:
  - **200 OK**: Returns a status message indicating success.
  - **500 Internal Server Error**: If there is an error during content preparation.

## Error Handling

All API responses will include an error message in the following format:

```json
{
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

## Authentication

Authentication is required for accessing the API. Please include the following header in your requests:

```
Authorization: Bearer <token>
```

## Conclusion

This API documentation provides a high-level overview of the available endpoints in the ChatBot application. For further details, please refer to the source code or contact the development team.