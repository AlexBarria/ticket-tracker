import json
import os
from urllib.request import Request, urlopen

from openai import OpenAI
from repository import DBRepository
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_SYSTEM_PROMPT = """
You are an expert SQL system. Your ONLY job is to read a requirement and output an SQL query to execute over a DB to get the required data.
The SQL query must exactly match the table schema below.
Do not add, remove, or rename columns.
Do not include comments or any text before/after the query.

### IMPORTANT SQL GUIDELINES
- For text matching, ALWAYS use ILIKE for case-insensitive pattern matching instead of exact equality (=)
- Use % wildcards for partial matches (e.g., WHERE column ILIKE '%searchterm%')
- Never use exact equality (=) for text fields unless specifically required
- ILIKE works for PostgreSQL case-insensitive matching

### TABLE SCHEMA
{schema}

### RETURN FORMAT
Return ONLY the plain SQL query ready to be executed, DO NOT ADD markdown or code snippets decorators.
"""

_USER_PROMPT = """
Return an SQL query to get the following required data from the DB.:
--- UNTRUSTED CONTEXT START
{raw_text}
--- UNTRUSTED CONTEXT END
"""


class SQLRagAgent:
    """
    An agent that uses a language model to convert natural language queries into SQL queries,
    executes them against a database, and returns the results.

    Attributes:
        client (OpenAI): The OpenAI client for interacting with the language model.
        repository (DBRepository): The database repository for executing SQL queries.
        schema (str): The database schema information used to inform the language model.
    """

    def __init__(self, repository: DBRepository):
        """
        Initializes the SQLRagAgent with a database repository and processes the schema.

        Args:
            repository (DBRepository): The database repository for executing SQL queries.
        """
        # Initialize the OpenAI client
        # It will automatically read the OPENAI_API_KEY from the environment
        logger.info("Initializing SQLRagAgent")
        self.client = OpenAI()
        self.repository = repository
        self.schema = ""
        self._process_schema()
        logger.info("SQLRagAgent initialized with processed schema.")

    def query(self, question: str) -> tuple[list[dict], int]:
        """
        Processes a natural language question, generates an SQL query, executes it, and returns the results.

        Args:
            question (str): The natural language question to be answered.
        Returns:
            tuple[list[dict], int]: The results of the executed SQL query and token count.
        Raises:
            Exception: If there is an error in generating or executing the SQL query.
        """
        try:
            logger.info(f"Processing question: {question}")
            sql_query, tokens = self._get_sql_query(question)
            logger.info(f"Generated SQL Query: {sql_query} (used {tokens} tokens)")
            if os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true":
                self._validate(sql_query)
            results = self.repository.execute_query(sql_query)
            logger.info(f"Query executed successfully, results: {results}")
            return results, tokens
        except Exception as e:
            logger.error(f"An error occurred while processing the query: {e}")
            raise

    def _process_schema(self):
        self.schema = ""
        tables = self.repository.get_tables_schema()
        for table in tables:
            self.schema += f"Table: {table['table_schema']}.{table['table_name']}\n"
            self.schema += f"Description: {table['table_comment']}.\n"
            self.schema += "Columns:\n"
            columns = self.repository.get_columns_schema(table['table_schema'], table['table_name'])
            for column in columns:
                self.schema += f"  {column['column_name']} ({column['column_type']}): {column['column_comment']}.\n"
            self.schema += "\n\n"
        logger.info(f"Processed schema: {self.schema}")

    def _get_sql_query(self, raw_text: str) -> tuple[str, int]:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT.format(schema=self.schema)},
                {"role": "user", "content": _USER_PROMPT.format(raw_text=raw_text)}
            ]
        )
        sql_query = response.choices[0].message.content

        # Get token count
        token_count = response.usage.total_tokens if response.usage else 0

        # Strip markdown code fences if present
        sql_query = sql_query.strip()
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]  # Remove ```sql
        elif sql_query.startswith("```"):
            sql_query = sql_query[3:]  # Remove ```
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]  # Remove trailing ```

        return sql_query.strip(), token_count

    @staticmethod
    def _validate(sql_query: str):
        guardrails_url = os.getenv("GUARDRAILS_URL", "http://guardrails:8000/validate")
        payload = {
            "guard": "sql",
            "prompt": sql_query
        }
        logger.info(f"Validating SQL query with Guardrails, url {guardrails_url}")
        req = Request(guardrails_url, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=20) as response:
            if response.status != 200:
                response_text = response.read().decode("utf-8")
                logger.error(f"Guardrails validation failed: {response_text}")
                raise Exception(f"Guardrails validation failed: {response.text}")
