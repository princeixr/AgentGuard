"""Mock email tools."""


def gmail_search(query: str) -> str:
    return f"found email threads for query: {query}"


def gmail_read(thread_id: str) -> str:
    return f"read email thread: {thread_id}"


def gmail_draft(to: str, subject: str = "", body: str = "") -> str:
    return f"drafted email to {to} with subject {subject}"


def gmail_send(to: str, subject: str = "", body: str = "") -> str:
    return f"sent email to {to} with subject {subject}"
