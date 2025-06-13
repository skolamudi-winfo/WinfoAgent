# Winfo AI Agents API

## Overview

Winfo AI Agents API is an enterprise-grade backend system built with FastAPI, designed to provide intelligent automation and conversational AI services for PreSales, Support, Configuration, Chat, File Management, and Service Issue (Jira) management. The platform integrates with Oracle and NoSQL databases, enforces secure HTTPS-only access, and is optimized for large-scale document and ticket management in enterprise environments.

---

## Features

- **Modular FastAPI Application**: Clean separation of concerns with routers for PreSales, Support, Configuration, Chat, File, and Service Issues, making the codebase maintainable and extensible.
- **Enterprise Security**: Enforces HTTPS for all endpoints and restricts CORS to trusted domains (`winfosolutions.com`), ensuring data privacy and compliance.
- **Database Integration**: Supports both Oracle and NoSQL (OCI) databases, enabling robust, scalable, and flexible data management for various enterprise needs.
- **Advanced Document Processing**: Handles PDF and other document uploads, performs chunking, and leverages LLMs for content extraction, summarization, and semantic search.
- **AI-Powered Agents**: Utilizes state-of-the-art LLMs (e.g., Gemini) for intelligent chat, ticket summarization, and document analysis, enhancing automation and user experience.
- **Jira Integration**: Automates ticket creation, updates, and management, streamlining support and service workflows.
- **Centralized Logging & Config Management**: All logs are stored centrally, and configuration is managed via JSON files for easy updates and environment management.
- **Utility Scripts**: Includes scripts for data loading, ticket fetching, and summary creation to support operations and maintenance.

---

## Project Structure

```
ChatBot/
│
├── Process.py                      # Main FastAPI application entry point
├── configuration/                  # Configuration files (DB, Google API, Jira, requirements)
│   ├── db_config.json
│   ├── Google_Key.json
│   ├── jira_config.json
│   └── requirements.txt
│
├── scripts/                        # Utility scripts for data and content management
│   ├── create_summary.py
│   ├── fetch_tickets_portal.py
│   └── load_files.py
│
└── src/
    ├── app/
    │   ├── chatbot/                # Chatbot and agent logic
    │   ├── metadata/               # Metadata and configuration management
    │   ├── services/               # Database and external service connectors
    │   └── utils/                  # Utility modules (PDF processing, logging, etc.)
    └── main/
        ├── models/                 # FastAPI models for each end point.
        └── routers/                # FastAPI routers for each API module
```

---

## Setup Instructions

### Prerequisites

- Python 3.12 or higher
- Access to Oracle and NoSQL (OCI) databases
- SSL certificates for HTTPS (`../certs/fullchain.pem`, `../certs/privkey.pem`, `../certs/oci_private.pem`)
- [pip](https://pip.pypa.io/en/stable/) for Python package management

### Installation

1. **Clone the repository**
    ```sh
    git clone <your-repo-url>
    cd ChatBot
    ```

2. **Install dependencies**
    ```sh
    pip install -r configuration/requirements.txt
    ```

3. **Prepare configuration files**
    - Place your `db_config.json`, `Google_Key.json`, and `jira_config.json` in the `configuration/` directory.
    - Ensure SSL certificates are available at the specified paths.

4. **Create required directories**
    ```sh
    mkdir -p DownloadedFiles/AgentFiles DownloadedFiles/JiraFiles DownloadedFiles/SupportDocs logs
    ```

5. **Run the application**
    ```sh
    python Process.py
    ```
    The server will start on port `8110` with HTTPS enabled.

---

## API Endpoints

All endpoints require HTTPS and are CORS-restricted to `winfosolutions.com` domains.

| Endpoint                        | Description                                 |
|----------------------------------|---------------------------------------------|
| `/Check`                        | Health check for the API                    |
| `/WAI/PreSalesAgent`            | PreSales agent for handling queries         |
| `/WAI`                          | Support agent for general support           |
| `/WAI/Config`                   | Configuration management                    |
| `/WAI/Chat`                     | Conversational AI chat endpoint             |
| `/WAI/File`                     | File upload and management                  |
| `/WAI/Issues`                   | Service issue (Jira) management             |

---

## Scripts

- **scripts/create_summary.py**: Summarizes ticket conversations using LLMs. Useful for generating concise overviews of support interactions.
- **scripts/load_files.py**: Loads and processes support documents, performs chunking, and embeds content for downstream AI tasks.
- **scripts/fetch_tickets_portal.py**: Fetches tickets from external portals (e.g., Jira) and prepares them for analysis or processing.

---

## Configuration

- **DB Config:** `configuration/db_config.json` — Oracle/NoSQL database connection details.
- **Google API Key:** `configuration/Google_Key.json` — Credentials for Google API integrations (e.g., Gemini LLM).
- **Jira Config:** `configuration/jira_config.json` — Jira API credentials and settings.
- **Logging Directory:** `logs/` — All application and agent logs are stored here.

---

## Security

- **HTTPS Only**: All API endpoints are accessible only via HTTPS, ensuring encrypted communication.
- **CORS Restriction**: Only trusted domains (e.g., `winfosolutions.com`) are allowed to access the API.
- **Credential Management**: Sensitive credentials are managed via configuration files and never hardcoded in the codebase.
- **Role-Based Access (optional)**: The architecture supports extension for role-based access control if required by enterprise policies.

---

## Troubleshooting & Support

- **Logs**: Check the `logs/` directory for detailed logs on API requests, errors, and agent activities.
- **Configuration Issues**: Ensure all required configuration files and SSL certificates are present and correctly formatted.
- **Database Connectivity**: Verify database credentials and network access if you encounter connection errors.

For further assistance, contact the Winfo Solutions support team.

---

## License

Proprietary. All rights reserved by Winfo Solutions.

---
