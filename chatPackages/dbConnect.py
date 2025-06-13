import oracledb
import json
import concurrent.futures


class DBConnection:
    _connection_pools = {}

    @classmethod
    def connect_db(cls, pool_name, config_path=None, db_details=None, min_conn=5, max_conn=10, increment_conn=2):
        """
        Get a connection from the connection pool. If the pool does not exist, initialize it.
        :param min_conn: Minimum connections keep ready for next time acquiring the connection (optional).
        :param max_conn: Maximum connections can connection pool to handle (optional).
        :param increment_conn: Connections increment for next execution (optional).
        :param config_path: Path to the database configuration JSON file (optional).
        :param db_details: Dictionary with DB connection details (optional).
        :param pool_name: Unique identifier for the connection pool.
        :return: Database connection object.
        """
        if not pool_name:
            raise Exception("pool_name is required to identify the connection pool.")

        # Initialize pool if it doesn't exist
        if pool_name not in cls._connection_pools:
            cls.initialize_pool(config_path, pool_name, db_details=db_details, min_conn=min_conn, max_conn=max_conn, increment_conn=increment_conn)

        try:
            return cls.get_connection(pool_name)
        except Exception as e:
            raise Exception(f"Oracle Connection Failed: {str(e)}")

    @classmethod
    def close_connection(cls, conn, pool_name):
        """
        Release a connection back to the correct pool.
        """
        try:
            if conn:
                if pool_name in cls._connection_pools:
                    cls.release_connection(conn, pool_name)
                else:
                    raise Exception(f"Connection pool '{pool_name}' is not initialized.")
            else:
                raise Exception("Connection is not established.")
        except oracledb.DatabaseError as e:
            raise Exception(f"Error closing connection: {str(e)}")

    @classmethod
    def initialize_pool(cls, config_path, pool_name, db_details=None, min_conn=2, max_conn=10, increment_conn=1):
        """
        Initialize a new connection pool and store it in the dictionary.
        """
        if pool_name in cls._connection_pools:
            return  # Pool already initialized

        if not db_details:
            try:
                with open(config_path, 'r') as config:
                    db_details = json.load(config)
            except Exception as e:
                raise Exception(f"Failed to read config file: {str(e)}")

        try:
            database_username = db_details["User"]
            database_password = db_details["Password"]
        except KeyError as e:
            raise Exception(f"Missing DB credentials: {str(e)}")

        try:
            dsn = db_details.get("dsn")  # Use pre-built DSN if available
            if not dsn:
                database_port = db_details["Port"]
                database_host_name = db_details["HostName"]
                database_service_name = db_details["ServiceName"]
                dsn = f"{database_host_name}:{database_port}/{database_service_name}"

            # Enable Thin Mode for better cloud support
            oracledb.init_oracle_client()

            cls._connection_pools[pool_name] = oracledb.SessionPool(
                user=database_username,
                password=database_password,
                dsn=dsn,
                min=min_conn,
                max=max_conn,
                increment=increment_conn,
                threaded=True,
                timeout=600
            )
            print(f"Connection pool '{pool_name}' established.")
        except Exception as e:
            raise Exception(f"Oracle Connection Failed: {str(e)}")

    @classmethod
    def get_connection(cls, pool_name):
        """
        Acquire a connection from the specified pool.
        """
        if pool_name not in cls._connection_pools:
            raise Exception(f"Connection pool '{pool_name}' is not initialized.")

        try:
            conn = cls._connection_pools[pool_name].acquire()
            print(f"Connection acquired from pool '{pool_name}'.")
            return conn
        except oracledb.Error as e:
            raise Exception(f"Failed to acquire connection from pool '{pool_name}': {str(e)}")

    @classmethod
    def release_connection(cls, conn, pool_name):
        """
        Release the connection back to the specific pool.
        """
        if pool_name not in cls._connection_pools:
            raise Exception(f"Connection pool '{pool_name}' is not initialized.")

        try:
            cls._connection_pools[pool_name].release(conn)
            print(f"Connection released back to pool '{pool_name}'.")
        except oracledb.Error as e:
            raise Exception(f"Failed to release connection to pool '{pool_name}': {str(e)}")

    @classmethod
    def close_pool(cls, pool_name):
        """
        Close a specific connection pool.
        """
        if pool_name in cls._connection_pools:
            try:
                cls._connection_pools[pool_name].close()
                del cls._connection_pools[pool_name]
                print(f"Connection pool '{pool_name}' closed.")
            except oracledb.Error as e:
                raise Exception(f"Failed to close connection pool '{pool_name}': {str(e)}")
        else:
            raise Exception(f"Connection pool '{pool_name}' does not exist or is already closed.")

    @classmethod
    def close_all_pools(cls):
        """
        Close all active connection pools concurrently.
        """
        pool_names = list(cls._connection_pools.keys())
        def close_pool_safely(pool_name):
            try:
                cls.close_pool(pool_name)
            except Exception as e:
                print(f"Failed to close pool '{pool_name}': {str(e)}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(close_pool_safely, pool_names)


if __name__ == '__main__':
    try:
        # Pool 1
        connection1 = DBConnection.connect_db(config_path='../configuration/oci_db_config.json',
                                              pool_name='pool1')
        print(f'Connection1: {connection1}')
        DBConnection.close_connection(connection1, 'pool1')

        # Pool 2 with different details
        db_details_2 ={
            "HostName": "waiagents01.winfosolutions.com",
            "Port": "1521",
            "ServiceName": "wai_pdb1.winfosolutions.com",
            "User": "WAI",
            "Password": "WElcome_123#",
            "DatabaseType": "SQL"
        }
        connection2 = DBConnection.connect_db(db_details=db_details_2, pool_name='pool2')
        print(f'Connection2: {connection2}')
        DBConnection.close_connection(connection2, 'pool2')

        # Closing all pools
        DBConnection.close_all_pools()

    except Exception as err:
        print(f"Error: {err}")
