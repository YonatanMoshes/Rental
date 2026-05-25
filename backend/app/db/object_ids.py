"""MongoDB ObjectId parsing utilities.

Provides safe conversion from string IDs to MongoDB ObjectIds.
"""

from bson import ObjectId


def parse_object_id(value: str) -> ObjectId | None:
    """Convert a string to ObjectId, or return None if invalid."""
    if not ObjectId.is_valid(value):
        return None
    return ObjectId(value)
