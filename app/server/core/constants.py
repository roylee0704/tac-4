"""
Constants for data processing and field flattening.

This module defines configuration constants used throughout the data processing pipeline,
particularly for flattening nested JSON/JSONL structures into flat database schemas.

Usage Patterns:
    - Nested objects: user.address.city → user__address__city
    - Array elements: items[0].name → items_0__name
    - Deep nesting: data.meta.tags[0] → data__meta__tags_0

Example:
    Original nested structure:
    {
        "user": {
            "name": "John",
            "address": {"city": "NYC"}
        },
        "items": [
            {"id": 1, "name": "Apple"},
            {"id": 2, "name": "Orange"}
        ]
    }

    Flattened structure:
    {
        "user__name": "John",
        "user__address__city": "NYC",
        "items_0__id": 1,
        "items_0__name": "Apple",
        "items_1__id": 2,
        "items_1__name": "Orange"
    }
"""

# Delimiter for separating nested object keys in flattened field names
# Used when converting nested dictionaries to flat structures
# Example: {"user": {"email": "test@example.com"}} → "user__email"
NESTED_FIELD_DELIMITER = "__"

# Delimiter for array index notation in flattened field names
# Used when converting array elements to indexed keys
# Example: {"items": [1, 2, 3]} → "items_0", "items_1", "items_2"
ARRAY_INDEX_DELIMITER = "_"
