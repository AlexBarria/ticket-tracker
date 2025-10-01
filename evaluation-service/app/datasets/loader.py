import json
import os
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime


class TestDataLoader:
    """Loader for test query datasets"""

    def __init__(self):
        self.datasets_dir = Path(__file__).parent

    def load_test_queries(self, filename: str = "test_queries.json") -> List[Dict[str, Any]]:
        """Load test queries from JSON file"""
        file_path = self.datasets_dir / filename

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                queries = json.load(f)
            return queries
        except FileNotFoundError:
            raise FileNotFoundError(f"Test queries file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in test queries file: {e}")

    def get_query_by_id(self, query_id: str, filename: str = "test_queries.json") -> Dict[str, Any]:
        """Get a specific query by ID"""
        queries = self.load_test_queries(filename)
        for query in queries:
            if query.get("query_id") == query_id:
                return query
        raise ValueError(f"Query with ID {query_id} not found")

    def get_sample_queries(self, count: int = 5, filename: str = "test_queries.json") -> List[Dict[str, Any]]:
        """Get a sample of queries for testing"""
        queries = self.load_test_queries(filename)
        return queries[:count] if len(queries) >= count else queries

    def validate_query_format(self, query: Dict[str, Any]) -> bool:
        """Validate that a query has the required fields"""
        required_fields = ["query_id", "question", "reference_answer"]
        return all(field in query for field in required_fields)

    def save_realtime_query(self, query: Dict[str, Any], filename: str = "realtime_queries.json") -> None:
        """Save a real-time query to the realtime queries file"""
        file_path = self.datasets_dir / filename

        # Load existing queries or create empty list
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                queries = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            queries = []

        # Add new query with timestamp
        query_with_metadata = {
            **query,
            "added_at": datetime.now().isoformat(),
            "source": "realtime"
        }
        queries.append(query_with_metadata)

        # Save back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(queries, f, indent=2, ensure_ascii=False)

    def get_realtime_queries(self, filename: str = "realtime_queries.json") -> List[Dict[str, Any]]:
        """Get all real-time queries"""
        file_path = self.datasets_dir / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def load_agent1_test_tickets(self, filename: str = "agent1_test_tickets.json") -> List[Dict[str, Any]]:
        """Load Agent 1 test tickets from JSON file"""
        file_path = self.datasets_dir / filename

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tickets = json.load(f)
            return tickets
        except FileNotFoundError:
            raise FileNotFoundError(f"Agent 1 test tickets file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Agent 1 test tickets file: {e}")

    def get_agent1_sample_tickets(self, count: int = 3, filename: str = "agent1_test_tickets.json") -> List[Dict[str, Any]]:
        """Get a sample of Agent 1 test tickets"""
        tickets = self.load_agent1_test_tickets(filename)
        return tickets[:count] if len(tickets) >= count else tickets