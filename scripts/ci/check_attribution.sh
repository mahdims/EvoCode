#!/usr/bin/env bash
#
# Reject commits that attribute authorship to an AI assistant.
#
# Checks the author, the committer, and any Co-authored-by trailers of every
# commit in a range. Run by CI on pull requests; also useful locally:
#
#   scripts/ci/check_attribution.sh                    # commits not on origin/main
#   scripts/ci/check_attribution.sh main..HEAD         # explicit range
#   scripts/ci/check_attribution.sh abc123             # a single commit
#
set -euo pipefail

# Case-insensitive ERE. Add patterns here to reject other assistants.
BANNED='claude|anthropic\.com|noreply@anthropic|copilot@|bot@openai'

RANGE="${1:-}"
if [ -z "$RANGE" ]; then
    base="$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main)"
    RANGE="${base}..HEAD"
fi

# A bare SHA means "just that commit", not a range.
if git rev-parse --quiet --verify "${RANGE}^{commit}" >/dev/null 2>&1; then
    commits="$RANGE"
else
    commits="$(git rev-list "$RANGE")"
fi

if [ -z "$commits" ]; then
    echo "No commits to check in range '${RANGE}'."
    exit 0
fi

failed=0

for sha in $commits; do
    short="$(git rev-parse --short "$sha")"
    subject="$(git show -s --format='%s' "$sha")"
    problems=()

    author="$(git show -s --format='%an <%ae>' "$sha")"
    if printf '%s' "$author" | grep -Eqi "$BANNED"; then
        problems+=("author: ${author}")
    fi

    committer="$(git show -s --format='%cn <%ce>' "$sha")"
    if printf '%s' "$committer" | grep -Eqi "$BANNED"; then
        problems+=("committer: ${committer}")
    fi

    # Any Co-authored-by trailer naming an assistant.
    while IFS= read -r trailer; do
        [ -n "$trailer" ] || continue
        if printf '%s' "$trailer" | grep -Eqi "$BANNED"; then
            problems+=("trailer: ${trailer}")
        fi
    done < <(git show -s --format='%B' "$sha" | grep -Ei '^co-authored-by:' || true)

    if [ ${#problems[@]} -gt 0 ]; then
        failed=1
        echo "FAIL ${short}  ${subject}"
        for p in "${problems[@]}"; do
            echo "       ${p}"
        done
    fi
done

if [ "$failed" -ne 0 ]; then
    cat >&2 <<'MSG'

This repository does not accept AI assistants as commit authors or co-authors.

To fix the most recent commit, delete the offending line from the message:
    git commit --amend
    git push --force-with-lease

For several commits, reword each one:
    git rebase -i <base>        # mark the listed commits as "reword"
    git push --force-with-lease

If the author or committer itself is wrong, correct your identity first:
    git config user.name  "Your Name"
    git config user.email "you@example.com"
    git commit --amend --reset-author

MSG
    exit 1
fi

echo "OK — no AI attribution found in $(echo "$commits" | wc -w | tr -d ' ') commit(s)."
