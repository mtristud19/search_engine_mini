from enum import StrEnum

class DocumentEvents(StrEnum):
    # Publish routing keys — use publish message
    CREATED = "document.created"
    UPDATED = "document.updated"
    DELETED = "document.deleted"

    # Binding patterns — declare queue binding
    ALL = "document.#"
    ALL_CREATED = "document.created.*"
    ALL_UPDATED = "document.updated.*"
    ALL_DELETED = "document.deleted.*"
    BY_CATEGORY = "document.*.{}"