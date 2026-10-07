#!/usr/bin/env bash
# Turn a fresh clone of the template into a plugin repo. Run once, on the
# host or in the container, from anywhere inside the clone:
#
#   .devcontainer/init-plugin.sh <name> [<origin-url>]
#
# <name> is the plugin family (directory under plugins/, MKP name):
# lowercase letters, digits and underscores. With <origin-url> the template
# remote is renamed to "template" and <origin-url> becomes "origin".
set -Eeuo pipefail

usage() {
    sed -n '5p' "$0" | sed 's/^#   /usage: /'
    exit 2
}

[[ $# -ge 1 && $# -le 2 ]] || usage
name=$1
origin_url=${2:-}

if [[ ! "$name" =~ ^[a-z][a-z0-9_]*$ ]]; then
    echo "ERROR: '$name' is not a valid plugin name (lowercase letters, digits, underscores)" >&2
    exit 1
fi

cd "$(dirname "$0")/.."

if [[ -e CLAUDE.local.md ]]; then
    echo "ERROR: CLAUDE.local.md exists already, initialized before?" >&2
    exit 1
fi

# Plugin-specific instructions for Claude Code go into CLAUDE.local.md, which
# git ignores; CLAUDE.md stays generic so nothing about the plugin is exposed.
cat >CLAUDE.local.md <<LOCAL
# CLAUDE.local.md - $name

Plugin-specific context for Claude Code. Not tracked by git (see .gitignore):
it only exists on this machine, so keep a copy if it matters.

## Project

CheckMK plugin \`$name\` - TODO: purpose, external system, status.

## Architecture

TODO: data flow (agent / special agent -> sections -> check plugins),
rulesets, graphing.

## Conventions

TODO: naming prefix, section format, state mapping, test data.
LOCAL
echo "Created CLAUDE.local.md (not tracked by git)"

# .gitkeep: an empty directory would not survive the first commit
mkdir -p "plugins/$name" && touch "plugins/$name/.gitkeep"
echo "Created plugins/$name/"

if [[ -n "$origin_url" ]]; then
    if git remote get-url origin >/dev/null 2>&1; then
        if git remote get-url template >/dev/null 2>&1; then
            echo "ERROR: remotes 'origin' and 'template' both exist, set origin by hand" >&2
            exit 1
        fi
        git remote rename origin template
        echo "Remote 'origin' renamed to 'template' (git pull template main for updates)"
    fi
    git remote add origin "$origin_url"
    echo "Remote 'origin' set to $origin_url"
fi

cat <<EOF

Next:
  1. Set EDITION and VARIANT in .devcontainer/devcontainer.json
  2. Describe the plugin in CLAUDE.local.md (private, not committed)
  3. Commit: git add -A && git commit -m "Initialize plugin $name"
  4. VS Code: "Dev Containers: Reopen in Container"
EOF
