# ChatBot API Documentation

This document provides an overview of all available APIs in the ChatBot project, including their endpoints, descriptions, request/response formats, and usage examples.

---

## Table of Contents
- [Health Check APIs](#health-check-apis)
- [Pre-Sales Agent APIs](#pre-sales-agent-apis)
- [Support Agent APIs](#support-agent-apis)
- [Configuration APIs](#configuration-apis)
- [Chat APIs](#chat-apis)
- [Service Issues (Jira) APIs](#service-issues-jira-apis)
- [File APIs](#file-apis)

---

## Health Check APIs

### 1. `GET /Check/Health`
**Description:** Returns the health status of the ChatBot API.

**Request:**
- No body required.

**Response:**
```json
{
  "status": "Success"
}
```

---

### 2. `GET /Check/TestConnections`
**Description:** Tests connectivity to the main database, NoSQL database, and logger.

**Request:**
- No body required.

**Response:**
```json
{
  "message": "Logger and database connections are working fine."
}
```
Or, on error:
```json
{
  "error": "<error message>"
}
```

---

## Pre-Sales Agent APIs

### 1. `POST /WAI/PreSalesAgent/Advanced`
**Description:** Initiates an advanced pre-sales chatbot query as a background task.

**Request Body:**
```json
{
  // Fields as defined in SalesChatRequest model
}
```

**Response:**
```json
{
  "data_type": "text",
  "data": "Processing started in the background."
}
```

---

### 2. `POST /WAI/PreSalesAgent/Basic`
**Description:** Processes a basic pre-sales chatbot query and returns the response synchronously.

**Request Body:**
```json
{
  // Fields as defined in SalesChatRequest model
}
```

**Response:**
```json
{
  "data_type": "text",
  "data": "<response text>",
  "chat_id": "<chat id>",
  "query_id": "<query id>"
}
```

---

## Support Agent APIs

### 1. `POST /WAI/SupportAgent`
**Description:** Handles support chatbot queries for customer issues and returns the response.

**Request Body:**
```json
{
  // Fields as defined in SupportChatRequest model
}
```

**Response:**
```json
{
  "data_type": "text",
  "data": {"resolution": "<response or error message>"},
  "chat_id": "<chat id>",
  "message_id": "<message id>"
}
```

---

## Configuration APIs

### 1. `POST /WAI/Config/PromptManager`
**Description:** Insert, update, or delete prompt configurations for the chatbot. Accepts a list of prompt configurations.

**Request Body:**
```json
{
  "prompts": [
    // List of prompt configuration objects
  ]
}
```

**Response:**
- Returns the result of the operation (success/failure message or updated data).

---

### 2. `GET /WAI/Config/PromptsConfigData`
**Description:** Fetches all configured prompts from the NoSQL database.

**Request:**
- No body required.

**Response:**
- List of all prompt configurations.

---

### 3. `POST /WAI/Config/CustomerProcessDetailsManager`
**Description:** Insert, update, or delete customer process details configuration. Accepts a list of process details.

**Request Body:**
```json
{
  "process_details": [
    // List of process detail objects
  ]
}
```

**Response:**
- Returns the result of the operation (success/failure message or updated data).

---

### 4. `GET /WAI/Config/CustomerProcessConfigData`
**Description:** Fetches all configured customer process details from the NoSQL database.

**Request:**
- No body required.

**Response:**
- List of all customer process details configurations.

---

## Chat APIs

### 1. `GET /WAI/Chat/ChatID/Generate`
**Description:** Generate a chat ID for new messages.

**Request:**
- No body required.

**Response:**
```json
{
  "chat_id": "<generated chat id>"
}
```

---

### 2. `GET /WAI/Chat/ChatID/Get/{issue_id}`
**Description:** Fetches the existing chat ID for a given issue ID.

**Request:**
- Path parameter: `issue_id`

**Response:**
```json
{
  "chat_id": "<chat id>"
}
```

---

### 3. `POST /WAI/Chat/MaxMessageId`
**Description:** Retrieves the maximum message ID for a given chat session, chat ID, and issue ID.

**Request Body:**
```json
{
  "session_id": "<session id>",
  "chat_id": "<chat id>",
  "issue_id": "<issue id>"
}
```

**Response:**
```json
{
  "data_type": "text",
  "max_message_id": <number>,
  "chat_id": "<chat id>"
}
```

---

### 4. `POST /WAI/Chat/Response`
**Description:** Fetches a specific chat response from the database using chat ID and message ID.

**Request Body:**
```json
{
  "chat_id": "<chat id>",
  "message_id": "<message id>"
}
```

**Response:**
```json
{
  "data_type": "text",
  "data": "<chat response>",
  "chat_id": "<chat id>",
  "message_id": "<message id>"
}
```

---

### 5. `POST /WAI/Chat/History`
**Description:** Retrieves the full chat history for a given chat session, chat ID, and issue ID.

**Request Body:**
```json
{
  "session_id": "<session id>",
  "chat_id": "<chat id>",
  "issue_id": "<issue id>"
}
```

**Response:**
- Returns the chat history (format depends on implementation).

---

### 6. `POST /WAI/Chat/Feedback`
**Description:** Inserts or updates feedback for a specific chat message in the NoSQL database.

**Request Body:**
```json
{
  // Fields as defined in MessageFeedback model
}
```

**Response:**
- Returns the result of the feedback operation (success/failure message).

---

## Service Issues (Jira) APIs

### 1. `GET /WAI/Issues/Load`
**Description:** Triggers an asynchronous background task to fetch the latest support tickets from Jira and update the database.

**Request:**
- No body required.

**Response:**
```
Fetching the latest tickets, it will take a few minutes...
```

---

## File APIs

### 1. `POST /WAI/File/Upload`
**Description:** Uploads a file (up to 10MB) for a specific user. The file is stored in a user-specific directory with a unique filename.

**Request:**
- Multipart/form-data with fields:
  - `file`: The file to upload
  - `json_data`: JSON string containing at least `{ "username": "<username>" }`

**Response:**
- Returns the unique filename or error message.

---

### 2. `GET /WAI/File/Download`
**Description:** Downloads a previously uploaded file for a specific user.

**Request:**
- Query parameters:
  - `username`: Username who uploaded the file
  - `filename`: Original filename uploaded by the user

**Response:**
- Returns the file as a download, or error if not found.

---

### 3. `DELETE /WAI/File/Delete`
**Description:** Deletes a previously uploaded file for a specific user.

**Request:**
- Query parameters:
  - `username`: Username who uploaded the file
  - `filename`: Original filename uploaded by the user

**Response:**
- Returns success or error message.

---

## Notes
- All endpoints require HTTPS.
- Some endpoints require specific request body formats (see above).
- For detailed model schemas, refer to the codebase (`src/main/models/`).
- Most endpoints expect JSON request bodies unless otherwise specified.
- For detailed schemas and additional endpoints, refer to the OpenAPI/Swagger documentation exposed by the FastAPI server (usually at `/docs`).
---

For further details, refer to the code or contact the development team.