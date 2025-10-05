from sqlalchemy import create_engine, text

_GET_TABLES_SCHEMA_QUERY = """
SELECT 
    t.table_schema as table_schema, 
	t.table_name as table_name, 
	obj_description((t.table_schema || '.' || quote_ident(t.table_name))::regclass, 'pg_class') AS table_comment
FROM information_schema.tables t
WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema') AND t.table_type = 'VIEW'
ORDER BY t.table_schema, t.table_name;
"""

_GET_COLUMNS_SCHEMA_QUERY = """
SELECT
    c.column_name as column_name,
    c.data_type as column_type,
    pg_catalog.col_description((c.table_schema || '.' || c.table_name)::regclass, c.ordinal_position) AS column_comment
FROM information_schema.columns AS c
WHERE c.table_schema = '{table_schema}' AND c.table_name = '{table_name}'
ORDER BY c.ordinal_position;
"""


class DBRepository:
    """
    Database repository for interacting with PostgreSQL database.

    Attributes:
        engine (Engine): SQLAlchemy engine for database connection.
    """

    def __init__(self, db_connection_string: str):
        """
        Initializes the DBRepository with a database connection string.
        """
        self.engine = create_engine(db_connection_string)

    def get_tables_schema(self) -> list[dict]:
        """
        Retrieves the schema, name and description of all tables in the database.

        Returns:
            list: A list of dictionaries containing table details.
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(_GET_TABLES_SCHEMA_QUERY))
            tables = []
            for row in result:
                tables.append({
                    "table_schema": row.table_schema,
                    "table_name": row.table_name,
                    "table_comment": row.table_comment
                })
            return tables

    def get_columns_schema(self, table_schema: str, table_name: str) -> list[dict]:
        """
        Retrieves the columns, their types and descriptions for a given table.

        Args:
            table_schema (str): The schema of the table.
            table_name (str): The name of the table.
        Returns:
            list: A list of dictionaries containing column details.
        """
        query = _GET_COLUMNS_SCHEMA_QUERY.format(table_schema=table_schema, table_name=table_name)
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            columns = []
            for row in result:
                columns.append({
                    "column_name": row.column_name,
                    "column_type": row.column_type,
                    "column_comment": row.column_comment
                })
            return columns

    def execute_query(self, sql_query: str) -> list[dict]:
        """
        Executes a given SQL query and returns the results.

        Args:
            sql_query (str): The SQL query to be executed.
        Returns:
            list: A list of dictionaries representing the query results.
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = []
            for row in result.mappings():
                rows.append({k: v for k, v in row.items()})
            return rows
