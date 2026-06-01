#!/bin/bash
set -euo pipefail

# Anchor to clavenar-specs root regardless of CWD.
cd "$(dirname "$0")/.."

MODE="patch"
while [ $# -gt 0 ]; do
    case "$1" in
        --major) MODE="major"; shift ;;
        --minor) MODE="minor"; shift ;;
        --patch) MODE="patch"; shift ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

[ -f VERSION ] || { echo "VERSION file missing" >&2; exit 1; }

old=$(tr -d '[:space:]' < VERSION)
case "$old" in
    [0-9]*.[0-9]*.[0-9]*) ;;
    *) echo "VERSION not semver (got '$old')" >&2; exit 1 ;;
esac

IFS='.' read -r major minor patch <<<"$old"
case "$MODE" in
    major) major=$((major + 1)); minor=0; patch=0 ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    patch) patch=$((patch + 1)) ;;
esac
new="${major}.${minor}.${patch}"

# VERSION is the source of truth for "what version we're on". The
# served version per env lives in clavenar-e2e/<env>/version.json
# and is updated by that env's deploy.sh on a successful
# `compose up -d`. Bumping here doesn't change what visitors see
# until you actually deploy.
printf '%s\n' "$new" > VERSION

git add VERSION
git -c user.name=VanteguardLabs -c user.email=vanteguardlabs@gmail.com \
    commit -m "bump to ${new}"
git push origin main

# Mirror into clavenar-website/public/version.json so a local-dev clone
# of the website (`cd clavenar-website && python -m http.server` etc.)
# shows the bumped version in the footer immediately on next pull —
# without waiting for an env deploy.sh run. The prod / dev compose
# stacks override this with the env-local version.json bind-mount,
# so this file's value is only ever seen outside the deployed stacks.
#
# Sibling repo; do the stage/commit/push in its own subshell so a
# dirty website tree doesn't poison the exit status of the version
# bump itself. The "if file changed" guard means a no-op bump
# (script ran twice, second time same version) doesn't churn the
# website repo's history.
website_dir="../clavenar-website"
if [ -f "${website_dir}/public/version.json" ]; then
    printf '{"version":"%s"}\n' "$new" > "${website_dir}/public/version.json"
    if ! git -C "$website_dir" diff --quiet -- public/version.json; then
        (cd "$website_dir" \
            && git add public/version.json \
            && git -c user.name=VanteguardLabs -c user.email=vanteguardlabs@gmail.com \
                  commit -m "Mirror VERSION ${new} into public/version.json" \
            && git push origin main) \
            || echo "[VERSION] website mirror commit failed (dirty tree?); local file updated" >&2
    fi
fi

echo "[VERSION] ${old} → ${new}"
