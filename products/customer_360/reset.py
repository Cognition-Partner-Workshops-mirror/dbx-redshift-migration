"""Remove only the approved demo product schema after bundle destruction."""
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState


def main():
    client = WorkspaceClient()
    response = client.statement_execution.execute_statement(
        warehouse_id="6dc4b80538621b7b",
        statement="DROP SCHEMA IF EXISTS demo_redshift.customer_360 CASCADE",
        wait_timeout="50s",
    )
    while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(1)
        response = client.statement_execution.get_statement(response.statement_id)
    if response.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(response.status.as_dict())
    print("Dropped demo_redshift.customer_360 (if present)")


if __name__ == "__main__":
    main()
