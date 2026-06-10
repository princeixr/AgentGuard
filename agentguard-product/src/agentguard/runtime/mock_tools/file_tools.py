"""Mock file tools."""


def file_search(query: str) -> str:
    return f"found files for query: {query}"


def file_read(path: str) -> str:
    return f"read file: {path}"


def file_summarize(path: str) -> str:
    return f"summarized file: {path}"


def file_write_summary(path: str, summary: str) -> str:
    return f"wrote summary to {path}: {summary}"


def file_delete(path: str) -> str:
    return f"deleted file: {path}"
