# History rewrite runbook for privacy incidents

This runbook supports issue #124 and similar cases where the current public tree is clean but private operational metadata remains in reachable Git history.

The goal is narrow: remove private infrastructure metadata from reachable history without deleting the portable, sanitized AI26 runtime code that is valid public research software.

## Safety boundary

Do not put private hostnames, database identifiers, credentials, source lists, IP addresses, paths or replacement rules in this repository, pull requests, issue comments or CI logs.

All sensitive match/replacement material must live in local files outside the clone. If any real credential value is discovered during the audit, rotate or revoke it before continuing with the rewrite.

## 1. Prepare an offline recovery point

Use a fresh mirror clone on a trusted machine:

```bash
git clone --mirror git@github.com:TomiToivio/LaclauGPT-Discourse-Analysis.git laclaugpt-history-rewrite.git
cd laclaugpt-history-rewrite.git
```

Create an offline bundle before changing anything. The helper script also creates one, but making an independent copy is recommended:

```bash
git bundle create ../laclaugpt-before-history-rewrite.bundle --all
```

Keep the bundle private and offline. It intentionally contains the old history and therefore must never be published.

## 2. Build private replacement and audit files

Create two local files outside the repository:

- a `git filter-repo --replace-text` file containing every private literal or regex that must be removed or neutralized;
- an audit-pattern file containing regular expressions that should have zero matches in every reachable revision after rewriting.

The replacement file follows the `git filter-repo` replace-text syntax. Prefer precise literals over broad regexes. Replace private identifiers and deployment paths with generic placeholders rather than deleting portable source files wholesale.

Do not commit either file.

## 3. Run the guarded rewrite

Install `git-filter-repo`, then run:

```bash
I_UNDERSTAND_HISTORY_REWRITE=YES \
AI26_HISTORY_REPLACEMENTS_FILE=/secure/path/replacements.txt \
AI26_HISTORY_AUDIT_PATTERNS_FILE=/secure/path/audit-patterns.txt \
AI26_HISTORY_BACKUP_BUNDLE=/secure/path/laclaugpt-before-rewrite.bundle \
bash /path/to/repository/scripts/rewrite_private_history.sh
```

The helper:

1. refuses to run outside a bare mirror clone;
2. creates a private recovery bundle;
3. rewrites history with `git filter-repo`;
4. scans every reachable revision for the supplied private patterns without printing matching content;
5. clones the rewritten mirror locally and runs the publication-safety guard;
6. stops before pushing.

If any audit match remains, do not push. Refine the local replacement rules and restart from a fresh mirror clone or the private recovery bundle.

## 4. Review a second fresh clone before publication

Before force-pushing, create a separate fresh clone from the rewritten mirror and review it as if it were the public repository:

```bash
git clone --no-local ./laclaugpt-history-rewrite.git ./review-clone
cd ./review-clone
python3 scripts/check_publication_safety.py
pytest -q tests/test_publication_safety.py
```

Also run targeted history searches against all refs using the same private audit patterns. Inspect branches and tags explicitly, not only `main`.

## 5. Publish the rewritten refs

Only after the fresh-clone review passes:

```bash
cd laclaugpt-history-rewrite.git
git push --force --mirror origin
```

Immediately make another fresh clone from GitHub and repeat publication-safety checks and targeted history searches. Confirm that the affected historical commit contents are no longer reachable from public branches or tags.

## 6. Collaborator recovery instructions

A history rewrite changes commit identities. The safest collaborator procedure is to re-clone rather than merge old history back into the cleaned repository.

Recommended message:

> The repository history was rewritten for privacy. Please archive or delete your old clone and make a fresh clone. Do not merge or push old branches back into the rewritten repository. If you have unpublished work, export it as patches or individual clean commits, inspect it for private material, then apply it onto a fresh clone.

If a collaborator must retain local work, prefer `git format-patch` or a carefully reviewed cherry-pick onto a fresh clone. Avoid ordinary merge/rebase operations that can reintroduce the old object graph.

## 7. GitHub caches, forks and external clones

A force-push removes the material from reachable repository history but cannot erase copies that already exist in forks, local clones, mirrors, caches or third-party archives.

After the rewrite:

- inspect public forks and mirrors where practical;
- coordinate with owners of known forks if the affected history is present;
- contact GitHub Support if sensitive historical objects remain retrievable through GitHub after the rewrite;
- treat any actually exposed credential as compromised even if Git history is later cleaned.

## Issue #124 completion criteria

The issue can be closed only when all of the following are true:

- the affected history has been audited across reachable refs;
- no unrotated credential value remains exposed;
- the rewrite has been performed with a private recovery bundle available;
- rewritten branches and tags have been checked in a fresh clone before and after the force-push;
- publication-safety tests pass;
- targeted history searches return no private deployment markers;
- collaborators have received re-clone/recovery guidance;
- cache/fork implications have been reviewed separately.
