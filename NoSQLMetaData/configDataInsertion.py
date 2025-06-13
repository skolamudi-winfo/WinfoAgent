from datetime import datetime, UTC

from chatPackages.nosqlConnection import NoSQLConnectionManager as cm, NoSQLTableManager as tm


class PromptConfigManager:
    """
    A class to manage prompt configurations for NoSQL databases.
    
    Methods:
        manage_prompts_config: Handles the insertion, update, or deletion of prompt configurations.
        wai_agent_prompts_config_manager: Manages individual prompt configurations based on the operation flag.
    """

    @classmethod
    async def manage_prompts_config(cls, prompts_config_data: list, handler, logger):
        """
        Handles the insertion, update, or deletion of prompt configurations.

        Args:
            prompts_config_data (list): A list of prompt configuration dictionaries.
            handler: The database connection handler.
            logger: Logger instance for logging errors and information.

        Returns:
            str: Success or error message.
        """
        error = None
        for each_prompt_config in prompts_config_data:
            try:
                operation_flag = each_prompt_config.get('operation_flag')
                cls._wai_agent_prompts_config_manager(each_prompt_config, operation_flag, handler, logger)
            except Exception as e:
                logger.error(f"Failed in insert/update/delete prompts config details. Error: {e}")
                error = e

        if error:
            return f"ERROR: {error}"
        else:
            return "SUCCESS: Data stored to DB."

    @classmethod
    def _wai_agent_prompts_config_manager(cls, prompts_config: dict, operation_flag: str, handler, logger):
        """
        Manages individual prompt configurations based on the operation flag.

        Args:
            prompts_config (dict): The prompt configuration data.
            operation_flag (str): The operation to perform (insert, update, delete).
            handler: The database connection handler.
            logger: Logger instance for logging errors and information.

        Raises:
            ValueError: If the operation flag is invalid.
            Exception: If the database operation fails.
        """
        now_utc = datetime.now(UTC).isoformat()

        if operation_flag.lower() == "insert" or operation_flag.lower() == "i":
            prompts_config["prompt_creation_time"] = now_utc
            prompts_config["prompt_last_updated"] = now_utc
            try:
                prompts_config['agent_prompt_id'] = tm.get_next_sequence_id(handler, 'WAIAgentPromptsConfigSeqId')
                tm.execute_insert_query(handler, prompts_config, 'WAIAgentPromptsConfig')
                logger.info("Insertion of prompt details is successful.")
            except Exception as e:
                logger.error(f"Failed to insert config data - \n{prompts_config}\n\nError: {e}")
                logger.error("Insertion of prompt details is failed.")
                raise Exception(f"Insertion failed. Error: {e}")

        elif operation_flag.lower() == "update" or operation_flag.lower() == "u":
            prompts_config["prompt_last_updated"] = now_utc
            try:
                tm.execute_update_query(handler, prompts_config, 'WAIAgentPromptsConfig')
                logger.info("Update of prompt details is successful.")
            except Exception as e:
                logger.error(f"Failed to update config data - \n{prompts_config}\n\nError: {e}")
                logger.error("Update of prompt details is failed.")
                raise Exception(f"Update failed. Error: {e}")

        elif operation_flag.lower() == 'delete' or operation_flag.lower() == 'd':
            try:
                tm.execute_delete_query(handler, prompts_config, 'WAIAgentPromptsConfig')
                logger.info("Deletion of prompt details is successful.")
            except Exception as e:
                logger.error(f"Failed to delete config data - \n{prompts_config}\n\nError: {e}")
                logger.error("Deletion of prompt details is failed.")
                raise Exception(f"Deletion failed. Error: {e}")
        else:
            raise ValueError("operation flag must be 'insert' or 'i' or 'update' or 'u' or 'delete' or 'd'")


if __name__ == '__main__':
    from chatPackages.loggerConfig import LoggerManager as lg
    import json

    l_logger = lg.configure_logger("../logs/config_insertion")
    l_config = "../configuration/config.json"
    with open(l_config, 'rb') as config_data:
        config_data = json.load(config_data)

    if config_data['WAI_NoSQL'] and str(config_data['WAI_NoSQL']['DatabaseType']).lower() == 'nosql':
        oci_config_data = config_data['WAI_NoSQL']
    else:
        oci_config_data = None
    # print(oci_config_data)

    l_handler = cm.get_nosql_conn(
        compartment_id=oci_config_data['compartment_id'],
        user_id=oci_config_data['user'],
        fingerprint=oci_config_data['fingerprint'],
        tenant_id=oci_config_data['tenancy'],
        region=oci_config_data['region'],
        private_key_file='../../certs/oci_private.pem'
    )

    prompt_config_l = [
  {
    "agent_prompt_id": 24,
    "system_instruction": "Objective: To analyze support agent queries, previous chat history, and summarized chat content to generate unit-level questions for resolving support tickets, specifying appropriate information sources. If the support agent query requests actions other than question generation (e.g., summarization, modifications), perform those actions and return null for questions. Focus on understanding the information need and intent of the query.  Instructions for Gemini (Issue Resolver Agent):  1. Receive Input:   * `support_agent_query` (string): The support agent's query, which can be a question, information request, suggestion, modification request, or any other instruction. Focus on understanding the information need and intent of the query.   * `previous_chat_history` (array of objects): The last 3 chat interactions, where each object contains 'query' and 'response' keys. If no interaction exists, both 'query' and 'response' values are null. Example: [{'query': '...', 'response': '...'}, {'query': null, 'response': null}, ...].   * `summarized_chat_content` (string): A summarized text of the entire chat history, provided by another agent.  2. Analyze Support Agent Query:   * Analyze the `support_agent_query` to understand its *purpose* and *information need*. Determine if it requires generating new questions or performing other actions. Focus on the underlying request.  3. Contextual Understanding:   * Analyze the `previous_chat_history` to understand the ongoing conversation and the customer's evolving problem.   * Analyze the `summarized_chat_content` to get a comprehensive view of the entire ticket history.  4. Generate Unit-Level Questions (If Applicable):   * If the `support_agent_query` requires generating questions, identify the questions needed to resolve the issue, considering the `previous_chat_history` and `summarized_chat_content`. Focus on the information needed to address the query's underlying intent.   * Ensure the generated questions are at a unit level (atomic and not further decomposable).   * For each question, specify the appropriate information source, using the following exact values: `winfobots_database`, `customer_oracle_database`, or `process_documents`. Prioritize checking application databases when relevant.  5. Perform Other Actions (If Applicable):   * If the `support_agent_query` requests actions other than question generation, perform those actions based on the provided inputs. Focus on the underlying intent.   * In these cases, return null for the `questions_for_resolution` field.  6. Structured JSON Output: Present your analysis in JSON format. The JSON object should have these fields:   * `questions_for_resolution` (array of objects, optional): A list of questions for resolution, each specifying the information source. If no questions are generated, return null.",
    "response_schema": {
      "title": "Questions for Resolution",
      "description": "Schema for a list of questions and their information sources, or an empty list.",
      "type": "OBJECT",
      "properties": {
        "questions_for_resolution": {
          "type": "ARRAY",
          "items": {
            "type": "OBJECT",
            "properties": {
              "question": {
                "type": "STRING",
                "description": "The question that needs resolution."
              },
              "information_source": {
                "type": "STRING",
                "description": "The source of information related to the question."
              }
            },
            "required": [
              "question",
              "information_source"
            ]
          }
        }
      },
      "required": [
        "questions_for_resolution"
      ]
    },
    "prompt_level": "Agent6",
    "customer": "AEI Support",
    "llm_model_name": "gemini-2.0-flash-001",
    "llm_server_location": "us-central1",
    "prompt_created_by": "satish.kolamudi@winfosolutions.com",
    "comments": "For Support user interactions to resolve the ticket",
    "product_name": "WinfoBots",
    "operation_flag": "I"
  }
]

    PromptConfigManager.manage_prompts_config(prompt_config_l, l_handler, l_logger)

    cm.close_nosql_conn(l_handler)
    lg.shutdown_logger(l_logger)
