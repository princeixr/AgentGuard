"""Mock calendar tools."""


def calendar_search(query: str) -> str:
    return f"found calendar events for query: {query}"


def calendar_read(event_id: str) -> str:
    return f"read calendar event: {event_id}"


def calendar_create_event(title: str, attendee: str | None = None) -> str:
    return f"created event {title} for {attendee or 'self'}"


def calendar_update_event(event_id: str, title: str | None = None) -> str:
    return f"updated event {event_id} title={title}"


def calendar_delete_event(event_id: str) -> str:
    return f"deleted event {event_id}"
