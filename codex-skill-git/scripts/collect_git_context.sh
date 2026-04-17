#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Error: not inside a git repository." >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

today="${1:-$(date +%Y-%m-%d)}"
since="${today} 00:00:00"

echo "Repository: $repo_root"
echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Today: $today"
echo
echo "== Status =="
git status --short
echo
echo "== Commits Since Local Midnight =="
git log --since="$since" --date=local --pretty=format:'%h %ad %s' --stat --no-merges || true
echo
echo "== Staged Diff Stat =="
git diff --cached --stat || true
echo
echo "== Unstaged Diff Stat =="
git diff --stat || true
