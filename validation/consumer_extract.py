"""Static extraction of named downstream queries; never imports consumer code."""
import ast
import json
import re
import xml.etree.ElementTree as ET


def pythonString(source, name):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                value = ast.literal_eval(node.value)
                if not isinstance(value, str):
                    raise ValueError(f"{name} must be a string literal")
                return value
    raise ValueError(f"string assignment {name!r} not found")


def notebookSource(text, tag):
    cells = [c for c in json.loads(text)["cells"] if tag in c.get("metadata", {}).get("tags", [])]
    if len(cells) != 1:
        raise ValueError(f"expected one notebook cell tagged {tag!r}, found {len(cells)}")
    source = cells[0]["source"]
    return "".join(source) if isinstance(source, list) else source


def extract(text, file, query, path=None):
    """Return a SQL string or file URI selected by the contract locator."""
    suffix = file.rsplit(".", 1)[-1].lower()
    if suffix == "ipynb":
        return pythonString(notebookSource(text, query), path or "query")
    if suffix == "py":
        return pythonString(text, path or query)
    if suffix == "twb":
        nodes = [d for d in ET.fromstring(text).iter("datasource") if d.get("caption") == query]
        if len(nodes) != 1:
            raise ValueError(f"expected one datasource caption {query!r}")
        relations = [r for r in nodes[0].iter("relation") if r.get("type") == "text"]
        if len(relations) != 1:
            raise ValueError("expected one custom SQL relation")
        return relations[0].text or ""
    if suffix == "tmdl":
        if not re.search(r"(?m)^table\s+(?:'" + re.escape(query) + r"'|" + re.escape(query) + r")\s*$", text):
            raise ValueError(f"table {query!r} not found")
        match = re.search(r'Value\.NativeQuery\s*\(\s*[^,]+,\s*"((?:[^"]|"")*)"', text)
        if not match:
            raise ValueError("Value.NativeQuery SQL literal not found")
        return match[1].replace('""', '"').replace("#(lf)", "\n").replace("#(cr)", "\r").replace("#(tab)", "\t")
    if suffix == "sh":
        match = re.search(r"<<-?\s*['\"]?" + re.escape(query) + r"['\"]?\s*\n(.*?)\n" +
                          re.escape(query) + r"\s*(?:\n|$)", text, re.DOTALL)
        if not match:
            raise ValueError(f"heredoc {query!r} not found")
        return match[1] + "\n"
    if suffix == "odc":
        ns = {"odc": "urn:schemas-microsoft-com:office:odc"}
        root = ET.fromstring(text)
        name = root.find(".//odc:Name", ns)
        command = root.find(".//odc:CommandText", ns)
        if name is None or name.text != query or command is None:
            raise ValueError(f"ODC {query!r} not found")
        return command.text or ""
    raise ValueError(f"unsupported consumer file: {file}")


def connectionIsDatabricks(text):
    """Require a migrated connection marker before executing a current query."""
    try:
        notebook = json.loads(text)
    except (ValueError, TypeError):
        notebook = None
    if isinstance(notebook, dict) and "cells" in notebook:
        text = "\n".join("".join(c.get("source", [])) for c in notebook["cells"])
    text = re.sub(r"<!--.*?-->|/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"(?m)^\s*//[^\n]*|--[^\n]*|#[^\n]*", "", text)
    lowered = text.lower()
    markers = ("databricks", "spark", "sql.connect", "sql_connector", "dbsql")
    redshift = (
        r"\bclass\s*=\s*['\"]redshift['\"]",
        r"\bdriver\s*=\s*\{?[^;\n]*redshift",
        r"\bamazonredshift\.database\s*\(",
        r"\b(?:import\s+redshift_connector|from\s+redshift_connector\s+import)\b",
        r"\bredshift_connector\.connect\s*\(",
        r"[\w.-]+\.redshift(?:-serverless)?\.amazonaws\.com\b",
    )
    return any(marker in lowered for marker in markers) and not any(re.search(p, lowered) for p in redshift)
