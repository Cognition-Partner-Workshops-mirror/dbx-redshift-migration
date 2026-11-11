import os
import subprocess
from pathlib import Path


def test_dry_run_has_no_mutations(tmp_path):
    log = tmp_path / "calls"
    git = tmp_path / "git"
    git.write_text('''#!/bin/sh
echo "git $*" >> "$CALL_LOG"
case "$*" in
  "rev-parse --show-toplevel") echo "$ROOT" ;;
  "rev-parse --verify refs/tags/consumer-cutover-baseline^{commit}") echo abc123 ;;
  "branch --show-current") echo operator ;;
  *) exit 99 ;;
esac
''')
    gh = tmp_path / "gh"
    gh.write_text('''#!/bin/sh
echo "gh $*" >> "$CALL_LOG"
case "$*" in
  "repo view "*) echo owner/repo ;;
  "pr list "*) printf '42\tfeature-cutover\tfalse\n' ;;
  *) exit 99 ;;
esac
''')
    for file in [git, gh]:
        file.chmod(0o755)
    root = Path(__file__).parents[2]
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "CALL_LOG": str(log),
           "ROOT": str(root), "MIG_CATALOG": "demo_redshift"}
    result = subprocess.run(["bash", str(root / "tools/consumer_reset.sh"), "--dry-run"],
                            env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "gh pr close 42" in result.stdout
    assert "git push origin --delete feature-cutover" in result.stdout
    assert "DELETE FROM demo_redshift.consumer_parity.results" in result.stdout
    assert "--force-with-lease" in result.stdout
    assert "push" not in log.read_text()
    assert "pr close" not in log.read_text()
    env["MIG_CATALOG"] = "other_catalog"
    result = subprocess.run(["bash", str(root / "tools/consumer_reset.sh"), "--dry-run"],
                            env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 2
