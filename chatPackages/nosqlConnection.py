import time
from borneo import NoSQLHandleConfig, NoSQLHandle, TableRequest, TableLimits, GetRequest, PutRequest, QueryRequest, DeleteRequest
from borneo.iam import SignatureProvider
from borneo.operations import ListTablesRequest, GetTableRequest
from collections import OrderedDict
import json
import os

os.environ["NOSQL_LOGLEVEL"] = "OFF"


class NoSQLConnectionManager:
    @classmethod
    def get_nosql_conn(cls, compartment_id=None, profile_name="DEFAULT", tenant_id=None, user_id=None, fingerprint=None,
                       private_key_file=None, region=None, oci_config_file=None, nosql_db_details: dict=None):
        """Establishes a connection to the NoSQL database."""
        try:
            if nosql_db_details and private_key_file:
                tenant_id = nosql_db_details.get('tenancy')
                user_id = nosql_db_details.get('user')
                fingerprint = nosql_db_details.get('fingerprint')
                region = nosql_db_details.get('region')
                compartment_id = nosql_db_details.get('compartment_id')
                provider = SignatureProvider(tenant_id=tenant_id, user_id=user_id, fingerprint=fingerprint,
                                             private_key=private_key_file)
            elif oci_config_file and region:
                provider = SignatureProvider(config_file=oci_config_file, profile_name=profile_name)
            elif tenant_id and user_id and fingerprint and private_key_file and region and compartment_id:
                provider = SignatureProvider(tenant_id=tenant_id, user_id=user_id, fingerprint=fingerprint,
                                             private_key=private_key_file)
            else:
                raise Exception("Expected configurations not received.")

            config = NoSQLHandleConfig(region, provider)
            config.set_default_compartment(compartment_id)
            conn = NoSQLHandle(config)
            print("NoSQL connection established.")
            return conn
        except Exception as e:
            raise e

    @classmethod
    def close_nosql_conn(cls, nosql_handle):
        """Closes the NoSQL database connection."""
        if nosql_handle:
            nosql_handle.close()
            print("NoSQL Connection closed.")


class NoSQLTableManager:
    """"""

    @classmethod
    def _ordered_dict_to_dict(cls, obj):
        if isinstance(obj, OrderedDict):
            return {k: cls._ordered_dict_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._ordered_dict_to_dict(item) for item in obj]
        else:
            return obj

    @classmethod
    def get_next_sequence_id(cls, handle, sequence_name):
        get_req = GetRequest().set_table_name("SequenceTable").set_key({"name": sequence_name})
        result = handle.get(get_req)

        if result.get_value() is not None:
            current_value = result.get_value().get("value")
            new_value = current_value + 1

            # Update the sequence
            value = {"name": sequence_name, "value": new_value}
            put_req = PutRequest().set_table_name("SequenceTable").set_value(value)
            handle.put(put_req)

            return new_value
        else:
            # Initialize sequence
            value = {"name": sequence_name, "value": 1}
            put_req = PutRequest().set_table_name("SequenceTable").set_value(value)
            handle.put(put_req)

            return 1

    @classmethod
    def execute_select_query(cls, handle, select_query):
        try:
            request = QueryRequest().set_statement(select_query).set_max_read_kb(2048)
            # result = handle.query(request)
            # query_data = result.get_results()

            rows = []
            for row in handle.query_iterable(request):
                rows.append(cls._ordered_dict_to_dict(row))

            return rows
        except Exception as e:
            cust_exp = f"Error executing query '{select_query}' \n Error: {e}"
            raise cust_exp

    @classmethod
    def execute_insert_query(cls, handle, inserting_data, table_name):
        insertion_request = PutRequest().set_table_name(table_name).set_value(inserting_data)
        result = handle.put(insertion_request)

        if result.get_version():
            insert_flg = True
        else:
            insert_flg = False

        return insert_flg

    @classmethod
    def execute_update_query(cls, handle, updating_data, table_name):
        request = PutRequest().set_table_name(table_name).set_value(updating_data)#.set_update(True)
        result = handle.put(request)

        if result.get_version():
            update_flg = True
        else:
            update_flg = False

        return update_flg

    @classmethod
    def execute_delete_query(cls, handle, delete_data, table_name):
        delete_request = DeleteRequest().set_table_name(table_name).set_key(delete_data)
        delete_result = handle.delete(delete_request)

        if delete_result.get_success():
            delete_flag = True
        else:
            delete_flag = False
            print("Record not found or already deleted.")

        return delete_flag


class NoSQLSchemaManager:
    """"""
    @classmethod
    def drop_table(cls, handle, table_name):
        """Drops a table from the NoSQL database with enhanced retry mechanism for rate-limiting errors."""
        try:
            drop_statement = f"DROP TABLE {table_name}"
            request = TableRequest().set_statement(drop_statement)

            print(f"Dropping table: {table_name}")

            retries = 10  # Maximum number of retries
            backoff = 2  # Initial backoff in seconds

            for attempt in range(retries):
                try:
                    result = handle.do_table_request(request, timeout_ms=30000, poll_interval_ms=1000)
                    print(f"Table '{table_name}' dropped successfully. Status: {result.get_state()}")
                    return
                except Exception as e:
                    if "rate limit" in str(e).lower() and attempt < retries - 1:
                        print(
                            f"Rate limit exceeded. Retrying in {backoff} seconds... (Attempt {attempt + 1}/{retries})"
                        )
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 60)  # Exponential backoff, max 60s
                    else:
                        raise e
            cust_exception = f"Failed to drop table '{table_name}' after {retries} attempts due to repeated rate-limiting."
            raise Exception(cust_exception)

        except Exception as e:
            print(f"Error dropping table '{table_name}': {e}")

    @classmethod
    def create_table(cls, handle, create_table_statement, table_name, read_units=50, write_units=50, storage_gb=1):
        """Creates a table in the NoSQL database with enhanced retry mechanism for rate-limiting errors."""
        try:
            request = TableRequest().set_statement(create_table_statement)
            request.set_table_limits(TableLimits(read_units, write_units, storage_gb))
            print(f"Creating table: {table_name}")

            retries = 10  # Increased retries
            backoff = 2  # Initial backoff in seconds
            for attempt in range(retries):
                try:
                    handle.do_table_request(request, timeout_ms=30000, poll_interval_ms=1000)
                    break  # Exit loop if successful
                except Exception as e:
                    if "rate limit" in str(e).lower() and attempt < retries - 1:
                        print(f"Rate limit exceeded. Retrying in {backoff} seconds... (Attempt {attempt + 1}/{retries})")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 60)  # Exponential backoff capped at 60 seconds
                    else:
                        raise e

            # Wait until the table becomes active
            get_req = GetTableRequest().set_table_name(table_name)
            for _ in range(30):  # Retry up to 30 times (~60s)
                result = handle.get_table(get_req)
                state = result.get_state()
                print(f"Table state: {state}")
                if state == "ACTIVE":
                    print(f"Table {table_name} is ready.")
                    return
                time.sleep(2)

            cust_exception = f"Timeout waiting for table {table_name} to become ACTIVE."
            raise Exception(cust_exception)
        except Exception as e:
            print(f"Error in CREATE TABLE statement: {create_table_statement}")
            cust_exception = f"Error creating table: {e}"
            raise Exception(cust_exception)

    @classmethod
    def execute_alter_query(cls, handle, alter_statement):
        try:
            request = TableRequest().set_statement(alter_statement)
            result = handle.do_table_request(request, 5000, 100)
            return True
        except Exception as e:
            print(f"Error altering table: {e}")
            return False

    @classmethod
    def create_index(cls, handle, create_index_statement):
        try:
            request = TableRequest().set_statement(create_index_statement)
            result = handle.do_table_request(request, timeout_ms=40000, poll_interval_ms=1000)
            # print(f"result: {result}")
            if result.get_state():
                print(f"Index created successfully.")
            else:
                print(f"Index creation did not reach ACTIVE state. Final state: {result.get_state()}")
        except Exception as e:
            print(f"Failed to create index. Error: {e}")

    @classmethod
    def get_all_tables(cls, handle):
        """Retrieves all table names from the NoSQL database."""
        try:
            request = ListTablesRequest()
            tables = handle.list_tables(request).get_tables()
            return tables
        except Exception as e:
            print(f"Failed to list tables: {e}")
            return []

    @classmethod
    def _extract_indexes_from_ddl(cls, ddl):
        """Extracts index definitions from a table's DDL."""
        lines = ddl.split(";")
        indexes = [line.strip() for line in lines if "CREATE INDEX" in line.upper()]
        return indexes

    @classmethod
    def get_all_db_objects(cls, handle):
        """Retrieves all database objects (tables, indexes, etc.) from the NoSQL database."""
        try:
            request = ListTablesRequest()
            table_names = handle.list_tables(request).get_tables()

            all_objects = []
            for table_name in table_names:
                get_request = GetTableRequest().set_table_name(table_name)
                table_result = handle.get_table(get_request)

                table_obj = {
                    "object_type": "TABLE",
                    "object_name": table_result.get_table_name(),
                    "state": table_result.get_state(),
                    "schema": table_result.get_ddl(),
                    "indexes": cls._extract_indexes_from_ddl(table_result.get_ddl()),
                    "limits": {
                        "read_units": table_result.get_table_limits().get_read_units(),
                        "write_units": table_result.get_table_limits().get_write_units(),
                        "storage_gb": table_result.get_table_limits().get_storage_gb()
                    },
                    "compartment": table_result.get_compartment_id()
                }
                all_objects.append(table_obj)

            return json.dumps(all_objects, indent=2)
        except Exception as e:
            print(f"Error retrieving database objects: {e}")
            return json.dumps([], indent=2)


if __name__ == '__main__':
    l_config = "../configuration/config.json"
    with open(l_config, 'rb') as config_data:
        config_data = json.load(config_data)

    if config_data['WAI_NoSQL'] and str(config_data['WAI_NoSQL']['DatabaseType']).lower() == 'nosql':
        oci_config_data = config_data['WAI_NoSQL']
    else:
        oci_config_data = None
    # print(f"oci_config_data: {oci_config_data}")
    l_handler = NoSQLConnectionManager.get_nosql_conn(
        nosql_db_details=oci_config_data,
        private_key_file='../../certs/oci_private.pem'
    )

    # l_tables = NoSQLTableManager.get_all_tables(l_handler)
    print(l_handler)

    # r_all_objects = NoSQLSchemaManager.get_all_db_objects(l_handler)
    # r_rows = NoSQLTableManager.execute_select_query(
    #     l_handler, """SELECT
    #             *
    #         FROM WAIAgentPromptsConfig
    #         WHERE product_name = 'Oracle'"""
    # )
    # for row in r_rows:
    #     row['customer'] = 'WELFULL'
    #     print(NoSQLTableManager.execute_update_query(l_handler, row, 'WAIAgentPromptsConfig'))


    # l_create_index_statement = """
    # CREATE INDEX idx_prompt_config_customer ON WAIAgentPromptsConfig(customer)
    # """
    # NoSQLSchemaManager.create_index(l_handler, l_create_index_statement)

    # print(NoSQLTableManager.get_next_sequence_id(l_handler, "SupportContentIdSeq"))
    # NoSQLSchemaManager.drop_table(l_handler, 'ChatFeedback')

    # all_contents_query = f"""
    # SELECT count(1) as count FROM ChatSessions WHERE issue_id = 'AEI-1810'
    # """
    # contents = NoSQLTableManager.execute_select_query(l_handler, all_contents_query)
    # print(f"Query for contents: \n{all_contents_query}")
    # print(f"all_contents: {contents}")

    # for each in contents:
    #     each['customer'] = 'AEI'
    #     print(f"each: {each}")
    #     r_update_flg = NoSQLTableManager.execute_update_query(l_handler, each, 'WAIAgentPromptsConfig')
    #     print(f"r_update_flg: {r_update_flg}")
        # break

    print(NoSQLSchemaManager.execute_alter_query(l_handler, "ALTER TABLE TicketSummary (ADD product_name STRING)"))

    NoSQLConnectionManager.close_nosql_conn(l_handler)
