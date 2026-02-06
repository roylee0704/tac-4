import json
import pandas as pd
import sqlite3
import io
import re
from typing import Dict, Any, List, Set
from .sql_security import (
    execute_query_safely,
    validate_identifier,
    SQLSecurityError
)
from .constants import NESTED_FIELD_DELIMITER, ARRAY_INDEX_DELIMITER

def flatten_dict(data: Any, parent_key: str = '', sep: str = NESTED_FIELD_DELIMITER) -> Dict[str, Any]:
    """
    Recursively flatten a nested dictionary structure into a flat dictionary.

    This function handles nested objects, arrays, and mixed data types by converting
    them into a single-level dictionary with compound keys using delimiters.

    Args:
        data: The data structure to flatten (dict, list, or primitive)
        parent_key: The key prefix for nested structures (used in recursion)
        sep: The delimiter to use for nested keys (default: NESTED_FIELD_DELIMITER)

    Returns:
        A flat dictionary with all nested structures converted to compound keys

    Examples:
        >>> flatten_dict({'a': {'b': 1, 'c': 2}})
        {'a__b': 1, 'a__c': 2}

        >>> flatten_dict({'items': [{'id': 1}, {'id': 2}]})
        {'items_0__id': 1, 'items_1__id': 2}

        >>> flatten_dict({'user': {'tags': ['admin', 'user']}})
        {'user__tags_0': 'admin', 'user__tags_1': 'user'}
    """
    items = []

    if isinstance(data, dict):
        # Handle dictionary: recursively flatten each key-value pair
        for key, value in data.items():
            # Create compound key with parent prefix
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            # Recursively flatten the value
            items.extend(flatten_dict(value, new_key, sep=sep).items())

    elif isinstance(data, list):
        # Handle list: convert to indexed keys and flatten each element
        for i, item in enumerate(data):
            # Use array index delimiter for list indices
            new_key = f"{parent_key}{ARRAY_INDEX_DELIMITER}{i}" if parent_key else str(i)
            # Recursively flatten each list element
            items.extend(flatten_dict(item, new_key, sep=sep).items())

    elif data is None:
        # Handle None values explicitly
        items.append((parent_key, None))

    else:
        # Handle primitive types (str, int, float, bool)
        # Convert all primitives to strings for consistency in database storage
        items.append((parent_key, str(data) if not isinstance(data, (str, type(None))) else data))

    return dict(items)


def sanitize_table_name(table_name: str) -> str:
    """
    Sanitize table name for SQLite by removing/replacing bad characters
    and validating against SQL injection
    """
    # Remove file extension if present
    if '.' in table_name:
        table_name = table_name.rsplit('.', 1)[0]

    # Replace bad characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)

    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized

    # Ensure it's not empty
    if not sanitized:
        sanitized = 'table'

    # Validate the sanitized name
    try:
        validate_identifier(sanitized, "table")
    except SQLSecurityError:
        # If validation fails, use a safe default
        sanitized = f"table_{hash(table_name) % 100000}"

    return sanitized

def convert_csv_to_sqlite(csv_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert CSV file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Read CSV into pandas DataFrame
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting CSV to SQLite: {str(e)}")

def convert_json_to_sqlite(json_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSON file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Parse JSON
        data = json.loads(json_content.decode('utf-8'))
        
        # Ensure it's a list of objects
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")
        
        if not data:
            raise ValueError("JSON array is empty")
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data)
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting JSON to SQLite: {str(e)}")


def detect_all_jsonl_fields(jsonl_content: bytes) -> List[str]:
    """
    Detect all unique field names across all records in a JSONL file.

    This function scans the entire JSONL file to collect all possible field names
    after flattening nested structures. This ensures consistent schema even when
    records have different field sets.

    Args:
        jsonl_content: The raw bytes content of the JSONL file

    Returns:
        A sorted list of all unique field names found across all records

    Raises:
        ValueError: If the file is empty or contains no valid JSON lines
    """
    fields: Set[str] = set()
    content_str = jsonl_content.decode('utf-8')
    lines = content_str.strip().split('\n')

    valid_lines = 0
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            # Skip empty lines
            continue

        try:
            # Parse JSON line
            record = json.loads(line)
            # Flatten the record and collect all field names
            flattened = flatten_dict(record)
            fields.update(flattened.keys())
            valid_lines += 1
        except json.JSONDecodeError as e:
            # Log malformed lines but continue processing
            print(f"Warning: Malformed JSON on line {line_num}: {str(e)}")
            continue

    if valid_lines == 0:
        raise ValueError("JSONL file contains no valid JSON records")

    # Return sorted list for consistent column ordering
    return sorted(fields)


def convert_jsonl_to_sqlite(jsonl_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSONL file content to SQLite table.

    This function processes JSONL (JSON Lines) files by:
    1. Detecting all possible fields across all records
    2. Flattening nested structures using configured delimiters
    3. Creating a SQLite table with consistent schema
    4. Filling missing fields with None for records that don't have them

    Args:
        jsonl_content: The raw bytes content of the JSONL file
        table_name: The desired name for the SQLite table

    Returns:
        A dictionary containing:
        - table_name: The sanitized table name
        - schema: Dictionary mapping column names to data types
        - row_count: Number of rows inserted
        - sample_data: List of up to 5 sample records

    Raises:
        Exception: If parsing fails or database operations fail
    """
    try:
        # Sanitize table name for SQL safety
        table_name = sanitize_table_name(table_name)

        # First pass: detect all possible fields across all records
        all_fields = detect_all_jsonl_fields(jsonl_content)

        # Second pass: parse records and build data with consistent schema
        records = []
        content_str = jsonl_content.decode('utf-8')
        lines = content_str.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                # Parse and flatten each record
                record = json.loads(line)
                flattened = flatten_dict(record)

                # Create a record with all fields, filling missing ones with None
                complete_record = {field: flattened.get(field) for field in all_fields}
                records.append(complete_record)

            except json.JSONDecodeError:
                # Skip malformed lines (already logged in detect phase)
                continue

        if not records:
            raise ValueError("No valid records found in JSONL file")

        # Convert to pandas DataFrame
        df = pd.DataFrame(records)

        # Clean column names following existing pattern
        df.columns = [
            col.lower().replace(' ', '_').replace('-', '_')
            for col in df.columns
        ]

        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")

        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()

        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type

        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]

        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]

        conn.close()

        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }

    except Exception as e:
        raise Exception(f"Error converting JSONL to SQLite: {str(e)}")