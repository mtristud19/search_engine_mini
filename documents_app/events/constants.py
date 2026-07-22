from enum import StrEnum

class DocumentEvents(StrEnum):
    CREATED = "document.created"
    UPDATED = "document.updated"
    DELETED = "document.deleted"