#!/usr/bin/env bash
set -euo pipefail

# Deliberate history-rewrite helper for issue #124.
#
# This script intentionally contains NO private deployment markers. Supply
# sensitive replacement/audit patterns from local files that are never added to
# Git. Run only from a fresh --mirror clone after maintainer approval.

if [[ "${I_UNDERSTAND_HISTORY_REWRITE:-}" != "YES" ]]; then
  echo "Refusing to rewrite history. Set I_UNDERSTAND_HISTORY_REWRITE=YES after review." >&2
  exit 2
fi

if [[ "$(git rev-parse --is-bare-repository 2>/dev/null || true)" != "true" ]]; then
  echo "Run this only inside a fresh 'git clone --mirror' repository." >&2
  exit 2
fi

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo is required." >&2
  exit 2
fi

REPLACEMENTS_FILE="${AI26_HISTORY_REPLACEMENTS_FILE:-}"
AUDIT_PATTERNS_FILE="${AI26_HISTORY_AUDIT_PATTERNS_FILE:-}"
BACKUP_BUNDLE="${AI26_HISTORY_BACKUP_BUNDLE:-}"

for required in REPLACEMENTS_FILE AUDIT_PATTERNS_FILE BACKUP_BUNDLE; do
  value="${!required:-}"
  if [[ -z "$value" ]]; then
    echo "Missing required environment variable: $required" >&2
    exit 2
  fi
done

if [[ ! -f "$REPLACEMENTS_FILE" ]]; then
  echo "Replacement file not found." >&2
  exit 2
fi
if [[ ! -f "$AUDIT_PATTERNS_FILE" ]]; then
  echo "Audit-pattern file not found." >&2
  exit 2
fi

# Keep the backup outside the repository. Do not publish it.
mkdir -p "$(dirname "$BACKUP_BUNDLE")"
git bundle create "$BACKUP_BUNDLE" --all

echo "Offline recovery bundle created. Starting filter-repo rewrite."
git filter-repo --replace-text "$REPLACEMENTS_FILE" --force

# Audit every reachable commit without printing the private patterns or matching
# lines. Only offending revision IDs are reported.
failed=0
while IFS= read -r pattern || [[ -n "$pattern" ]]; do
  [[ -z "$pattern" || "$pattern" == \#* ]] && continue
  while IFS= read -r rev; do
    if git grep -q -I -E "$pattern" "$rev" -- . 2>/dev/null; then
      echo "History audit failed in reachable revision: $rev" >&2
      failed=1
    fi
  done < <(git rev-list --all)
done < "$AUDIT_PATTERNS_FILE"

if [[ "$failed" -ne 0 ]]; then
  echo "Rewrite did not pass the targeted history audit. Do NOT push." >&2
  exit 1
fi

# Also verify that the current tree passes the repository publication-safety
# guard when a worktree can be checked out from the mirror.
tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

git clone --no-local . "$tmp/review" >/dev/null 2>&1
(
  cd "$tmp/review"
  python3 scripts/check_publication_safety.py
)

echo "Rewrite passed targeted history audit and current-tree publication checks."
echo "Do not push until a second fresh-clone review is complete."
echo "When approved, push from this mirror with: git push --force --mirror origin"
