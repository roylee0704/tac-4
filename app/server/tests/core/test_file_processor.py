import pytest
import json
import pandas as pd
import sqlite3
import os
import io
from pathlib import Path
from unittest.mock import patch
from core.file_processor import (
    convert_csv_to_sqlite,
    convert_json_to_sqlite,
    convert_jsonl_to_sqlite,
    flatten_dict,
    detect_all_jsonl_fields
)


@pytest.fixture
def test_db():
    """Create an in-memory test database"""
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    
    # Patch the database connection to use our in-memory database
    with patch('core.file_processor.sqlite3.connect') as mock_connect:
        mock_connect.return_value = conn
        yield conn
    
    conn.close()


@pytest.fixture
def test_assets_dir():
    """Get the path to test assets directory"""
    return Path(__file__).parent.parent / "assets"


class TestFileProcessor:
    
    def test_convert_csv_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real CSV file
        csv_file = test_assets_dir / "test_users.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 4  # 4 users in test file
        assert len(result['sample_data']) <= 5  # Should return up to 5 samples
        
        # Verify schema has expected columns (cleaned names)
        assert 'name' in result['schema']
        assert 'age' in result['schema'] 
        assert 'city' in result['schema']
        assert 'email' in result['schema']
        
        # Verify sample data structure and content
        john_data = next((item for item in result['sample_data'] if item['name'] == 'John Doe'), None)
        assert john_data is not None
        assert john_data['age'] == 25
        assert john_data['city'] == 'New York'
        assert john_data['email'] == 'john@example.com'
    
    def test_convert_csv_to_sqlite_column_cleaning(self, test_db, test_assets_dir):
        # Test column name cleaning with real file
        csv_file = test_assets_dir / "column_names.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "test_users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify columns were cleaned in the schema
        assert 'full_name' in result['schema']
        assert 'birth_date' in result['schema']
        assert 'email_address' in result['schema']
        assert 'phone_number' in result['schema']
        
        # Verify sample data has cleaned column names and actual content
        sample = result['sample_data'][0]
        assert 'full_name' in sample
        assert 'birth_date' in sample
        assert 'email_address' in sample
        assert sample['full_name'] == 'John Doe'
        assert sample['birth_date'] == '1990-01-15'
    
    def test_convert_csv_to_sqlite_with_inconsistent_data(self, test_db, test_assets_dir):
        # Test with CSV that has inconsistent row lengths - should raise error
        csv_file = test_assets_dir / "invalid.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "inconsistent_table"
        
        # Pandas will fail on inconsistent CSV data
        with pytest.raises(Exception) as exc_info:
            convert_csv_to_sqlite(csv_data, table_name)
        
        assert "Error converting CSV to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real JSON file
        json_file = test_assets_dir / "test_products.json"
        with open(json_file, 'rb') as f:
            json_data = f.read()
        
        table_name = "products"
        result = convert_json_to_sqlite(json_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 3  # 3 products in test file
        assert len(result['sample_data']) == 3
        
        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'price' in result['schema']
        assert 'category' in result['schema']
        assert 'in_stock' in result['schema']
        
        # Verify sample data structure and content
        laptop_data = next((item for item in result['sample_data'] if item['name'] == 'Laptop'), None)
        assert laptop_data is not None
        assert laptop_data['price'] == 999.99
        assert laptop_data['category'] == 'Electronics'
        assert laptop_data['in_stock'] == True
    
    def test_convert_json_to_sqlite_invalid_json(self):
        # Test with invalid JSON
        json_data = b'invalid json'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "Error converting JSON to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_not_array(self):
        # Test with JSON that's not an array
        json_data = b'{"name": "John", "age": 25}'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "JSON must be an array of objects" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_empty_array(self):
        # Test with empty JSON array
        json_data = b'[]'
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)

        assert "JSON array is empty" in str(exc_info.value)

    # JSONL Tests
    def test_flatten_dict_simple(self):
        # Test simple nested object
        data = {'a': {'b': 1, 'c': 2}}
        result = flatten_dict(data)
        assert result == {'a__b': '1', 'a__c': '2'}

    def test_flatten_dict_deep_nesting(self):
        # Test deep nesting
        data = {'level1': {'level2': {'level3': {'level4': 'value'}}}}
        result = flatten_dict(data)
        assert result == {'level1__level2__level3__level4': 'value'}

    def test_flatten_dict_arrays(self):
        # Test arrays of primitives
        data = {'tags': ['admin', 'user', 'moderator']}
        result = flatten_dict(data)
        assert result == {'tags_0': 'admin', 'tags_1': 'user', 'tags_2': 'moderator'}

    def test_flatten_dict_nested_arrays(self):
        # Test nested objects in arrays
        data = {'items': [{'id': 1, 'name': 'Item1'}, {'id': 2, 'name': 'Item2'}]}
        result = flatten_dict(data)
        assert result == {
            'items_0__id': '1',
            'items_0__name': 'Item1',
            'items_1__id': '2',
            'items_1__name': 'Item2'
        }

    def test_flatten_dict_mixed_types(self):
        # Test mixed data types
        data = {
            'string': 'text',
            'number': 42,
            'boolean': True,
            'null': None,
            'nested': {'value': 123}
        }
        result = flatten_dict(data)
        assert result['string'] == 'text'
        assert result['number'] == '42'
        assert result['boolean'] == 'True'
        assert result['null'] is None
        assert result['nested__value'] == '123'

    def test_flatten_dict_empty_objects(self):
        # Test empty objects and arrays
        data = {'empty_obj': {}, 'empty_array': []}
        result = flatten_dict(data)
        # Empty structures produce no fields
        assert result == {}

    def test_convert_jsonl_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real JSONL file
        jsonl_file = test_assets_dir / "test_events.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "events"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result

        # Test the returned data
        assert result['row_count'] == 5  # 5 events in test file
        assert len(result['sample_data']) == 5

        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'event_type' in result['schema']
        assert 'timestamp' in result['schema']
        assert 'user_id' in result['schema']

        # Verify sample data structure
        login_event = next((item for item in result['sample_data'] if item['event_type'] == 'login'), None)
        assert login_event is not None
        assert login_event['id'] in ['1', '4', 1, 4]  # Two login events (may be string or int)

    def test_convert_jsonl_nested_objects(self, test_db, test_assets_dir):
        # Load JSONL with nested objects
        jsonl_file = test_assets_dir / "test_nested.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "nested_users"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify nested fields are flattened
        assert 'user__email' in result['schema']
        assert 'user__address__city' in result['schema']
        assert 'user__address__zip' in result['schema']
        assert 'preferences__theme' in result['schema']
        assert 'preferences__notifications' in result['schema']

        # Verify data
        assert result['row_count'] == 3
        john_data = next((item for item in result['sample_data'] if item['name'] == 'John Doe'), None)
        assert john_data is not None
        assert john_data['user__email'] == 'john@example.com'
        assert john_data['user__address__city'] == 'New York'

    def test_convert_jsonl_nested_arrays(self, test_db, test_assets_dir):
        # Load JSONL with nested arrays
        jsonl_file = test_assets_dir / "test_complex.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "orders"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify array elements are indexed
        assert 'items_0__id' in result['schema']
        assert 'items_0__name' in result['schema']
        assert 'items_0__price' in result['schema']
        assert 'items_0__specs__cpu' in result['schema']
        assert 'items_1__id' in result['schema']

        # Verify data
        assert result['row_count'] == 3
        alice_order = next((item for item in result['sample_data'] if item['customer'] == 'Alice'), None)
        assert alice_order is not None
        assert alice_order['items_0__name'] == 'Laptop'

    def test_convert_jsonl_inconsistent_fields(self, test_db, test_assets_dir):
        # Load JSONL with inconsistent fields
        jsonl_file = test_assets_dir / "test_inconsistent.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "inconsistent"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify all fields are detected
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'field_a' in result['schema']
        assert 'field_b' in result['schema']
        assert 'field_c' in result['schema']
        assert 'field_d' in result['schema']
        assert 'field_e_0' in result['schema']
        assert 'nested__deep__value' in result['schema']

        # Verify row count
        assert result['row_count'] == 5

    def test_convert_jsonl_empty_file(self):
        # Test with empty JSONL file
        jsonl_data = b''
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "Error converting JSONL to SQLite" in str(exc_info.value)

    def test_convert_jsonl_malformed_line(self, test_db):
        # Test with malformed JSON line (should skip bad lines)
        jsonl_data = b'{"id": 1, "name": "Valid"}\n{invalid json}\n{"id": 2, "name": "Also Valid"}'
        table_name = "test_table"

        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Should process valid lines and skip malformed ones
        assert result['row_count'] == 2
        assert result['sample_data'][0]['name'] == 'Valid'
        assert result['sample_data'][1]['name'] == 'Also Valid'

    def test_jsonl_column_name_cleaning(self, test_db):
        # Test column name cleaning in JSONL
        jsonl_data = b'{"User Name": "John", "E-Mail": "john@example.com", "Phone Number": "123-456-7890"}'
        table_name = "test_cleaning"

        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify columns are cleaned
        assert 'user_name' in result['schema']
        assert 'e_mail' in result['schema']
        assert 'phone_number' in result['schema']

    def test_detect_all_jsonl_fields(self, test_assets_dir):
        # Test field detection
        jsonl_file = test_assets_dir / "test_inconsistent.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        fields = detect_all_jsonl_fields(jsonl_data)

        # Should detect all unique fields across all records
        assert 'id' in fields
        assert 'name' in fields
        assert 'field_a' in fields
        assert 'field_b' in fields
        assert 'field_c' in fields
        assert 'field_d' in fields
        assert 'field_e_0' in fields
        assert 'field_e_1' in fields
        assert 'field_e_2' in fields
        assert 'nested__deep__value' in fields