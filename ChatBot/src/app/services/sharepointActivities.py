import requests
import os
import pandas as pd
import json
from emailActivities import get_file_type
from datetime import datetime
from urllib.parse import urlparse, quote
from folderActivities import sanitize_filename


def check_path_type(path, logger):
    logger.info('check_path_type function called.')
    if os.path.isfile(path):
        return "File"
    elif os.path.isdir(path):
        return "Directory"
    else:
        logger.error('Invalid path or does not exist')
        return "Invalid path or doesn't exist"


def get_sp_folder_path(process_name, target_application, file_url, folder_name, db_cursor, logger):
    logger.info('get_sp_folder_path function called.')
    parsed_url = urlparse(file_url)

    parent_path_sql = (
        "select DOC_REP_OUTPUT_FOLDER from PROCESS_ADMINISTRATION where WB_PROCESS_NAME = :process_name "
        "and TARGET_APPLICATION = :target_application"
    )
    db_cursor.execute(
        parent_path_sql,
        {
            'process_name': process_name,
            'target_application': target_application
        }
    )
    parent_path = db_cursor.fetchone()[0]

    site_name_sql = (
        "select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg "
        "where cl.CONFIG_GROUP_ID = cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME= 'Sharepoint' "
        "and cl.CONFIGURATION_NAME = 'Site Name'"
    )
    db_cursor.execute(site_name_sql)
    site_name = db_cursor.fetchone()[0]

    root_folder_sql = (
        "select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg "
        "where cl.CONFIG_GROUP_ID = cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME= 'Sharepoint' "
        "and cl.CONFIGURATION_NAME = 'Root Folder'"
    )
    db_cursor.execute(root_folder_sql)
    root_folder = db_cursor.fetchone()[0]

    # Extract query parameters
    # query_params = parse_qs(parsed_url.query)

    # Get the file parameter and decode it
    # file_param = query_params.get('file', [None])[0]

    # if not file_param:
    #     return None

    # Decode the file parameter
    # decoded_file_param = unquote(file_param)

    # Extract the base URL
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Define the new path structure
    new_path = f"/sites/{site_name}/Shared {root_folder}/Forms/AllItems.aspx"

    # Encode the new id parameter value
    new_id_value = quote(f'/sites/{site_name}/Shared {root_folder}/{parent_path}/{folder_name}')

    # Construct the new URL
    new_query = f"id={new_id_value}"
    output_url = f"{base_url}{new_path}?{new_query}"
    # print(f'output_url: {output_url}')

    return output_url


def get_sharepoint_details(db_cursor, logger):
    logger.info('get_sharepoint_details function called.')
    try:
        site_id = ("select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg where cl.CONFIG_GROUP_ID = "
                   "cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME = 'Sharepoint' and cl.CONFIGURATION_NAME = 'Site ID'")
        db_cursor.execute(site_id)
        site_id = db_cursor.fetchone()[0]

        drive_id = ("select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg where cl.CONFIG_GROUP_ID = "
                    "cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME = 'Sharepoint' and cl.CONFIGURATION_NAME = 'Drive ID'")
        db_cursor.execute(drive_id)
        drive_id = db_cursor.fetchone()[0]

        client_details = (
            "select CONFIGURATION_VALUE, winbot_toolkit.decrypt(CONFIG_PASSWORD) from WB_CONFIG_LINES cl, "
            "WB_CONFIG_GROUP cg where cl.CONFIG_GROUP_ID = cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME = "
            "'Sharepoint' and cl.CONFIGURATION_NAME = 'Client Details'")
        db_cursor.execute(client_details)
        client_id, client_secret = db_cursor.fetchone()

        tenant_id = (
            "select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg where cl.CONFIG_GROUP_ID = "
            "cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME = 'Sharepoint' and cl.CONFIGURATION_NAME = 'Tenant ID'")
        db_cursor.execute(tenant_id)
        tenant_id = db_cursor.fetchone()[0]

        scope = ("select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg where cl.CONFIG_GROUP_ID = "
                 "cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME = 'Sharepoint' and cl.CONFIGURATION_NAME = 'Sharepoint "
                 "Scope'")
        db_cursor.execute(scope)
        scope = db_cursor.fetchone()[0]

        # input_path = (
        #     "select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg where cl.CONFIG_GROUP_ID = "
        #     "cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME = 'Sharepoint' and cl.CONFIGURATION_NAME = 'Input Path'")
        # db_cursor.execute(input_path)
        # input_path = db_cursor.fetchone()[0]
        #
        # output_path = (
        #     "select CONFIGURATION_VALUE from WB_CONFIG_LINES cl, WB_CONFIG_GROUP cg where cl.CONFIG_GROUP_ID = "
        #     "cg.CONFIG_GROUP_ID and cg.CONFIG_GROUP_NAME = 'Sharepoint' and cl.CONFIGURATION_NAME = 'Output Path'")
        # db_cursor.execute(output_path)
        # output_path = db_cursor.fetchone()[0]

        details = {
            'SITE_ID': site_id,
            'DRIVE_ID': drive_id,
            'CLIENT_ID': client_id,
            'CLIENT_SECRET': client_secret,
            'TENANT_ID': tenant_id,
            'SCOPE': scope
            # 'INPUT_PATH': input_path,
            # 'OUTPUT_PATH': output_path
        }

        logger.info('Fetched sharepoint details from DB.')
    except Exception as e:
        logger.error(f'Sharepoint details are not configured. Error details: {e}')
        details = None

    return details


def get_sharepoint_path(process_name, target_application, db_cursor, logger):
    logger.info('get_sharepoint_path function called.')
    sharepoint_path_query = (f'select * from PROCESS_ADMINISTRATION where WB_PROCESS_NAME = \'{process_name}\' '
                             f'and TARGET_APPLICATION = \'{target_application}\'')
    # print(f'sharepoint_path_query: {sharepoint_path_query}')

    try:
        db_cursor.execute(sharepoint_path_query)
        logger.info('Getting sharepoint  path.')

        sharepoint_path_cols = [x[0] for x in db_cursor.description]
        sharepoint_path_rows = db_cursor.fetchall()
        sharepoint_path = pd.DataFrame(sharepoint_path_rows, columns=sharepoint_path_cols)
        sharepoint_path = sharepoint_path.to_json(orient='table')
        sharepoint_path = json.dumps(json.loads(sharepoint_path), sort_keys=False)

        sharepoint_path = json.loads(sharepoint_path)
        if sharepoint_path['data']:
            sharepoint_path = sharepoint_path['data'][0]
            sharepoint_path = sharepoint_path['DOC_REP_OUTPUT_FOLDER']
            logger.info('Sharepoint path received.')
        else:
            logger.error('Failed to get sharepoint path.')
            sharepoint_path = ''

        return sharepoint_path
    except Exception as e:
        logger.error(f'Failed to update file. Error details: {e}')
        return ''


def get_access_token(sp_details, logger):
    logger.info('get_access_token function called.')
    client_id = sp_details['CLIENT_ID']
    client_secret = sp_details['CLIENT_SECRET']
    tenant_id = sp_details['TENANT_ID']
    scope = sp_details['SCOPE']
    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    token_params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': scope,
    }

    access_token = ''
    try:
        token_response = requests.post(token_url, data=token_params)
        access_token = token_response.json()['access_token']
        logger.info('Access token generated.')
    except Exception as e:
        logger.error(f'Failed to generate access token. Error details: {e}')
        logger.error(f"sharepoint details: {sp_details}")

    return access_token


def get_access_token_1(client_id, client_secret, tenant_id, scope, logger):
    logger.info('get_access_token function called.')

    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    token_params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': scope,
    }

    access_token = ''
    try:
        token_response = requests.post(token_url, data=token_params)
        access_token = token_response.json()['access_token']
        logger.info('Access token generated.')
    except Exception as e:
        logger.error(f'Failed to generate access token. Error details: {e}')

    return access_token


def get_folder_id(access_token, drive_id, sh_path, logger):
    logger.info('get_folder_id function called.')
    folder_api_url = 'https://graph.microsoft.com/v1.0/drives/' + drive_id + '/root:/' + sh_path
    headers = {
        'Authorization': 'Bearer ' + access_token,
        # 'Accept': 'application/json;odata=verbose',
    }

    folder_id = ''
    try:
        response = requests.get(folder_api_url, headers=headers)
        folder_id = response.json()['id']
        logger.info('Folder id received.')
    except Exception as e:
        logger.error(f'Failed to get folder id. Error details: {e}')
    return folder_id


def create_sh_folder(access_token, site_id, drive_id, parent_folder_id, new_folder_name, logger):
    logger.info('create_sh_folder function called.')
    create_folder_url = (f'https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/'
                         f'{parent_folder_id}/children')
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json',
    }

    folder_payload = {
        'name': new_folder_name,
        'folder': {},
        '@microsoft.graph.conflictBehavior': 'fail',  # Specify behavior in case of a name conflict
    }
    response = requests.post(create_folder_url, headers=headers, json=folder_payload)
    return response.status_code


def download_sh_file(access_token, drive_id, file_id, file_name, folder_path, logger):
    logger.info('download_sh_file function called.')
    # Get the current time
    current_time = datetime.now()
    name_with_date = str(current_time).replace('-', '').replace('.', '').replace(':', '').replace(' ', '')
    file_name = name_with_date + file_name
    file_name = sanitize_filename(file_name)
    file_name = str(file_name).strip()
    local_path_to_save = folder_path + '\\' + file_name
    download_file_api_url = 'https://graph.microsoft.com/v1.0/drives/' + drive_id + '/items/' + file_id + '/content'
    headers = {
        'Authorization': 'Bearer ' + access_token,
    }
    response = requests.get(download_file_api_url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(local_path_to_save, "wb") as file:
            file.write(response.content)
    else:
        print(f"Failed to get file ID. Status code: {response.status_code}")
        return ""

    return local_path_to_save


def create_folder(full_path, folder_name, logger):
    logger.info('create_folder function called.')
    directory_path = str(full_path) + "\\" + folder_name
    try:
        os.makedirs(directory_path)
    except FileExistsError:
        print('file already present')
    return directory_path


def get_item_type(item_id, drive_id, access_token, logger):
    logger.info('get_item_type function called.')
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }
    url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        item_details = response.json()
        item_type = item_details.get('folder', None)
        if item_type is not None:
            return 'folder'
        else:
            return 'file'
    else:
        return None


def get_site_id(site_name, tenant_name, headers, logger):
    logger.info('get_site_id function called.')
    try:
        api_url = f"https://graph.microsoft.com/v1.0/sites/{tenant_name}:/sites/{site_name}"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json().get('id')
    except Exception as e:
        logger.error(f'Failed to get site id. Error details; {e}')
        return ''


def get_drive_id(site_name, tenant_name, headers, logger):
    logger.info('get_drive_id function called.')
    site_id = get_site_id(site_name, tenant_name, headers, logger)
    try:
        api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json().get('id')
    except Exception as e:
        logger.error(f'Failed to get drive id. Error details: {e}')


def move_sh_file(access_token, drive_id, file_id, destination_folder_id, child_name, logger):
    logger.info('move_sh_file function called')

    # Get the current time
    current_time = datetime.now()
    name_with_date = str(current_time).replace('-', '').replace('.', '').replace(':', '').replace(' ', '')
    child_name = name_with_date + child_name
    move_sh_file = 'https://graph.microsoft.com/v1.0/drives/' + drive_id + '/items/' + file_id

    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json',
    }
    move_payload = {
        'parentReference': {
            'id': destination_folder_id
        },
        'name': child_name
    }
    response = requests.patch(move_sh_file, headers=headers, json=move_payload)

    return response.json()["webUrl"]


def upload_file(source_path, access_token, site_id, drive_id, sp_path, logger):
    logger.info('upload_file function called.')

    if not os.path.exists(source_path):
        logger.error(f'The source file {source_path} does not exist.')
        return False, 'Source file does not exist.', '', ''

    try:
        with open(source_path, 'rb') as file:
            file_name = os.path.basename(source_path)
            logger.info(f'Uploading {file_name} to SharePoint.')
            content = file.read()

            upload_url = (f'https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{sp_path}/'
                          f'{file_name}:/content?@microsoft.graph.conflictBehavior=rename')

            response = requests.put(
                upload_url,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/octet-stream'
                },
                data=content
            )

            if response.status_code in [200, 201]:
                try:
                    # print(f'response.json(): {response.json()}')
                    file_url = response.json().get('webUrl')
                    file_id = response.json().get('id')
                    new_file_name = response.json().get('name')
                    if file_url and file_id and new_file_name:
                        logger.info('File uploaded successfully.')
                        return True, new_file_name, file_url, file_id
                    else:
                        logger.error('Response JSON did not contain expected keys.')
                        return False, 'Response JSON did not contain expected keys.', '', ''
                except ValueError as e:
                    logger.error(f'Error parsing response JSON: {e}')
                    return False, 'Error parsing response JSON.', '', ''
            else:
                logger.error(f'Failed to upload file to SharePoint with error {response.status_code}: {response.text}')
                return False, (f'Failed to upload file to SharePoint with error {response.status_code}: '
                               f'{response.text}'), '', ''
    except Exception as e:
        logger.error(f'Failed to upload file to SharePoint. Error details: {e}')
        return False, 'Failed to upload file to SharePoint.', '', ''


def upload_file_1(source_path, access_token, site_id, drive_id, sp_path, logger, file_name):
    logger.info('upload_file function called.')

    with open(source_path, 'rb') as file:
        if file_name is None or file_name == '':
            file_name = os.path.basename(source_path)
            logger.info(f'Uploading {file_name} file to the sharepoint.')
        content = file.read()

        try:
            response = requests.put(
                f'https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{sp_path}/{file_name}'
                f':/content',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/octet-stream'
                }, data=content)

            if response.status_code in [200, 201]:
                file_url = response.json()['webUrl']
                file_id = response.json()['id']
                logger.info('File uploaded successfully.')
                return True, file_name, file_url, file_id
            else:
                logger.error(f'Failed to upload file to sharepoint with error {response.status_code}')
                return False, f'Failed to upload file to sharepoint with error {response.status_code}', None
        except Exception as e:
            logger.error(f'Failed to upload file to sharepoint. Error details: {e}')
            return False, f'Failed to upload file to sharepoint.', None


def upload_sharepoint(source_path, process_name, target_application, conn, logger, rpa_id='', sub_folder_path=None):
    logger.info('upload_sharepoint function called.')

    path_type = check_path_type(source_path, logger)

    # db_cursor = conn.cursor()
    sp_details = None

    with conn.cursor() as db_cursor:
        try:
            sp_details = get_sharepoint_details(db_cursor, logger)
            logger.info('Received sharepoint details')
        except Exception as e:
            logger.error(f'Failed to get sharepoint details. Error details: {e}')

        if sp_details:
            access_token = get_access_token(sp_details, logger)
        else:
            return False, '', '', ''

        site_id = sp_details['SITE_ID']
        drive_id = sp_details['DRIVE_ID']
        sp_path = get_sharepoint_path(process_name, target_application, db_cursor, logger)
        # print(f"sp_path: {sp_path}")
        sp_path += f"/{sub_folder_path}" if sub_folder_path else ''
        if str(rpa_id).strip():
            sp_path += f'/RPA-{rpa_id}'
        # print(f'sp_path: {sp_path}')

    if path_type.lower() == 'file':
        logger.info('Uploading file to the sharepoint.')
        status, file_name, file_url, file_id = upload_file(source_path, access_token, site_id, drive_id, sp_path,
                                                           logger)
        return status, file_url, file_id, file_name

    elif path_type.lower() == 'directory':
        logger.info('uploading folder to the sharepoint.')
        all_file_paths = []
        all_file_ids = []
        status = False
        try:
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    status, file_name, resp, file_id = upload_file(file_path, access_token, site_id, drive_id, sp_path,
                                                                   logger)
                    all_file_paths.append(resp)
                    all_file_ids.append(file_id)
        except Exception as e:
            return False, f'Failed to upload files to sharepoint. Error details: {e}', '', ''
        return status, all_file_paths, all_file_ids, ''
    else:
        return False, '', '', ''


def download_sharepoint(queue_data, access_token, site_id, drive_id, sh_path, loc_path, sh_move_path, process_name,
                        target_application, cursor, logger):
    folder_id = get_folder_id(access_token, drive_id, sh_path, logger)
    logger.info(f'folder id of{sh_path} is {folder_id}')

    move_folder_id = get_folder_id(access_token, drive_id, sh_move_path, logger)
    logger.info(f'move folder path {sh_move_path} and that folder id {move_folder_id}')

    folder_childers_api_url = ('https://graph.microsoft.com/v1.0/drives/' + drive_id + '/items/'
                               + folder_id + '/children')
    headers = {
        'Authorization': 'Bearer ' + access_token,
        # 'Accept': 'application/json;odata=verbose',
    }
    logger.info("trying to get the sharepoint folder child items")
    response = requests.get(folder_childers_api_url, headers=headers)
    if response.status_code == 200:
        logger.info("successfully get the child items")

        folder_child = response.json()['value']

        for child in folder_child:

            child_id = child['id']
            child_name = child['name']
            logger.info(f'child name :{child_name}')

            logger.info(f'checking the child item type [file or folder]')
            if get_item_type(child_id, drive_id, access_token, logger) == 'file':
                filepath = download_sh_file(access_token, drive_id, child_id, child_name, loc_path, logger)

                # url = move_sh_file(access_token, drive_id, child_id, move_folder_id, child_name, logger)
                file_name, extension = os.path.splitext(child_name)
                file_type = get_file_type(extension, logger)

                sender_email_address = child['createdBy']['user']['email']
                sender_name = child['createdBy']['user']['displayName']

                date_srt = child['fileSystemInfo']['createdDateTime']
                print(f'date string in sharepoint  {date_srt}')
                parsed_date = datetime.strptime(date_srt, '%Y-%m-%dT%H:%M:%SZ')
                # date_string = parsed_date.strftime('%Y-%m-%d %H:%M:%S')DD-MM-YYYY
                print(f'parsed date {parsed_date}')

                # date_string = parsed_date.strftime('%d-%m-%Y')
                date_string = parsed_date.strftime('%d-%m-%Y %H:%M:%S')
                print(f'final date string {date_string}')
                output_dict = {
                    "PROCESS_NAME": f"{process_name}",
                    "FILE_NAME": f"{child_name}",
                    "FILE_SOURCE_PATH": f"{sh_path}",
                    "FILE_LOCAL_PATH": f"{filepath}",
                    "FILE_SOURCE": "sharepoint",
                    "STATUS": "New",
                    "REQUESTED_DATE": f"{date_string}",
                    "REQUESTED_BY": f"{sender_email_address}",
                    "REQUESTER_NAME": f"{sender_name}",
                    "FILE_TYPE": f"{file_type}",
                    "TARGET_APPLICATION": f"{target_application}"
                }

                queue_data.append(output_dict)
                # uq.update_to_queue(data, cursor, logger)

            if get_item_type(child_id, drive_id, access_token, logger) == 'folder':
                create_folder(loc_path, child_name, logger)
                create_sh_folder(access_token, site_id, drive_id, move_folder_id, child_name, logger)
                sh_child_path = sh_path + '/' + child_name
                mov_child_path = sh_move_path + '/' + child_name
                loc_child_path = loc_path + '\\' + child_name

                download_sharepoint(queue_data, access_token, site_id, drive_id, sh_child_path, loc_child_path,
                                    mov_child_path,
                                    process_name, target_application, cursor, logger)

    return queue_data


def move_sharepoint(access_token, site_id, drive_id, inti_sh_path, move_sh_path, logger):
    init_folder_id = get_folder_id(access_token, drive_id, inti_sh_path, logger)
    move_foldr_id = get_folder_id(access_token, drive_id, move_sh_path, logger)

    folder_childers_api_url = ('https://graph.microsoft.com/v1.0/drives/' + drive_id + '/items/' + init_folder_id +
                               '/children')
    headers = {
        'Authorization': 'Bearer ' + access_token,
        # 'Accept': 'application/json;odata=verbose',
    }
    response = requests.get(folder_childers_api_url, headers=headers)
    if response.status_code == 200:
        folder_child = response.json()['value']

        for child in folder_child:

            child_id = child['id']
            child_name = child['name']

            if get_item_type(child_id, drive_id, access_token, logger) == 'file':
                move_sh_file(access_token, drive_id, child_id, move_foldr_id, child_name, logger)

            if get_item_type(child_id, drive_id, access_token, logger) == 'folder':
                create_sh_folder(access_token, site_id, drive_id, move_foldr_id, child_name, logger)
                sh_child_path = inti_sh_path + '/' + child_name
                mov_child_path = move_sh_path + '/' + child_name

                move_sharepoint(access_token, site_id, drive_id, sh_child_path, mov_child_path, logger)

    return response.status_code


def download_sharepoint_contents(data, conn, logger):
    cursor = conn.cursor()
    sh_details = get_sharepoint_details(cursor, logger)
    site_id = sh_details['SITE_ID']
    drive_id = sh_details['DRIVE_ID']
    client_id = sh_details['CLIENT_ID']
    client_secret = sh_details['CLIENT_SECRET']
    tenant_id = sh_details['TENANT_ID']
    scope = sh_details['SCOPE']
    access_token = get_access_token_1(client_id, client_secret, tenant_id, scope, logger)
    download_folder = '../DownloadedFiles'

    loc_path = os.path.abspath(download_folder)

    logger.info('Created folder in the local system.')
    sh_path = sh_details['INPUT_PATH']
    sh_move_path = sh_details['OUTPUT_PATH']
    # process_name = 'Supplier Invoice Creation'
    # target_application = 'Oracle EBS'
    process_name = data['process_name']
    target_application = data['target_application']
    queue_data = []
    list_queue = download_sharepoint(queue_data, access_token, site_id, drive_id, sh_path, loc_path, sh_move_path,
                                     process_name, target_application, cursor, logger)
    move_sharepoint(access_token, site_id, drive_id, sh_path, sh_move_path, logger)
    return list_queue


def custom_data_update(queue_data, conn, logger):
    try:
        logger.info('custom data update function called')
        cursor = conn.cursor()
        final_data = []
        print('=====================queue_data=======')
        print(queue_data)
        for row_data in queue_data:
            print(row_data)
            if 'custom' in row_data['FILE_NAME'].lower():
                print('inside loop')
                print(row_data)
                row_data['FILE_CLASSIFICATION'] = 'custom clearance'
            final_data.append(row_data)
        print('===============after loop=====')
        print(final_data)
        uq.update_to_queue(final_data, cursor, logger)
    except Exception as e:
        logger.error(f'Unable to update the queue data.the Error details is {str(e)}')


def sh_upload_file(local_path, path, file_name, conn, logger):
    cursor = conn.cursor()
    sh_details = get_sharepoint_details(cursor, logger)
    print(sh_details)
    site_id = sh_details['SITE_ID']
    drive_id = sh_details['DRIVE_ID']
    client_id = sh_details['CLIENT_ID']
    client_secret = sh_details['CLIENT_SECRET']
    tenant_id = sh_details['TENANT_ID']
    scope = sh_details['SCOPE']
    input_path = sh_details['INPUT_PATH']
    output_path = sh_details['OUTPUT_PATH']

    access_token = get_access_token_1(client_id, client_secret, tenant_id, scope, logger)
    parent_folder_path = output_path
    folders = path.split(',')

    for folder in folders:
        parent_folder_id = get_folder_id(access_token, drive_id, parent_folder_path, logger)
        print(parent_folder_id)
        res = create_sh_folder(access_token, site_id, drive_id, parent_folder_id, folder, logger)
        print(f'create_sh_folder {str(res)}')
        parent_folder_path = parent_folder_path + "/" + folder
        print(parent_folder_path)
    print(parent_folder_path)
    status, file_name, file_url, file_id = upload_file_1(local_path, access_token, site_id, drive_id,
                                                         parent_folder_path, logger, file_name)
    return status, file_name, file_url, file_id


def delete_sh_file(access_token, site_id, drive_id, file_id):
    delete_file_url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{file_id}'
    headers = {
        'Authorization': 'Bearer ' + access_token,
    }
    response = requests.delete(delete_file_url, headers=headers)
    return response.status_code


if __name__ == '__main__':
    ###########################################
    from dbConnection import DBConnection as db
    from loggerConfig import LoggerManager as lg
    ###########################################
    connection = db.connect_db('../configuration/config(internal demo).json')
    logger = lg.configure_logger('../logs/sharepoint')
    # file_path = ('https://nufarm.sharepoint.com/:x:/r/sites/msteams_4d77ce_623393/_layouts/15/Doc.aspx?sourcedoc'
    #              '=%7BFD952A5A-6E44-4425-BEFC-C33DE6F8C491%7D&file=RPA-106%20SIT_Interco.xlsb&action=default'
    #              '&mobileredirect=true')

    upload_status, url, f_id, f_name = upload_sharepoint(
        'C://Users/SatishKumarKolamudi/Downloads/PRA35.pdf',
        'Cash Receipts Management', 'Oracle EBS', connection, logger)
    print(f'upload_status: {upload_status}, url: {url}, f_id: {f_id}, f_name: {f_name}')

    # folder_url = get_sp_folder_path(file_path, 'RPA-106', logger)
    # print(f'folder_url: {folder_url}')

    if connection:
        db.close_db_connect(connection)

    lg.shutdown_logger(logger)
