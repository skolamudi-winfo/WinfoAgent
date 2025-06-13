import json
import os
from jira import JIRA
from datetime import datetime
import re
import requests
from vertexai.generative_models import Part
import oracledb
import mimetypes

from chatPackages.gcsActivities import GCSManager as gcs
from chatPackages.prompts import VertexAIService as pr
from chatPackages.prompts import MimeTypes as mt
from chatPackages.aiAgents import SupportAgent as sa
from chatPackages.nosqlConnection import NoSQLTableManager as tm


class AttachmentProcessor:
    """"""
    @classmethod
    def _get_attachment_content_gcs(cls, file_path, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json', model_name='gemini-2.0-flash-001'):
        """Processes an attachment and extracts content."""
        mime_type = mt.get_mime_type(file_path)
        file_part = Part.from_uri(
            uri=file_path,
            mime_type=mime_type,
        )

        prompt = """
analyze the provided attachment and extract the actual content from it. with proper headings when required.
        """
        system_instruction = """
You are a very professional document analyzer specialist. Understand the documents provided and return the response based on the prompt asked by the user we might have images inside the pdf, analyze the images as well inside the pdf.
        """

        contents = [file_part, prompt]
        file_content = pr.get_prompt_response(
            contents, logger, model_name=model_name,
            system_instruction=system_instruction,
            google_key_config_path=google_key_config_path
        )
        bucket_name, blob_name, file_name = gcs.parse_gcs_link(file_path)
        del_flg = gcs.delete_from_gcs(bucket_name, blob_name, logger, google_key_path=google_key_config_path)
        if del_flg:
            logger.info(f"File {file_path} deleted from GCS.")
        else:
            logger.error("Failed to delete file from gcs.")

        return file_content

    @classmethod
    def _get_attachment_content(
            cls, file_path, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
            model_name='gemini-2.0-flash-001'
    ):
        """Processes an attachment and extracts content."""

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"
            logger.warning(f"Could not guess MIME type for {file_path}. \nUsing {mime_type}.")

        file_part = Part.from_data(
            data=file_bytes,
            mime_type=mime_type
        )

        prompt = """
    analyze the provided attachment and extract the actual content from it. with proper headings when required.
            """
        system_instruction = """
    You are a very professional document analyzer specialist. Understand the documents provided and return the response based on the prompt asked by the user we might have images inside the pdf, analyze the images as well inside the pdf.
            """

        contents = [file_part, prompt]
        file_content = pr.get_prompt_response(
            contents, logger, model_name=model_name,
            system_instruction=system_instruction,
            google_key_config_path=google_key_config_path
        )

        os.remove(file_path)

        return file_content

class ProcesTicketsDB:
    @classmethod
    def _get_existing_tickets(cls, application_db_conn, logger):
        logger.info("Fetching the existing tickets from DB.")
        tickets = []
        tickets_query = "select jira_ticket_id from support_tickets"

        try:
            with application_db_conn.cursor() as db_cursor:
                db_cursor.execute(tickets_query)
                tickets = db_cursor.fetchall()
                tickets = [ticket[0] for ticket in tickets]
        except Exception as e:
            logger.error(f"Failed to get the existing tickets from DB. Error details: {e}")

        return tickets

    @classmethod
    def _update_ticket_details(cls, ticket_details, customer_name, conn, logger):
        logger.info("Updating the ticket details...")

        try:
            update_ticket_query = {}
            jira_ticket_id = ticket_details.get("jira_ticket_id")

            if not jira_ticket_id:
                logger.error("JIRA Ticket ID is missing, skipping update.")
                return

            for field in ["assignee", "closed_date", "status", "resolution_comments", "ai_comments", "comments",
                          "process_name"]:
                value = ticket_details.get(field)
                if value and value not in ["None", "null"]:
                    if field == 'assignee':
                        assignee_name = ticket_details.get('assignee').get('assignee_name')
                        update_ticket_query['assignee_name'] = assignee_name if assignee_name else ''
                        assignee_email = ticket_details.get('assignee').get('assignee_email')
                        update_ticket_query['assignee_email'] = assignee_email if assignee_email else ''
                    elif field == 'status':
                        update_ticket_query['ticket_status'] = value
                    elif field == 'comments':
                        value = json.dumps(value, indent=4)
                        update_ticket_query['all_comments'] = str(value)
                    elif field == 'closed_date':
                        update_ticket_query['ticket_closed_date'] = value
                    else:
                        update_ticket_query[field] = value

            if "ticket_closed_date" in update_ticket_query:
                update_ticket_query["ticket_closed_date"] = datetime.strptime(update_ticket_query["ticket_closed_date"],
                                                                       "%Y-%m-%d %H:%M:%S")

            # Ensure we have fields to update
            if not update_ticket_query:
                logger.warning("No valid fields to update. Skipping execution.")
                return

            # Construct update query dynamically
            update_query_fields = ', '.join(
                f"{col} = TO_DATE(:{col}, 'YYYY-MM-DD HH24:MI:SS')" if col == "closed_date" else f"{col} = :{col}"
                for col in update_ticket_query.keys()
            )

            executable_query = f"""
                UPDATE support_tickets 
                SET {update_query_fields} 
                WHERE jira_ticket_id = :jira_ticket_id AND customer_name = :customer_name
            """

            # Add necessary parameters
            update_ticket_query["jira_ticket_id"] = jira_ticket_id
            update_ticket_query["customer_name"] = customer_name

            logger.info(f"Jira update query: {executable_query}")
            logger.info(f"Update Query Parameters: {update_ticket_query}")
            # print(f"executable_query: {executable_query}")
            # print(f"update_ticket_query: {update_ticket_query}")
            # Execute query with better error handling
            with conn.cursor() as db_cursor:
                db_cursor.execute(executable_query, update_ticket_query)
                conn.commit()

            logger.info("Ticket details updated successfully!")

        except Exception as e:
            logger.error(f"Unable to update the Jira ticket details in DB. Error: {e}", exc_info=True)

    @classmethod
    async def _insert_ticket(cls, ticket_details, existing_tickets, db_cursor, logger):
        insert_ticket = """
        insert into support_tickets(
          ticket_id,
          jira_ticket_id,
          summary,
          description,
          assignee_name,
          assignee_email,
          ticket_created_date,
          ticket_status,
          customer_name,
          process_name,
          priority,
          all_comments,
          product_name
        ) 
        values(
          support_ticket_id_seq.nextval,
          :jira_ticket_id,
          :summary,
          :description,
          :assignee_name,
          :assignee_email,
          to_date(:ticket_created_date, 'YYYY-MM-DD HH24:MI:SS'),
          :ticket_status,
          :customer_name,
          :process_name,
          :priority,
          :all_comments,
          :product_name
        )"""

        if ticket_details.get('jira_ticket_id') not in existing_tickets:
            try:
                db_cursor.execute(
                    insert_ticket,
                    {
                        'jira_ticket_id': ticket_details.get('jira_ticket_id'),
                        'summary': ticket_details.get('summary'),
                        'description': ticket_details.get('description'),
                        'assignee_name': ticket_details.get('assignee').get('name'),
                        'assignee_email': ticket_details.get('assignee').get('email'),
                        'ticket_created_date': ticket_details.get('created'),
                        'ticket_status': ticket_details.get('status'),
                        'customer_name': ticket_details.get('customer_name'),
                        'process_name': ticket_details.get('process_name'),
                        'priority': ticket_details.get('priority'),
                        'product_name': ticket_details.get('product_name'),
                        'all_comments': str(ticket_details.get('comments'))
                    }
                )
                db_cursor.connection.commit()
            except Exception as e:
                logger.error(f"Failed to insert ticket details to DB. Error details; {e}")
        else:
            cls._update_ticket_details(ticket_details, ticket_details.get('customer_name'), application_db_conn, logger)

    @classmethod
    def _store_tickets_db(cls, tickets, application_db_conn, logger):
        logger.info("Storing tickets into db..")

        existing_tickets = cls._get_existing_tickets(application_db_conn, logger)

        insert_ticket = """
insert into support_tickets(
  ticket_id,
  jira_ticket_id,
  summary,
  description,
  assignee_name,
  assignee_email,
  ticket_created_date,
  ticket_status,
  customer_name,
  process_name,
  priority,
  all_comments,
  product_name
) 
values(
  support_ticket_id_seq.nextval,
  :jira_ticket_id,
  :summary,
  :description,
  :assignee_name,
  :assignee_email,
  to_date(:ticket_created_date, 'YYYY-MM-DD HH24:MI:SS'),
  :ticket_status,
  :customer_name,
  :process_name,
  :priority,
  :all_comments,
  :product_name
)"""

        with application_db_conn.cursor() as db_cursor:
            for each_ticket in tickets:
                # print(f"each_ticket: {each_ticket}")


    @classmethod
    def _get_available_tickets(cls, conn, logger):
        pass

    @classmethod
    def _fetch_customer_process_data(cls, nosql_conn, logger):
        logger.info("Fetching customer process data...")

        customer_details_query = f"""
        SELECT 
            customer_name, 
            process_name, 
            process_details,
            product_name
        FROM CustomerProcessDetails
"""
        # print(f'customer_details_query: {customer_details_query}')
        try:
            rows = tm.execute_select_query(nosql_conn, customer_details_query)
            # print(f"rows: {rows}")
            product_dict = {}

            for each_row in rows:
                customer_name = each_row.get('customer_name')
                process_name = each_row.get('process_name')
                process_description = each_row.get('process_details', {}).get('description', '')
                product_name = each_row.get('product_name')

                if product_name not in product_dict:
                    product_dict[product_name] = {}

                if customer_name not in product_dict[product_name]:
                    product_dict[product_name][customer_name] = []

                product_dict[product_name][customer_name].append({
                    "process_name": process_name,
                    "process_description": process_description
                })

            final_result = {}
            for product_name, customers in product_dict.items():
                final_result[product_name] = {
                    customer_id: processes
                    for customer_id, processes in customers.items()
                }

            return final_result

        except Exception as e:
            logger.error(f"Error while fetching customer process data: {str(e)}")
            return {}

    @classmethod
    def _get_process_flow(cls, customer_name, process_name, nosql_conn, logger):
        logger.info("Fetching the process flow from db..")

        process_flow_query = f"""
        SELECT 
            process_details 
        FROM CustomerProcessDetails 
        where customer_name = '{customer_name}' 
        and process_name = '{process_name}'
        """

        # print(f"process_flow_query: {process_flow_query}")
        try:
            process_data = tm.execute_select_query(nosql_conn, process_flow_query)
            process_flow = process_data[0].get('process_details').get('flow')
        except Exception as e:
            logger.error(f"Failed to get the process flow for customer_name: {customer_name}, process_name: {process_name}. Error details: {e}")
            process_flow = ''

        return process_flow


class JiraActivities (AttachmentProcessor, ProcesTicketsDB):
    @classmethod
    def _authenticate_jira(cls, server_url, jira_user_name, jira_api_token, logger):
        logger.info(f"Authenticating Jira with username - {jira_user_name}...")
        try:
            jira_options = {'server': server_url}
            jira = JIRA(options=jira_options, basic_auth=(jira_user_name, jira_api_token))
            logger.info(f"Jira account authenticated with user: {jira_user_name}")
            return jira
        except Exception as e:
            logger.error(f'Exception while authenticating Jira account: {e}')
            return None

    @classmethod
    def _format_jira_date(cls, date_str):
        """Converts Jira date format to 'YYYY-MM-DD HH24:MI:SS' format."""
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%d %H:%M:%S")
        return None

    @classmethod
    def _clean_summary(cls, description, logger):
        """Cleans and formats Jira descriptions by removing unnecessary elements and special characters."""
        logger.info('Cleaning Summary...')

        try:
            if not description:
                return ''

            patterns = [
                (r'[\u200B-\u200D\uFEFF]', ''),  # Remove zero-width spaces, BOM (Byte Order Mark), etc.
                (r'\S+@\S+\.\S+', ''),  # Remove email addresses
                # (r'\[.*?]', ''),  # Remove content inside square brackets
                (r'{color.*?}', ''),  # Remove {color} tags
                (r'<[^>]+>', ''),  # Remove HTML tags
                (r'{[^{}]*}', ''),  # Remove unnecessary curly brackets
                (r'\s+', ' ')  # Replace multiple spaces with a single space
            ]

            # Apply all regex substitutions
            for pattern, replacement in patterns:
                description = re.sub(pattern, replacement, description)

            return description.strip()
        except Exception as e:
            logger.error(f'Exception while cleaning summary: {e}', exc_info=True)
            return ''

    @classmethod
    def _download_attachment(cls, attachment, save_path, jira_user_name, jira_api_token, logger):
        """Downloads an attachment from Jira and saves it locally."""
        try:
            attachment_url = attachment.content
            filename = os.path.join(save_path, attachment.filename)

            response = requests.get(attachment_url, auth=(jira_user_name, jira_api_token), stream=True)
            if response.status_code == 200:
                with open(filename, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        file.write(chunk)
                logger.info(f"Downloaded attachment: {filename}")
                return filename
            else:
                logger.warning(
                    f"Failed to download attachment {attachment.filename} - Status Code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading attachment {attachment.filename}: {e}")
            return None

    @classmethod
    def get_tickets_bkp(cls, server_url, jira_user_name, jira_api_token, logger, status='', project_name='AEI', assignee='', google_key_path='../configuration/Google_Key(WinfoBots).json'):
        """Fetches new tickets from Jira and downloads attachments."""
        try:
            logger.info("Fetching new tickets")

            # Constructing JQL query correctly
            jql_str = f'project = "{project_name}"'
            if status.lower() != 'all':
                if not status:
                    jql_str += ' AND (status = "NEW" OR status = "InProgress")'
                elif status:
                    jql_str += f' AND status = "{status}"'

            if assignee:
                jql_str += f' AND assignee = "{assignee}"'

            tickets = []
            jira = cls._authenticate_jira(server_url, jira_user_name, jira_api_token, logger)
            if not jira:
                logger.error("JIRA authentication failed, unable to fetch tickets")
                return json.dumps({"tickets": tickets}, indent=4)

            logger.info(f"Jira querying with: {jql_str}")
            issues = jira.search_issues(jql_str)

            save_attachments_path = '../DownloadedFiles/JiraFiles'
            os.makedirs(save_attachments_path, exist_ok=True)

            if issues:
                for single_issue in issues:
                    ticket_attachments_dict = dict()

                    ticket_attachments = []
                    if single_issue.fields.attachment:
                        for attachment in single_issue.fields.attachment:
                            file_path = cls._download_attachment(attachment, save_attachments_path, jira_user_name,
                                                                 jira_api_token, logger)
                            if file_path:
                                file_path = os.path.abspath(str(file_path))
                                ticket_attachments.append(file_path)

                    if len(ticket_attachments) > 0:
                        for each_attachment in ticket_attachments:
                            file_name = each_attachment.split('\\')[-1]
                            uploaded_path = gcs.upload_to_gcs(
                                'winfobots',
                                each_attachment,
                                f'SupportTicketAttachments/{file_name}',
                                logger,
                                google_key_path=google_key_path
                            )
                            ticket_attachments_dict[each_attachment] = uploaded_path

                    attachment_content = ''
                    for each_gcs in ticket_attachments_dict.values():
                        file_content = cls._get_attachment_content_gcs(each_gcs, logger, google_key_config_path=google_key_path, model_name='gemini-2.0-flash-001')
                        attachment_content += file_content
                    # print(f"ticket id: {single_issue.key}\nattachment_content: {attachment_content}")
                    description = cls._clean_summary(single_issue.fields.description, logger) + attachment_content

                    assignee_details = single_issue.fields.assignee
                    assignee_name = assignee_details.displayName if assignee_details else ""
                    assignee_email = getattr(assignee_details, 'emailAddress', "")
                    comments = [
                        cls._clean_summary(comment.body, logger) for comment in
                        single_issue.fields.comment.comments
                    ] if single_issue.fields.comment.comments else []
                    comments = '\n\n'.join(comments)

                    ticket_data = {
                        "customer_name": project_name,
                        "jira_ticket_id": str(single_issue.key).strip(),
                        "summary": str(single_issue.fields.summary).strip(),
                        "description": description or "No description",
                        "assignee": {
                            "name": assignee_name,
                            "email": assignee_email
                        },
                        "created": cls._format_jira_date(single_issue.fields.created),
                        "closed_date": cls._format_jira_date(getattr(single_issue.fields, 'resolutiondate', None)),
                        "status": single_issue.fields.status.name,
                        "process_name": getattr(single_issue.fields, 'process_name', "Not Set"),
                        "priority": single_issue.fields.priority.name if single_issue.fields.priority else "Not Set",
                        "comments": comments
                    }
                    tickets.append(ticket_data)

                logger.info(f"Fetched {len(tickets)} new tickets")
                return json.dumps({"tickets": tickets}, indent=4)
            else:
                logger.info("No new tickets found.")
                return json.dumps({"tickets": []}, indent=4)

        except Exception as e:
            logger.error(f'Exception while fetching new tickets - {e}', exc_info=True)
            return json.dumps({"tickets": []}, indent=4)

    @classmethod
    def _process_attachments_and_get_content_gcs(cls, ticket_attachments, logger, gcs_bucket_name='winfobots', gcs_folder_path='SupportTicketAttachments', google_key_config_path='../configuration/Google_Key(WinfoBots).json', model_name='gemini-2.0-flash-001'):
        logger.info("Processing attachments and extracting the content from the file..")
        attachment_content = []
        ticket_attachments_dict = {}

        try:
            for each_attachment in ticket_attachments:
                file_name = os.path.basename(each_attachment)
                uploaded_path = gcs.upload_to_gcs(
                    gcs_bucket_name,
                    each_attachment,
                    f'{gcs_folder_path}/{file_name}',
                    logger,
                    google_key_path=google_key_config_path
                )
                ticket_attachments_dict[each_attachment] = uploaded_path

            for each_gcs in ticket_attachments_dict.values():
                try:
                    file_content = cls._get_attachment_content_gcs(
                        each_gcs, logger, google_key_config_path=google_key_config_path, model_name=model_name
                    )
                    attachment_content.append(file_content)
                except Exception as e:
                    logger.error(f"Failed to get the file content for `{each_gcs}`. Error Details: {e}")
        except Exception as e:
            logger.error(f"Failed to process GCS file. Error details: {e}")

        return attachment_content

    @classmethod
    def _process_attachments_and_get_content(
            cls, ticket_attachments, logger, google_key_config_path='../configuration/Google_Key(WinfoBots).json',
            model_name='gemini-2.0-flash-001'
    ):
        logger.info("Processing attachments and extracting the content from the file..")
        attachment_content = []

        for each_attachment in ticket_attachments:
            try:
                file_content = cls._get_attachment_content(
                    each_attachment, logger, google_key_config_path=google_key_config_path, model_name=model_name
                )
                attachment_content.append(file_content)
            except Exception as e:
                logger.error(f"Failed to get the file content for `{each_attachment}`. Error Details: {e}")

        return attachment_content

    @classmethod
    def _download_comment_attachment(cls, issue, file_name, save_path, logger):
        """Downloads inline images found in Jira comments."""
        try:
            for attachment in issue.fields.attachment:
                if attachment.filename == file_name:
                    file_path = os.path.join(save_path, attachment.filename)
                    with open(file_path, 'wb') as file:
                        file.write(attachment.get())
                    logger.info(f"Downloaded comment attachment: {file_path}")
                    return file_path
            logger.warning(f"Attachment {file_name} not found in issue {issue.key}")
        except Exception as e:
            logger.error(f"Error downloading comment attachment {file_name}: {e}")
        return ''

    @classmethod
    def get_tickets(cls, product_name, server_url, jira_user_name, jira_api_token, logger, status='', project_name='AEI', assignee='',
                    p_closed_ticket_ids=None, p_not_closed_ticket_ids=None, exclude_tickets=False,
                    google_key_path='../configuration/Google_Key(WinfoBots).json',
                    save_attachments_path ='../DownloadedFiles/JiraFiles'):
        """Fetches new tickets from Jira and downloads attachments for respective comments."""
        try:
            logger.info("Fetching new tickets")

            # Construct JQL query
            jql_str = f'project = "{project_name}"'

            try:
                if p_closed_ticket_ids:
                    ticket_condition = "NOT IN" if exclude_tickets else "IN"
                    ticket_list_str = ", ".join(f'"{tid}"' for tid in p_closed_ticket_ids)
                    jql_str += f' AND key {ticket_condition} ({ticket_list_str})'
            except Exception as e:
                logger.error(
                    f"Failed to apply ticket ids condition with value - {p_closed_ticket_ids}. Error details: {e}"
                )

            if status.lower() != 'all':
                jql_str += f' AND status IN ("NEW", "InProgress")' if not status else f' AND status = "{status}"'
            if assignee:
                jql_str += f' AND assignee = "{assignee}"'

            tickets = []
            jira = cls._authenticate_jira(server_url, jira_user_name, jira_api_token, logger)
            if not jira:
                logger.error("JIRA authentication failed, unable to fetch tickets")
                return json.dumps({"tickets": tickets}, indent=4)

            logger.info(f"Jira querying with: {jql_str}")
            issues = jira.search_issues(jql_str)

            # save_attachments_path = '../DownloadedFiles/JiraFiles'
            os.makedirs(save_attachments_path, exist_ok=True)

            if issues:
                for single_issue in issues:
                    ticket_comments = []

                    # Process Jira Comments & Download Attachments
                    if single_issue.fields.comment.comments:
                        comment_id = 1
                        for comment in single_issue.fields.comment.comments:
                            comment_attachments = []

                            # Extract Author Details
                            author_name = comment.author.displayName if comment.author else ""
                            author_email = getattr(comment.author, 'emailAddress', "")
                            comment_text = cls._clean_summary(comment.body, logger)

                            jira_images = re.findall(r'!(.+?)\|thumbnail!', comment.body)  # Atlassian wiki-style

                            for image_name in jira_images:
                                file_path = cls._download_comment_attachment(single_issue, image_name,
                                                                             save_attachments_path, logger)
                                file_path = str(file_path)

                                if file_path:
                                    abs_file_path = os.path.abspath(file_path)
                                    comment_attachments.append(abs_file_path)

                            comments_attachment_content = cls._process_attachments_and_get_content(
                                comment_attachments, logger, google_key_config_path=google_key_path
                            )

                            ticket_comments.append({
                                "comment_id": comment_id,
                                "author": author_name,
                                "author_email": author_email,
                                "timestamp": cls._format_jira_date(comment.created),
                                "text": comment_text,
                                "attachments_content": comments_attachment_content
                            })

                            comment_id += 1

                    ticket_attachments = []
                    if single_issue.fields.attachment:
                        for attachment in single_issue.fields.attachment:
                            file_path = cls._download_attachment(
                                attachment, save_attachments_path, jira_user_name, jira_api_token, logger
                            )
                            if file_path:
                                abs_file_path = os.path.abspath(str(file_path))
                                ticket_attachments.append(abs_file_path)

                    if str(single_issue.key).strip() in p_not_closed_ticket_ids:
                        attachment_content = cls._process_attachments_and_get_content(
                            ticket_attachments, logger, google_key_config_path=google_key_path
                        )
                        description = cls._clean_summary(single_issue.fields.description, logger) + '\n\n'.join(attachment_content)
                    else:
                        description = ''

                    assignee_details = single_issue.fields.assignee
                    assignee_name = assignee_details.displayName if assignee_details else ""
                    assignee_email = getattr(assignee_details, 'emailAddress', "")

                    ticket_data = {
                        "customer_name": project_name,
                        "jira_ticket_id": str(single_issue.key).strip(),
                        "summary": str(single_issue.fields.summary).strip(),
                        "description": description,
                        "assignee": {
                            "name": assignee_name,
                            "email": assignee_email
                        },
                        "created": cls._format_jira_date(single_issue.fields.created),
                        "closed_date": cls._format_jira_date(getattr(single_issue.fields, 'resolutiondate', None)),
                        "status": single_issue.fields.status.name,
                        "process_name": getattr(single_issue.fields, 'process_name', ""),
                        "priority": single_issue.fields.priority.name if single_issue.fields.priority else "",
                        "comments": ticket_comments,
                        "product_name": product_name
                    }
                    tickets.append(ticket_data)
                    # break

                logger.info(f"Fetched {len(tickets)} new tickets")
                return json.dumps({"tickets": tickets}, indent=4)
            else:
                logger.info("No new tickets found.")
                return json.dumps({"tickets": []}, indent=4)

        except Exception as e:
            logger.error(f'Exception while fetching new tickets - {e}', exc_info=True)
            return json.dumps({"tickets": []}, indent=4)

    @classmethod
    def _process_tickets(
            cls, all_customer_process_details, application_db_conn, nosql_conn, logger,
            google_key_config_path='../configuration/Google_Key(WinfoBots).json'
    ):
        logger.info("Started processing tickets..")

        tickets_query = (
            "select TICKET_ID, JIRA_TICKET_ID, SUMMARY, DESCRIPTION, CUSTOMER_NAME, PRODUCT_NAME "
            "from support_tickets "
            # "where JIRA_TICKET_ID = 'WIS-30529'"
            "where lower(TICKET_STATUS) not in ('resolved', 'completed', 'closed') "
            "and ai_comments is null order by 1"
        )

        with application_db_conn.cursor() as application_db_cursor:
            application_db_cursor.execute(tickets_query)
            all_tickets = application_db_cursor.fetchall()
            # print(f"all_tickets: {all_tickets}")

            for each_ticket in all_tickets:
                # ticket_id = each_ticket[0]
                jira_ticket_id = each_ticket[1]
                # ticket_summary = each_ticket[2]
                ticket_description = each_ticket[3]
                customer_name = each_ticket[4]
                product_name = each_ticket[5]

                try:
                    customer_process_details = all_customer_process_details.get(product_name).get(customer_name)
                    # print(f"customer_process_details: {customer_process_details}")
                except Exception as e:
                    logger.error(f"failed to get the customer process details. Error: {e}")
                    customer_process_details = []

                # if isinstance(ticket_summary, oracledb.LOB):
                #     ticket_summary = ticket_summary.read()
                if isinstance(ticket_description, oracledb.LOB):
                    ticket_description = ticket_description.read()

                ag1_resp = sa.Agents.agent1(
                    '',
                    ticket_description,
                    customer_process_details,
                    customer_name,
                    product_name,
                    nosql_conn,
                    logger,
                    google_key_config_path=google_key_config_path
                )
                # print(f"ag1_resp: {ag1_resp}")
                if not ag1_resp:
                    continue

                ag1_resp = json.loads(ag1_resp)

                try:
                    query = f"""
                            SELECT count(1) AS count 
                            FROM SupportAnalyzerAgentResponses 
                            WHERE issue_id = '{jira_ticket_id}' AND customer_name = '{customer_name}'
                            """
                    # print(f"query: {query}")
                    ticket_cnt = tm.execute_select_query(nosql_conn, query)
                    ticket_cnt = ticket_cnt[0].get('count')
                except Exception as e:
                    logger.error(f"Failed to get the count of jira ticket from response table. Error details: {e}")
                    ticket_cnt = 0

                if ticket_cnt == 0:
                    try:
                        ag1_resp_insertion = {
                            "issue_id": jira_ticket_id,
                            "customer_name": customer_name,
                            "ag1_resp": ag1_resp,
                            "ag2_resp": ag2_resp
                        }

                        ticket_flg = tm.execute_insert_query(
                            nosql_conn, ag1_resp_insertion, 'SupportAnalyzerAgentResponses'
                        )
                    except Exception as e:
                        logger.error(f"Unable to insert the jira ticket summary. Error details: {e}")
                        ticket_flg = False
                else:
                    try:
                        ag1_resp_update = {
                            "issue_id": jira_ticket_id,
                            "customer_name": customer_name,
                            "ag1_resp": ag1_resp
                        }

                        ticket_flg = tm.execute_update_query(nosql_conn, ag1_resp_update, 'SupportAnalyzerAgentResponses')
                    except Exception as e:
                        logger.error(f"Unable to insert the jira ticket summary. Error details: {e}")
                        ticket_flg = False

                process_flow = cls._get_process_flow(customer_name, ag1_resp.get('process_name'), nosql_conn, logger)
                ag2_resp = sa.Agents.agent2(
                    '',
                    ag1_resp.get('ticket_description'),
                    customer_name,
                    ag1_resp.get('process_name'),
                    process_flow,
                    product_name,
                    nosql_conn,
                    logger,
                    google_key_config_path=google_key_config_path
                )
                # print(f"ag2_resp: {ag2_resp}")

                if not ag2_resp:
                    continue

                ag2_resp = json.loads(ag2_resp)
                if ticket_flg:
                    try:
                        update_ticket = {
                            "issue_id": jira_ticket_id,
                            "customer_name": customer_name,
                            "ag1_2_resp": ag2_resp
                        }

                        update_flg = tm.execute_update_query(
                            nosql_conn, update_ticket, 'SupportAnalyzerAgentResponses'
                        )
                    except Exception as e:
                        logger.error(f"Failed to update agent 2 to ticket - {jira_ticket_id}. Error details: {e}")

                categorized_questions = sa.GetContents.group_questions_by_source(ag2_resp, logger)
                # print(f"categorized_questions: {categorized_questions}")

                doc_resp, winfo_db_data, oracle_db_data = sa.Agents.agent3(
                    categorized_questions, product_name, ag1_resp.get('process_name'), customer_name,
                    application_db_conn, nosql_conn, logger, google_key_config_path=google_key_config_path
                )

                ag3_resp = []

                if ticket_flg:
                    try:
                        update_ticket = {
                            "issue_id": jira_ticket_id,
                            "customer_name": customer_name,
                            "ag3_doc_resp": doc_resp,
                            "ag3_app_db_resp": winfo_db_data,
                            "ag3_oracle_db_resp": oracle_db_data
                        }

                        update_flg = tm.execute_update_query(
                            nosql_conn, update_ticket, 'SupportAnalyzerAgentResponses'
                        )
                    except Exception as e:
                        logger.error(f"Failed to update agent3 for ticket - {jira_ticket_id}. Error details: {e}")

                ag3_resp.extend(doc_resp)
                ag3_resp.extend(winfo_db_data)
                ag3_resp.extend(oracle_db_data)

                # print(f"ag3_resp: {ag3_resp}")

                ag4_resp = sa.Agents.agent4(
                    ag1_resp.get('ticket_description'), ag3_resp, customer_name, product_name, nosql_conn, logger,
                    google_key_config_path=google_key_config_path
                )
                ag4_resp = json.loads(ag4_resp)

                if ticket_flg:
                    try:
                        update_ticket = {
                            "issue_id": jira_ticket_id,
                            "customer_name": customer_name,
                            "ag1_4_resp": ag4_resp
                        }

                        update_flg = tm.execute_update_query(
                            nosql_conn, update_ticket, 'SupportAnalyzerAgentResponses'
                        )
                    except Exception as e:
                        logger.error(f"Failed to update agent4 for ticket - {jira_ticket_id}. Error details: {e}")

                # print(f"ag4_resp: {ag4_resp}")

                ai_resolution = ag4_resp.get('resolution')
                # print(f"ai_resolution: {ai_resolution}")
                if ai_resolution:
                    ai_res_comments = {
                        'jira_ticket_id': jira_ticket_id,
                        'ai_comments': ai_resolution,
                        'process_name': ag1_resp.get('process_name')
                    }

                    # print(f"ai_res_comments: {ai_res_comments}")
                    cls._update_ticket_details(ai_res_comments, customer_name, application_db_conn, logger)
                # break

    @classmethod
    def _get_resolved_tickets(cls, customer_name, winfo_db_conn, logger):
        logger.info(f"Fetching the resolved ticket ids for customer: {customer_name}")
        try:
            ticket_query_closed = """
select jira_ticket_id 
FROM support_tickets 
WHERE lower(TICKET_STATUS) in ('resolved', 'completed', 'closed') 
and customer_name = :customer_name
order by 1
            """

            with winfo_db_conn.cursor() as winfo_db_cursor:
                winfo_db_cursor.execute(ticket_query_closed, {'customer_name': customer_name})
                closed_ticket_ids = winfo_db_cursor.fetchall()
                closed_ticket_ids = [ticket[0] for ticket in closed_ticket_ids]
        except Exception as e:
            logger.warning(f"Failed to get the list of resolved tickets from winfo DB. Error details: {e}")
            closed_ticket_ids = []

        try:
            ticket_query_not_closed = """
select jira_ticket_id 
FROM support_tickets 
WHERE lower(TICKET_STATUS) not in ('resolved', 'completed', 'closed') 
and customer_name = :customer_name
order by 1
            """

            with winfo_db_conn.cursor() as winfo_db_cursor:
                winfo_db_cursor.execute(ticket_query_not_closed, {'customer_name': customer_name})
                not_closed_ticket_ids = winfo_db_cursor.fetchall()
                not_closed_ticket_ids = [ticket[0] for ticket in not_closed_ticket_ids]
        except Exception as e:
            logger.warning(f"Failed to get the list of resolved tickets from winfo DB. Error details: {e}")
            not_closed_ticket_ids = []

        return not_closed_ticket_ids, closed_ticket_ids

    @classmethod
    def jira_support_agents(
            cls, application_db_conn, nosql_conn, logger, status='all', assignee='',
            jira_config_path='../configuration/jira_config.json',
            google_key_config_path='../configuration/Google_Key(WinfoBots).json',
            save_attachments_path='../DownloadedFiles/JiraFiles'
    ):
        logger.info("Jira support agents function called.")
        with open(jira_config_path, 'r') as jira_config_file:
            jira_config = json.load(jira_config_file)

        projects = jira_config.get('projects')
        all_tickets = []
        for each_project in projects:
            try:
                server = each_project['jira_server']
                jira_user_name = each_project['jira_username']
                jira_api_token = each_project['jira_api_token']
                project_name = each_project['jira_project_name']
                product_name = each_project['product_name']

                r_not_closed_ticket_ids, r_closed_ticket_ids = cls._get_resolved_tickets(
                    project_name, application_db_conn, logger
                )
                # print(f'ticket_ids: {ticket_ids}')
                if r_closed_ticket_ids:
                    exclude_tickets = True
                else:
                    exclude_tickets = False

                tickets = cls.get_tickets(
                    product_name, server, jira_user_name, jira_api_token, logger, project_name=project_name,
                    status=status, assignee=assignee, p_closed_ticket_ids=r_closed_ticket_ids,
                    p_not_closed_ticket_ids=r_not_closed_ticket_ids, exclude_tickets=exclude_tickets,
                    google_key_path=google_key_config_path, save_attachments_path=save_attachments_path
                )
                tickets = json.loads(tickets)
                all_tickets.extend(tickets.get('tickets'))
            except Exception as e:
                logger.error(f"jira configurations are not configured properly. Error details: {e}")
                continue
            # break

        # print(f"all_tickets: {all_tickets}")

        cls._store_tickets_db(all_tickets, application_db_conn, logger)

        cust_process_data = cls._fetch_customer_process_data(nosql_conn, logger)
        # print(f"cust_process_data: {cust_process_data}")

        cls._process_tickets(
            cust_process_data,
            application_db_conn,
            nosql_conn,
            logger,
            google_key_config_path=google_key_config_path
        )


if __name__ == '__main__':
    from loggerConfig import LoggerManager as lg
    from dbConnect import DBConnection as db
    from nosqlConnection import NoSQLConnectionManager as nosql_db

    with open('../configuration/config.json', 'r') as db_details:
        db_details = json.load(db_details)
        wai_dev_db = db_details.get('WAI_NONPROD')
        nosql_db_details = db_details.get('WAI_NoSQL')

    l_wai_dev_db_conn = db.connect_db('wai_dev_db', db_details=wai_dev_db)
    l_nosql_conn = nosql_db.get_nosql_conn(
        nosql_db_details=nosql_db_details,
        private_key_file='../../certs/oci_private.pem'
    )
    l_logger = lg.configure_logger('../logs/JiraActivities')

    JiraActivities.jira_support_agents(
        l_wai_dev_db_conn,
        l_nosql_conn,
        l_logger,
        google_key_config_path='../configuration/Google_Key(WAI).json',
        jira_config_path='../configuration/jira_config.json'
    )

    # print(JiraActivities.fetch_customer_process_data(l_nosql_conn, l_logger))

    db.close_connection(l_wai_dev_db_conn, 'wai_dev_db')
    nosql_db.close_nosql_conn(l_nosql_conn)
    db.close_all_pools()
    lg.shutdown_logger(l_logger)
