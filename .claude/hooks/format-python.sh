#!/usr/bin/env bash
# PostToolUse hook: format Python files Claude edited with the pinned
# black/isort from the image, so its changes are CI-clean right away.
# PostToolUse cannot block; exit 2 only shows the error (e.g. a syntax error
# black cannot parse) to Claude. Outside the devcontainer (no black) it does
# nothing.
set -uo pipefail

file=$(jq -r '.tool_input.file_path // empty')
[[ "$file" == *.py && -f "$file" ]] || exit 0
command -v black >/dev/null && command -v isort >/dev/null || exit 0

# pyproject.toml in the project root holds the black/isort settings
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! { isort -q "$file" && black -q "$file"; }; then
    echo "format-python: black/isort failed on $file" >&2
    exit 2
fi
