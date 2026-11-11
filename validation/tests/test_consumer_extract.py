import json

import pytest

from validation.consumer_extract import connectionIsDatabricks, extract


@pytest.mark.parametrize("file,query,text", [
    ("book.twb", "Orders", '<workbook><datasource caption="Orders"><relation type="text">SELECT 1;</relation></datasource></workbook>'),
    ("orders.tmdl", "Orders", 'table Orders\n partition Orders = m\n  source = Value.NativeQuery(Source, "SELECT 1;")'),
    ("service.py", "SQL", 'SQL = "SELECT 1;"'),
    ("job.sh", "SQL", "psql <<'SQL'\nSELECT 1;\nSQL\n"),
    ("book.odc", "Orders", '<root xmlns:odc="urn:schemas-microsoft-com:office:odc"><odc:Name>Orders</odc:Name><odc:CommandText>SELECT 1;</odc:CommandText></root>'),
])
def test_formats(file, query, text):
    assert extract(text, file, query).strip() == "SELECT 1;"
    with pytest.raises(ValueError):
        extract(text, file, "missing")


def test_notebook_sql_and_file():
    text = json.dumps({"cells": [{"metadata": {"tags": ["orders"]}, "source": [
        'query = "SELECT 1;"\n', 'export_path = "/Volumes/demo_redshift/gold/exports/orders.csv"\n']} ]})
    assert extract(text, "orders.ipynb", "orders") == "SELECT 1;"
    assert extract(text, "orders.ipynb", "orders", "export_path").endswith("orders.csv")
    with pytest.raises(ValueError):
        extract(text, "orders.ipynb", "absent")


def test_escaped_m_literal():
    assert extract('table Orders\nValue.NativeQuery(Source, "SELECT ""x""#(lf)FROM t;")',
                   "orders.tmdl", "Orders") == 'SELECT "x"\nFROM t;'


def test_invalid_and_empty():
    with pytest.raises(ValueError):
        extract("", "query.txt", "query")
    with pytest.raises(SyntaxError):
        extract("SQL =", "query.py", "SQL")
    assert extract('SQL = ""', "query.py", "SQL") == ""
    assert connectionIsDatabricks("from databricks import sql")
    assert not connectionIsDatabricks("redshift_connector.connect()")
