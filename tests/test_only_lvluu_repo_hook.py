"""The Claude Code guard keeps pushes, PRs and remotes on lvluu/museai, never the fork parent d4ncboz/museai."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).parent.parent / ".claude" / "hooks" / "only-lvluu-repo.py"


def blocked(cmd):
    res = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}),
                         capture_output=True, text=True)
    return res.returncode == 2


@pytest.mark.parametrize("cmd", [
    "gh pr create --fill",
    "gh pr create --base main --title x --body y",
    "gh pr close 7 --repo d4ncboz/museai",
    "gh pr comment 2 -R d4ncboz/museai --body x",
    "git remote add upstream https://github.com/d4ncboz/museai.git",
    "git push upstream main",
])
def test_blocks_the_fork_parent(cmd):
    assert blocked(cmd)


@pytest.mark.parametrize("cmd", [
    "gh pr create --repo lvluu/museai --fill",
    "gh pr create -R lvluu/museai --fill",
    "git push -u origin fix/x",
    "gh pr view 2 --repo d4ncboz/museai",
    "pytest -q",
])
def test_lets_our_repo_through(cmd):
    assert not blocked(cmd)
