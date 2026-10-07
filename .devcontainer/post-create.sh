#!/usr/bin/env bash
# Runs once after the container has been created (postCreateCommand).
set -Eeuo pipefail

OMD_ROOT="${OMD_ROOT:-/omd/sites/cmk}"
WORKSPACE="${WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"

# No symlinks from ~/local to workspace directories here: Checkmk 2.5 copies
# ~/local into a snapshot on every config generation and fails on symlinks to
# directories outside it (IsADirectoryError). Workspace directories the site
# needs are bind mounts in devcontainer.json; temp/ is not linked at all.

# The bind-mounted workspace belongs to the host user, not cmk: without this,
# git refuses to work in it ("detected dubious ownership").
git config --global --add safe.directory "$WORKSPACE"

# Fixed GUI login for local development only: cmkadmin / cmkadmin
set +u
source "$OMD_ROOT/.profile"
set -u
echo 'cmkadmin' | cmk-passwd -i cmkadmin
