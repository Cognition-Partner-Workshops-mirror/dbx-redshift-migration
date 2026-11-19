"""Create or update the Account Manager Assistant and verify its canonical questions."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

TITLE = "Account Manager Assistant"
SPACE = Path(__file__).with_name("space.json")


def find_space(workspace):
    token = None
    matches = []
    while True:
        page = workspace.genie.list_spaces(page_size=100, page_token=token)
        matches.extend(space for space in page.spaces or [] if space.title == TITLE)
        token = page.next_page_token
        if not token:
            break
    if len(matches) > 1:
        raise RuntimeError(f"Multiple Genie spaces named {TITLE!r}. Resolve the duplicate before continuing.")
    return matches[0] if matches else None


def configure(workspace, warehouse):
    space = find_space(workspace)
    settings = {
        "title": TITLE,
        "description": "Explore certified customer health and order metrics as of December 31, 2025.",
        "warehouse_id": warehouse,
        "serialized_space": json.dumps(json.loads(SPACE.read_text())),
    }
    if space:
        workspace.genie.update_space(space.space_id, **settings)
    else:
        home = workspace.current_user.me().user_name
        parent = f"/Workspace/Users/{home}/customer-360"
        workspace.workspace.mkdirs(parent)
        space = workspace.genie.create_space(parent_path=parent, **settings)
    workspace.permissions.update(
        "genie", space.space_id,
        access_control_list=[AccessControlRequest(group_name="users", permission_level=PermissionLevel.CAN_RUN)],
    )
    return space.space_id


def verify(workspace, space_id):
    questions = json.loads(SPACE.read_text())["config"]["sample_questions"]

    def check(index):
        question = questions[index]["question"][0]
        message = workspace.genie.start_conversation_and_wait(space_id, question, timeout=timedelta(minutes=3))
        attachment = next((a for a in message.attachments or [] if a.query), None)
        if not attachment:
            raise RuntimeError(f"No SQL attachment for {question}")
        response = workspace.genie.get_message_attachment_query_result(
            space_id, message.conversation_id, message.message_id, attachment.attachment_id
        ).statement_response
        rows = response.result.data_array
        if index == 0:
            correct = bool(rows and rows[0][0] == "SOTH" and Decimal(rows[0][1]) == Decimal("292691.46"))
        elif index == 1:
            correct = bool(rows and {"342", "Emerson", "Silva", "At risk"}.issubset(rows[0]))
        else:
            correct = bool(rows and len(rows) == 6 and any(r[0] == "Champion" and int(r[1]) == 272 for r in rows))
        if not correct or (index != 1 and "MEASURE(" not in attachment.query.query.upper()):
            raise AssertionError(f"Unexpected Genie answer to {question!r}: {rows}")
        return question

    with ThreadPoolExecutor(max_workers=3) as executor:
        for question in executor.map(check, range(3)):
            print(f"Genie verified: {question}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--id", action="store_true")
    args = parser.parse_args()
    workspace = WorkspaceClient()
    if args.id or args.verify:
        space = find_space(workspace)
        if not space:
            parser.error(f"{TITLE} has not been created")
        if args.id:
            print(space.space_id)
        else:
            verify(workspace, space.space_id)
    else:
        print(configure(workspace, args.warehouse))


if __name__ == "__main__":
    main()
