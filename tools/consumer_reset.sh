#!/usr/bin/env bash
set -euo pipefail
dry_run=false
case "${1:-}" in
  --dry-run) dry_run=true ;;
  "") ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 2 ;;
esac
catalog="${MIG_CATALOG:-demo_redshift}"
[[ "$catalog" == demo_redshift ]] || { echo 'Only demo_redshift is allowed' >&2; exit 2; }
root="$(git rev-parse --show-toplevel)"
cd "$root"
baseline="$(git rev-parse --verify 'refs/tags/consumer-cutover-baseline^{commit}')"
[[ "$(git branch --show-current)" != consumer-cutover ]] || {
  echo 'Switch away from consumer-cutover before resetting it' >&2; exit 2;
}
if ! $dry_run; then
  : "${GH_TOKEN:?GH_TOKEN is required}"
  : "${DATABRICKS_WAREHOUSE_ID:?DATABRICKS_WAREHOUSE_ID is required}"
fi
repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
prs="$(gh pr list --repo "$repo" --base consumer-cutover --state open --limit 1000 \
  --json number,headRefName,isCrossRepository --jq '.[] | [.number, .headRefName, .isCrossRepository] | @tsv')"
execute() {
  printf '%q ' "$@"; printf '\n'
  if ! $dry_run; then "$@"; fi
}
while IFS=$'\t' read -r number head cross; do
  [[ -n "$number" ]] || continue
  [[ "$cross" == false ]] || { echo "Refusing cross-repository PR #$number" >&2; exit 2; }
  case "$head" in main|master|consumer-cutover|migration-run-*|orchestration/*)
    echo "Refusing protected head $head" >&2; exit 2 ;;
  esac
done <<< "$prs"
while IFS=$'\t' read -r number head cross; do
  [[ -n "$number" ]] || continue
  execute gh pr close "$number" --repo "$repo"
  execute git push origin --delete "$head"
done <<< "$prs"
execute git fetch origin consumer-cutover
if $dry_run; then
  echo "git push origin --force-with-lease=refs/heads/consumer-cutover:<fetched-sha> $baseline:refs/heads/consumer-cutover"
else
  remote="$(git rev-parse refs/remotes/origin/consumer-cutover)"
  execute git push origin "--force-with-lease=refs/heads/consumer-cutover:$remote" \
    "$baseline:refs/heads/consumer-cutover"
fi
execute git branch -f consumer-cutover "$baseline"
if $dry_run; then
  echo "DELETE FROM $catalog.consumer_parity.results"
else
  python - <<'PY'
import os
from validation.dbsql import DbSql
DbSql(catalog=os.environ.get("MIG_CATALOG", "demo_redshift")).run(
    "DELETE FROM demo_redshift.consumer_parity.results")
print("consumer_parity.results cleared")
PY
fi
