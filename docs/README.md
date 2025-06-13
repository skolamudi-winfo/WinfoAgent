# ChatBot Project

## Overview
The ChatBot project is designed to provide a conversational interface for users, leveraging advanced chatbot technologies. This document serves as a guide to understanding the structure, setup, and usage of the application.

## Project Structure
The project is organized into several key directories and files:

```
ChatBot/
├── src/
│   ├── main/
│   │   ├── __init__.py
│   │   ├── process.py               
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routes/                   
│   │   │   ├── __init__.py
│   │   │   ├── sales_routes.py       
│   │   │   ├── support_routes.py     
│   │   │   ├── config_routes.py      
│   │   │   ├── history_routes.py     
│   │   │   └── health_routes.py      
│	│	│                             
│   │   ├── utils/                    
│   │   │   ├── __init__.py           
│   │   │   ├── logger.py             
│   │   │   ├── query_executor.py
│   │   │   ├── string_utils.py
│   │   │   └── file_utils.py
│	│	│
│   │   ├── services/                 
│   │   │   ├── __init__.py
│   │   │   ├── database_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── content_preparation_service.py
│   │   │   └── ticket_service.py
│	│	│
│   │   ├── chatbot/                  
│   │   │   ├── __init__.py
│   │   │   ├── sales_chatbot.py
│   │   │   ├── support_chatbot.py
│   │   │   ├── oracle_support_process.py
│   │   │   └── winfo_support_process.py
│	│	│
│   │   └── metadata/                 
│   │       ├── __init__.py
│   │       ├── config_data_insertion.py
│   │       ├── nosql_table_creation.py
│   │       └── metadata_manager.py
│   │
│   ├── logs/                         
│   │   ├── app.log                   
│   │   ├── sales_chatbot/
│   │   │   ├── advanced.log          
│   │   │   ├── basic.log             
│   │   ├── support_chatbot/
│   │   │   ├── support_agent.log     
│   │   │   ├── issue_loader.log      
│   │   ├── config/
│   │   │   ├── prompt_manager.log    
│   │   │   ├── config_insertion.log  
│   │   ├── history/
│   │   │   ├── chat_history.log      
│   │   │   ├── max_query_id.log      
│   │   ├── health/
│   │   │   ├── health_check.log      
│   │   │   ├── connection_test.log   
│   │   └── other_logs/               
│   │
│   ├── docs/                         
│   │   ├── README.md                 
│   │   ├── architecture.md           
│   │   ├── api_documentation.md      
│   │   └── setup_guide.md            
│   │
│   ├── data/                         
│   │   ├── input/                    
│   │   ├── output/                   
│   │   └── temp/                     
│   │
│   ├── requirements.txt              
│   ├── setup.py                      
│   └── README.md                     
│
├── certs/                            
│   ├── cert.pem
│   ├── privkey.pem
│
├── configuration/                    
│   ├── config.json
│   ├── gcs_config.json
│   ├── Google_Key(WAI).json
│   ├── jira_config.json
│   └── ...
│
├── NoSQLMetaData/                    
│   ├── configDataInsertion.py
│   ├── nosqlTableCreation.py
│   └── logs/
│
├── sample test files/                
│   ├── test001.py
│   ├── test002.py
│   └── ...
│
├── Dockerfile                        
└── .dockerignore
```

## Installation
To set up the project, follow these steps:

1. Clone the repository:
   ```
   git clone <repository-url>
   cd ChatBot
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure your environment settings in `src/config/settings.py`.

## Usage
To run the application, execute the following command:
```
python src/main.py
```

## Testing
Unit tests are located in the `tests` directory. To run the tests, use:
```
pytest tests/
```

## Documentation
Additional documentation can be found in the `docs` directory, including:
- **architecture.md**: Overview of the system architecture.
- **api_documentation.md**: Details on the API endpoints and usage.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for discussion.

## License
This project is licensed under the MIT License. See the LICENSE file for details.