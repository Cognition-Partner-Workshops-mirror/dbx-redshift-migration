"""Idempotent Genie lifecycle using the default CLI/SDK authentication profile."""
import argparse
import json
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

ROOT = Path(__file__).parent
TITLE = "Account Manager Assistant"
WAREHOUSE = "6dc4b80538621b7b"
DESCRIPTION = "Certified account intelligence as of 2025-12-31: net completed-order revenue, customer profiles, health and revenue at risk."


def find_space(client):
    matches = []
    token = None
    while True:
        page = client.genie.list_spaces(page_token=token)
        matches.extend(s for s in page.spaces or [] if s.title == TITLE)
        token = page.next_page_token
        if not token:
            break
    if len(matches) > 1:
        raise RuntimeError(f"Multiple spaces named {TITLE!r}; refusing ambiguous update/delete")
    return matches[0] if matches else None


def deploy(client):
    payload = json.dumps(json.loads((ROOT / "space.json").read_text()))
    existing = find_space(client)
    settings = {"warehouse_id": WAREHOUSE, "title": TITLE, "description": DESCRIPTION,
                "serialized_space": payload}
    if existing:
        space = client.genie.update_space(existing.space_id, **settings)
    else:
        parent = f"/Workspace/Users/{client.current_user.me().user_name}/customer_360"
        client.workspace.mkdirs(parent)
        space = client.genie.create_space(parent_path=parent, **settings)
    client.permissions.update("genie", space.space_id, access_control_list=[
        AccessControlRequest(group_name="users", permission_level=PermissionLevel.CAN_RUN)
    ])
    (ROOT / ".space_id").write_text(space.space_id + "\n")
    print(f"space_id: {space.space_id}")
    print(f"space_url: {client.config.host}/genie/rooms/{space.space_id}")
    return space.space_id


def delete(client):
    existing = find_space(client)
    if existing:
        client.genie.trash_space(existing.space_id)
        print(f"Trashed Genie space: {existing.space_id}")
    else:
        print("No matching Genie space; nothing to delete")
    (ROOT / ".space_id").unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "delete"])
    args = parser.parse_args()
    {"deploy": deploy, "delete": delete}[args.action](WorkspaceClient())
