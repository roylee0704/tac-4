# Feature: JSONL File Upload Support

## Feature Description
Add support for uploading JSONL (JSON Lines) files to the Natural Language SQL Interface. JSONL files contain one JSON object per line and are commonly used for streaming data, logs, and large datasets. The feature will parse JSONL files to detect all possible fields across all records, flatten nested objects and arrays using configurable delimiters, and create a SQLite table just like the existing CSV and JSON upload functionality. This enables users to query semi-structured and nested data using natural language.

## User Story
As a data analyst
I want to upload JSONL files with nested and semi-structured data
So that I can query complex datasets using natural language without manually preprocessing them

## Problem Statement
Currently, the application only supports CSV and JSON array files. However, many real-world datasets come in JSONL format, which is the standard for streaming data, API logs, and large datasets that don't fit in memory as a single JSON array. Users with JSONL files must either convert them manually or cannot use the application at all. Additionally, nested JSON structures in both JSON and JSONL formats present challenges for relational database storage.

## Solution Statement
Extend the file upload functionality to detect and process JSONL files by reading them line by line, collecting all unique fields across all records, and flattening nested structures using a double-underscore (`__`) delimiter for nested fields and an underscore followed by index (`_0`, `_1`, etc.) for array elements. Store these delimiter configurations in a constants file for easy updates. The solution will reuse the existing upload infrastructure, security patterns, and UI components while adding JSONL-specific parsing logic.

## Relevant Files
Use these files to implement the feature:

**Server-side files:**
- `app/server/core/file_processor.py` - Add `convert_jsonl_to_sqlite()` function and nested data flattening logic
- `app/server/server.py` - Update file upload endpoint to accept `.jsonl` files
- `app/server/core/data_models.py` - No changes needed (existing models support JSONL)

**Client-side files:**
- `app/client/index.html` - Update file upload text to mention `.jsonl` support
- `app/client/src/main.ts` - Update file input accept attribute to include `.jsonl`

**Test files:**
- `app/server/tests/core/test_file_processor.py` - Add comprehensive JSONL tests
- `app/server/tests/assets/` - Create JSONL test files with various structures

### New Files
- `app/server/core/constants.py` - Store delimiter configurations for nested field flattening
- `app/server/tests/assets/test_events.jsonl` - Test file with simple JSONL records
- `app/server/tests/assets/test_nested.jsonl` - Test file with nested objects and arrays
- `app/server/tests/assets/test_complex.jsonl` - Test file with deeply nested structures

## Implementation Plan
### Phase 1: Foundation
Create the constants file for delimiter configurations, implement the nested data flattening utilities, and set up the core JSONL parsing logic. This foundational work will be used by both JSON and JSONL processors.

### Phase 2: Core Implementation
Implement the JSONL file processor that reads files line by line, detects all possible fields by scanning the entire file, flattens nested structures, and converts the data to a SQLite table following existing security patterns.

### Phase 3: Integration
Update the server upload endpoint and client UI to support JSONL files, create comprehensive test files, and validate that all existing functionality remains intact with zero regressions.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Create Constants Module
- Create `app/server/core/constants.py` file
- Define `NESTED_FIELD_DELIMITER = "__"` constant for separating nested object keys
- Define `ARRAY_INDEX_DELIMITER = "_"` constant for array index notation
- Add documentation explaining the delimiter usage with examples
- Add module docstring explaining the purpose and usage patterns

### Implement Field Flattening Utilities
- Add `flatten_dict()` function in `file_processor.py` that recursively flattens nested dictionaries using `NESTED_FIELD_DELIMITER`
- Add `flatten_list()` helper that converts list items to indexed keys (e.g., `items_0`, `items_1`)
- Handle mixed types in arrays by converting all elements to strings for consistency
- Add type checking to handle None, empty objects, and empty arrays gracefully
- Ensure the flattening logic preserves all data without loss
- Add inline documentation explaining the flattening algorithm

### Implement JSONL Field Detection
- Add `detect_all_jsonl_fields()` function that reads entire JSONL file and collects all unique field names
- Parse each line as JSON and collect keys from flattened records
- Return a comprehensive set of all possible fields across all records
- Handle malformed lines gracefully with error logging
- Ensure consistent column ordering for predictable table schemas
- Add progress indication for large files (optional for Phase 1)

### Implement JSONL to SQLite Converter
- Add `convert_jsonl_to_sqlite()` function in `file_processor.py`
- Accept `jsonl_content: bytes` and `table_name: str` parameters
- Use `sanitize_table_name()` to clean the table name
- Call `detect_all_jsonl_fields()` to get complete field list before processing
- Read JSONL line by line, flatten each record, and fill missing fields with None
- Convert data to pandas DataFrame with all detected columns
- Clean column names following existing pattern (lowercase, underscore replacement)
- Use `df.to_sql()` with `if_exists='replace'` to create SQLite table
- Return same structure as existing converters: `{table_name, schema, row_count, sample_data}`
- Apply all SQL security patterns from `sql_security.py`
- Add comprehensive error handling with descriptive messages

### Write Unit Tests for Flattening
- Create test cases for `flatten_dict()` with simple nested objects
- Test deep nesting (3+ levels) with various data types
- Test arrays of primitives, objects, and mixed types
- Test edge cases: empty objects, null values, numeric keys
- Test special characters in keys and ensure they're cleaned
- Verify delimiter usage matches constants
- Test that flattening is reversible for debugging purposes (optional)

### Create JSONL Test Assets
- Create `app/server/tests/assets/test_events.jsonl` with 5 simple event records (id, event_type, timestamp, user_id)
- Create `app/server/tests/assets/test_nested.jsonl` with nested objects (user with address object, preferences object)
- Create `app/server/tests/assets/test_complex.jsonl` with nested arrays and objects (orders with items array, each item has properties)
- Create `app/server/tests/assets/test_inconsistent.jsonl` with varying fields per record
- Ensure test files cover all edge cases: empty lines, malformed JSON, unicode characters

### Write Unit Tests for JSONL Processing
- Add `test_convert_jsonl_to_sqlite_success()` using `test_events.jsonl`
- Add `test_convert_jsonl_nested_objects()` using `test_nested.jsonl`
- Add `test_convert_jsonl_nested_arrays()` using `test_complex.jsonl`
- Add `test_convert_jsonl_inconsistent_fields()` using `test_inconsistent.jsonl`
- Add `test_convert_jsonl_empty_file()` to test error handling
- Add `test_convert_jsonl_malformed_line()` to test robustness
- Add `test_jsonl_column_name_cleaning()` to verify naming conventions
- Verify all tests use mocked database connections like existing tests
- Assert correct schema structure, row counts, and sample data

### Update Server Upload Endpoint
- In `server.py`, update the file type validation to include `.jsonl` extension
- Update the file upload endpoint to check for `.jsonl` extension
- Add conditional logic to call `convert_jsonl_to_sqlite()` for JSONL files
- Ensure existing CSV and JSON functionality remains unchanged
- Add logging for JSONL file uploads
- Update endpoint documentation string to mention JSONL support

### Update Client File Input
- In `app/client/index.html`, update file input `accept` attribute from `.csv,.json` to `.csv,.json,.jsonl`
- Update drop zone text from "Drag and drop .csv or .json files here" to "Drag and drop .csv, .json, or .jsonl files here"
- Ensure no other client-side validation prevents JSONL uploads
- Verify file upload modal displays correctly with updated text

### Update README Documentation
- In `README.md`, update features list to mention JSONL support
- Change "Drag-and-drop file upload (.csv and .json)" to "Drag-and-drop file upload (.csv, .json, and .jsonl)"
- Update usage section to mention JSONL files
- Add note about nested field flattening with delimiter explanation
- Update security section if needed to clarify JSONL parsing security

### Run Test Suite
- Execute `cd app/server && uv run pytest` to run all tests
- Verify all new JSONL tests pass
- Verify all existing CSV and JSON tests still pass
- Check for any regressions in SQL injection tests
- Review test coverage report to ensure new code is adequately tested

### Manual End-to-End Testing
- Start application with `./scripts/start.sh`
- Upload `test_events.jsonl` and verify table creation
- Upload `test_nested.jsonl` and verify nested fields are flattened correctly
- Upload `test_complex.jsonl` and verify array indexing works
- Query uploaded JSONL tables using natural language
- Verify flattened column names are intuitive and queryable
- Test uploading JSONL file with same name twice (should replace)
- Verify error handling for invalid JSONL files
- Test mixed uploads (CSV, JSON, JSONL) to ensure all formats work together

### Security Validation
- Run `cd app/server && uv run pytest tests/test_sql_injection.py -v`
- Verify SQL injection protection applies to JSONL uploads
- Test JSONL files with malicious field names (SQL keywords, special chars)
- Verify `sanitize_table_name()` and `validate_identifier()` work correctly
- Test JSONL files with extremely large records or deeply nested structures
- Ensure file upload size limits prevent DoS attacks
- Verify no code execution risks from parsing arbitrary JSONL content

## Testing Strategy
### Unit Tests
- Test `flatten_dict()` with various nested object structures
- Test `flatten_list()` with arrays of different types
- Test `detect_all_jsonl_fields()` with consistent and inconsistent records
- Test `convert_jsonl_to_sqlite()` with valid and invalid JSONL files
- Test delimiter configuration usage from constants module
- Test error handling for malformed JSONL lines
- Test column name cleaning and sanitization
- Test integration with existing SQL security patterns

### Integration Tests
- Test full upload flow from client to database for JSONL files
- Test querying JSONL-derived tables with natural language
- Test schema retrieval for tables created from JSONL
- Test deleting tables created from JSONL uploads
- Test concurrent uploads of different file types
- Test uploading files with identical names across formats
- Test large JSONL files (1000+ lines) for performance
- Test JSONL files with deeply nested structures (5+ levels)

### Edge Cases
- Empty JSONL file (no lines)
- JSONL file with only blank lines
- JSONL file with one malformed line among valid lines
- JSONL records with completely different field sets
- Nested objects with numeric keys
- Arrays with mixed types (strings, numbers, objects, nulls)
- Unicode characters in field names and values
- Very long field names (100+ characters)
- JSONL file with duplicate field names after flattening
- Fields containing delimiter characters in their names
- Null and undefined values in nested structures
- Empty arrays and empty objects
- JSONL files with inconsistent line endings (LF vs CRLF)

## Acceptance Criteria
- Users can upload JSONL files via drag-and-drop or file browser
- JSONL files are parsed line by line to detect all possible fields
- Nested objects are flattened using `__` delimiter (e.g., `user__address__city`)
- Array elements are indexed using `_` delimiter (e.g., `items_0__name`)
- Delimiters are configurable via constants file for easy updates
- One JSONL file generates exactly one SQLite table
- Tables created from JSONL files work with natural language queries
- File upload UI displays ".csv, .json, or .jsonl" text
- All existing CSV and JSON upload functionality continues to work
- SQL injection protection applies to JSONL uploads
- Error messages are clear when JSONL parsing fails
- Test files exist in `tests/assets/` directory for validation
- All unit and integration tests pass with zero regressions
- README documentation reflects JSONL support

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run all server tests to validate zero regressions
- `cd app/server && uv run pytest tests/core/test_file_processor.py -v` - Run file processor tests with verbose output
- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestFileProcessor::test_convert_jsonl_to_sqlite_success -v` - Run specific JSONL test
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` - Verify SQL injection protection still works
- `./scripts/start.sh` - Start application and manually test:
  - Upload `test_events.jsonl` and verify table creation
  - Upload `test_nested.jsonl` and query nested fields
  - Upload `test_complex.jsonl` and verify array flattening
  - Run natural language queries against JSONL-derived tables
  - Test error handling with malformed JSONL file
  - Verify upload modal shows JSONL in supported formats
  - Delete JSONL-derived tables and verify cleanup
- `cd app/server && uv run python -c "from core.file_processor import flatten_dict; print(flatten_dict({'a': {'b': {'c': 1}}})))"` - Test flattening utility directly
- `cd app/client && npm run build` - Ensure client builds without errors

## Notes
- JSONL format is line-delimited JSON, commonly used for streaming data and log files
- The double-underscore (`__`) delimiter is a common convention in data engineering (e.g., BigQuery, Snowflake)
- Array indexing with `_0` notation is intuitive and prevents naming collisions
- Scanning the entire file first ensures consistent schemas even with inconsistent data
- Consider adding a file size warning for very large JSONL files (100MB+) in future iterations
- Future enhancement: Add option to sample large JSONL files instead of reading all records
- Future enhancement: Support compressed JSONL files (.jsonl.gz)
- Future enhancement: Add UI preview of flattened column names before upload
- The flattening approach prioritizes queryability over preserving original structure
- Users querying nested fields will use flattened names (e.g., "user__email" instead of nested access)
- Consider adding a data dictionary or column metadata to help users understand flattened structures
- JSONL files can be extremely large; consider adding streaming processing for files >100MB
- The delimiter constants can be changed globally, but changing them requires re-uploading existing data
- If a JSONL file has inconsistent schemas, all possible fields are included with NULL for missing values
