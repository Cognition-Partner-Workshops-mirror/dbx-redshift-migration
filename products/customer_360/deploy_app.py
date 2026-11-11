"""Reconcile Genie, deploy bundle, grant app UC access, then start the app."""
import argparse
import os
import subprocess
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from genie.manage import deploy, find_space


def grant_access(client, principal):
    if not principal:
        raise RuntimeError("App service principal is not available")
    identifier = "`" + principal.replace("`", "``") + "`"
    for sql in (
        "GRANT USE CATALOG ON CATALOG demo_redshift TO " + identifier,
        "GRANT USE SCHEMA ON SCHEMA demo_redshift.customer_360 TO " + identifier,
        "GRANT SELECT ON SCHEMA demo_redshift.customer_360 TO " + identifier,
    ):
        result = client.statement_execution.execute_statement(
            warehouse_id="6dc4b80538621b7b", statement=sql, wait_timeout="50s")
        deadline = time.monotonic() + 120
        while result.status.state in (StatementState.PENDING, StatementState.RUNNING):
            if time.monotonic() > deadline:
                raise TimeoutError("App permission grant timed out")
            time.sleep(1)
            result = client.statement_execution.get_statement(result.statement_id)
        if result.status.state != StatementState.SUCCEEDED:
            raise RuntimeError(f"App permission grant failed: {result.status.as_dict()}")
    print("Granted app principal USE CATALOG, USE SCHEMA and SELECT on customer_360")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "destroy"])
    parser.add_argument("--target", default="demo")
    parser.add_argument("--profile", default="DEFAULT")
    args = parser.parse_args()
    client = WorkspaceClient(profile=args.profile)
    if args.action == "deploy":
        space_id = deploy(client)
    else:
        space = find_space(client)
        space_id = space.space_id if space else ""
    env = {**os.environ, "BUNDLE_VAR_genie_space_id": space_id}
    command = ["databricks", "bundle", args.action, "-t", args.target, "--profile", args.profile]
    if args.action == "destroy":
        command.append("--auto-approve")
    subprocess.run(command, env=env, check=True)
    if args.action == "deploy":
        grant_access(client, client.apps.get("customer-lookup").service_principal_client_id)
        subprocess.run(["databricks", "bundle", "run", "customer-lookup", "-t", args.target,
                        "--profile", args.profile], env=env, check=True)


if __name__ == "__main__":
    main()
