#!/usr/bin/env bash
set -euo pipefail

# Auto-commit & push on file changes.
# Usage:
#   bash auto_push.sh
#
# Requirements:
#   - git repo with a configured remote (origin)
#   - authentication configured (recommended: SSH key + git@github.com remote)
#   - inotify-tools installed: apt install -y inotify-tools

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH="${AUTO_PUSH_BRANCH:-main}"
DEBOUNCE_SECONDS="${AUTO_PUSH_DEBOUNCE_SECONDS:-2}"

cd "$REPO_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is not installed." >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: $REPO_DIR is not a git repository." >&2
  exit 1
fi

if ! command -v inotifywait >/dev/null 2>&1; then
  echo "ERROR: inotifywait not found. Install: apt install -y inotify-tools" >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: remote 'origin' is not configured." >&2
  exit 1
fi

touch .autopush.lock 2>/dev/null || true

echo "Auto-push is running in: $REPO_DIR"
echo "Remote: $(git remote get-url origin)"
echo "Branch: $BRANCH"

EXCLUDE_REGEX='(^|/)(\.git/|venv/|\.venv/|__pycache__/|instance/|tenants/|\.pytest_cache/|\.mypy_cache/|\.ruff_cache/)'

last_run=0

while true; do
  # Wait for filesystem changes (recursive)
  inotifywait -r -q \
    -e modify,attrib,close_write,move,create,delete \
    --exclude "$EXCLUDE_REGEX" \
    "$REPO_DIR" >/dev/null 2>&1 || true

  # Debounce multiple quick changes
  now="$(date +%s)"
  if (( now - last_run < DEBOUNCE_SECONDS )); then
    sleep "$DEBOUNCE_SECONDS"
  fi
  last_run="$(date +%s)"

  # Skip if nothing to commit
  if [ -z "$(git status --porcelain)" ]; then
    continue
  fi

  # Ensure we are on a branch
  current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  if [ "$current_branch" = "HEAD" ] || [ -z "$current_branch" ]; then
    echo "WARN: detached HEAD, skipping push." >&2
    continue
  fi

  # Stage + commit
  git add -A

  if [ -n "$(git diff --cached --name-only)" ]; then
    msg="auto: sync $(date -Is)"
    git commit -m "$msg" >/dev/null 2>&1 || true
  fi

  # Push (set upstream if needed)
  if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
    git push >/dev/null 2>&1 || {
      echo "ERROR: git push failed." >&2
      exit 1
    }
  else
    git push -u origin "$current_branch" >/dev/null 2>&1 || {
      echo "ERROR: git push -u failed." >&2
      exit 1
    }
  fi

  echo "PUSHED: $(date -Is)"
done

