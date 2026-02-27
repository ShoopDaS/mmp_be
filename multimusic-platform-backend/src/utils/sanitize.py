import re


def sanitize_text(value: str) -> str:
    """
    Strip whitespace, control characters, and HTML tags from a text field.

    Keeps tab (\\x09), newline (\\x0A), and carriage return (\\x0D) so that
    multi-line description values are preserved; all other C0/C1 control
    characters and DEL are removed.
    """
    value = value.strip()
    # Remove control characters (keep \t \n \r)
    value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
    # Strip HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    return value
