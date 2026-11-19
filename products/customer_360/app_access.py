"""Grant the Customer Lookup service principal access to its certified sources."""

import argparse

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import PermissionsChange, Privilege
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

CATALOG = "demo_redshift"
SCHEMA = f"{CATALOG}.customer_360"
SOURCES = ("customer_profile", "customer_health", "order_facts", "customer_health_metrics", "revenue_metrics")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--warehouse-admin-profile", required=True)
    parser.add_argument("--genie-space", required=True)
    args = parser.parse_args()
    workspace = WorkspaceClient()
    principal = workspace.apps.get("customer-lookup").service_principal_client_id
    if not principal:
        raise RuntimeError("Customer Lookup does not have a service principal yet")

    for kind, name, privilege in [
        ("catalog", CATALOG, Privilege.USE_CATALOG),
        ("schema", SCHEMA, Privilege.USE_SCHEMA),
        *(("table", f"{SCHEMA}.{source}", Privilege.SELECT) for source in SOURCES),
    ]:
        workspace.grants.update(kind, name, changes=[PermissionsChange(principal=principal, add=[privilege])])

    workspace.permissions.update("genie", args.genie_space, access_control_list=[
        AccessControlRequest(service_principal_name=principal, permission_level=PermissionLevel.CAN_RUN)
    ])
    warehouse_admin = WorkspaceClient(profile=args.warehouse_admin_profile)
    warehouse_admin.permissions.update("warehouses", args.warehouse, access_control_list=[
        AccessControlRequest(service_principal_name=principal, permission_level=PermissionLevel.CAN_USE)
    ])
    print("Customer Lookup has access to the certified sources, warehouse and Genie space.")


if __name__ == "__main__":
    main()
