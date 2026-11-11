"""Create or update the "Account Manager Assistant" Genie space from space.json (matched by title)."""

import json
import os
import pathlib

from databricks.sdk import WorkspaceClient

TITLE = "Account Manager Assistant"
DESCRIPTION = "Plain-English questions about customer health and revenue, backed by the certified customer_360 metric views. Data as of 2025-12-31."
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "6dc4b80538621b7b")
SPACE_FILE = pathlib.Path(__file__).with_name("space.json")


def find_space(w: WorkspaceClient) -> str | None:
    token = None
    while True:
        query = {"page_size": 100, **({"page_token": token} if token else {})}
        resp = w.api_client.do("GET", "/api/2.0/genie/spaces", query=query)
        for s in resp.get("spaces", []):
            if s.get("title") == TITLE:
                return s["space_id"]
        token = resp.get("next_page_token")
        if not token:
            return None


def main() -> None:
    w = WorkspaceClient()
    serialized = json.dumps(json.loads(SPACE_FILE.read_text()))
    body = {"title": TITLE, "description": DESCRIPTION, "warehouse_id": WAREHOUSE_ID, "serialized_space": serialized}
    space_id = find_space(w)
    if space_id:
        w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=body)
        print(f"updated {space_id}")
    else:
        parent = f"/Workspace/Users/{w.current_user.me().user_name}/customer_360"
        w.workspace.mkdirs(parent)
        space_id = w.api_client.do("POST", "/api/2.0/genie/spaces", body={**body, "parent_path": parent})["space_id"]
        print(f"created {space_id}")
    w.api_client.do(
        "PATCH",
        f"/api/2.0/permissions/genie/{space_id}",
        body={"access_control_list": [{"group_name": "users", "permission_level": "CAN_RUN"}]},
    )
    print(f"{w.config.host}/genie/rooms/{space_id}")


if __name__ == "__main__":
    main()
