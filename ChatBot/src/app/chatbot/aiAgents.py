import json
from collections import defaultdict
from datetime import datetime, timezone
import concurrent.futures

from src.app.services.vertixAIActivities import VertexAIService as vai
from src.app.utils.dataValidation import Utils as ut
from src.app.services.embeddingActivites import EmbeddingManager as em
from src.app.services.nosqlConnection import NoSQLTableManager as tm


class SalesAgent:
    """"""

    def __init__(self):
        pass

    class ContentRetriever:
        """"""

        def __init__(self):
            pass

        @classmethod
        def _query_vectors(cls, product, query_embedding, num_neighbours, db_cursor, logger):
            """
            Queries the database to find the nearest content IDs
            based on vector similarity to the query_embedding.
            """
            vectors_query = f"""
            select distinct content_id
              from (
               select sc.content_id,
                      sce.embedding
                 from sales_content_embedding_new sce,
                      sales_content sc
                where sce.content_id = sc.content_id
                  and (sc.product = :product or sc.product = 'General')
                order by vector_distance(
                  sce.embedding,
                  :query_embedding
               ) asc
                fetch first
                  {num_neighbours}
               rows only
            )"""
            try:
                # query_embedding = str(query_embedding)
                logger.info(f"vector search query: {vectors_query} with product {product}")
                db_cursor.execute(
                    vectors_query,
                    {
                        'product': product,
                        'query_embedding': str(query_embedding)
                    }
                )
                vectors_data = db_cursor.fetchall()
                # vectors_data = vectors_data[0][0]
                # content_ids = str(vectors_data).split(',')
                content_ids = [v_id[0] for v_id in vectors_data]
            except Exception as e:
                logger.error(f'Error fetching Content IDs from Database: {e}')
                logger.error(
                    f'vectors_query: {vectors_query}\nquery_embedding: {query_embedding}\n embedding_type: {type(query_embedding)}\n product: {product}')
                content_ids = []
            return content_ids

        @classmethod
        def _get_content(cls, product, content_ids, db_cursor, logger):
            """
            Retrieves content text for the specified content IDs
            from the database table 'sales_content'.
            """
            logger.info('Get Content Function Called')
            if not content_ids:
                return []

            final_texts = ''
            content_query = ("SELECT content FROM sales_content WHERE content_id IN (" +
                             ",".join(map(str, content_ids)) + ") and product like '" + product + "'")
            try:
                db_cursor.execute(content_query)
                sales_content = db_cursor.fetchall()
                logger.info("Contents fetched from the DB.")
            except Exception as e:
                logger.error(f'Error fetching Content from Database: {e}')
                logger.error(f'content query: {content_query}')
                sales_content = []

            # final_texts = '\n'.join(
            #     (
            #         str(content[0].read()) if hasattr(content[0], 'read') else str(content[0]))
            #     for content in sales_content
            # )

            def process_content(content):
                return content[0].read() if hasattr(content[0], 'read') else str(content[0])

            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
                    final_texts = '\n'.join(executor.map(process_content, sales_content))
                    logger.info("Content convertion to readable is completed.")
            except Exception as e:
                logger.error(f"Failed to convert DB data into readable. Error details: {e}")

            return final_texts

    class Agents(ContentRetriever):
        """"""

        @classmethod
        def agent1(cls, user_question, logger, model_name='gemini-2.0-flash-001',
                   google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                   previous_conversation=''):
            logger.info(f"Agent1 started with user question: {user_question}")

            ag1_sys_instructions = """
  Objective: To effectively understand and answer complex user queries, especially those related to Winfo Solutions, WinfoBots, WinfoTest, WinfoData, WinfoCloudX, Winfo Oracle Practice, and Winfo Organisation, by identifying the sequence of elaborate and clear questions that need to be answered to achieve the user's intended outcome. WinfoBots automates Oracle EBS and Fusion processes. WinfoTest automates Oracle Fusion testing. Output in JSON format.\n\nInstructions for Gemini:\n\n1. Receive User Query and Previous Conversations:\n    * Get the user's complete question (`main_question`).\n    * If available, receive the last 3 conversations between the user and the agent in the `previous_conversation` field. This field will be empty or null for fresh chats.\n\n2. Contextual Understanding and Intent Analysis:\n    * If `previous_conversation` is present, analyze it to understand the ongoing conversation and the user's evolving needs.\n    * Use the context from the previous conversations to better understand the `main_question`.\n    * **Crucially, understand the user's underlying intent: what do they want to achieve?** Focus on the desired outcome, not just the literal question.\n\n3. Identify Elaborate and Clear Questions to Achieve User's Intent:\n    * Determine the *sequence of questions* that need to be answered to fully address the user's query and, more importantly, to help them achieve their intended outcome. These questions should be specific and logically lead to the desired result.\n    * Consider the context from `previous_conversation` to avoid redundant questions and to build upon existing information.\n    * **Create questions that guide the user towards their goal, ensuring each question is self-contained and fully understandable.** Avoid ambiguity and assumptions. Each question will be processed individually by the next agent.\n    * **Make each question elaborate and clear, providing sufficient context for the next agent to understand what information is being sought.**\n    * List these questions clearly and concisely. *Focus on the questions needed to answer the user's query and achieve their intent.*\n\n4. Structured JSON Output: Present your analysis in JSON format. The JSON object should have these fields:\n\n    * `user_query` (string, required): The original user query.\n    * `previous_conversation` (array, optional): The last 3 conversations between the user and the agent. Will be empty or null for fresh chats. Each conversation should be an object with `user` and `agent` fields.\n    * `questions_to_answer` (array, required): A list of the elaborate and clear questions that need to be answered to achieve the solution and the user's intent.\n\n5. Optional: Providing the Solution: If possible, answer the `questions_to_answer` and provide the final solution. Cite your information sources. For questions requiring more information, ask the user for clarification. **Remember, the primary goal is to create elaborate and clear questions that guide the user towards their desired outcome, not to provide instructions on how to use external tools.**
  """

            ag1_resp_schema = {
                "type": "OBJECT",
                "properties": {
                    "user_query": {
                        "type": "STRING",
                        "description": "The original user query."
                    },
                    "questions_to_answer": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING",
                            "description": "A question that needs to be answered to address the user query."
                        }
                    }
                },
                "required": [
                    "user_query",
                    "questions_to_answer"
                ]
            }

            ag1_prompt = f'''
previous_conversation - {previous_conversation}

main_question - "{user_question}"
            '''

            ag1_res = vai.get_prompt_response(
                ag1_prompt,
                logger,
                model_name=model_name,
                location='us-central1',
                google_key_config_path=google_key_config_path,
                system_instruction=ag1_sys_instructions,
                response_schema=ag1_resp_schema
            )
            logger.info(f"Agent1 processed user question: {user_question}")
            logger.info(f"Agent1 response: {ag1_res}")

            try:
                start_index = ag1_res.find('{')
                end_index = ag1_res.rfind('}')
                ag1_res = ag1_res[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent1 response: {e}")
                ag1_res = '{"questions_to_answer":[]}'

            return ag1_res

        @classmethod
        def agent2(cls, user_question, questions_list, logger, model_name='gemini-2.0-flash-001',
                   google_key_config_path='../configuration/Google_Key(WinfoBots).json', previous_conversation=''):
            logger.info(f"Sales chart bot stated with agent2. user question: {questions_list}")

            ag2_sys_instruction = """
  Objective: To refine and generate further sub-questions based on a given sub-question, classifying them for information retrieval with a focus on accurate categorization. Minimize 'more-info' questions by making valid assumptions based on the main user query and previous conversation history. Output in JSON format.\n\nInstructions for Gemini (Secondary Agent):\n\n1. Receive Input:\n    * `main_question` (string): The original user query.\n    * `sub_question` (string): The sub-question from the primary agent.\n    * `previous_conversation` (array, optional): The last 3 conversations between the user and the agent. Will be empty or null for fresh chats. Each conversation should be an object with `user` and `agent` fields.\n\n2. Contextual Understanding:\n    * If `previous_conversation` is present, analyze it to understand the ongoing conversation and the user's evolving needs.\n    * Use the context from the previous conversations to better understand the `main_question` and `sub_question`.\n\n3. Further Deconstruction: If the `sub_question` can be further divided, do so. Create detailed, granular questions that can be directly answered.\n\n4. Information Categorization (Critical Distinction):\n    * Classify each generated sub-question as: generic, specific, generic-realtime, or more-info.\n    * **'Specific' Classification:**\n        * **Only classify a sub-question as 'specific' if it pertains directly to a product or service offered by Winfo Solutions.**\n        * Winfo Solutions' internal resources contain information about its products and services exclusively. Therefore, 'specific' questions are those that can be answered using internal documentation.\n    * **'Generic-Realtime' Classification:**\n        * **Classify sub-questions that require information from the external world (e.g., market trends, industry news, general knowledge, customer strategies, investment information) as 'generic-realtime'.**\n        * These questions will be answered by the next agent using external search engines and internet research.\n        * If the sub_question is related to strategy or investment, always classify it as 'generic-realtime'.\n    * **'Generic' Classification:** General knowledge questions that do not require up-to-date web information.\n    * **'More-Info' Classification:** Questions requiring user clarification.\n    * If 'specific', identify the related Winfo product/service (WinfoBots, WinfoTest, WinfoData, WinfoCloudX, Winfo Oracle Practice, Winfo Organisation).\n    * If 'generic-realtime', ensure the question targets up-to-date web information.\n\n5. Assumption-Based Minimization of 'more-info':\n    * Analyze the `main_question` and `previous_conversation` to make reasonable assumptions that could help answer the `sub_question` without requiring further user input.\n    * Document these assumptions in the `assumptions` field.\n\n6. Structured JSON Output: Present your analysis in JSON format. Each generated sub-question should have these fields:\n    * `original_sub_question` (string, required): The original sub-question received.\n    * `sub_question` (string, required): The sub-question itself.\n    * `information_type` (string, optional): The type of information needed (see above). Omit if `question_type` is `more-info`.\n    * `question_type` (string, required): The question type (see above).\n    * `specific_details` (string, optional): If `question_type` is `specific`, specify the Winfo specific details.\n    * `assumptions` (array of strings, optional): List any assumptions made while generating the sub-question.\n\n7. Focus on Question Generation: Your primary task is to generate and classify sub-questions, not to provide answers. Minimize 'more-info' questions through valid assumptions, taking into account previous conversations. **Prioritize accurate classification, especially between 'specific' and 'generic-realtime', as this will significantly impact the quality of the final response.**
  """

            ag2_resp_schema = {
                "type": "OBJECT",
                "properties": {
                    "original_sub_question": {
                        "type": "STRING",
                        "description": "The original sub-question received from the previous agent."
                    },
                    "deconstructed_query": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "sub_question": {
                                    "type": "STRING",
                                    "description": "A sub-question derived from the original sub-question."
                                },
                                "information_type": {
                                    "type": "STRING",
                                    "description": "The type of information needed for the sub-question.",
                                    "enum": [
                                        "General Internet Knowledge",
                                        "Core Product-Specific Information",
                                        "Real-time Web Information"
                                    ]
                                },
                                "question_type": {
                                    "type": "STRING",
                                    "description": "The type of the sub-question.",
                                    "enum": [
                                        "generic",
                                        "specific",
                                        "generic-realtime",
                                        "more-info"
                                    ]
                                },
                                "specific_details": {
                                    "type": "STRING",
                                    "description": "The Winfo specific details related to the sub-question. Only present if question_type is 'specific'.",
                                    "enum": [
                                        "WinfoBots",
                                        "WinfoTest",
                                        "WinfoData",
                                        "WinfoCloudX",
                                        "Winfo Oracle Practice",
                                        "Winfo Organisation"
                                    ]
                                },
                                "assumptions": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "STRING"
                                    },
                                    "description": "List of assumptions made while generating the sub-question."
                                }
                            },
                            "required": [
                                "sub_question",
                                "question_type"
                            ]
                        }
                    }
                },
                "required": [
                    "original_sub_question",
                    "deconstructed_query"
                ]
            }

            final_res = []

            for each_question in questions_list:
                ag2_prompt = f'''
main_question - "{user_question}"
sub_question - "{each_question}"

previous_conversation - {previous_conversation}
                '''
                ag2_res = vai.get_prompt_response(
                    ag2_prompt,
                    logger,
                    model_name=model_name,
                    location='us-central1',
                    google_key_config_path=google_key_config_path,
                    system_instruction=ag2_sys_instruction,
                    response_schema=ag2_resp_schema
                )

                logger.info(f"Agent2 processed for agent1's sub-question: {each_question}")
                logger.info(f"Agent2 response: {ag2_res}")

                try:
                    start_index = ag2_res.find('{')
                    end_index = ag2_res.rfind('}')
                    ag2_res = ag2_res[start_index:end_index + 1]
                except Exception as e:
                    logger.error(f"Error occurred while parsing agent2 response: {e}")
                    ag2_res = f'''{{"deconstructed_query": [], "user_query": "{each_question}"}}'''

                ag2_res = json.loads(ag2_res)
                # ag2_res['user_query'] = each_question
                final_res.append(ag2_res)

            return final_res

        @classmethod
        def agent3(cls, query, reference_data, logger, model_name='gemini-2.0-flash-001',
                   google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                   response_schema=None, previous_conversation=''
                   ):
            """
            Generates a chatbot prompt to get a response from the model.

            Constructs a detailed prompt outlining the required behavior of the chatbot
            and passes it along with the reference data for model processing.
            """
            try:
                logger.info('Agent3 sales Chat Bot Prompt Function called')

                system_instruction = """
Objective: To synthesize a concise and continuous answer to the user's main question using the provided context and previous conversation history, building upon previous responses if necessary, and formatting the response in Markdown. Limit to a maximum of two iterations.\n\nInstructions for Gemini (Answer Synthesis Agent):\n\n1. Receive Input:\n  * `main_question` (string): The original question asked by the user.\n  * `context` (array of objects): The collection of sub-questions and their answers generated by previous agents. Each object should contain `sub_question`, `answer`, and relevant metadata.\n  * `previous_answer_generated` (string, optional): The partially constructed answer from the previous iteration. If this is the first iteration, this field will be absent or empty.\n  * `previous_conversation` (array, optional): The last 3 conversations between the user and the agent. Will be empty or null for fresh chats. Each conversation should be an object with `user` and `agent` fields.\n\n2. Contextual Understanding:\n  * If `previous_conversation` is present, analyze it to understand the ongoing conversation and the user's evolving needs.\n  * Use the context from the previous conversations to better understand the `main_question` and the provided `context`.\n\n3. Answer Synthesis and Continuation:\n  * Analyze the `main_question`, `context`, and `previous_conversation` to understand the user's intent and the relevant information.\n  * If `previous_answer_generated` is present, ensure the new response is a logical continuation of the previous one, not a repetition or disconnected information.\n  * Only proceed to a second iteration if the user has explicitly requested a detailed answer, if the question inherently requires extensive information, or if the initial response is demonstrably incomplete.\n\n4. Iterative Response (Maximum Two Iterations):\n  * First Iteration: Generate an initial response based on the `context`.\n  * Second Iteration: If a second iteration is needed, receive the `previous_answer_generated` and continue building the response. The second response must be a continuation of the previous one.\n  * After the second iteration, the response must be complete.\n\n5. Markdown Output:\n  * Output the generated answer to the `main_question`, **formatted in Markdown**. Use appropriate Markdown syntax for headings, lists, bold/italic text, code blocks, etc., to enhance readability.\n\n6. Contextual Accuracy:\n  * Ensure the answer accurately reflects the information provided in the `context` and is relevant to the `main_question`, considering the `previous_conversation`.\n\n7. Focus on Continuity: The second response must be a logical continuation of the first, providing additional relevant information, not a repetition or a disjointed answer.\n\n8. Markdown Formatting: The output **must** be formatted using Markdown syntax for clear and easy information absorption by the user.

Expected Output:A string representing the generated response, adhering to the above guidelines. Please provide only the relevant answer in a structured manner with proper headings if needed and do not specify the source of content.

Example:
User Query: "What is the capital of France?"

Reference Data:"Paris is the capital of France."
"The Eiffel Tower is in Paris."
"France is in Europe."

Output: "Paris is the capital of France."

Additional Considerations:Contextual Understanding:

Leverage the context provided by the user query and the reference texts to enhance the relevance of the response.

Semantic Similarity: Apply semantic analysis to find closely related content when direct answers are not evident.
Error Management: Implement robust error handling strategies to address data gaps or ambiguous queries effectively.
                """

                prompt = f"""
previous_conversation - {previous_conversation}

main_question - '{query}'
Reference Data: 
'''
{reference_data}
'''
                        """
                # print(f"prompt: {prompt}")
                return vai.get_prompt_response(
                    prompt,
                    logger,
                    google_key_config_path=google_key_config_path,
                    response_schema=response_schema,
                    model_name=model_name,
                    system_instruction=system_instruction
                )
            except Exception as e:
                logger.error(f'Error fetching response from prompt: {e}')
                return ''

        @classmethod
        def agent4(cls, user_question, all_contents, previous_answer_generated, logger,
                   model_name='gemini-2.0-flash-001',
                   google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                   previous_conversation=''):
            logger.info(f"Agent4 called for summarizing all the responses from agent3...")

            ag4_sys_instruction = """
  Objective: To synthesize a comprehensive and continuous answer to the user's main question using the provided context and previous conversation history, building upon previous responses if necessary, explicitly listing assumptions at the end, and formatting the response in Markdown. Limit to a maximum of two iterations. Output in JSON format.\n\nInstructions for Gemini (Answer Synthesis Agent):\n\n1. Receive Input:\n    * `main_question` (string): The original question asked by the user.\n    * `context` (array of objects): The collection of sub-questions and their answers generated by previous agents. Each object should contain `sub_question`, `answer`, and relevant metadata.\n    * `previous_answer_generated` (string, optional): The partially constructed answer from the previous iteration. If this is the first iteration, this field will be absent or empty.\n    * `previous_conversation` (array, optional): The last 3 conversations between the user and the agent. Will be empty or null for fresh chats. Each conversation should be an object with `user` and `agent` fields.\n\n2. Contextual Understanding:\n    * If `previous_conversation` is present, analyze it to understand the ongoing conversation and the user's evolving needs.\n    * Use the context from the previous conversations to better understand the `main_question` and the provided `context`.\n\n3. Answer Synthesis and Continuation:\n    * Analyze the `main_question`, `context`, and `previous_conversation` to understand the user's intent and the relevant information.\n    * If `previous_answer_generated` is present, ensure the new response is a logical continuation of the previous one, not a repetition or disconnected information.\n    * Only proceed to a second iteration if the user has explicitly requested a detailed answer, if the question inherently requires extensive information, or if the initial response is demonstrably incomplete.\n\n4. Iterative Response (Maximum Two Iterations):\n    * First Iteration: Generate an initial response based on the `context`. If the response is complete, set `finished_response` to \"yes\". If more information or refinement is needed, set `finished_response` to \"no\".\n    * Second Iteration: If `finished_response` was \"no\" in the first iteration, receive the `previous_answer_generated` and continue building the response. Set `finished_response` to \"yes\" to indicate the final answer. The second response must be a continuation of the previous one.\n    * After the second iteration, the response must be complete and `finished_response` must be \"yes\".\n\n5. Structured JSON Output:\n    * `response` (string): The generated answer to the `main_question`, **formatted in Markdown**. Use appropriate Markdown syntax for headings, lists, bold/italic text, code blocks, etc., to enhance readability.\n    * `finished_response` (string): Either \"yes\" (answer is complete) or \"no\" (more information needed, only applicable on first iteration).\n    * `assumptions` (array of strings, optional): List any assumptions made during the answer synthesis process. This should be placed at the end of the `response` string.\n\n6. Contextual Accuracy and Assumption Awareness:\n    * Ensure the answer accurately reflects the information provided in the `context` and is relevant to the `main_question`, considering the `previous_conversation`.\n    * Explicitly list all assumptions made during the answer synthesis process at the end of the response, so the user is aware of the context used for the answer.\n\n7. Focus on Continuity: The second response must be a logical continuation of the first, providing additional relevant information, not a repetition or a disjointed answer.\n\n8. Markdown Formatting: The `response` field **must** be formatted using Markdown syntax for clear and easy information absorption by the user.
            """

            ag4_resp_schema = {
                "type": "OBJECT",
                "properties": {
                    "response": {
                        "type": "STRING",
                        "description": "The generated answer to the main_question."
                    },
                    "finished_response": {
                        "type": "STRING",
                        "enum": [
                            "yes",
                            "no"
                        ],
                        "description": "Indicates whether the answer is complete ('yes') or requires further iteration ('no')."
                    },
                    "assumptions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                        "description": "List of assumptions made during the answer synthesis process."
                    }
                },
                "required": [
                    "response",
                    "finished_response"
                ]
            }

            ag4_prompt = f'''
main_question - "{user_question}"
context - {all_contents}

previous_answer_generated - {previous_answer_generated}

previous_conversation - {previous_conversation}
            '''

            ag4_res = vai.get_prompt_response(
                ag4_prompt,
                logger,
                model_name=model_name,
                location='us-central1',
                google_key_config_path=google_key_config_path,
                system_instruction=ag4_sys_instruction,
                response_schema=ag4_resp_schema
            )

            logger.info(f"Agent4 response: {ag4_res}")

            try:
                start_index = ag4_res.find('{')
                end_index = ag4_res.rfind('}')
                ag4_res = ag4_res[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent2 response: {e}")
                ag4_res = f'''{{"finished_response": "no", "response": "", "assumptions": []}}'''

            try:
                ag4_res = json.loads(ag4_res)
            except Exception as e:
                logger.error(f"Error occurred while parsing agent2 response: {e}")
                ag4_res = f'''{{"finished_response": "no", "response": "", "assumptions": []}}'''

            return ag4_res

        @classmethod
        def basic_agent(cls, user_question, db_cursor, logger,
                        model_name='gemini-2.0-flash-001', specific_details='WinfoBots',
                        google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                        response_schema=None, previous_conversation='', nearest_neighbours=30,
                        location='us-central1'):
            logger.info("Basic Agent called for getting the basic info of embedding...")
            try:
                each_sub_question = ut.clean_string(user_question).lower()
                # print(f"each_sub_question: {each_sub_question}")

                each_question_embedding = em.get_embedding(
                    each_sub_question, logger, google_key_config_path=google_key_config_path, location=location
                )
                l_content_ids = cls._query_vectors(specific_details, each_question_embedding, nearest_neighbours,
                                                   db_cursor,
                                                   logger)
                logger.info(
                    f"contents used for specific question:\n specific details:{specific_details}\nquestion: {each_sub_question}\ncontents: {l_content_ids}")
                l_contents = cls._get_content(specific_details, l_content_ids, db_cursor, logger)
                prompt_res = cls.agent3(each_sub_question, l_contents, logger,
                                        google_key_config_path=google_key_config_path,
                                        response_schema=response_schema, model_name=model_name,
                                        previous_conversation=previous_conversation)
            except Exception as e:
                logger.error(f"Error occurred while processing basic agent: {e}")
                prompt_res = ''

            logger.info(f"Response: {prompt_res}")

            return prompt_res

    class GetContents(Agents):
        """"""

        @classmethod
        def get_specific_questions_contents(
                cls,
                specific_questions,
                db_cursor,
                logger,
                nearest_neighbours=60,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                response_schema=None,
                model_name='gemini-2.0-flash-001'
        ):
            """"""
            logger.info(
                f"Sales chart bot stated with get_specific_questions_contents. user question: {specific_questions}")

            # final_content_ids = {}
            final_specific_ques_res = []
            try:
                for each_set in specific_questions:
                    specific_details = each_set['specific_details']
                    ag1_question = each_set['ag1_question']
                    sub_questions = each_set['sub_questions']
                    if len(sub_questions) == 0:
                        continue

                    sub_questions_resp = {"ag1_question": ag1_question, "response": ""}
                    for each_sub_question in sub_questions:
                        # print(f"specific_question: {specific_question}")
                        each_sub_question = ut.clean_string(each_sub_question).lower()
                        # print(f"each_sub_question: {each_sub_question}")

                        prompt_res = cls.basic_agent(each_sub_question, db_cursor, logger, model_name=model_name,
                                                     specific_details=specific_details,
                                                     google_key_config_path=google_key_config_path,
                                                     response_schema=response_schema,
                                                     nearest_neighbours=nearest_neighbours)

                        sub_questions_resp["response"] += f"\n\n{prompt_res}"

                    final_specific_ques_res.append(sub_questions_resp)
                    # break
            except Exception as e:
                logger.error(f"Sales chart bot failed with get specific questions contents. error: {e}")
                logger.error(f"specific_questions: {specific_questions}")

            return final_specific_ques_res

        @classmethod
        def get_generic_questions_contents(cls, generic_questions, logger,
                                           google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """"""
            all_generic_responses = []
            for generic_question in generic_questions:
                ag1_question = generic_question['ag1_question']
                sub_questions = generic_question['sub_questions']
                each_generic_question_resp = {"ag1_question": ag1_question, "response": ""}
                if len(sub_questions) == 0:
                    # sub_questions = [ag1_question]
                    continue

                with open(google_key_config_path) as l_config_data:
                    service_account_details = json.load(l_config_data)

                l_api_key = service_account_details.get('api_key')
                for each_sub_question in sub_questions:
                    try:
                        generic_response = vai.get_prompt_response(
                            each_sub_question, logger, model_name='gemini-2.0-flash-001', location='us-central1',
                            google_search=True,
                            google_key_config_path=google_key_config_path,
                            api_key=l_api_key
                        )
                        logger.info(f"Generic question user question: {generic_question}")
                        logger.info(f"Sales chart bot response for get_generic_questions_contents: {generic_response}")
                    except Exception as e:
                        logger.error(f"Sales chart bot failed with get_generic_questions_contents. error: {e}")
                        logger.error(f"generic_question: {generic_question}")
                        generic_response = ''

                    each_generic_question_resp['response'] += f"\n\n{generic_response}" if generic_response else ''
                    all_generic_responses.append(each_generic_question_resp)

            return all_generic_responses

        @classmethod
        def _process_questions(cls, data, logger):
            logger.info(f"Processing questions...\n{data}")
            grouped_questions = {
                "all_specific_questions": defaultdict(set),
                "all_generic_questions": set(),
                "all_more_info_questions": set()
            }

            user_query = data.get("original_sub_question", "")

            for item in data.get("deconstructed_query", []):
                question_type = item.get("question_type")
                sub_question = item.get("sub_question", "").strip()

                if question_type == "specific":
                    specific_details = item.get("specific_details", "").strip()
                    grouped_questions["all_specific_questions"][(user_query, specific_details)].add(sub_question)

                elif question_type == "generic" or question_type == "generic-realtime":
                    grouped_questions["all_generic_questions"].add(sub_question)

                elif question_type == "more-info":
                    grouped_questions["all_more_info_questions"].add(sub_question)
                else:
                    logger.debug(f"unhandled question type: {sub_question}")

            formatted_specific_questions = [
                {
                    "ag1_question": key[0],
                    "specific_details": key[1],
                    "sub_questions": sorted(list(questions))
                }
                for key, questions in grouped_questions["all_specific_questions"].items()
            ]

            return {
                "all_specific_questions": formatted_specific_questions,
                "all_generic_questions": [
                    {"ag1_question": user_query,
                     "sub_questions": sorted(list(grouped_questions["all_generic_questions"]))}],
                "all_more_info_questions": [
                    {"ag1_question": user_query,
                     "sub_questions": sorted(list(grouped_questions["all_more_info_questions"]))}]
            }

        @classmethod
        def categorize_questions(cls, ag2_res, logger):
            logger.info(f"Categorizing questions...\n{ag2_res}")

            categorized_questions = {"all_specific_questions": [], "all_generic_questions": [],
                                     "all_more_info_questions": []}
            try:
                for each_ag2_question in ag2_res:
                    processed_ag2_questions = cls._process_questions(each_ag2_question, logger)

                    categorized_questions["all_specific_questions"].extend(
                        processed_ag2_questions["all_specific_questions"])
                    categorized_questions["all_generic_questions"].extend(
                        processed_ag2_questions["all_generic_questions"])
                    categorized_questions["all_more_info_questions"].extend(
                        processed_ag2_questions["all_more_info_questions"])

            except Exception as e:
                logger.error(f"Sales chart bot failed with categorize_questions. error: {e}")
                logger.error(f"Agent2 Response: {ag2_res}")

            return categorized_questions


class SupportAgent:
    """"""

    class ContentRetriever:
        """"""

        def __init__(self):
            pass

        @classmethod
        def _query_vectors(cls, product_name, process_name, customer_name, query_embedding, num_neighbours,
                           db_cursor, logger):
            """
            Queries the database to find the nearest content IDs
            based on vector similarity to the query_embedding.
            """
            vectors_query = f"""
            select distinct content_id
            from(
            select content_id, embedding 
            from support_content_embedding 
            where upper(customer_name) = upper(:customer_name) 
            """

            if process_name:
                vectors_query += f"""
                and (process_name = '{process_name}' or process_name is null) 
                """

            vectors_query += f"""
            and upper(product_name) = upper(:product_name)
            order by vector_distance(
            embedding,
            :query_embedding
            ) asc
            fetch first
            {num_neighbours}
            rows only
            )"""
            try:
                # query_embedding = str(query_embedding)
                logger.info(
                    f"vector search query: {vectors_query} with following conditions \nproduct name: {product_name}"
                    f"\nprocess name: {process_name}\ncustomer name: {customer_name}"
                )
                db_cursor.execute(
                    vectors_query,
                    {
                        'product_name': product_name,
                        # 'process_name': process_name,
                        'customer_name': customer_name,
                        'query_embedding': str(query_embedding)
                    }
                )
                vectors_data = db_cursor.fetchall()
                content_ids = [v_id[0] for v_id in vectors_data]
            except Exception as e:
                logger.error(f'Error fetching support content ids from Database: {e}')
                logger.error(
                    f'query_embedding: {query_embedding}\n embedding_type: {type(query_embedding)}'
                )
                content_ids = []
            return content_ids

        @classmethod
        def _general_query_vectors(cls, product_name, process_name, customer_name, query_embedding, num_neighbours,
                           db_cursor, logger):
            """
            Queries the database to find the nearest content IDs
            based on vector similarity to the query_embedding.
            """
            vectors_query = f"""
            select distinct content_id
            from(
            select content_id, embedding 
            from general_content_embedding 
            where 1 = 1 
            """
            if process_name:
                vectors_query += f"""
            and (process_name = '{process_name}' or process_name is null) 
            """

            vectors_query += f"""
            and upper(product_name) = upper(:product_name)
            order by vector_distance(
            embedding,
            :query_embedding
            ) asc
            fetch first
            {num_neighbours}
            rows only
            )"""
            try:
                # query_embedding = str(query_embedding)
                logger.info(
                    f"vector search query: {vectors_query} with following conditions \nproduct name: {product_name}"
                    f"\nprocess name: {process_name}"
                )
                db_cursor.execute(
                    vectors_query,
                    {
                        'product_name': product_name,
                        # 'process_name': process_name,
                        # 'customer_name': customer_name,
                        'query_embedding': str(query_embedding)
                    }
                )
                vectors_data = db_cursor.fetchall()
                content_ids = [v_id[0] for v_id in vectors_data]
            except Exception as e:
                logger.error(f'Error fetching support content ids from Database: {e}')
                logger.error(
                    f'query_embedding: {query_embedding}\n embedding_type: {type(query_embedding)}'
                )
                content_ids = []
            return content_ids

        @classmethod
        def _get_content(cls, product, content_ids, nosql_conn, logger):
            """
            Retrieves content text for the specified content IDs
            from the database table 'SUPPORT_CONTENT'.
            """
            logger.info('Get Content Function Called')
            if not content_ids:
                return []

            content_query = ("SELECT content_details FROM SupportDocumentsContent WHERE content_id IN (" +
                             ",".join(map(str, content_ids)) + ")")
            try:
                # print(f"content_query: {content_query}")
                sales_content_l = tm.execute_select_query(nosql_conn, content_query)
                sales_content = [each_content.get('content_details').get('content') for each_content in sales_content_l]
            except Exception as e:
                logger.error(f'Error fetching Content from Database: {e}')
                logger.error(f'content query: {content_query}')
                sales_content = []

            # final_texts = [(str(content[0].read()) if hasattr(content[0], 'read') else str(content[0])) for content in
            #                sales_content]
            final_texts = '\n\n'.join(sales_content)
            # print(f"final_texts: {final_texts}")
            return final_texts

        @classmethod
        def _get_general_content(cls, product, content_ids, nosql_conn, logger):
            """
            Retrieves content text for the specified content IDs
            from the database table 'SUPPORT_CONTENT'.
            """
            logger.info('Get Content Function Called')
            if not content_ids:
                return []

            content_query = ("SELECT content_details FROM GeneralDocumentsContent WHERE content_id IN (" +
                             ",".join(map(str, content_ids)) + ")")
            try:
                # print(f"content_query: {content_query}")
                sales_content_l = tm.execute_select_query(nosql_conn, content_query)
                sales_content = [each_content.get('content_details').get('content') for each_content in sales_content_l]
            except Exception as e:
                logger.error(f'Error fetching Content from Database: {e}')
                logger.error(f'content query: {content_query}')
                sales_content = []

            # final_texts = [(str(content[0].read()) if hasattr(content[0], 'read') else str(content[0])) for content in
            #                sales_content]
            final_texts = '\n\n'.join(sales_content)
            # print(f"final_texts: {final_texts}")
            return final_texts


    class GetContents(ContentRetriever):
        """"""

        @classmethod
        def _basic_agent(
                cls, user_question, customer_name, product_name, process_name, db_cursor,
                nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                previous_conversation=''
        ):
            logger.info("Basic Agent called for getting the basic info of embedding...")
            try:

                prompt_config_query = f"""
                SELECT 
                    system_instruction, 
                    response_schema,
                    input_prompt,
                    llm_model_name,
                    llm_server_location, 
                    nearest_neighbours
                FROM WAIAgentPromptsConfig
                WHERE upper(customer) = upper('{customer_name}')
                and prompt_level = 'Agent3.1'
                and upper(product_name) = upper('{product_name}')
                """

                try:
                    prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                    system_instructions = prompt_config_details[0].get('system_instruction')
                    llm_model_name = prompt_config_details[0].get('llm_model_name')
                    llm_server_location = prompt_config_details[0].get('llm_server_location')
                    nearest_neighbours = prompt_config_details[0].get('nearest_neighbours')
                except Exception as e:
                    logger.error(
                        f"Agent3.1 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                    system_instructions = ''
                    llm_server_location = 'us-central1'
                    llm_model_name = 'gemini-2.0-flash-001'
                    nearest_neighbours = 30

                each_sub_question = ut.clean_string(user_question).lower()
                # print(f"each_sub_question: {each_sub_question}")

                each_question_embedding = em.get_embedding(
                    each_sub_question, logger, google_key_config_path=google_key_config_path, location=llm_server_location
                )
                l_content_ids = cls._query_vectors(
                    product_name, process_name, customer_name, each_question_embedding,
                    nearest_neighbours, db_cursor, logger
                )
                logger.info(
                    f"contents used for specific question:\n specific details:{product_name}\nquestion: {each_sub_question}\ncontents: {l_content_ids}")
                l_contents = cls._get_content(product_name, l_content_ids, nosql_conn, logger)
                prompt_res = cls._prompt_resp(
                    each_sub_question, l_contents, system_instructions, llm_model_name, llm_server_location, logger,
                    google_key_config_path=google_key_config_path, previous_conversation=previous_conversation
                )
            except Exception as e:
                logger.error(f"Error occurred while processing basic agent: {e}")
                prompt_res = ''

            logger.info(f"Response: {prompt_res}")

            return prompt_res

        @classmethod
        def _general_basic_agent(
                cls, user_question, customer_name, product_name, process_name, db_cursor,
                nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                previous_conversation=''
        ):
            logger.info("Basic Agent called for getting the basic info of embedding...")
            try:

                prompt_config_query = f"""
                SELECT 
                    system_instruction, 
                    response_schema,
                    input_prompt,
                    llm_model_name,
                    llm_server_location, 
                    nearest_neighbours
                FROM WAIAgentPromptsConfig
                WHERE customer = '{customer_name}'
                and prompt_level = 'Agent3.1'
                and product_name = '{product_name}'
                """

                try:
                    prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                    system_instructions = prompt_config_details[0].get('system_instruction')
                    llm_model_name = prompt_config_details[0].get('llm_model_name')
                    llm_server_location = prompt_config_details[0].get('llm_server_location')
                    nearest_neighbours = prompt_config_details[0].get('nearest_neighbours')
                except Exception as e:
                    logger.error(
                        f"Agent3.1 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                    system_instructions = ''
                    llm_server_location = 'us-central1'
                    llm_model_name = 'gemini-2.0-flash-001'
                    nearest_neighbours = 30

                each_sub_question = ut.clean_string(user_question).lower()
                # print(f"each_sub_question: {each_sub_question}")

                each_question_embedding = em.get_embedding(
                    each_sub_question, logger, google_key_config_path=google_key_config_path, location=llm_server_location
                )
                l_content_ids = cls._general_query_vectors(
                    product_name, process_name, customer_name, each_question_embedding,
                    nearest_neighbours, db_cursor, logger
                )
                logger.info(
                    f"contents used for specific question:\n specific details:{product_name}\nquestion: {each_sub_question}\ncontents: {l_content_ids}")
                l_contents = cls._get_general_content(product_name, l_content_ids, nosql_conn, logger)
                prompt_res = cls._prompt_resp(
                    each_sub_question, l_contents, system_instructions, llm_model_name, llm_server_location, logger,
                    google_key_config_path=google_key_config_path, previous_conversation=previous_conversation
                )
            except Exception as e:
                logger.error(f"Error occurred while processing basic agent: {e}")
                prompt_res = ''

            logger.info(f"Response: {prompt_res}")

            return prompt_res

        @classmethod
        def _prompt_resp(
                cls, issue_question, reference_data, system_instructions, llm_model_name, llm_server_location, logger,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json', previous_conversation=''
        ):
            """
            Generates a chatbot prompt to get a response from the model.

            Constructs a detailed prompt outlining the required behavior of the chatbot
            and passes it along with the reference data for model processing.
            """
            try:
                logger.info(f'Support agent 1 called with the following issue_question: \n{issue_question}')
                prompt = f"""
                "main_question": "{issue_question}"
                "context": 
                '''
                {reference_data}
                '''

                "previous_conversation": {previous_conversation}
                """
                # print(f"prompt: {prompt}")
                return vai.get_prompt_response(
                    prompt,
                    logger,
                    google_key_config_path=google_key_config_path,
                    model_name=llm_model_name,
                    system_instruction=system_instructions,
                    location=llm_server_location
                )
            except Exception as e:
                logger.error(f'Error fetching response from prompt: {e}')
                return ''

        @classmethod
        def get_customer_doc_questions_contents(
                cls,
                doc_questions,
                product_name,
                process_name,
                customer_name,
                db_cursor,
                nosql_conn,
                logger,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json'
        ):
            """"""
            logger.info(
                f"Support chart bot stated with get_customer_doc_questions_contents. user question: {doc_questions}")

            fina_ques_res = []
            try:
                for each_question in doc_questions:
                    prompt_res = cls._basic_agent(
                        each_question, customer_name, product_name, process_name, db_cursor, nosql_conn,
                        logger, google_key_config_path=google_key_config_path,
                    )
                    each_resp = {
                        "question": each_question,
                        "answer": prompt_res
                    }

                    fina_ques_res.append(each_resp)
                    # break
            except Exception as e:
                logger.error(f"Support chart bot failed with get doc questions contents. error: {e}")
                logger.error(f"doc_questions: {doc_questions}")

            return fina_ques_res

        @classmethod
        def get_general_doc_questions_contents(
                cls,
                doc_questions,
                product_name,
                process_name,
                customer_name,
                db_cursor,
                nosql_conn,
                logger,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json'
        ):
            """"""
            logger.info(
                f"Support chart bot stated with get_customer_doc_questions_contents. user question: {doc_questions}")

            fina_ques_res = []
            try:
                for each_question in doc_questions:
                    prompt_res = cls._general_basic_agent(
                        each_question, customer_name, product_name, process_name, db_cursor, nosql_conn,
                        logger, google_key_config_path=google_key_config_path,
                    )
                    each_resp = {
                        "question": each_question,
                        "answer": prompt_res
                    }

                    fina_ques_res.append(each_resp)
                    # break
            except Exception as e:
                logger.error(f"Support chart bot failed with get doc questions contents. error: {e}")
                logger.error(f"doc_questions: {doc_questions}")

            return fina_ques_res

        @classmethod
        def group_questions_by_source(cls, all_questions, logger):
            logger.info("Grouping questions by source function called.")
            grouped_questions = defaultdict(list)
            try:
                for item in all_questions["questions_for_resolution"]:
                    source = item["information_source"]
                    question = item["question"]

                    grouped_questions[source].append(question)

                return dict(grouped_questions)
            except Exception as e:
                logger.error(f"Error while grouping the questions. Error details: {e}")
                return None

        @classmethod
        def get_product_db_questions_contents(
                cls,
                winfo_db_questions,
                db_cursor,
                logger,
                nearest_neighbours=60,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json',
                response_schema=None,
                model_name='gemini-2.0-flash-001'
        ):
            """"""
            logger.info(
                f"Support chart bot stated with get_winfo_db_questions_contents. user question: {winfo_db_questions}"
            )
            final_res = ''
            try:
                pass
            except Exception as e:
                logger.error(f"Support chart bot failed with get winfo db questions contents. error: {e}")
                logger.error(f"winfo_db_questions: {winfo_db_questions}")

            return final_res

        @classmethod
        def get_oracle_db_questions_contents(cls, oracle_db_questions, logger,
                                             google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """"""
            logger.info(
                f"Support chat bot started get_oracle_db_questions_contents with questions: \n{oracle_db_questions}")
            final_resp = ''
            try:
                pass
            except Exception as e:
                logger.error(f"Support chart bot failed with get oracle db questions contents. error: {e}")
                logger.error(f"oracle_db_questions: {oracle_db_questions}")

            return final_resp

    class Agents(GetContents):
        @classmethod
        def agent1(cls, previous_chats, ticket_description, customer_process_descriptions, customer_name, product_name,
                   nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            logger.info(f'Support agent 1 called with the following ticket description: \n{ticket_description}')

            prompt_config_query = f"""
            SELECT 
                system_instruction, 
                response_schema,
                input_prompt,
                llm_model_name,
                llm_server_location, 
                nearest_neighbours
            FROM WAIAgentPromptsConfig
            WHERE customer = '{customer_name}'
            and prompt_level = 'Agent1'
            and product_name = '{product_name}'
            """

            try:
                prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                system_instructions = prompt_config_details[0].get('system_instruction')
                llm_model_name = prompt_config_details[0].get('llm_model_name')
                llm_server_location = prompt_config_details[0].get('llm_server_location')
            except Exception as e:
                logger.error(f"Agent1 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                system_instructions = ''
                llm_model_name = 'gemini-2.0-flash-001'
                llm_server_location = 'us-central1'

            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "ticket_description": {
                        "type": "STRING",
                        "description": "The customer's description of the issue."
                    },
                    "process_name": {
                        "type": "STRING",
                        "description": "The derived name of the WinfoBots process."
                    }
                },
                "required": [
                    "ticket_description",
                    "process_name"
                ]
            }

            ag1_prompt = f''''
    {{
      "ticket_description": """{ticket_description}""",
      "previous_ticket_interactions": "{previous_chats}",
      "customer_process_descriptions": {customer_process_descriptions}
    }}
            '''

            ag1_resp = vai.get_prompt_response(
                ag1_prompt, logger, system_instruction=system_instructions, model_name=llm_model_name,
                location=llm_server_location, response_schema=response_schema,
                google_key_config_path=google_key_config_path
            )
            logger.info(f"Support agent1 resp: \n {ag1_resp}")

            try:
                start_index = ag1_resp.find('{')
                end_index = ag1_resp.rfind('}')
                ag1_resp = ag1_resp[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent1 response: {e}")
                ag1_resp = None

            return ag1_resp

        @classmethod
        def agent2(cls, ticket_description, customer_id, process_name, process_flow,
                   product_name, nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            logger.info(
                f'Support agent 2 called with the following ticket: \n Ticket description: {ticket_description}\nCustomer ID: {customer_id}\nProcess Name: {process_name}\nProccess Flow: {process_flow}')

            prompt_config_query = f"""
                        SELECT 
                            system_instruction, 
                            response_schema,
                            input_prompt,
                            llm_model_name,
                            llm_server_location, 
                            nearest_neighbours
                        FROM WAIAgentPromptsConfig
                        WHERE customer = '{customer_id}'
                        and prompt_level = 'Agent2'
                        and product_name = '{product_name}'
                        """

            try:
                prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                system_instructions = prompt_config_details[0].get('system_instruction')
                llm_model_name = prompt_config_details[0].get('llm_model_name')
                llm_server_location = prompt_config_details[0].get('llm_server_location')
            except Exception as e:
                logger.error(f"Agent2 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                system_instructions = ''
                llm_model_name = 'gemini-2.0-flash-001'
                llm_server_location = 'us-central1'

            response_schema = {
              "properties": {
                "questions_for_resolution": {
                  "description": "A list of questions for resolution, each specifying the information source.",
                  "items": {
                    "properties": {
                      "information_source": {
                        "description": "The information source for the next agent.",
                        "enum": [
                          "customer_database",
                          "customer_documents",
                          "oracle_general_documents",
                          "product_database"
                        ],
                        "type": "STRING"
                      },
                      "question": {
                        "description": "A clear and detailed question for resolving the WinfoBots issue.",
                        "type": "STRING"
                      }
                    },
                    "required": [
                      "question",
                      "information_source"
                    ],
                    "type": "OBJECT"
                  },
                  "type": "ARRAY"
                }
              },
              "required": [
                "questions_for_resolution"
              ],
              "type": "OBJECT"
            }

            ag2_prompt = f'''
    {{
      "ticket_description": """{ticket_description}""",
      "customer_id": "{customer_id}",
      "process_name": "{process_name}",
      "process_flow": """{process_flow}"""
    }}
            '''

            ag2_resp = vai.get_prompt_response(
                ag2_prompt, logger, system_instruction=system_instructions, model_name=llm_model_name,
                location=llm_server_location, response_schema=response_schema,
                google_key_config_path=google_key_config_path
            )
            logger.info(f"Support agent2 resp: \n {ag2_resp}")

            try:
                start_index = ag2_resp.find('{')
                end_index = ag2_resp.rfind('}')
                ag2_resp = ag2_resp[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent1 response: {e}")
                ag2_resp = None

            return ag2_resp

        @classmethod
        def agent3(cls, categorized_questions, product_name, process_name, customer_name, ai_db_conn,
                   nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'
                   ):
            """"""
            logger.info(f'Support agent 3 called with the following categorized_questions: \n{categorized_questions}')

            doc_resp = []
            winfo_db_data = []
            oracle_db_data = []
            oracle_general_content = []

            try:
                winfo_db_questions = categorized_questions.get('product_database')
                oracle_db_questions = categorized_questions.get('customer_database')
                doc_questions = categorized_questions.get('customer_documents')
                oracle_general_questions = categorized_questions.get('oracle_general_documents')

                if doc_questions:
                    with ai_db_conn.cursor() as ai_db_cursor:
                        doc_resp = cls.get_customer_doc_questions_contents(
                            doc_questions, product_name, process_name, customer_name, ai_db_cursor, nosql_conn, logger,
                             google_key_config_path=google_key_config_path
                        )

                if oracle_general_questions:
                    with ai_db_conn.cursor() as ai_db_cursor:
                        oracle_general_content = cls.get_general_doc_questions_contents(
                            oracle_general_questions, product_name, process_name, customer_name, ai_db_cursor, nosql_conn, logger,
                             google_key_config_path=google_key_config_path
                        )

                doc_resp.extend(oracle_general_content)

                if winfo_db_questions:
                    winfo_db_data = []

                if oracle_db_questions:
                    oracle_db_data = []


            except Exception as e:
                logger.error(f'Error fetching response from each category: {e}')

            return doc_resp, winfo_db_data, oracle_db_data

        @classmethod
        def agent4(cls, ticket_description, resolved_questions, customer_name, product_name, process_flow, nosql_conn,
                   logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            logger.info(f'Support agent 4 called with the following ticket_description: \n{ticket_description}')

            prompt_config_query = f"""
            SELECT 
                system_instruction, 
                response_schema,
                input_prompt,
                llm_model_name,
                llm_server_location, 
                nearest_neighbours
            FROM WAIAgentPromptsConfig
            WHERE customer = '{customer_name}'
            and prompt_level = 'Agent4'
            and product_name = '{product_name}'
            """

            try:
                prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                system_instructions = prompt_config_details[0].get('system_instruction')
                llm_model_name = prompt_config_details[0].get('llm_model_name')
                llm_server_location = prompt_config_details[0].get('llm_server_location')
            except Exception as e:
                logger.error(
                    f"Agent4 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                system_instructions = ''
                llm_model_name = 'gemini-2.0-flash-001'
                llm_server_location = 'us-central1'

            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "resolution": {
                        "type": "STRING",
                        "description": "The generated resolution to the ticket description, formatted in Markdown."
                    },
                    "assumptions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                        "description": "A list of assumptions made during the resolution synthesis process. If no assumptions were made, provide [\"none\"]."
                    },
                    "additional_questions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                        "description": "A list of clear and specific additional questions formulated during the resolution process. If no additional questions were formulated, provide [\"none\"]."
                    }
                },
                "required": [
                    "resolution",
                    "assumptions",
                    "additional_questions"
                ]
            }

            ag4_prompt = f'''
{{
"ticket_description": """{ticket_description}""",
"resolved_questions": {resolved_questions},
"process_flow": """{process_flow}"""
}}
            '''

            ag4_resp = vai.get_prompt_response(
                ag4_prompt, logger, model_name=llm_model_name, location=llm_server_location,
                response_schema=response_schema, google_key_config_path=google_key_config_path,
                system_instruction=system_instructions
            )

            logger.info(f"Agent4 response: \n{ag4_resp}")

            try:
                start_index = ag4_resp.find('{')
                end_index = ag4_resp.rfind('}')
                ag4_resp = ag4_resp[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent1 response: {e}")
                ag4_resp = None

            return ag4_resp

        @classmethod
        def agent5(cls, customer_name, product_name, ticket_desc, ticket_comments, previous_chats, previous_summary,
                   ai_comments, nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            """
            Generating summary for the provided information.
            """
            logger.info(
                'Support agent 5 called with the following for summarization.'
            )

            prompt_config_query = f"""
            SELECT 
                system_instruction, 
                response_schema,
                input_prompt,
                llm_model_name,
                llm_server_location, 
                nearest_neighbours
            FROM WAIAgentPromptsConfig
            WHERE customer = '{customer_name}'
            and prompt_level = 'Agent5'
            and product_name = '{product_name}'
            """

            try:
                prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                system_instructions = prompt_config_details[0].get('system_instruction')
                llm_model_name = prompt_config_details[0].get('llm_model_name')
                llm_server_location = prompt_config_details[0].get('llm_server_location')
            except Exception as e:
                logger.error(
                    f"Agent5 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                system_instructions = ''
                llm_model_name = 'gemini-2.0-flash-001'
                llm_server_location = 'us-central1'

            ag5_prompt = f"""
{{
"ticket_description": '''{ticket_desc}''',
"ticket_comments": {ticket_comments},
"previous_summary": {previous_summary},
"initial_agent_response": '''{ai_comments}''',
"chat_history": {previous_chats},
}}
                    """

            ag5_resp = vai.get_prompt_response(
                ag5_prompt, logger, system_instruction=system_instructions, model_name=llm_model_name,
                location=llm_server_location, google_key_config_path=google_key_config_path
            )
            logger.info(f"Support agent5 resp: \n {ag5_resp}")

            return ag5_resp

        @classmethod
        def agent6(cls, product_name, previous_chats, support_query, summarized_chat_content,
                   customer_id, process_name, process_flow, nosql_conn, logger,
                   google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            logger.info(
                f'Support agent 6 called with the following ticket: \n Support query: {support_query}\n'
                f'Customer ID: {customer_id}\nProcess Name: {process_name}\nProccess Flow: {process_flow}'
            )

            prompt_config_query = f"""
            SELECT 
                system_instruction, 
                response_schema,
                input_prompt,
                llm_model_name,
                llm_server_location, 
                nearest_neighbours
            FROM WAIAgentPromptsConfig
            WHERE customer = '{customer_id}'
            and prompt_level = 'Agent6'
            and product_name = '{product_name}'
            """

            try:
                prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                system_instructions = prompt_config_details[0].get('system_instruction')
                llm_model_name = prompt_config_details[0].get('llm_model_name')
                llm_server_location = prompt_config_details[0].get('llm_server_location')
            except Exception as e:
                logger.error(
                    f"Agent6 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                system_instructions = ''
                llm_model_name = 'gemini-2.0-flash-001'
                llm_server_location = 'us-central1'

            response_schema = {
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
                                    "description": "The source of information related to the question.",
                                    "enum": [
                                        "customer_database",
                                        "customer_documents",
                                        "oracle_general_documents",
                                        "product_database"
                                    ]
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
            }

            ag6_prompt = f'''
{{
"support_agent_question": "{support_query}",
"previous_chat_history": {previous_chats},
"summarized_chat_content": "{summarized_chat_content}"
}}
            '''

            ag6_resp = vai.get_prompt_response(
                ag6_prompt, logger, system_instruction=system_instructions, model_name=llm_model_name,
                location=llm_server_location, response_schema=response_schema,
                google_key_config_path=google_key_config_path
            )
            logger.info(f"Support agent6 resp: \n {ag6_resp}")

            try:
                start_index = ag6_resp.find('{')
                end_index = ag6_resp.rfind('}')
                ag6_resp = ag6_resp[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent1 response: {e}")
                ag6_resp = None

            return ag6_resp

        @classmethod
        def agent7(
                cls, customer_name, product_name, ticket_description, initial_analysis, nosql_conn, logger,
                generated_questions_answers, chat_summary, chat_history, support_agent_query,
                google_key_config_path='../configuration/Google_Key(WinfoBots).json'
        ):
            logger.info(f'Support agent7 called with the following ticket_description: \n{ticket_description}')

            prompt_config_query = f"""
            SELECT 
                system_instruction, 
                response_schema,
                input_prompt,
                llm_model_name,
                llm_server_location, 
                nearest_neighbours
            FROM WAIAgentPromptsConfig
            WHERE customer = '{customer_name}'
            and prompt_level = 'Agent7'
            and product_name = '{product_name}'
            """

            try:
                prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                system_instructions = prompt_config_details[0].get('system_instruction')
                llm_model_name = prompt_config_details[0].get('llm_model_name')
                llm_server_location = prompt_config_details[0].get('llm_server_location')
            except Exception as e:
                logger.error(
                    f"Agent4 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                system_instructions = ''
                llm_model_name = 'gemini-2.0-flash-001'
                llm_server_location = 'us-central1'

            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "resolution": {
                        "type": "STRING",
                        "description": "The generated guidance for the agent or draft response for the customer, formatted in Markdown. Tone and content adapt based on the agent's query intent."
                    },
                    "assumptions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                        "description": "A list of assumptions made *about the problem context, data, or situation* during synthesis. Provides [] if none."
                    },
                    "additional_questions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        },
                        "description": "A list of specific questions targeting *information gaps in the provided context data* needed to complete the resolution content accurately. Provides [] if none."
                    }
                },
                "required": [
                    "resolution",
                    "assumptions",
                    "additional_questions"
                ]
            }

            ag7_prompt = f"""
{{
    "initial_analysis": '''{initial_analysis}''',
    "generated_questions_answers": {generated_questions_answers},
    "chat_summary": '''{chat_summary}''',
    "ticket_description": '''{ticket_description}''',
    "chat_history": {chat_history},
    "support_agent_query": "{support_agent_query}"
}}
            """

            ag7_resp = vai.get_prompt_response(
                ag7_prompt, logger, model_name=llm_model_name, location=llm_server_location,
                response_schema=response_schema,
                google_key_config_path=google_key_config_path, system_instruction=system_instructions
            )

            logger.info(f"Agent7 response: \n{ag7_resp}")

            try:
                start_index = ag7_resp.find('{')
                end_index = ag7_resp.rfind('}')
                ag7_resp = ag7_resp[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent1 response: {e}")
                ag7_resp = None

            return ag7_resp

        @classmethod
        def agent8(cls, ticket_description, customer_id, process_name, process_flow,
                   product_name, additional_questions, nosql_conn, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json'):
            logger.info(
                f'Support agent8 called with the following ticket: \n Ticket description: {ticket_description}\nCustomer ID: {customer_id}\nProcess Name: {process_name}\nProccess Flow: {process_flow}')

            prompt_config_query = f"""
                SELECT 
                    system_instruction, 
                    response_schema,
                    input_prompt,
                    llm_model_name,
                    llm_server_location, 
                    nearest_neighbours
                FROM WAIAgentPromptsConfig
                WHERE customer = '{customer_id}'
                and prompt_level = 'Agent8'
                and product_name = '{product_name}'
            """

            try:
                prompt_config_details = tm.execute_select_query(nosql_conn, prompt_config_query)
                system_instructions = prompt_config_details[0].get('system_instruction')
                llm_model_name = prompt_config_details[0].get('llm_model_name')
                llm_server_location = prompt_config_details[0].get('llm_server_location')
            except Exception as e:
                logger.error(f"Agent8 prompt is not configured. Error: {e}\nprompt_config_query: {prompt_config_query}")
                return None

            response_schema = {
              "properties": {
                "questions_for_resolution": {
                  "description": "A list of questions for resolution, each specifying the information source.",
                  "items": {
                    "properties": {
                      "information_source": {
                        "description": "The information source for the next agent.",
                        "enum": [
                          "customer_database",
                          "customer_documents",
                          "oracle_general_documents",
                          "product_database"
                        ],
                        "type": "STRING"
                      },
                      "question": {
                        "description": "A clear and detailed question for resolving the WinfoBots issue.",
                        "type": "STRING"
                      }
                    },
                    "required": [
                      "question",
                      "information_source"
                    ],
                    "type": "OBJECT"
                  },
                  "type": "ARRAY"
                }
              },
              "required": [
                "questions_for_resolution"
              ],
              "type": "OBJECT"
            }

            ag8_prompt = f'''
    {{
      "ticket_description": """{ticket_description}""",
      "customer_id": "{customer_id}",
      "process_name": "{process_name}",
      "process_flow": """{process_flow}""",
      "additional_questions": """{additional_questions}"""
    }}
            '''

            ag8_resp = vai.get_prompt_response(
                ag8_prompt, logger, system_instruction=system_instructions, model_name=llm_model_name,
                location=llm_server_location, response_schema=response_schema,
                google_key_config_path=google_key_config_path
            )
            logger.info(f"Support agent8 resp: \n {ag8_resp}")

            try:
                start_index = ag8_resp.find('{')
                end_index = ag8_resp.rfind('}')
                ag8_resp = ag8_resp[start_index:end_index + 1]
            except Exception as e:
                logger.error(f"Error occurred while parsing agent1 response: {e}")
                ag8_resp = None

            return ag8_resp

        @classmethod
        def complete_response_analyzer(
                cls, prev_resp, jira_ticket_id, ticket_description, ticket_flg, process_name, product_name,
                process_flow, customer_name, application_db_conn, nosql_conn, ag1_resp, logger, google_key_config_path
        ):
            logger.info(f"Complete response analyzer function called.")

            # ai_analysis = prev_resp
            all_resp = []
            ag4_resp = {"resolution": "Unable to get the response. Please contact the support team."}
            for i in range(4):
                prev_resp = json.loads(prev_resp)
                categorized_questions = cls.group_questions_by_source(prev_resp, logger)
                # print(f"categorized_questions: {categorized_questions}")

                doc_resp, winfo_db_data, oracle_db_data = cls.agent3(
                    categorized_questions, product_name, ag1_resp.get('process_name'), customer_name,
                    application_db_conn, nosql_conn, logger, google_key_config_path=google_key_config_path
                )

                all_resp.extend(doc_resp)
                all_resp.extend(winfo_db_data)
                all_resp.extend(oracle_db_data)

                ag4_resp = cls.agent4(
                    ag1_resp.get('ticket_description'), all_resp, customer_name, product_name, process_flow,
                    nosql_conn, logger, google_key_config_path=google_key_config_path
                )
                print(ag4_resp)
                ag4_resp = json.loads(ag4_resp)
                additional_questions = ag4_resp.get('additional_questions')
                if not additional_questions or i == 0:
                    break
                prev_resp = cls.agent8(
                    ticket_description=ticket_description,
                    customer_id=customer_name,
                    process_name=process_name,
                    process_flow=process_flow,
                    product_name=product_name,
                    additional_questions= additional_questions,
                    nosql_conn=nosql_conn,
                    logger=logger,
                    google_key_config_path=google_key_config_path
                )

                if not prev_resp:
                    break
            print(f"ag4_resp: {ag4_resp}")
            return json.dumps(ag4_resp, indent=2)

        @classmethod
        def question_analyzer(
                cls, jira_ticket_id, ticket_flg, agent_questions, product_name, customer_name, process_flow,
                application_db_conn, nosql_conn, ag1_resp, logger, google_key_config_path
        ):

            categorized_questions = cls.group_questions_by_source(agent_questions, logger)
            # print(f"categorized_questions: {categorized_questions}")

            doc_resp, winfo_db_data, oracle_db_data = cls.agent3(
                categorized_questions, product_name, ag1_resp.get('process_name'), customer_name,
                application_db_conn, nosql_conn, logger, google_key_config_path=google_key_config_path
            )

            ag3_resp = []

            # if ticket_flg:
            #     try:
            #         update_ticket = {
            #             "issue_id": jira_ticket_id,
            #             "customer_name": customer_name,
            #             "ag3_doc_resp": doc_resp,
            #             "ag3_app_db_resp": winfo_db_data,
            #             "ag3_oracle_db_resp": oracle_db_data
            #         }
            #
            #         update_flg = tm.execute_update_query(
            #             nosql_conn, update_ticket, 'SupportAnalyzerAgentResponses'
            #         )
            #     except Exception as e:
            #         logger.error(f"Failed to update agent3 for ticket - {jira_ticket_id}. Error details: {e}")

            ag3_resp.extend(doc_resp)
            ag3_resp.extend(winfo_db_data)
            ag3_resp.extend(oracle_db_data)

            # print(f"ag3_resp: {ag3_resp}")

            ag4_resp = cls.agent4(
                ag1_resp.get('ticket_description'), ag3_resp, customer_name, product_name, process_flow, nosql_conn,
                logger, google_key_config_path=google_key_config_path
            )

            # if ticket_flg:
            #     try:
            #         update_ticket = {
            #             "issue_id": jira_ticket_id,
            #             "customer_name": customer_name,
            #             "ag1_4_resp": json.loads(ag4_resp)
            #         }
            #
            #         update_flg = tm.execute_update_query(
            #             nosql_conn, update_ticket, 'SupportAnalyzerAgentResponses'
            #         )
            #     except Exception as e:
            #         logger.error(f"Failed to update agent4 for ticket - {jira_ticket_id}. Error details: {e}")

            return ag4_resp

    @classmethod
    async def initial_ticket_summary(
            cls, chat_id, issue_id, ticket_status, ticket_desc, ticket_comments, ai_comments,
            customer_name, product_name, nosql_conn, logger,
            google_key_config_path='configuration/Google_Key(WinfoBots).json'
    ):
        print("in Ticket summary call")
        logger.info("Initial ticket summary function called for summarizing the ticket details.")

        try:
            ticket_comments = json.loads(ticket_comments)
            processed_comments = len(ticket_comments)
        except Exception as e:
            logger.error(f"Loading comments failed. Error: {e}")
            processed_comments = 0

        chat_summary = cls.Agents.agent5(
            customer_name, product_name, ticket_desc, ticket_comments, [], '',
            ai_comments, nosql_conn, logger, google_key_config_path=google_key_config_path
        )

        insert_ticket_summary_query = {
            "issue_id": issue_id,
            "chat_id": chat_id,
            "processed_message_id": 0,
            "ticket_status": ticket_status,
            "summary": {
                "chat_summary": chat_summary,
                "ticket_description": ticket_desc,
                "all_comments": ticket_comments,
                "ai_comments": ai_comments,
            },
            "customer_name": customer_name,
            "product_name": product_name,
            "last_accessed_time": datetime.now(timezone.utc).isoformat(timespec='microseconds'),
            "processed_comment_id": processed_comments
        }
        logger.info(f"insert_ticket_summary_query: {insert_ticket_summary_query}")
        try:
            inert_flg = tm.execute_insert_query(nosql_conn, insert_ticket_summary_query, 'TicketSummary')
        except Exception as e:
            logger.error(
                f"Failed to insert chat summary for chat id: {chat_id}. Error details: {e}")


if __name__ == '__main__':
    from src.app.services.nosqlConnection import NoSQLConnectionManager as cm
    from src.app.utils.loggerConfig import LoggerManager as lg
    import asyncio

    l_config = "../configuration/config.json"
    with open(l_config, 'rb') as config_data:
        config_data = json.load(config_data)

    if config_data['WAI_NoSQL'] and str(config_data['WAI_NoSQL']['DatabaseType']).lower() == 'nosql':
        oci_config_data = config_data['WAI_NoSQL']
    else:
        oci_config_data = None
    # print(f"oci_config_data: {oci_config_data}")
    l_handler = cm.get_nosql_conn(
        nosql_db_details=oci_config_data,
        private_key_file='../../certs/oci_private.pem'
    )
    l_logger = lg.configure_logger('../logs/aiAgents')
    asyncio.run(
        SupportAgent.initial_ticket_summary(
        'U7dnS95y9f4rUrtcf7fyv6u',
        'AEI-1719',
        'InProgress',
        '''
Hi Team, Unable to Login to SAP instance while performing Sales Order creation automation. Timestamp: 19-04-2025 04:32:26 Regards, WinfoBots. Attachment: https://advenergy.sharepoint.com/sites/Departments/wwbusinesoperations/CCR/Shared%20Documents/SAP%20RPA%20LAM%20Portal%20Extract/error_screenshot19.04.2025%2004.32.19.png
        ''',
        '''
[
  {
    "comment_id": 1,
    "author": "Barasha Bharali",
    "author_email": "barasha.bharali@winfosolutions.com",
    "timestamp": "2025-02-05 19:34:38",
    "text": "!image-20250205-140435.png|width=1057,height=840,alt=\\"image-20250205-140435.png\\"!",
    "attachments_content": []
  },
  {
    "comment_id": 2,
    "author": "Sai Koteswara Rao Chinni",
    "author_email": "koteswararao.chinni@winfosolutions.com",
    "timestamp": "2025-03-25 19:16:48",
    "text": "The error message suggests a potential issue with data validation or system processing within the Sales Order HUB. Since the PO and Sales Order were successfully created the day before, it's likely that a temporary system glitch or a data inconsistency caused the failure. As a temporary solution, manually splitting the Hub pulls transaction, as suggested by the user, should allow the sales order to be created. It's important to investigate the underlying cause of the error to prevent future occurrences. This may involve checking system logs, reviewing the error message more closely, and potentially contacting technical support for further assistance.",
    "attachments_content": []
  },
  {
    "comment_id": 3,
    "author": "Barasha Bharali",
    "author_email": "barasha.bharali@winfosolutions.com",
    "timestamp": "2025-04-10 11:43:56",
    "text": "want to turn off the bot for this org, so not deployed yet",
    "attachments_content": []
  }
]
        ''',
        '',
        'AEI',
        'WinfoBots',
        l_handler,
        l_logger,
        r'../configuration/Google_Key(WinfoBots).json'
        )
    )
    lg.shutdown_logger(l_logger)

    cm.close_nosql_conn(l_handler)
