import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "reporting_service", Path(__file__).parents[2] / "consumers/reporting-api/service.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class Connection:
    description = (("metric",),)

    def __init__(self, rows, fail=False):
        self.rows = rows
        self.fail = fail
        self.closed = 0

    def cursor(self):
        return self

    def execute(self, sql):
        self.sql = sql
        if self.fail:
            raise RuntimeError("connection unavailable")

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed += 1


@pytest.mark.parametrize("path", service.QUERIES)
def test_routes(path):
    connection = Connection([(42,)])
    assert service.fetch(path, lambda: connection) == [{"metric": 42}]
    assert connection.sql == service.QUERIES[path]
    assert connection.closed == 2


def test_empty_and_error():
    assert service.fetch("/health", lambda: Connection([])) == []
    connection = Connection([], fail=True)
    with pytest.raises(RuntimeError):
        service.fetch("/health", lambda: connection)
    assert connection.closed == 2
    with pytest.raises(KeyError):
        service.fetch("/unknown", lambda: connection)
