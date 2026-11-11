"""Display helpers for free text rendered by Streamlit's Markdown renderer."""
import re


def literal_dollars(value):
    return re.sub(r"(?<!\\)\$", r"\\$", value) if isinstance(value, str) else value
