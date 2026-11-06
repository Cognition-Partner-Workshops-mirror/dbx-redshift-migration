# Databricks notebook source
import re
from pathlib import Path

from databricks.sdk.runtime import dbutils, spark

dbutils.widgets.text("catalog", "demo_redshift")
dbutils.widgets.text("sql_file", "")
catalog = dbutils.widgets.get("catalog")
if catalog != "demo_redshift":
    raise ValueError("Only demo_redshift is allowed for this run")
spark.sql(f"USE CATALOG `{catalog}`").collect()


def split_statements(sql):
    tokens = re.compile(
        r"--[^\n]*|/\*.*?\*/|'(?:\\.|''|[^'\\])*'|\"(?:\"\"|[^\"])*\"|"
        r"`(?:``|[^`])*`|\$(?:[A-Za-z_]\w*)?\$|[A-Za-z_]\w*|;|.",
        re.DOTALL,
    )
    parts = list(tokens.finditer(sql))
    depth = 0
    start = 0
    dollar = None
    for index, match in enumerate(parts):
        token = match.group()
        if dollar:
            if token == dollar:
                dollar = None
            continue
        if token.startswith("$"):
            dollar = token
            continue
        word = token.upper()
        following = next((m.group().upper() for m in parts[index + 1:]
                          if not m.group().isspace()), "")
        previous = sql[match.start() - 1:match.start()]
        if previous not in (".",) and word == "BEGIN" and following not in ("TRANSACTION", "WORK", ";", "") or word == "CASE":
            depth += 1
        elif word == "END" and depth and following not in ("IF", "LOOP", "WHILE", "FOR", "REPEAT"):
            depth -= 1
        elif token == ";" and depth == 0:
            yield sql[start:match.start()]
            start = match.end()
    if sql[start:].strip():
        yield sql[start:]


path = Path(dbutils.widgets.get("sql_file"))
for statement in split_statements(path.read_text()):
    if re.sub(r"--[^\n]*|/\*.*?\*/", "", statement, flags=re.DOTALL).strip():
        spark.sql(statement).collect()
print(f"Completed {path.name} in {catalog}")
